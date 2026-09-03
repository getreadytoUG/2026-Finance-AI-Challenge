import httpx
from pydantic import BaseModel

from app.core.config import settings

# 2026-08-24: 예전 /opi/youthPlcyList.do(XML) 엔드포인트는 실제 운영 환경에서
# 302 -> http://www.youthcenter.go.kr:8080/ 로 리다이렉트되며 죽어있는 것을 확인했다.
# 실제 키로 직접 호출해 검증한 현재 엔드포인트로 교체.
YOUTH_CENTER_API_URL = "https://www.youthcenter.go.kr/go/ythip/getPlcy"


class RawYouthPolicy(BaseModel):
    policy_id: str
    policy_name: str
    description: str
    apply_url: str
    application_period: str
    min_age: int | None
    max_age: int | None
    min_income_krw: int | None
    max_income_krw: int | None
    marital_status: str
    region_code: str
    large_category: str = ""
    mid_category: str = ""
    apply_start_ymd: str | None = None
    apply_end_ymd: str | None = None
    # 2026-09-03 추가: pvsnInstGroupCd(제공기관그룹코드) — matching.py의
    # is_likely_template_region_code 주석 참고.
    institution_group_code: str = ""


def fetch_policies(page_num: int = 1, page_size: int = 100) -> list[RawYouthPolicy]:
    if not settings.youth_center_api_key:
        raise RuntimeError("YOUTH_CENTER_API_KEY is not set — see README '온통청년 API 키 발급'")
    params = {
        "apiKeyNm": settings.youth_center_api_key,
        "pageNum": page_num,
        "pageSize": page_size,
        "pageType": 1,
        "rtnType": "json",
    }
    response = httpx.get(YOUTH_CENTER_API_URL, params=params, timeout=10.0)
    response.raise_for_status()
    return _parse_youth_policy_json(response.json())


# 아래 필드명(plcyNm, plcyExplnCn, sprtTrgtMinAge, mrgSttsCd, zipCd 등)은 실제 API 키로
# 라이브 응답을 받아 확인한 값이다 — 예전 XML 버전의 "미검증" 상태와 달리 실제 검증됨.
# 다만 mrgSttsCd(혼인상태 코드, 예: "0055003")는 온통청년 공통코드 표를 확보하지 못해
# "기혼"/"미혼" 문자열로 정규화하지 못하고 원본 코드값을 그대로 담는다 — matching.py의
# 혼인상태 필터는 현재 이 코드값과 매치되는 경우가 없어 사실상 항상 통과(permissive)한다.
def _parse_youth_policy_json(payload: dict) -> list[RawYouthPolicy]:
    items = payload.get("result", {}).get("youthPolicyList", [])
    policies = []
    for item in items:
        apply_start_ymd, apply_end_ymd = _split_apply_period(item.get("aplyYmd") or "")
        policies.append(
            RawYouthPolicy(
                policy_id=item.get("plcyNo") or "",
                policy_name=item.get("plcyNm") or "",
                description=item.get("plcyExplnCn") or "",
                # aplyUrlAddr(신청 URL)이 비어있는 레코드가 실측 2,730건 중 1,820건
                # (67%)이나 된다 — "자세히 보기"가 href=""로 렌더돼 클릭해도 같은
                # 페이지로 돌아오는 것처럼 보이는 버그의 원인이었다(2026-08-26 발견).
                # refUrlAddr1/2(참고 URL)에 실제로 접근 가능한 링크가 있는 경우가
                # 그중 1,253건이라, 신청 URL이 없으면 참고 URL로 대체한다.
                apply_url=item.get("aplyUrlAddr") or item.get("refUrlAddr1") or item.get("refUrlAddr2") or "",
                application_period=item.get("aplyYmd") or "상시",
                min_age=_bounded_int_or_none(item.get("sprtTrgtMinAge")),
                max_age=_bounded_int_or_none(item.get("sprtTrgtMaxAge")),
                min_income_krw=_bounded_income_krw_or_none(item.get("earnMinAmt")),
                max_income_krw=_bounded_income_krw_or_none(item.get("earnMaxAmt")),
                marital_status=item.get("mrgSttsCd") or "",
                region_code=item.get("zipCd") or "",
                large_category=item.get("lclsfNm") or "",
                mid_category=item.get("mclsfNm") or "",
                apply_start_ymd=apply_start_ymd,
                apply_end_ymd=apply_end_ymd,
                institution_group_code=item.get("pvsnInstGroupCd") or "",
            )
        )
    return policies


