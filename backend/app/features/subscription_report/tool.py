from app.features.subscription_report.schemas import (
    SubscriptionItem,
    SubscriptionReportInput,
    SubscriptionReportOutput,
)
from app.tools.base import ToolContext, ToolSpec


def run(input: SubscriptionReportInput, ctx: ToolContext) -> SubscriptionReportOutput:
    items = [
        SubscriptionItem(service_name="Netflix (샘플)", monthly_cost_krw=17_000),
        SubscriptionItem(service_name="YouTube Premium (샘플)", monthly_cost_krw=14_900),
    ]
    return SubscriptionReportOutput(
        month=input.month,
        items=items,
        total_cost_krw=sum(item.monthly_cost_krw for item in items),
    )


TOOL_SPEC = ToolSpec(
    name="subscription_report",
    description="한 달간의 구독 서비스 사용 내역과 총 비용을 리포트합니다",
    input_schema=SubscriptionReportInput,
    output_schema=SubscriptionReportOutput,
    entrypoint=run,
)
