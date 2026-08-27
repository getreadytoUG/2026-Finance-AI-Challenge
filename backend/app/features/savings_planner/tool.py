import math

from app.features.savings_planner.models import SavingsLinkedBenefit
from app.features.savings_planner.schemas import SavingsAllocation, SavingsPlanInput, SavingsPlanOutput
from app.tools.base import ToolContext, ToolSpec


def run(input: SavingsPlanInput, ctx: ToolContext) -> SavingsPlanOutput:
    linked_rows = ctx.db.query(SavingsLinkedBenefit).filter(SavingsLinkedBenefit.user_id == ctx.user_id).all()
    linked_monthly_benefit = sum(row.estimated_monthly_benefit_krw for row in linked_rows)

    naive_monthly_target = math.ceil(input.goal_amount_krw / input.goal_months)
    goal_net = max(0, input.goal_amount_krw - linked_monthly_benefit * input.goal_months)
    monthly_required = math.ceil(goal_net / input.goal_months)

    allocations = []
    # 정책 혜택이 목표 대비 과해도(예: 목표는 월 100만원인데 혜택이 월 150만원)
    # 이 목표에 실제로 쓰이는 만큼만 "정책 혜택 활용"에 표시한다 — 초과분까지
    # 보여주면 이 목표에 다 들어가는 것처럼 오해를 줄 수 있다.
    benefit_allocation = min(linked_monthly_benefit, naive_monthly_target)
    if benefit_allocation > 0:
        allocations.append(SavingsAllocation(category="정책 혜택 활용", monthly_amount_krw=benefit_allocation))
    allocations.append(SavingsAllocation(category="직접 저축", monthly_amount_krw=monthly_required))

    warning = None
    if monthly_required > input.monthly_income_krw:
        warning = "월 저축 필요액이 입력한 월급을 초과합니다. 목표 금액이나 기간을 조정해보세요."

    return SavingsPlanOutput(
        allocations=allocations,
        monthly_required_krw=monthly_required,
        linked_monthly_benefit_krw=linked_monthly_benefit,
        feasibility_warning=warning,
    )


TOOL_SPEC = ToolSpec(
    name="savings_planner",
    description="월급과 목표 금액을 기반으로 저축/적금 배분을 설계합니다",
    input_schema=SavingsPlanInput,
    output_schema=SavingsPlanOutput,
    entrypoint=run,
)
