from datetime import date, datetime, timedelta, timezone
from typing import Literal

_KST = timezone(timedelta(hours=9))
_CLOSING_SOON_DAYS = 7

# compute_policy_status()가 낼 수 있는 값 전부 — LLM 도구 호출 스키마(policy_chat)에서
# "마감 임박" 같은 자유 텍스트가 keyword로 잘못 들어가 매칭이 안 되는 문제를 막기 위해
# status를 이 Literal로 제한한다. STATUS_ORDER의 키와 반드시 동일하게 유지할 것.
PolicyStatusLabel = Literal["임박", "여유", "상시", "예정", "만료"]

# "정책 읽기" 탭 정렬 순서: 임박 - 여유 - 상시 - 예정 - 만료
STATUS_ORDER: dict[str, int] = {
    "임박": 0,
    "여유": 1,
    "상시": 2,
    "예정": 3,
    "만료": 4,
}


def today_kst() -> date:
    return datetime.now(_KST).date()


def compute_policy_status(
    apply_start_ymd: str | None, apply_end_ymd: str | None, today: date
) -> tuple[str, str]:
    """(상태 텍스트, 이모지) 튜플을 반환한다."""
    if not apply_end_ymd:
        return "상시", "🟢"

    end = _parse_ymd(apply_end_ymd)
    if today > end:
        return "만료", "🔴"

    if apply_start_ymd:
        start = _parse_ymd(apply_start_ymd)
        if today < start:
            return "예정", "⚪"

    if (end - today).days <= _CLOSING_SOON_DAYS:
        return "임박", "🟡"
    return "여유", "🟢"


def _parse_ymd(value: str) -> date:
    return date(int(value[0:4]), int(value[4:6]), int(value[6:8]))
