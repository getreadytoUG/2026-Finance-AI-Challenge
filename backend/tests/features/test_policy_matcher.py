from app.features.policy_matcher.schemas import PolicyMatchInput
from app.features.policy_matcher.tool import TOOL_SPEC, run
from app.tools.base import ToolContext


def test_tool_spec_has_expected_name_and_schemas():
    assert TOOL_SPEC.name == "policy_matcher"
    assert TOOL_SPEC.entrypoint is run


def test_run_marks_young_applicant_eligible():
    ctx = ToolContext(user_id=1, db=None)
    result = run(PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region="서울"), ctx)
    assert len(result.options) >= 1
    assert result.options[0].eligible is True


def test_run_marks_over_age_applicant_ineligible():
    ctx = ToolContext(user_id=1, db=None)
    result = run(PolicyMatchInput(age=50, is_married=False, annual_income_krw=40_000_000, region="서울"), ctx)
    assert result.options[0].eligible is False


def test_run_gives_married_applicant_better_rate():
    ctx = ToolContext(user_id=1, db=None)
    married = run(PolicyMatchInput(age=29, is_married=True, annual_income_krw=40_000_000, region="서울"), ctx)
    single = run(PolicyMatchInput(age=29, is_married=False, annual_income_krw=40_000_000, region="서울"), ctx)
    assert married.options[0].preferential_rate_percent < single.options[0].preferential_rate_percent
