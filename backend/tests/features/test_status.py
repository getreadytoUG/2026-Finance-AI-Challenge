from datetime import date

from app.features.policy_matcher.status import compute_policy_status


def test_no_end_date_means_always_open():
    status, emoji = compute_policy_status(None, None, date(2026, 8, 24))
    assert status == "신청가능"
    assert emoji == "🟢"


def test_before_start_date_means_upcoming():
    status, emoji = compute_policy_status("20260901", "20260930", date(2026, 8, 24))
    assert status == "신청예정"
    assert emoji == "⚪"


def test_far_from_deadline_means_open():
    status, emoji = compute_policy_status("20260801", "20260910", date(2026, 8, 24))
    assert status == "신청가능"
    assert emoji == "🟢"


def test_exactly_seven_days_before_deadline_is_closing_soon():
    status, emoji = compute_policy_status("20260801", "20260831", date(2026, 8, 24))
    assert status == "마감임박"
    assert emoji == "🟡"


def test_eight_days_before_deadline_is_still_open():
    status, emoji = compute_policy_status("20260801", "20260901", date(2026, 8, 24))
    assert status == "신청가능"
    assert emoji == "🟢"


def test_after_end_date_means_closed():
    status, emoji = compute_policy_status("20260701", "20260801", date(2026, 8, 24))
    assert status == "마감"
    assert emoji == "🔴"
