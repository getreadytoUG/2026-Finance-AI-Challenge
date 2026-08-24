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
        policies.append(
            RawYouthPolicy(
                policy_id=item.get("plcyNo") or "",
                policy_name=item.get("plcyNm") or "",
                description=item.get("plcyExplnCn") or "",
                apply_url=item.get("aplyUrlAddr") or "",
                application_period=item.get("aplyYmd") or "상시",
                min_age=_bounded_int_or_none(item.get("sprtTrgtMinAge")),
                max_age=_bounded_int_or_none(item.get("sprtTrgtMaxAge")),
                min_income_krw=_bounded_int_or_none(item.get("earnMinAmt")),
                max_income_krw=_bounded_int_or_none(item.get("earnMaxAmt")),
                marital_status=item.get("mrgSttsCd") or "",
                region_code=item.get("zipCd") or "",
                large_category=item.get("lclsfNm") or "",
                mid_category=item.get("mclsfNm") or "",
                apply_start_ymd=_ymd_or_none(item.get("bizPrdBgngYmd")),
                apply_end_ymd=_ymd_or_none(item.get("bizPrdEndYmd")),
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


def _ymd_or_none(value: str | None) -> str | None:
    # bizPrdBgngYmd/bizPrdEndYmd는 상시/연중 정책이면 공백 8칸("        ")으로 온다.
    if not value:
        return None
    stripped = value.strip()
    return stripped if len(stripped) == 8 and stripped.isdigit() else None


def fetch_all_policies() -> list[RawYouthPolicy]:
    # 실측 결과(2026-08-24) pageSize를 크게 주면 한 번의 요청으로 전체(~2,728건)를
    # 가져올 수 있었다 — 페이지네이션 루프가 필요 없다. totCount가 이 상한을
    # 넘어서면 초과분이 누락되므로 여유 있게 잡는다.
    return fetch_policies(page_num=1, page_size=5000)
