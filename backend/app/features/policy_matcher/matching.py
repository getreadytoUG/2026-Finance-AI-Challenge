from typing import Literal

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

# LLM 도구 호출 스키마(policy_chat)에서 region을 자유 텍스트로 두면 모델이
# "서울시 강남구"처럼 매핑에 없는 표기를 만들어내고, 그게 fail-open으로 조용히
# 필터링 없이 통과해버려 사용자는 "필터가 적용됐다"고 착각하게 된다. REGIONS와
# 반드시 동일하게 유지할 것 — 위 목록이 바뀌면 이것도 같이 바꿔야 한다.
PolicyRegion = Literal[
    "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
    "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주",
]

# 2026-08-26 실측: zipCd에 "12"로 시작하는 코드가 820건(전체 2,730건 중 30%)에서
# 발견됐다 — sprvsnInstCdNm을 온통청년 원본 API에서 직접 까보니 압도적 다수가
# "전남광주통합특별시"(광주광역시+전라남도 통합 이후의 새 광역자치단체명)와 그
# 산하 기관(광양시/순천시/여수시 등)이었다. 광주/전남을 하나로 합친 새 시도가
# 생기면서 부여된 신규 코드로 보인다 — 강원/전북이 특별자치도로 바뀌며 코드가
# 51/52로 바뀐 것(위 REGIONS 주석 참고)과 같은 종류의 변화다. 다만 이번엔 지역
# "이름"이 아니라 지역 "개수"(2개→1개)가 바뀐 셈이라 기존 광주/전남 데이터도
# 완전히 사라지지 않고 섞여 있을 수 있어, 두 이름 모두 새 코드(12)와 각자의
# 옛 코드(29/46)를 함께 매칭하도록 둔다 — 하나만 남기면 아직 옛 코드로 남아있는
# 레코드나 이미 새 코드로 넘어간 레코드 중 한쪽을 못 찾게 된다.
_REGION_PREFIXES: dict[str, tuple[str, ...]] = {
    "서울": ("11",), "서울시": ("11",), "서울특별시": ("11",),
    "부산": ("26",), "부산시": ("26",), "부산광역시": ("26",),
    "대구": ("27",), "대구시": ("27",), "대구광역시": ("27",),
    "인천": ("28",), "인천시": ("28",), "인천광역시": ("28",),
    "광주": ("29", "12"), "광주시": ("29", "12"), "광주광역시": ("29", "12"),
    "대전": ("30",), "대전시": ("30",), "대전광역시": ("30",),
    "울산": ("31",), "울산시": ("31",), "울산광역시": ("31",),
    "세종": ("36",), "세종시": ("36",), "세종특별자치시": ("36",),
    "경기": ("41",), "경기도": ("41",),
    "강원": ("51",), "강원도": ("51",), "강원특별자치도": ("51",),
    "충북": ("43",), "충청북도": ("43",),
    "충남": ("44",), "충청남도": ("44",),
    "전북": ("52",), "전라북도": ("52",), "전북특별자치도": ("52",),
    "전남": ("46", "12"), "전라남도": ("46", "12"),
    "경북": ("47",), "경상북도": ("47",),
    "경남": ("48",), "경상남도": ("48",),
    "제주": ("50",), "제주도": ("50",), "제주특별자치도": ("50",),
}


def region_names_for_prefix(prefix: str) -> list[str]:
    # admin "코드값" 화면(2026-09-03 추가)이 zipCd 접두사별로 REGIONS 중 어디에
    # 매핑되는지 보여줄 때 쓴다 — REGIONS는 별칭("서울시"/"서울특별시" 등) 없이
    # 정식 표기 17개만 담고 있어서, 그 각각의 _REGION_PREFIXES 튜플에 이 접두사가
    # 있는지만 확인하면 별칭 중복 없이 정확히 한 번씩만 나온다.
    return [name for name in REGIONS if prefix in _REGION_PREFIXES.get(name, ())]


def region_matches(policy_region_code: str, input_region: str) -> bool:
    prefixes = _REGION_PREFIXES.get(input_region.strip())
    if prefixes is None:
        # 매핑에 없는 표기("서울 강남구" 등)는 잘못 걸러내는 것보다 노출하는 쪽이
        # 안전하므로 필터링하지 않는다.
        return True
    codes = [c.strip() for c in policy_region_code.split(",") if c.strip()]
    return any(code.startswith(prefix) for code in codes for prefix in prefixes)


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


