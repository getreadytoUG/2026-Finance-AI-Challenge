from app.features.card_spending_report.schemas import (
    CardSpendingReportInput,
    CardSpendingReportOutput,
    CategorySpending,
)
from app.tools.base import ToolContext, ToolSpec


def run(input: CardSpendingReportInput, ctx: ToolContext) -> CardSpendingReportOutput:
    categories = [
        CategorySpending(category="식비 (샘플)", amount_krw=320_000),
        CategorySpending(category="교통 (샘플)", amount_krw=95_000),
        CategorySpending(category="쇼핑 (샘플)", amount_krw=210_000),
    ]
    return CardSpendingReportOutput(
        month=input.month,
        categories=categories,
        total_amount_krw=sum(c.amount_krw for c in categories),
    )


TOOL_SPEC = ToolSpec(
    name="card_spending_report",
    description="한 달간의 카드 사용 내역을 카테고리별로 분석해 리포트합니다",
    input_schema=CardSpendingReportInput,
    output_schema=CardSpendingReportOutput,
    entrypoint=run,
)
