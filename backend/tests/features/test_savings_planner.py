import math
from datetime import datetime, timezone

from app.features.savings_planner.models import SavingsLinkedBenefit
from app.features.savings_planner.schemas import SavingsPlanInput
from app.features.savings_planner.tool import TOOL_SPEC, run
from app.tools.base import ToolContext


def _link_benefit(db_session, user_id: int, amount: int, policy_key: str = "P1") -> SavingsLinkedBenefit:
    row = SavingsLinkedBenefit(
        user_id=user_id,
        policy_key=policy_key,
        policy_name="테스트 정책",
        estimated_monthly_benefit_krw=amount,
        linked_at=datetime.now(timezone.utc),
    )
    db_session.add(row)
    db_session.commit()
    return row


def test_tool_spec_has_expected_name():
    assert TOOL_SPEC.name == "savings_planner"
    assert TOOL_SPEC.entrypoint is run


def test_run_computes_monthly_required_amount(db_session):
    ctx = ToolContext(user_id=1, db=db_session)
    result = run(SavingsPlanInput(monthly_income_krw=3_000_000, goal_amount_krw=12_000_000, goal_months=12), ctx)
    assert result.monthly_required_krw == 1_000_000


def test_run_rounds_up_when_goal_does_not_divide_evenly(db_session):
    ctx = ToolContext(user_id=1, db=db_session)
    result = run(SavingsPlanInput(monthly_income_krw=3_000_000, goal_amount_krw=1_000_000, goal_months=3), ctx)
    assert result.monthly_required_krw == math.ceil(1_000_000 / 3)


def test_run_allocates_full_required_amount_to_savings_category_when_no_linked_benefit(db_session):
    ctx = ToolContext(user_id=1, db=db_session)
    result = run(SavingsPlanInput(monthly_income_krw=3_000_000, goal_amount_krw=6_000_000, goal_months=6), ctx)
    assert result.linked_monthly_benefit_krw == 0
    assert len(result.allocations) == 1
    assert result.allocations[0].category == "직접 저축"
    assert sum(a.monthly_amount_krw for a in result.allocations) == result.monthly_required_krw


def test_run_subtracts_linked_benefit_from_required_amount(db_session):
    _link_benefit(db_session, user_id=1, amount=200_000)
    ctx = ToolContext(user_id=1, db=db_session)
    result = run(SavingsPlanInput(monthly_income_krw=3_000_000, goal_amount_krw=12_000_000, goal_months=12), ctx)

    assert result.linked_monthly_benefit_krw == 200_000
    # 12,000,000 - 200,000*12 = 9,600,000 -> 월 800,000
    assert result.monthly_required_krw == 800_000


def test_run_splits_allocations_into_policy_benefit_and_direct_savings(db_session):
    _link_benefit(db_session, user_id=1, amount=200_000)
    ctx = ToolContext(user_id=1, db=db_session)
    result = run(SavingsPlanInput(monthly_income_krw=3_000_000, goal_amount_krw=12_000_000, goal_months=12), ctx)

    categories = {a.category: a.monthly_amount_krw for a in result.allocations}
    assert categories["정책 혜택 활용"] == 200_000
    assert categories["직접 저축"] == 800_000


def test_run_caps_benefit_allocation_at_naive_monthly_target(db_session):
    # 목표는 월 100만원(1,200만원/12개월)인데 혜택이 월 150만원이면, "정책 혜택
    # 활용" 줄은 실제로 이 목표에 쓰이는 100만원까지만 보여줘야 한다.
    _link_benefit(db_session, user_id=1, amount=1_500_000)
    ctx = ToolContext(user_id=1, db=db_session)
    result = run(SavingsPlanInput(monthly_income_krw=3_000_000, goal_amount_krw=12_000_000, goal_months=12), ctx)

    categories = {a.category: a.monthly_amount_krw for a in result.allocations}
    assert categories["정책 혜택 활용"] == 1_000_000
    assert result.monthly_required_krw == 0
    assert "직접 저축" not in categories or categories["직접 저축"] == 0


def test_run_sets_feasibility_warning_when_required_exceeds_income(db_session):
    ctx = ToolContext(user_id=1, db=db_session)
    result = run(SavingsPlanInput(monthly_income_krw=500_000, goal_amount_krw=12_000_000, goal_months=12), ctx)
    assert result.monthly_required_krw > 500_000
    assert result.feasibility_warning is not None


def test_run_has_no_warning_when_required_amount_is_within_income(db_session):
    ctx = ToolContext(user_id=1, db=db_session)
    result = run(SavingsPlanInput(monthly_income_krw=3_000_000, goal_amount_krw=12_000_000, goal_months=12), ctx)
    assert result.feasibility_warning is None


def test_run_ignores_other_users_linked_benefits(db_session):
    _link_benefit(db_session, user_id=2, amount=200_000)
    ctx = ToolContext(user_id=1, db=db_session)
    result = run(SavingsPlanInput(monthly_income_krw=3_000_000, goal_amount_krw=12_000_000, goal_months=12), ctx)
    assert result.linked_monthly_benefit_krw == 0
    assert result.monthly_required_krw == 1_000_000
