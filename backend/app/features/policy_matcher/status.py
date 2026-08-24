from datetime import date, datetime, timedelta, timezone

_KST = timezone(timedelta(hours=9))
_CLOSING_SOON_DAYS = 7


def today_kst() -> date:
    return datetime.now(_KST).date()


def compute_policy_status(
    apply_start_ymd: str | None, apply_end_ymd: str | None, today: date
) -> tuple[str, str]:
    """(상태 텍스트, 이모지) 튜플을 반환한다."""
    if not apply_end_ymd:
        return "신청가능", "🟢"

    end = _parse_ymd(apply_end_ymd)
    if today > end:
        return "마감", "🔴"

    if apply_start_ymd:
        start = _parse_ymd(apply_start_ymd)
        if today < start:
            return "신청예정", "⚪"

    if (end - today).days <= _CLOSING_SOON_DAYS:
        return "마감임박", "🟡"
    return "신청가능", "🟢"


def _parse_ymd(value: str) -> date:
    return date(int(value[0:4]), int(value[4:6]), int(value[6:8]))