_ALL_PROVINCE_PREFIXES = frozenset(prefix for prefixes in _REGION_PREFIXES.values() for prefix in prefixes)


def _distinct_province_count(region_code: str) -> int:
    codes = [c.strip()[:2] for c in region_code.split(",") if c.strip()]
    return len(set(codes) & _ALL_PROVINCE_PREFIXES)


# 실측 결과(2026-08) zipCd가 채워진 정책 2,728건 중 417건이 정확히 17개 시도 중
# 15개를 커버하는 값으로 뭉쳐 있다 — 그 사이(2~14개)는 8건뿐이라 자연스러운
# 다지역 정책(예: "대구 경북 청년 아카데미" 2개 시도, "고립은둔청년 지원 시범사업"
# 4개 시도)과 뚜렷이 구분된다. 실제로 "울산 동구 청년의 날 기념행사 운영"처럼
# 제목은 특정 구 단위인데 zipCd는 이 15개 시도 패턴으로 찍힌 사례를 확인했다.
_NATIONWIDE_TEMPLATE_PROVINCE_THRESHOLD = 15

# 2026-09-03: 위 "넓은 지역코드" 패턴이 전부 데이터 결함인 건 아니었다 — "햇살론유스"
# 처럼 서민금융진흥원이 운영하는 진짜 전국 단위 금융 상품도 zipCd에 17개 시도를 다
# 나열해서 같은 패턴으로 찍힌다(사용자 지적: "햇살론유스가 왜 안 나오지?" — 이
# 필터에 잘못 걸려서 빠지고 있었다). 온통청년 공식 코드정의서(pvsnInstGroupCd,
# 제공기관그룹코드)로 실측 교차검증한 결과(2026-09-03, 2,750건 기준):
#   - (중앙부처, 15개 이상 시도) 300건 — 햇살론유스처럼 진짜 전국 상품
#   - (지자체,   15개 이상 시도) 120건 — 서산시/의성군처럼 데이터 입력 실수로
#     보이는 건(같은 정책이 올바른 zipCd로 중복 등록된 사례도 확인됨)
# 지자체가 등록한 정책이 시/도 대부분을 커버하는 건 있을 수 없는 일에 가깝지만,
# 중앙부처가 그러는 건 오히려 정상이다 — 그래서 제공기관이 중앙부처(0054001)로
# 확인된 경우엔 이 필터를 아예 적용하지 않는다. institution_group_code가 아직
# None/빈 값인 기존 캐시 레코드(마이그레이션 직후, 다음 배치 전)는 예전처럼
# 안전한 쪽(지자체로 간주해 필터링)으로 취급한다.
_INSTITUTION_GROUP_CENTRAL = "0054001"


def is_likely_template_region_code(policy: CachedPolicy) -> bool:
    if not policy.region_code:
        return False
    if policy.institution_group_code == _INSTITUTION_GROUP_CENTRAL:
        return False
    return _distinct_province_count(policy.region_code) >= _NATIONWIDE_TEMPLATE_PROVINCE_THRESHOLD


# 2026-09-03: 온통청년 공식 "API코드정보.xlsx" 코드정의서(오픈API 소개 페이지의
# "코드정의서 다운로드" 링크, /downloadform/API코드정보.xlsx)를 직접 받아 확인한
# mrgSttsCd(결혼상태코드, 코드그룹 0055)의 실제 뜻이다 — 그동안 "기혼"/"미혼"이라는
# 사람이 읽는 문자열과 비교하고 있었는데, 실제 저장되는 값은 이 코드였다(아래 참고).
# 라이브 조회(2026-09-03, 2,750건)로 세 값 다 실제로 쓰이는 걸 확인했다:
#   0055001 기혼    48건
#   0055002 미혼    23건
#   0055003 제한없음 2,677건 (그 외 나머지 정책은 이 필드가 빈 문자열)
MARITAL_STATUS_CODE_MARRIED = "0055001"
MARITAL_STATUS_CODE_UNMARRIED = "0055002"
MARITAL_STATUS_CODE_UNRESTRICTED = "0055003"
MARITAL_STATUS_LABELS: dict[str, str] = {
    MARITAL_STATUS_CODE_MARRIED: "기혼",
    MARITAL_STATUS_CODE_UNMARRIED: "미혼",
    MARITAL_STATUS_CODE_UNRESTRICTED: "제한없음",
}


