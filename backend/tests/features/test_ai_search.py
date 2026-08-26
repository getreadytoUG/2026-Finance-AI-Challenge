import itertools
from datetime import datetime, timedelta, timezone

from app.features.policy_chat.ai_search import search_policies
from app.features.policy_chat.schemas import PolicyChatSearchInput
from app.features.policy_matcher.models import CachedPolicy

_key_seq = itertools.count(1)


def _seed_policy(db_session, **overrides) -> CachedPolicy:
    defaults = dict(
        policy_key=f"P{next(_key_seq)}",
        policy_name="테스트 정책",
        description="지원 내용 설명",
        apply_url="https://example.com",
        application_period="상시",
        apply_start_ymd=None,
        apply_end_ymd=None,
        min_age=None,
        max_age=None,
        min_income_krw=None,
        max_income_krw=None,
        marital_status="",
        region_code="",
        large_category="일자리",
        mid_category="",
        refreshed_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    row = CachedPolicy(**defaults)
    db_session.add(row)
    db_session.commit()
    return row


def _filters(**overrides) -> PolicyChatSearchInput:
    return PolicyChatSearchInput(**overrides)


def test_search_includes_all_categories_not_just_financial(db_session):
    # policy_chat_search(위젯 챗봇)와의 핵심 차이 — 금융 카테고리로 한정하지 않는다.
    _seed_policy(db_session, large_category="일자리")
    _seed_policy(db_session, large_category="주거")
    items, total = search_policies(db_session, _filters(), include_closed=False, page=1, page_size=10)
    assert total == 2
    assert len(items) == 2


def test_search_filters_by_age(db_session):
    _seed_policy(db_session, min_age=19, max_age=34)
    items, total = search_policies(db_session, _filters(age=50), include_closed=False, page=1, page_size=10)
    assert total == 0
    items, total = search_policies(db_session, _filters(age=25), include_closed=False, page=1, page_size=10)
    assert total == 1


def test_search_filters_by_income(db_session):
    _seed_policy(db_session, max_income_krw=30_000_000)
    items, total = search_policies(
        db_session, _filters(annual_income_krw=40_000_000), include_closed=False, page=1, page_size=10
    )
    assert total == 0
    items, total = search_policies(
        db_session, _filters(annual_income_krw=20_000_000), include_closed=False, page=1, page_size=10
    )
    assert total == 1


def test_search_filters_by_marital_status(db_session):
    _seed_policy(db_session, marital_status="기혼")
    items, total = search_policies(
        db_session, _filters(is_married=False), include_closed=False, page=1, page_size=10
    )
    assert total == 0
    items, total = search_policies(
        db_session, _filters(is_married=True), include_closed=False, page=1, page_size=10
    )
    assert total == 1


def test_search_filters_by_region(db_session):
    _seed_policy(db_session, region_code="26110")
    items, total = search_policies(db_session, _filters(region="서울"), include_closed=False, page=1, page_size=10)
    assert total == 0
    items, total = search_policies(db_session, _filters(region="부산"), include_closed=False, page=1, page_size=10)
    assert total == 1


def test_search_filters_by_category(db_session):
    _seed_policy(db_session, large_category="일자리,주거")
    items, total = search_policies(
        db_session, _filters(category="교육"), include_closed=False, page=1, page_size=10
    )
    assert total == 0
    items, total = search_policies(
        db_session, _filters(category="주거"), include_closed=False, page=1, page_size=10
    )
    assert total == 1


def test_search_filters_by_keyword(db_session):
    _seed_policy(db_session, policy_name="전세자금 대출")
    _seed_policy(db_session, policy_name="창업 지원금")
    items, total = search_policies(
        db_session, _filters(keyword="전세"), include_closed=False, page=1, page_size=10
    )
    assert total == 1
    assert items[0].policy_name == "전세자금 대출"


def test_search_excludes_expired_by_default(db_session):
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y%m%d")
    _seed_policy(db_session, apply_start_ymd="20200101", apply_end_ymd=yesterday)
    items, total = search_policies(db_session, _filters(), include_closed=False, page=1, page_size=10)
    assert total == 0
    items, total = search_policies(db_session, _filters(), include_closed=True, page=1, page_size=10)
    assert total == 1


def test_search_filters_by_status(db_session):
    from app.features.policy_matcher.status import today_kst

    soon = (today_kst() + timedelta(days=3)).strftime("%Y%m%d")
    _seed_policy(db_session, policy_name="상시 정책")  # apply_end_ymd=None -> 상시
    _seed_policy(db_session, policy_name="임박 정책", apply_start_ymd="20200101", apply_end_ymd=soon)

    items, total = search_policies(db_session, _filters(status="임박"), include_closed=False, page=1, page_size=10)
    assert total == 1
    assert items[0].policy_name == "임박 정책"

    items, total = search_policies(db_session, _filters(status="상시"), include_closed=False, page=1, page_size=10)
    assert total == 1
    assert items[0].policy_name == "상시 정책"


def test_search_status_expired_overrides_include_closed_toggle(db_session):
    # "마감된 것만 보여줘"를 채팅으로 요청하면(status="만료"), 화면의
    # "마감된 정책도 보기" 체크박스가 꺼져 있어도(include_closed=False) 보여야 한다.
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y%m%d")
    _seed_policy(db_session, apply_start_ymd="20200101", apply_end_ymd=yesterday)
    items, total = search_policies(
        db_session, _filters(status="만료"), include_closed=False, page=1, page_size=10
    )
    assert total == 1


def test_search_sorts_newlywed_first_when_married(db_session):
    _seed_policy(db_session, policy_name="일반 정책")
    _seed_policy(db_session, policy_name="신혼부부 전세자금 대출")
    items, total = search_policies(db_session, _filters(is_married=True), include_closed=False, page=1, page_size=10)
    assert total == 2
    assert items[0].policy_name == "신혼부부 전세자금 대출"


def test_search_paginates_results(db_session):
    for i in range(15):
        _seed_policy(db_session, policy_name=f"정책{i}")
    items, total = search_policies(db_session, _filters(), include_closed=False, page=1, page_size=10)
    assert total == 15
    assert len(items) == 10
    items, total = search_policies(db_session, _filters(), include_closed=False, page=2, page_size=10)
    assert total == 15
    assert len(items) == 5
