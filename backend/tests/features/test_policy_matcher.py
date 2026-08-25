import itertools
from datetime import datetime, timezone

from app.features.policy_matcher.categories import FINANCIAL_LARGE_CATEGORY
from app.features.policy_matcher.models import CachedPolicy
from app.features.policy_matcher.schemas import PolicyMatchInput
from app.features.policy_matcher.tool import TOOL_SPEC, run
from app.tools.base import ToolContext

_key_seq = itertools.count(1)


def _seed_policy(db_session, **overrides) -> CachedPolicy:
    defaults = dict(
        policy_key=f"P{next(_key_seq)}",
        policy_name="테스트 정책",
        description="지원 내용 설명",
        apply_url="https://www.youthcenter.go.kr",
        application_period="상시",
        apply_start_ymd=None,
        apply_end_ymd=None,
        min_age=None,
        max_age=None,
        min_income_krw=None,
        max_income_krw=None,
        marital_status="",
        region_code="",
        large_category=FINANCIAL_LARGE_CATEGORY,
        mid_category="취약계층 및 금융지원",
        refreshed_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    row = CachedPolicy(**defaults)
    db_session.add(row)
    db_session.commit()
    return row


def _ctx(db_session) -> ToolContext:
    return ToolContext(user_id=1, db=db_session)


def test_tool_spec_has_expected_name_and_schemas():
    assert TOOL_SPEC.name == "policy_matcher"
    assert TOOL_SPEC.entrypoint is run


def test_run_includes_eligible_financial_policy_without_conditions(db_session):
    _seed_policy(db_session)
    result = run(PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region="서울"), _ctx(db_session))
    assert len(result.options) == 1
    assert result.options[0].policy_name == "테스트 정책"


def test_run_excludes_applicant_outside_age_range(db_session):
    _seed_policy(db_session, min_age=19, max_age=34)
    result = run(PolicyMatchInput(age=50, is_married=False, annual_income_krw=40_000_000, region="서울"), _ctx(db_session))
    assert result.options == []


def test_run_requires_marriage_when_policy_restricts_to_married(db_session):
    _seed_policy(db_session, marital_status="기혼")
    single = run(PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region="서울"), _ctx(db_session))
    married = run(PolicyMatchInput(age=29, is_married=True, annual_income_krw=40_000_000, region="서울"), _ctx(db_session))
    assert single.options == []
    assert len(married.options) == 1


def test_run_excludes_applicant_over_income_ceiling(db_session):
    _seed_policy(db_session, max_income_krw=30_000_000)
    result = run(PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region="서울"), _ctx(db_session))
    assert result.options == []


def test_run_excludes_applicant_below_income_floor(db_session):
    _seed_policy(db_session, min_income_krw=50_000_000)
    result = run(PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region="서울"), _ctx(db_session))
    assert result.options == []


def test_run_excludes_applicant_outside_region(db_session):
    _seed_policy(db_session, region_code="부산")
    result = run(PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region="서울"), _ctx(db_session))
    assert result.options == []


def test_run_includes_applicant_inside_region(db_session):
    _seed_policy(db_session, region_code="11110,11140,26110")
    result = run(PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region="서울"), _ctx(db_session))
    assert len(result.options) == 1


def test_run_excludes_region_restricted_policy_when_input_region_empty(db_session):
    _seed_policy(db_session, region_code="부산")
    result = run(PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region=""), _ctx(db_session))
    assert result.options == []


def test_run_excludes_ineligible_policies_entirely(db_session):
    _seed_policy(db_session, policy_name="부적격 정책", min_age=50)
    _seed_policy(db_session, policy_name="적격 정책")
    result = run(PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region="서울"), _ctx(db_session))
    names = [o.policy_name for o in result.options]
    assert names == ["적격 정책"]


def test_run_excludes_non_financial_policy_even_if_eligible(db_session):
    _seed_policy(db_session, policy_name="일자리 정책", large_category="일자리")
    result = run(PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region="서울"), _ctx(db_session))
    assert result.options == []


def test_run_includes_financial_policy_tagged_with_multiple_large_categories(db_session):
    _seed_policy(db_session, policy_name="복합 태그 정책", large_category=f"일자리,{FINANCIAL_LARGE_CATEGORY}")
    result = run(PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region="서울"), _ctx(db_session))
    assert len(result.options) == 1
    assert result.options[0].policy_name == "복합 태그 정책"


def test_run_sorts_newlywed_policies_first_when_married(db_session):
    _seed_policy(db_session, policy_name="일반 청년 대출")
    _seed_policy(db_session, policy_name="신혼부부 전세자금 대출")
    _seed_policy(db_session, policy_name="또 다른 일반 정책")
    result = run(PolicyMatchInput(age=29, is_married=True, annual_income_krw=40_000_000, region="서울"), _ctx(db_session))
    names = [o.policy_name for o in result.options]
    assert names == ["신혼부부 전세자금 대출", "일반 청년 대출", "또 다른 일반 정책"]


def test_run_does_not_reorder_when_not_married(db_session):
    _seed_policy(db_session, policy_name="일반 청년 대출")
    _seed_policy(db_session, policy_name="신혼부부 전세자금 대출")
    result = run(PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region="서울"), _ctx(db_session))
    names = [o.policy_name for o in result.options]
    assert names == ["일반 청년 대출", "신혼부부 전세자금 대출"]


def test_run_marks_is_newlywed_policy_flag_on_options(db_session):
    _seed_policy(db_session, policy_name="신혼부부 전세자금 대출")
    _seed_policy(db_session, policy_name="일반 청년 대출")
    result = run(PolicyMatchInput(age=29, is_married=True, annual_income_krw=40_000_000, region="서울"), _ctx(db_session))
    flags = {o.policy_name: o.is_newlywed_policy for o in result.options}
    assert flags["신혼부부 전세자금 대출"] is True
    assert flags["일반 청년 대출"] is False


def test_run_uses_combined_household_income_when_spouse_income_given(db_session):
    _seed_policy(db_session, max_income_krw=50_000_000)
    result = run(
        PolicyMatchInput(
            age=29,
            is_married=True,
            annual_income_krw=40_000_000,
            region="서울",
            spouse_annual_income_krw=20_000_000,
        ),
        _ctx(db_session),
    )
    assert result.options == []


def test_run_maps_policy_fields_into_output_option(db_session):
    _seed_policy(
        db_session,
        policy_name="청년 월세 지원",
        description="월 20만원 지원",
        apply_url="https://example.com/apply",
        application_period="2026-01-01 ~ 2026-12-31",
    )
    result = run(PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region="서울"), _ctx(db_session))
    option = result.options[0]
    assert option.policy_name == "청년 월세 지원"
    assert option.benefit_description == "월 20만원 지원"
    assert option.reference_url == "https://example.com/apply"
    assert option.application_period == "2026-01-01 ~ 2026-12-31"
