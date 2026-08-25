from app.features.card_spending_report.tool import TOOL_SPEC as CARD_SPENDING_REPORT_SPEC
from app.features.policy_chat.tool import TOOL_SPEC as POLICY_CHAT_SEARCH_SPEC
from app.features.policy_matcher.tool import TOOL_SPEC as POLICY_MATCHER_SPEC
from app.features.savings_planner.tool import TOOL_SPEC as SAVINGS_PLANNER_SPEC
from app.features.subscription_report.tool import TOOL_SPEC as SUBSCRIPTION_REPORT_SPEC
from app.tools.registry import registry

ALL_TOOL_SPECS = [
    POLICY_MATCHER_SPEC,
    POLICY_CHAT_SEARCH_SPEC,
    SAVINGS_PLANNER_SPEC,
    SUBSCRIPTION_REPORT_SPEC,
    CARD_SPENDING_REPORT_SPEC,
]


def register_all_tools() -> None:
    for spec in ALL_TOOL_SPECS:
        registry.register(spec)
