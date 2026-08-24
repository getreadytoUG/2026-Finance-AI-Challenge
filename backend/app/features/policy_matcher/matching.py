from app.features.policy_matcher.schemas import PolicyMatchInput
from app.features.policy_matcher.youth_center_client import RawYouthPolicy

# 온통청년 API의 zipCd는 법정동코드 콤마목록(예: "11110,11140,...")이고, 앞 2자리가
# 시도 코드다. 사용자는 자유 텍스트로 지역을 입력하므로, 흔히 쓰는 표기를 이 2자리
# 코드로 매핑해 zipCd 목록과 대조한다. 2024년 이후 변경된 강원특별자치도(51)/
# 전북특별자치도(52) 코드 반영.
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


def _region_matches(policy_region_code: str, input_region: str) -> bool:
    prefix = _REGION_PREFIXES.get(input_region.strip())
    if prefix is None:
        # 매핑에 없는 표기("서울 강남구" 등)는 잘못 걸러내는 것보다 노출하는 쪽이
        # 안전하므로 필터링하지 않는다.
        return True
    codes = [c.strip() for c in policy_region_code.split(",") if c.strip()]
    return any(code.startswith(prefix) for code in codes)


def is_eligible(policy: RawYouthPolicy, input: PolicyMatchInput) -> bool:
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
    if policy.min_income_krw is not None and input.annual_income_krw < policy.min_income_krw:
        return False
    if policy.max_income_krw is not None and input.annual_income_krw > policy.max_income_krw:
        return False
    if policy.region_code:
        if not input.region or not _region_matches(policy.region_code, input.region):
            return False
    return True
