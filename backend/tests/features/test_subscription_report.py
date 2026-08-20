from app.features.subscription_report.schemas import SubscriptionReportInput
from app.features.subscription_report.tool import TOOL_SPEC, run
from app.tools.base import ToolContext


def test_tool_spec_has_expected_name():
    assert TOOL_SPEC.name == "subscription_report"
    assert TOOL_SPEC.entrypoint is run


def test_run_returns_items_and_matching_total():
    ctx = ToolContext(user_id=1, db=None)
    result = run(SubscriptionReportInput(month="2026-07"), ctx)
    assert len(result.items) >= 1
    assert result.total_cost_krw == sum(item.monthly_cost_krw for item in result.items)