def is_married_only_policy(policy: CachedPolicy) -> bool:
    return policy.marital_status == MARITAL_STATUS_CODE_MARRIED


def is_unmarried_only_policy(policy: CachedPolicy) -> bool:
    return policy.marital_status == MARITAL_STATUS_CODE_UNMARRIED


# is_eligible()과 policy_chat/tool.py의 _matches()가 나이/소득 조건을 똑같이 비교하는
# 코드를 각자 복붙해 갖고 있었다(사용자 지적, 2026-09-03 "필터링이 다 꼬여있다") —
# 여기로 합쳐서 두 곳이 항상 같은 로직을 쓰게 한다. 두 호출부의 차이는 "값이
# 없을 때 어떻게 하느냐"뿐이라 그것만 파라미터(age/annual_income_krw를 Optional로)로
# 흡수한다: is_eligible은 항상 값이 있는 PolicyMatchInput을 넘기고, _matches는
# 대화에서 아직 언급 안 된 조건에 None을 넘겨 "그 조건은 안 본다"는 뜻으로 쓴다.
def age_matches(policy: CachedPolicy, age: int | None) -> bool:
    if age is None:
        return True
    if policy.min_age is not None and age < policy.min_age:
        return False
    if policy.max_age is not None and age > policy.max_age:
        return False
    return True


def income_matches(
    policy: CachedPolicy, annual_income_krw: int | None, spouse_annual_income_krw: int | None = None
) -> bool:
    if annual_income_krw is None:
        return True
    # 소득 요건은 개인이 아니라 가구소득 기준인 정책이 많으므로, 배우자 소득이
    # 있으면 합산한 가구소득으로 심사한다.
    household_income = annual_income_krw + (spouse_annual_income_krw or 0)
    if policy.min_income_krw is not None and household_income < policy.min_income_krw:
        return False
    if policy.max_income_krw is not None and household_income > policy.max_income_krw:
        return False
    return True


def is_eligible(policy: CachedPolicy, input: PolicyMatchInput) -> bool:
    if not age_matches(policy, input.age):
        return False
    if is_married_only_policy(policy) and not input.is_married:
        return False
    if is_unmarried_only_policy(policy) and input.is_married:
        return False
    if not income_matches(policy, input.annual_income_krw, input.spouse_annual_income_krw):
        return False
    if policy.region_code:
        if not input.region or not region_matches(policy.region_code, input.region):
            return False
    # 장애인/국가보훈대상자 전용 정책은 명시적으로 "아님"(False)이라고 답한 사용자
    # 에게만 걸러낸다 — 값을 아직 입력하지 않은 기존 유저(None)는 다른 확장
    # 필드들과 동일하게 fail-open으로 계속 노출한다(하위 호환).
    if is_disability_targeted_policy(policy) and input.has_disability is False:
        return False
    if is_veteran_targeted_policy(policy) and input.is_veteran is False:
        return False
    return True


# 온통청년 API에는 "신혼부부 대상" 여부를 담는 구조화된 필드가 없다 — 실제 응답의
# 전체 필드를 조사해본 결과(2026-08):
#   - plcyKywdNm(정책 키워드명)은 대출/주거지원/보조금 같은 "혜택 종류" 태그이지
#     대상(신혼부부 등) 태그가 아니다. "신혼부부"가 들어간 정책 69건 중 이 필드에
#     "신혼부부"가 찍힌 건 0건.
#   - mrgSttsCd(혼인상태코드)는 기혼/미혼 둘로만 나뉘고(위 MARITAL_STATUS_LABELS
#     참고) "신혼부부"라는 별도 값이 없다 — 대부분(97%)은 "제한없음"이라 국가근로
#     장학금처럼 혼인과 무관한 정책도 여기 섞여 있다.
# 그래서 정책명/설명 텍스트에 신혼부부 관련 키워드가 들어있는지로 판별한다. "결혼"
# 단독 키워드는 오탐이 많아(미혼남녀 만남 프로그램, 결혼이민여성 취업지원 등) 뺐다.
# CachedPolicy는 배치가 주기적으로 갱신하므로, 새 정책이 캐시에 들어오면 이름/설명에
# 아래 키워드가 있는지 그때그때 다시 계산된다 — 별도 코드 수정 필요 없이 자동으로 잡힌다.
NEWLYWED_KEYWORDS = ("신혼", "청년부부", "예비부부")