def _bounded_int_or_none(value: str | None) -> int | None:
    # 실측 결과 "0"은 실제 0(나이/금액)이 아니라 "제한 없음" sentinel로 쓰인다
    # (예: sprtTrgtAgeLmtYn="Y"인데 sprtTrgtMinAge/MaxAge가 둘 다 "0"인 레코드가 다수).
    # 0을 그대로 하한/상한으로 쓰면 사실상 모든 사용자를 걸러내므로 None(제한 없음)으로 취급한다.
    if not value or not value.isdigit():
        return None
    parsed = int(value)
    return parsed if parsed > 0 else None


# earnMinAmt/earnMaxAmt(소득 조건)만 쓰는 단위 보정 — sprtTrgtMinAge/MaxAge(나이)는
# 단위 문제가 없으므로 위 _bounded_int_or_none을 그대로 쓰고, 소득 필드만 이걸 쓴다.
# 실측 결과(2026-09-03, 실제 API 라이브 호출): 소득 조건이 있는 29건 중 28건이
# "5000"/"3500"/"9999" 같은 1,200~10,000 사이 값이었다 — 실제 청년/신혼부부
# 소득기준(3,600만원~7,000만원대)과 맞춰보면 이건 "원"이 아니라 "만원" 단위다
# ("9999"는 "사실상 상한없음" sentinel로 보인다). 근데 딱 1건("청년부부 주거환경
# 개선사업")만 43,056,240처럼 이미 원 단위 그대로 들어와 있었다 — 정책을 등록하는
# 기관마다 입력 단위가 다른 것으로 보인다(온통청년 쪽에 별도 정규화가 없음).
# 두 케이스가 자릿수 차이가 워낙 커서(만 단위 vs 억 단위) 값 크기로 구분해도
# 안전하다: 100만 미만이면 만원 단위로 보고 10,000을 곱해 원으로 환산하고,
# 그 이상이면 이미 원 단위인 것으로 보고 그대로 쓴다.
_INCOME_MANWON_THRESHOLD = 1_000_000


def _bounded_income_krw_or_none(value: str | None) -> int | None:
    parsed = _bounded_int_or_none(value)
    if parsed is None:
        return None
    return parsed * 10_000 if parsed < _INCOME_MANWON_THRESHOLD else parsed


def _split_apply_period(aply_ymd: str) -> tuple[str | None, str | None]:
    # 상태 배지(임박/여유/상시/예정/만료)는 "신청기간"(aplyYmd) 기준으로 계산해야
    # 한다. bizPrdBgngYmd/bizPrdEndYmd는 "사업기간"(정책 전체 운영기간)이라 신청
    # 마감일과 다른 경우가 흔해서 — 실측 사례로, 신청기간은 이미 끝났는데
    # (aplyYmd="20260501 ~ 20260619") 사업기간은 한참 남아있어서(~20270630)
    # bizPrd* 기준으로 계산하면 "여유"로 잘못 표시됐다. aplyYmd가 "YYYYMMDD ~
    # YYYYMMDD" 형식이 아니면(빈 문자열 등 — 상시/연중) (None, None)을 반환한다.
    if "~" not in aply_ymd:
        return None, None
    start_raw, _, end_raw = aply_ymd.partition("~")
    start = start_raw.strip()
    end = end_raw.strip()
    if len(start) == 8 and start.isdigit() and len(end) == 8 and end.isdigit():
        return start, end
    return None, None


def fetch_all_policies() -> list[RawYouthPolicy]:
    # 실측 결과(2026-08-24) pageSize를 크게 주면 한 번의 요청으로 전체(~2,728건)를
    # 가져올 수 있었다 — 페이지네이션 루프가 필요 없다. totCount가 이 상한을
    # 넘어서면 초과분이 누락되므로 여유 있게 잡는다.
    return fetch_policies(page_num=1, page_size=5000)
