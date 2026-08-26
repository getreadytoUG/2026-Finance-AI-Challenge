from app.auth.models import User
from app.features.policy_matcher.categories import category_tags
from app.features.policy_matcher.models import CachedPolicy
from app.features.policy_matcher.status import compute_policy_status, today_kst
from app.llm.base import Message
from app.llm.factory import get_provider


def _profile_text(user: User) -> str:
    lines = []
    if user.age is not None:
        lines.append(f"나이: {user.age}세")
    if user.is_married is not None:
        lines.append(f"기혼 여부: {'기혼' if user.is_married else '미혼'}")
    if user.annual_income_krw is not None:
        lines.append(f"연소득: {user.annual_income_krw:,}원")
    if user.is_married and user.spouse_annual_income_krw is not None:
        lines.append(f"배우자 연소득: {user.spouse_annual_income_krw:,}원")
    if user.region is not None:
        lines.append(f"거주 지역: {user.region}")
    return "\n".join(lines) if lines else "(등록된 정보 없음)"


def _policy_text(policy: CachedPolicy) -> str:
    status, emoji = compute_policy_status(policy.apply_start_ymd, policy.apply_end_ymd, today_kst())
    lines = [
        f"정책명: {policy.policy_name}",
        f"분야: {', '.join(category_tags(policy.large_category)) or '기타'}",
        f"설명: {policy.description}",
        f"신청 기간: {policy.application_period} (현재 상태: {emoji} {status})",
    ]
    if policy.min_age is not None or policy.max_age is not None:
        min_age = f"{policy.min_age}세" if policy.min_age is not None else "제한 없음"
        max_age = f"{policy.max_age}세" if policy.max_age is not None else "제한 없음"
        lines.append(f"연령 조건: {min_age} ~ {max_age}")
    if policy.min_income_krw is not None or policy.max_income_krw is not None:
        min_income = f"{policy.min_income_krw:,}원" if policy.min_income_krw is not None else "제한 없음"
        max_income = f"{policy.max_income_krw:,}원" if policy.max_income_krw is not None else "제한 없음"
        lines.append(f"소득 조건: {min_income} ~ {max_income}")
    if policy.marital_status:
        lines.append(f"혼인 조건 코드: {policy.marital_status}")
    if policy.region_code:
        lines.append(f"지역 코드: {policy.region_code}")
    return "\n".join(lines)


_SYSTEM_PROMPT = (
    "당신은 청년/신혼부부를 위한 정책 분석 도우미입니다. 아래 사용자 프로필과 정책 정보를 "
    "바탕으로, 이 사용자에게 이 정책이 얼마나 적합한지 개인화된 분석 리포트를 작성하세요.\n\n"
    "리포트는 아래 네 항목을 한국어로, 각 항목을 줄바꿈으로 구분해 간결하게 작성하세요:\n"
    "1) 적합도 판단 — 프로필 조건(나이/소득/혼인/지역)과 정책 조건을 대조해 적합/부적합/조건부 "
    "적합 중 하나로 판단하고 이유를 설명\n"
    "2) 예상 혜택 요약\n"
    "3) 신청 시 유의사항이나 미리 준비할 점\n"
    "4) 다음 행동 제안(예: 신청 링크 방문, 필요 서류 확인 등)\n\n"
    "정책 데이터에 없는 내용은 추측해서 지어내지 말고, 모른다고 솔직히 말하세요."
)


def generate_policy_report(user: User, policy: CachedPolicy) -> str:
    provider = get_provider()
    user_msg = f"[사용자 프로필]\n{_profile_text(user)}\n\n[정책 정보]\n{_policy_text(policy)}"
    response = provider.chat(
        [Message(role="system", content=_SYSTEM_PROMPT), Message(role="user", content=user_msg)],
        tools=[],
    )
    return response.content or "분석 결과를 생성하지 못했습니다."