def is_newlywed_policy(policy: CachedPolicy) -> bool:
    haystack = policy.policy_name + policy.description
    return any(keyword in haystack for keyword in NEWLYWED_KEYWORDS)


# 온통청년 API에는 신혼부부와 마찬가지로 "장애인 대상"/"국가보훈대상자 대상" 여부를
# 담는 구조화된 필드가 없다(youth_center_client.py의 RawYouthPolicy 필드 목록 참고 —
# 지원대상 관련 필드는 min/max_age, marital_status, region_code뿐). 그래서 신혼부부
# 판별과 비슷하게 키워드로 판별하되, **정책명(title)만** 본다 — is_newlywed_policy와
# 달리 description은 넣지 않는다. 실제 캐시 데이터로 검증해보니(2026-09-02) description
# 까지 포함하면 "저소득 서민, 청년, 신혼부부, 장애인, 국가유공자 등 주거취약계층"처럼
# 여러 대상 집단을 나열하는 설명문에 걸려, 장애인/보훈대상자 "전용"이 아니라 청년
# 일반도 받을 수 있는 정책(통합공공임대주택 등)까지 잘못 걸러내는 오탐이 실측됐다.
# 반면 정책명 자체에 이 키워드가 박혀있는 정책("경계선지능청년지원", "제대군인
# 직업능력개발훈련" 등)은 실제로 그 집단 전용인 경우가 실측 전수조사에서 전부
# 맞았다. "일반" 병기 정책(예: "평생교육이용권[일반·장애인] 지원")은 장애인
# 전용이 아니라 일반인도 받을 수 있다는 뜻이라 별도로 제외한다.
# "경계성 지능"(구 경계선지능)은 법적 장애 등급은 아니지만 실제 온통청년 정책들이
# 장애인과 함께 지원대상으로 묶어 쓰는 표현이라 포함한다(사용자 요청, 2026-09-02).
# "장애" 단독 키워드는 "장애물없는" 등 오탐이 있어(신혼부부의 "결혼" 단독 제외와
# 동일한 이유) 넣지 않았다.
DISABILITY_KEYWORDS = ("장애인", "경계성지능", "경계선지능", "경계지능", "경계성 지능", "경계선 지능")
VETERAN_KEYWORDS = ("보훈대상자", "국가유공자", "보훈보상대상자", "제대군인", "국가보훈")


def is_disability_targeted_policy(policy: CachedPolicy) -> bool:
    if "일반" in policy.policy_name:
        return False
    return any(keyword in policy.policy_name for keyword in DISABILITY_KEYWORDS)


def is_veteran_targeted_policy(policy: CachedPolicy) -> bool:
    if "일반" in policy.policy_name:
        return False
    return any(keyword in policy.policy_name for keyword in VETERAN_KEYWORDS)


# 2026-09-02 추가: 저축플랜 시뮬레이터가 "청년도약계좌" 하나로 고정된 예시 대신,
# 실제 캐시에 있는 저축/자산형성형 정책을 찾아 보여주기 위한 판별자
# (savings_simulator/simulator.py의 match_real_savings_policies 참고). 위
# is_disability_targeted_policy 등과 동일하게 정책명만 본다 — 실측 결과(2026-09-02)
# 이 키워드들은 설명문까지 봐도 오탐이 딱히 없었지만, 다른 대상군 필터들과의 일관성을
# 위해 정책명 기준으로 통일한다.
SAVINGS_ACCOUNT_KEYWORDS = ("저축계좌", "적금", "통장", "자산형성", "재형저축", "내일채움공제")


def is_savings_account_policy(policy: CachedPolicy) -> bool:
    return any(keyword in policy.policy_name for keyword in SAVINGS_ACCOUNT_KEYWORDS)
