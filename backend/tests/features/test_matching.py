from app.features.policy_matcher.matching import (
    has_specific_eligibility_condition,
    is_eligible,
    is_likely_template_region_code,
    is_newlywed_policy,
)
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


def test_income_ceiling_uses_combined_household_income_when_spouse_income_given():
    policy = _policy(max_income_krw=50_000_000)
    # 본인 소득만으로는 통과하지만, 배우자 소득을 합치면 상한을 넘는다.
    assert is_eligible(policy, _input(annual_income_krw=40_000_000)) is True
    assert (
        is_eligible(
            policy, _input(annual_income_krw=40_000_000, spouse_annual_income_krw=20_000_000)
        )
        is False
    )


def test_income_floor_uses_combined_household_income_when_spouse_income_given():
    policy = _policy(min_income_krw=50_000_000)
    # 본인 소득만으로는 하한 미달이지만, 배우자 소득을 합치면 통과한다.
    assert is_eligible(policy, _input(annual_income_krw=40_000_000)) is False
    assert (
        is_eligible(
            policy, _input(annual_income_krw=40_000_000, spouse_annual_income_krw=20_000_000)
        )
        is True
    )


def test_has_specific_eligibility_condition_is_false_when_all_four_fields_are_none():
    assert has_specific_eligibility_condition(_policy()) is False


def test_has_specific_eligibility_condition_is_true_when_any_one_field_is_set():
    assert has_specific_eligibility_condition(_policy(min_age=19)) is True
    assert has_specific_eligibility_condition(_policy(max_age=39)) is True
    assert has_specific_eligibility_condition(_policy(min_income_krw=1)) is True
    assert has_specific_eligibility_condition(_policy(max_income_krw=1)) is True


_15_PROVINCE_CODES = ",".join(
    f"{p}110" for p in ("11", "26", "27", "28", "29", "30", "31", "36", "41", "51", "43", "44", "52", "46", "47")
)  # 17개 시도 중 15개


def test_is_likely_template_region_code_is_false_for_empty_region_code():
    assert is_likely_template_region_code(_policy(region_code="")) is False


def test_is_likely_template_region_code_is_false_for_a_single_region():
    assert is_likely_template_region_code(_policy(region_code="11110,11140")) is False


def test_is_likely_template_region_code_is_true_when_15_or_more_provinces_are_covered():
    assert is_likely_template_region_code(_policy(region_code=_15_PROVINCE_CODES)) is True


def test_is_newlywed_policy_matches_keyword_in_name_or_description():
    assert is_newlywed_policy(_policy(policy_name="신혼부부 전세자금 대출이자 지원")) is True
    assert is_newlywed_policy(_policy(description="예비·신혼부부 대상 건강검진 지원")) is True
    assert is_newlywed_policy(_policy(policy_name="청년 전세자금 대출")) is False


def test_is_newlywed_policy_matches_청년부부_and_예비부부_without_신혼():
    assert is_newlywed_policy(_policy(policy_name="청년부부 결혼축하금 지원사업")) is True
    assert is_newlywed_policy(_policy(policy_name="예비부부 건강검진 사업")) is True


def test_is_newlywed_policy_does_not_match_unrelated_결혼_policies():
    # "결혼"만 들어간 정책은 신혼부부와 무관한 경우가 많아(미혼남녀 만남 지원,
    # 결혼이민여성 취업지원 등) 키워드에서 제외했다.
    assert is_newlywed_policy(_policy(policy_name="미혼남녀 만남 지원 프로그램")) is False
    assert is_newlywed_policy(_policy(policy_name="결혼이민여성 취업지원")) is False
