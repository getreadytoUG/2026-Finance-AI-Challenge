from app.features.card_spending_report.schemas import CardSpendingReportInput
from app.features.card_spending_report.tool import TOOL_SPEC, run
from app.tools.base import ToolContext


def test_tool_spec_has_expected_name():
    assert TOOL_SPEC.name == "card_spending_report"
    assert TOOL_SPEC.entrypoint is run


def test_run_returns_categories_and_matching_total():
    ctx = ToolContext(user_id=1, db=None)
    result = run(CardSpendingReportInput(month="2026-07"), ctx)
    assert len(result.categories) >= 1
    assert result.total_amount_krw == sum(c.amount_krw for c in result.categories)
