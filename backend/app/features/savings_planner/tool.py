import math

from app.features.savings_planner.schemas import SavingsAllocation, SavingsPlanInput, SavingsPlanOutput
from app.tools.base import ToolContext, ToolSpec


def run(input: SavingsPlanInput, ctx: ToolContext) -> SavingsPlanOutput:
    monthly_required = math.ceil(input.goal_amount_krw / input.goal_months)
    return SavingsPlanOutput(
        allocations=[SavingsAllocation(category="목표 적금 (샘플 배분)", monthly_amount_krw=monthly_required)],
        monthly_required_krw=monthly_required,
    )


TOOL_SPEC = ToolSpec(
    name="savings_planner",
    description="월급과 목표 금액을 기반으로 저축/적금 배분을 설계합니다",
    input_schema=SavingsPlanInput,
    output_schema=SavingsPlanOutput,
    entrypoint=run,
)
