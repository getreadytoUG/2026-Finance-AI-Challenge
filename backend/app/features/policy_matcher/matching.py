from app.features.policy_matcher.models import CachedPolicy
from app.features.policy_matcher.schemas import PolicyMatchInput

# 온통청년 API의 zipCd는 법정동코드 콤마목록(예: "11110,11140,...")이고, 앞 2자리가
# 시도 코드다. 사용자는 자유 텍스트로 지역을 입력하므로, 흔히 쓰는 표기를 이 2자리
# 코드로 매핑해 zipCd 목록과 대조한다. 2024년 이후 변경된 강원특별자치도(51)/
# 전북특별자치도(52) 코드 반영.
# 프론트가 지역 입력을 자유 텍스트 대신 이 목록에서 고르게 강제한다 —
# "전라도"처럼 매핑에 없는 표기를 입력하면 룰베이스 매칭이 그냥 통과(fail-open)
# 시켜버려서 지역 필터가 사실상 무력화되는 문제를 막는다.
REGIONS: list[str] = [
    "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
    "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주",
]

_REGION_PREFIXES: dict[str, str] = {
    "서울": "11", "서울시": "11", "서울특별시": "11",
    "부산": "26", "부산시": "26", "부산광역시": "26",
    "대구": "27", "대구시": "27", "대구광역시": "27",
    "인천": "28", "인천시": "28", "인천광역시": "28",
    "광주": "29", "광주시": "29", "광주광역시": "29",
    "대전": "30", "대전시": "30", "대전광역시": "30",
    "울산": "31", "울산시": "31", "울산광역시": "31",
    "세종": "36", "세종시": "36", "세종특별자치시": "36",
    "경기": "41", "경기도": "41",
    "강원": "51", "강원도": "51", "강원특별자치도": "51",
    "충북": "43", "충청북도": "43",
    "충남": "44", "충청남도": "44",
    "전북": "52", "전라북도": "52", "전북특별자치도": "52",
    "전남": "46", "전라남도": "46",
    "경북": "47", "경상북도": "47",
    "경남": "48", "경상남도": "48",
    "제주": "50", "제주도": "50", "제주특별자치도": "50",
}


def region_matches(policy_region_code: str, input_region: str) -> bool:
    prefix = _REGION_PREFIXES.get(input_region.strip())
    if prefix is None:
        # 매핑에 없는 표기("서울 강남구" 등)는 잘못 걸러내는 것보다 노출하는 쪽이
        # 안전하므로 필터링하지 않는다.
        return True
    codes = [c.strip() for c in policy_region_code.split(",") if c.strip()]
    return any(code.startswith(prefix) for code in codes)


# 온통청년 API는 나이 무제한을 "0/0"(sprtTrgtMinAge=0, sprtTrgtMaxAge=0) sentinel로
# 표현하는 레코드가 많고(_bounded_int_or_none 참고), 소득 조건도 "학자금 지원구간"
# 같은 별도 등급 체계를 earnEtcCn 자유텍스트로만 주는 경우 earnMinAmt/earnMaxAmt가
# 똑같이 0/0으로 찍힌다 — 결과적으로 min_age/max_age/min_income_krw/max_income_krw가
# 전부 None이 되어 "국가장학금"처럼 사실상 프로필과 무관하게 아무나 통과하는 정책이
# "맞춤 추천"에 계속 섞여 들어온다. 나이·소득 중 하나라도 구조화된 조건이 있는
# 정책만 추천 대상으로 좁혀 이런 "조건 없음" 레코드를 알림에서 제외한다(사용자 요청,
# 2026-08-25). policy_matcher 검색/정책 읽기 탭에는 적용하지 않는다 — 사용자가 직접
# 조건을 넣어 조회하는 흐름이라 "조건 없음" 정책도 결과에 포함되는 게 자연스럽다.
def has_specific_eligibility_condition(policy: CachedPolicy) -> bool:
    return any(
        value is not None
        for value in (policy.min_age, policy.max_age, policy.min_income_krw, policy.max_income_krw)
    )


_ALL_PROVINCE_PREFIXES = frozenset(_REGION_PREFIXES.values())


def _distinct_province_count(region_code: str) -> int:
    codes = [c.strip()[:2] for c in region_code.split(",") if c.strip()]
    return len(set(codes) & _ALL_PROVINCE_PREFIXES)


