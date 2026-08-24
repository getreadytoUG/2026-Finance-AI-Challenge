from datetime import date

from app.features.policy_matcher.status import STATUS_ORDER, compute_policy_status


def test_no_end_date_means_always_open():
    status, emoji = compute_policy_status(None, None, date(2026, 8, 24))
    assert status == "상시"
    assert emoji == "🟢"


def test_before_start_date_means_upcoming():
    status, emoji = compute_policy_status("20260901", "20260930", date(2026, 8, 24))
    assert status == "예정"
    assert emoji == "⚪"


def test_far_from_deadline_means_open():
    status, emoji = compute_policy_status("20260801", "20260910", date(2026, 8, 24))
    assert status == "여유"
    assert emoji == "🟢"


def test_exactly_seven_days_before_deadline_is_closing_soon():
    status, emoji = compute_policy_status("20260801", "20260831", date(2026, 8, 24))
    assert status == "임박"
    assert emoji == "🟡"


def test_eight_days_before_deadline_is_still_open():
    status, emoji = compute_policy_status("20260801", "20260901", date(2026, 8, 24))
    assert status == "여유"
    assert emoji == "🟢"


def test_after_end_date_means_closed():
    status, emoji = compute_policy_status("20260701", "20260801", date(2026, 8, 24))
    assert status == "만료"
    assert emoji == "🔴"


def test_status_order_matches_임박_여유_상시_예정_만료():
    assert STATUS_ORDER == {"임박": 0, "여유": 1, "상시": 2, "예정": 3, "만료": 4}
