import math

from app.features.savings_planner.schemas import SavingsPlanInput
from app.features.savings_planner.tool import TOOL_SPEC, run
from app.tools.base import ToolContext


def test_tool_spec_has_expected_name():
    assert TOOL_SPEC.name == "savings_planner"
    assert TOOL_SPEC.entrypoint is run


def test_run_computes_monthly_required_amount():
    ctx = ToolContext(user_id=1, db=None)
    result = run(SavingsPlanInput(monthly_income_krw=3_000_000, goal_amount_krw=12_000_000, goal_months=12), ctx)
    assert result.monthly_required_krw == 1_000_000


def test_run_rounds_up_when_goal_does_not_divide_evenly():
    ctx = ToolContext(user_id=1, db=None)
    result = run(SavingsPlanInput(monthly_income_krw=3_000_000, goal_amount_krw=1_000_000, goal_months=3), ctx)
    assert result.monthly_required_krw == math.ceil(1_000_000 / 3)


def test_run_allocates_full_required_amount_to_savings_category():
    ctx = ToolContext(user_id=1, db=None)
    result = run(SavingsPlanInput(monthly_income_krw=3_000_000, goal_amount_krw=6_000_000, goal_months=6), ctx)
    assert sum(a.monthly_amount_krw for a in result.allocations) == result.monthly_required_krw
