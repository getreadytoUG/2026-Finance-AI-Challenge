from app.features.policy_matcher.matching import is_eligible
from app.features.policy_matcher.schemas import PolicyMatchInput
from app.features.policy_matcher.youth_center_client import RawYouthPolicy


def _policy(**overrides) -> RawYouthPolicy:
    defaults = dict(
        policy_id="",
        policy_name="테스트 정책",
        description="지원 내용 설명",
        apply_url="https://www.youthcenter.go.kr",
        application_period="상시",
        min_age=None,
        max_age=None,
        min_income_krw=None,
        max_income_krw=None,
        marital_status="",
        region_code="",
    )
    defaults.update(overrides)
    return RawYouthPolicy(**defaults)


def _input(**overrides) -> PolicyMatchInput:
    defaults = dict(age=29, is_married=False, annual_income_krw=40_000_000, region="서울")
    defaults.update(overrides)
    return PolicyMatchInput(**defaults)


def test_policy_without_conditions_is_always_eligible():
    assert is_eligible(_policy(), _input()) is True


def test_applicant_outside_age_range_is_ineligible():
    assert is_eligible(_policy(min_age=19, max_age=34), _input(age=50)) is False


def test_marriage_requirement_is_enforced_both_ways():
    policy = _policy(marital_status="기혼")
    assert is_eligible(policy, _input(is_married=False)) is False
    assert is_eligible(policy, _input(is_married=True)) is True


def test_income_ceiling_is_enforced():
    assert is_eligible(_policy(max_income_krw=30_000_000), _input(annual_income_krw=40_000_000)) is False


def test_income_floor_is_enforced():
    assert is_eligible(_policy(min_income_krw=50_000_000), _input(annual_income_krw=40_000_000)) is False


def test_region_restricted_policy_is_ineligible_outside_region():
    assert is_eligible(_policy(region_code="부산"), _input(region="서울")) is False


def test_region_restricted_policy_is_ineligible_when_input_region_empty():
    assert is_eligible(_policy(region_code="부산"), _input(region="")) is False