# 실측 결과(2026-08) zipCd가 채워진 정책 2,728건 중 417건이 정확히 17개 시도 중
# 15개를 커버하는 값으로 뭉쳐 있다 — 그 사이(2~14개)는 8건뿐이라 자연스러운
# 다지역 정책(예: "대구 경북 청년 아카데미" 2개 시도, "고립은둔청년 지원 시범사업"
# 4개 시도)과 뚜렷이 구분된다. 실제로 "울산 동구 청년의 날 기념행사 운영"처럼
# 제목은 특정 구 단위인데 zipCd는 이 15개 시도 패턴으로 찍힌 사례를 확인했다 —
# 진짜 전국 대상 정책은 보통 zipCd를 아예 비워두므로(397건, is_eligible의
# fail-open으로 이미 통과) 이 패턴은 실제 지역 조건이 아니라 지역 필드를 복붙한
# 템플릿/기본값일 뿐이다. 나이·소득의 "0/0" sentinel과 같은 부류의 데이터 결함이라
# has_specific_eligibility_condition과 같은 방식으로 "맞춤 추천"에서만 걸러낸다.
_NATIONWIDE_TEMPLATE_PROVINCE_THRESHOLD = 15


def is_likely_template_region_code(policy: CachedPolicy) -> bool:
    if not policy.region_code:
        return False
    return _distinct_province_count(policy.region_code) >= _NATIONWIDE_TEMPLATE_PROVINCE_THRESHOLD


def is_eligible(policy: CachedPolicy, input: PolicyMatchInput) -> bool:
    if policy.min_age is not None and input.age < policy.min_age:
        return False
    if policy.max_age is not None and input.age > policy.max_age:
        return False
    # marital_status는 youth_center_client가 원본 코드값(예: "0055003")을 그대로 담는다
    # — 온통청년 공통코드 표를 확보하지 못해 "기혼"/"미혼" 문자열과는 매치되지 않는다.
    if policy.marital_status == "기혼" and not input.is_married:
        return False
    if policy.marital_status == "미혼" and input.is_married:
        return False
    # 소득 요건은 개인이 아니라 가구소득 기준인 정책이 많으므로, 배우자 소득이
    # 있으면 합산한 가구소득으로 심사한다.
    household_income = input.annual_income_krw + (input.spouse_annual_income_krw or 0)
    if policy.min_income_krw is not None and household_income < policy.min_income_krw:
        return False
    if policy.max_income_krw is not None and household_income > policy.max_income_krw:
        return False
    if policy.region_code:
        if not input.region or not region_matches(policy.region_code, input.region):
            return False
    return True


# 온통청년 API에는 "신혼부부 대상" 여부를 담는 구조화된 필드가 없다 — 실제 응답의
# 전체 필드를 조사해본 결과(2026-08):
#   - plcyKywdNm(정책 키워드명)은 대출/주거지원/보조금 같은 "혜택 종류" 태그이지
#     대상(신혼부부 등) 태그가 아니다. "신혼부부"가 들어간 정책 69건 중 이 필드에
#     "신혼부부"가 찍힌 건 0건.
#   - mrgSttsCd(혼인상태코드)는 전체 정책의 97%(2,655/2,728)가 "0055003" 하나로
#     쏠려 있고 그 안엔 국가근로장학금처럼 혼인과 무관한 정책도 섞여 있다 — "제한
#     없음" sentinel일 뿐 혼인상태 분류값이 아니다(위 is_eligible 주석 참고).
# 그래서 정책명/설명 텍스트에 신혼부부 관련 키워드가 들어있는지로 판별한다. "결혼"
# 단독 키워드는 오탐이 많아(미혼남녀 만남 프로그램, 결혼이민여성 취업지원 등) 뺐다.
# CachedPolicy는 배치가 주기적으로 갱신하므로, 새 정책이 캐시에 들어오면 이름/설명에
# 아래 키워드가 있는지 그때그때 다시 계산된다 — 별도 코드 수정 필요 없이 자동으로 잡힌다.
NEWLYWED_KEYWORDS = ("신혼", "청년부부", "예비부부")


def is_newlywed_policy(policy: CachedPolicy) -> bool:
    haystack = policy.policy_name + policy.description
    return any(keyword in haystack for keyword in NEWLYWED_KEYWORDS)
