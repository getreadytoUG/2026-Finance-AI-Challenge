from app.features.policy_matcher.schemas import PolicyMatchInput
from app.features.policy_matcher.youth_center_client import RawYouthPolicy


def is_eligible(policy: RawYouthPolicy, input: PolicyMatchInput) -> bool:
    if policy.min_age is not None and input.age < policy.min_age:
        return False
    if policy.max_age is not None and input.age > policy.max_age:
        return False
    # marital_status는 youth_center_client._parse_youth_policy_xml()이 "기혼"/"미혼"/""로
    # 정규화한다고 가정한다 — 실제 API 코드 체계 확인 시 그쪽과 함께 맞춰야 한다.
    if policy.marital_status == "기혼" and not input.is_married:
        return False
    if policy.marital_status == "미혼" and input.is_married:
        return False
    if policy.min_income_krw is not None and input.annual_income_krw < policy.min_income_krw:
        return False
    if policy.max_income_krw is not None and input.annual_income_krw > policy.max_income_krw:
        return False
    if policy.region_code and (not input.region or (policy.region_code not in input.region and input.region not in policy.region_code)):
        return False
    return True
