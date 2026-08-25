from app.features.policy_chat import tool
from app.features.policy_chat.schemas import PolicyChatSearchInput
from app.features.policy_chat.tool import TOOL_SPEC, run
from app.features.policy_matcher.categories import FINANCIAL_LARGE_CATEGORY
from app.features.policy_matcher.youth_center_client import RawYouthPolicy
from app.tools.base import ToolContext

CTX = ToolContext(user_id=1, db=None)


def _policy(**overrides) -> RawYouthPolicy:
    defaults = dict(
        policy_id="",
        policy_name="테스트 정책",
        description="지원 내용 설명",
        apply_url="https://www.youthcenter.go.kr",
        application_period="상시",
        min_age=None,
        max_age=None,
        min_income_krw=None,
        max_income_krw=None,
        marital_status="",
        region_code="",
        large_category=FINANCIAL_LARGE_CATEGORY,
    )
    defaults.update(overrides)
    return RawYouthPolicy(**defaults)


def test_tool_spec_has_expected_name():
    assert TOOL_SPEC.name == "policy_chat_search"
    assert TOOL_SPEC.entrypoint is run


def test_run_returns_all_financial_policies_when_no_conditions_given(monkeypatch):
    monkeypatch.setattr(tool, "fetch_all_policies", lambda: [_policy(), _policy(policy_name="다른 정책")])
    result = run(PolicyChatSearchInput(), CTX)
    assert len(result.options) == 2


def test_run_excludes_non_financial_policy(monkeypatch):
    monkeypatch.setattr(tool, "fetch_all_policies", lambda: [_policy(large_category="일자리")])
    result = run(PolicyChatSearchInput(), CTX)
    assert result.options == []


def test_run_filters_by_age_only_when_given(monkeypatch):
    monkeypatch.setattr(tool, "fetch_all_policies", lambda: [_policy(min_age=19, max_age=34)])
    assert len(run(PolicyChatSearchInput(age=50), CTX).options) == 0
    assert len(run(PolicyChatSearchInput(age=25), CTX).options) == 1
    assert len(run(PolicyChatSearchInput(), CTX).options) == 1  # 나이 안 주면 그냥 통과


def test_run_uses_combined_household_income_when_given(monkeypatch):
    monkeypatch.setattr(tool, "fetch_all_policies", lambda: [_policy(max_income_krw=50_000_000)])
    matched = run(
        PolicyChatSearchInput(annual_income_krw=40_000_000, spouse_annual_income_krw=20_000_000), CTX
    )
    assert matched.options == []
    matched = run(PolicyChatSearchInput(annual_income_krw=40_000_000), CTX)
    assert len(matched.options) == 1


def test_run_filters_by_region_only_when_given(monkeypatch):
    monkeypatch.setattr(tool, "fetch_all_policies", lambda: [_policy(region_code="26110")])
    assert run(PolicyChatSearchInput(region="서울"), CTX).options == []
    assert len(run(PolicyChatSearchInput(region="부산"), CTX).options) == 1
    assert len(run(PolicyChatSearchInput(), CTX).options) == 1


def test_run_filters_by_keyword(monkeypatch):
    monkeypatch.setattr(
        tool,
        "fetch_all_policies",
        lambda: [_policy(policy_name="전세자금 대출"), _policy(policy_name="창업 지원금")],
    )
    result = run(PolicyChatSearchInput(keyword="전세"), CTX)
    assert len(result.options) == 1
    assert result.options[0].policy_name == "전세자금 대출"


def test_run_sorts_newlywed_policies_first_when_married(monkeypatch):
    monkeypatch.setattr(
        tool,
        "fetch_all_policies",
        lambda: [_policy(policy_name="일반 대출"), _policy(policy_name="신혼부부 전세자금 대출")],
    )
    result = run(PolicyChatSearchInput(is_married=True), CTX)
    names = [o.policy_name for o in result.options]
    assert names == ["신혼부부 전세자금 대출", "일반 대출"]


def test_run_caps_results_at_max(monkeypatch):
    monkeypatch.setattr(
        tool, "fetch_all_policies", lambda: [_policy(policy_id=str(i), policy_name=f"정책{i}") for i in range(20)]
    )
    result = run(PolicyChatSearchInput(), CTX)
    assert len(result.options) == tool.MAX_RESULTS
