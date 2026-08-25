import itertools
from datetime import datetime, timezone

from app.features.policy_chat import tool
from app.features.policy_chat.schemas import PolicyChatSearchInput
from app.features.policy_chat.tool import TOOL_SPEC, run
from app.features.policy_matcher.categories import FINANCIAL_LARGE_CATEGORY
from app.features.policy_matcher.models import CachedPolicy
from app.tools.base import ToolContext

_key_seq = itertools.count(1)


def _seed_policy(db_session, **overrides) -> CachedPolicy:
    defaults = dict(
        policy_key=f"P{next(_key_seq)}",
        policy_name="테스트 정책",
        description="지원 내용 설명",
        apply_url="https://www.youthcenter.go.kr",
        application_period="상시",
        apply_start_ymd=None,
        apply_end_ymd=None,
        min_age=None,
        max_age=None,
        min_income_krw=None,
        max_income_krw=None,
        marital_status="",
        region_code="",
        large_category=FINANCIAL_LARGE_CATEGORY,
        mid_category="취약계층 및 금융지원",
        refreshed_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    row = CachedPolicy(**defaults)
    db_session.add(row)
    db_session.commit()
    return row


def _ctx(db_session) -> ToolContext:
    return ToolContext(user_id=1, db=db_session)


def test_tool_spec_has_expected_name():
    assert TOOL_SPEC.name == "policy_chat_search"
    assert TOOL_SPEC.entrypoint is run


def test_run_returns_all_financial_policies_when_no_conditions_given(db_session):
    _seed_policy(db_session)
    _seed_policy(db_session, policy_name="다른 정책")
    result = run(PolicyChatSearchInput(), _ctx(db_session))
    assert len(result.options) == 2


def test_run_excludes_non_financial_policy(db_session):
    _seed_policy(db_session, large_category="일자리")
    result = run(PolicyChatSearchInput(), _ctx(db_session))
    assert result.options == []


def test_run_filters_by_age_only_when_given(db_session):
    _seed_policy(db_session, min_age=19, max_age=34)
    assert len(run(PolicyChatSearchInput(age=50), _ctx(db_session)).options) == 0
    assert len(run(PolicyChatSearchInput(age=25), _ctx(db_session)).options) == 1
    assert len(run(PolicyChatSearchInput(), _ctx(db_session)).options) == 1  # 나이 안 주면 그냥 통과


def test_run_uses_combined_household_income_when_given(db_session):
    _seed_policy(db_session, max_income_krw=50_000_000)
    matched = run(
        PolicyChatSearchInput(annual_income_krw=40_000_000, spouse_annual_income_krw=20_000_000), _ctx(db_session)
    )
    assert matched.options == []
    matched = run(PolicyChatSearchInput(annual_income_krw=40_000_000), _ctx(db_session))
    assert len(matched.options) == 1


def test_run_filters_by_region_only_when_given(db_session):
    _seed_policy(db_session, region_code="26110")
    assert run(PolicyChatSearchInput(region="서울"), _ctx(db_session)).options == []
    assert len(run(PolicyChatSearchInput(region="부산"), _ctx(db_session)).options) == 1
    assert len(run(PolicyChatSearchInput(), _ctx(db_session)).options) == 1


def test_run_filters_by_keyword(db_session):
    _seed_policy(db_session, policy_name="전세자금 대출")
    _seed_policy(db_session, policy_name="창업 지원금")
    result = run(PolicyChatSearchInput(keyword="전세"), _ctx(db_session))
    assert len(result.options) == 1
    assert result.options[0].policy_name == "전세자금 대출"


def test_run_sorts_newlywed_policies_first_when_married(db_session):
    _seed_policy(db_session, policy_name="일반 대출")
    _seed_policy(db_session, policy_name="신혼부부 전세자금 대출")
    result = run(PolicyChatSearchInput(is_married=True), _ctx(db_session))
    names = [o.policy_name for o in result.options]
    assert names == ["신혼부부 전세자금 대출", "일반 대출"]


def test_run_excludes_expired_policy(db_session):
    _seed_policy(db_session, policy_name="마감된 정책", apply_start_ymd="20200101", apply_end_ymd="20200201")
    result = run(PolicyChatSearchInput(), _ctx(db_session))
    assert result.options == []


def test_run_includes_status_and_emoji_on_options(db_session):
    _seed_policy(db_session)
    result = run(PolicyChatSearchInput(), _ctx(db_session))
    assert result.options[0].status == "상시"
    assert result.options[0].status_emoji == "🟢"


def test_run_caps_results_at_max(db_session):
    for i in range(20):
        _seed_policy(db_session, policy_name=f"정책{i}")
    result = run(PolicyChatSearchInput(), _ctx(db_session))
    assert len(result.options) == tool.MAX_RESULTS
