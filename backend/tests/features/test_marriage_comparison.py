import itertools
from datetime import date, datetime, timezone

from app.features.policy_matcher.categories import FINANCIAL_LARGE_CATEGORY
from app.features.policy_matcher.marriage_comparison import build_marriage_scenarios, compare_marriage_scenarios
from app.features.policy_matcher.models import CachedPolicy
from app.features.policy_matcher.schemas import MarriageComparisonInput

_key_seq = itertools.count(1)
_TODAY = date(2026, 8, 31)


def _policy(**overrides) -> CachedPolicy:
    defaults = dict(
        policy_key=f"P{next(_key_seq)}",
        policy_name="테스트 정책",
        description="지원 내용 설명",
        apply_url="https://www.youthcenter.go.kr",
        application_period="상시",
        apply_start_ymd=None,
        apply_end_ymd=None,
        min_age=19,
        max_age=39,
        min_income_krw=None,
        max_income_krw=None,
        marital_status="",
        region_code="",
        large_category=FINANCIAL_LARGE_CATEGORY,
        mid_category="",
        refreshed_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return CachedPolicy(**defaults)


def _input(**overrides) -> MarriageComparisonInput:
    defaults = dict(age=29, region="서울", annual_income_krw=40_000_000, spouse_annual_income_krw=20_000_000)
    defaults.update(overrides)
    return MarriageComparisonInput(**defaults)


def _compare(policies, marriage_input, today=_TODAY):
    unmarried, married = build_marriage_scenarios(marriage_input)
    return compare_marriage_scenarios(policies, unmarried, married, today)


def test_policy_with_ceiling_between_individual_and_household_income_is_unmarried_only():
    # 개인소득(4천만)으론 통과하지만, 배우자 소득(2천만)을 합치면 상한(5천만)을 넘는다.
    policy = _policy(max_income_krw=50_000_000)
    result = _compare([policy], _input())
    assert [p.policy_key for p in result.unmarried_only] == [policy.policy_key]
    assert result.married_only == []
    assert result.both == []


def test_policy_with_floor_between_individual_and_household_income_is_married_only():
    # 개인소득(4천만)만으론 하한(5천만) 미달이지만, 배우자 소득을 합치면 통과한다.
    policy = _policy(min_income_krw=50_000_000)
    result = _compare([policy], _input())
    assert [p.policy_key for p in result.married_only] == [policy.policy_key]
    assert result.unmarried_only == []
    assert result.both == []


def test_policy_eligible_in_both_scenarios_lands_in_both():
    policy = _policy(max_income_krw=100_000_000)
    result = _compare([policy], _input())
    assert [p.policy_key for p in result.both] == [policy.policy_key]
    assert result.married_only == []
    assert result.unmarried_only == []


def test_policy_ineligible_in_both_scenarios_is_excluded_entirely():
    policy = _policy(min_age=50, max_age=60)
    result = _compare([policy], _input())
    assert result.married_only == result.unmarried_only == result.both == []


def test_non_financial_category_policy_is_excluded_entirely():
    policy = _policy(large_category="일자리", max_income_krw=50_000_000)
    result = _compare([policy], _input())
    assert result.married_only == result.unmarried_only == result.both == []


def test_expired_policy_is_excluded_entirely():
    policy = _policy(
        max_income_krw=50_000_000,
        apply_start_ymd="20260101",
        apply_end_ymd="20260101",
    )
    result = _compare([policy], _input())
    assert result.married_only == result.unmarried_only == result.both == []


def test_policy_without_specific_condition_is_excluded_entirely():
    policy = _policy(min_age=None, max_age=None, min_income_krw=None, max_income_krw=None)
    result = _compare([policy], _input())
    assert result.married_only == result.unmarried_only == result.both == []


def test_template_region_policy_is_excluded_entirely():
    fifteen_provinces = ",".join(
        f"{p}110"
        for p in ("11", "26", "27", "28", "29", "30", "31", "36", "41", "51", "43", "44", "52", "46", "47")
    )
    policy = _policy(region_code=fifteen_provinces)
    result = _compare([policy], _input())
    assert result.married_only == result.unmarried_only == result.both == []


def test_scenarios_are_identical_when_spouse_income_is_not_given():
    # is_eligible의 혼인상태 필드 비교는 죽은 코드라(matching.py 참고) 실제로
    # 자격을 바꾸는 건 가구소득 합산뿐이다 — 배우자 소득을 안 넣으면 두 시나리오가
    # 완전히 같아진다는 걸 명시적으로 문서화한다(회귀 방지).
    policy_a = _policy(max_income_krw=50_000_000)
    policy_b = _policy(min_age=50, max_age=60)  # 둘 다에서 탈락
    result = _compare([policy_a, policy_b], _input(spouse_annual_income_krw=None))
    assert result.married_only == []
    assert result.unmarried_only == []
    assert [p.policy_key for p in result.both] == [policy_a.policy_key]
