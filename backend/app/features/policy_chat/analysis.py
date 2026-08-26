from typing import Literal

from pydantic import BaseModel, ValidationError

from app.auth.models import User
from app.features.policy_matcher.categories import category_tags
from app.features.policy_matcher.models import CachedPolicy
from app.features.policy_matcher.status import compute_policy_status, today_kst
from app.llm.base import Message
from app.llm.factory import get_provider
from app.tools.base import ToolSpec


class PolicyAnalysisResult(BaseModel):
    # 자유 텍스트로 두면 "조건부 적합"처럼 애매한 값이 섞여 프론트에서 원 색깔로
    # 표시하기 어려워진다 — 좋다/나쁘다 둘 중 하나로만 강제한다(2026-08-26 요청).
    fit: Literal["적합", "부적합"]
    # 적합할 때는 이유를 안 적어도 된다 — 부적합일 때만 우려 지점을 채운다.
    concerns: str | None = None
    benefit_summary: str
    application_notes: str
    # 신청 전에 미리 챙겨야 할 서류/조건 체크리스트 — application_notes(문장형
    # 유의사항)와 별도로 목록 형태로 둬야 프론트에서 리스트로 렌더링할 수 있다.
    required_documents: list[str] = []


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
    "바탕으로 이 사용자에게 이 정책이 적합한지 분석해 반드시 policy_analysis_result 도구를 "
    "호출해 결과를 반환하세요.\n\n"
    "- fit: 프로필 조건(나이/소득/혼인/지역)과 정책 조건을 대조해 '적합' 또는 '부적합' 중 하나로만 "
    "판단하세요. 애매하면 보수적으로 '부적합'으로 판단하세요.\n"
    "- concerns: fit이 '적합'이면 비워두세요. fit이 '부적합'이면 어떤 조건이 왜 우려되는지 한두 "
    "문장으로만 적으세요 — 적합한 이유는 설명하지 마세요.\n"
    "- benefit_summary: 이 정책이 제공하는 예상 혜택을 간결하게 요약하세요.\n"
    "- application_notes: 신청 시 유의사항을 간결하게 적으세요(구비 서류 목록은 여기 말고 "
    "required_documents에 담으세요).\n"
    "- required_documents: 신청 전에 미리 준비해야 할 서류나 증빙(예: 재직증명서, 주민등록등본, "
    "소득금액증명원 등)을 항목별로 나열하세요. 정책 정보에 구체적인 서류가 안 나와 있으면 "
    "일반적으로 요구되는 서류를 상식선에서 제시하되, 정책과 무관한 내용은 지어내지 마세요. "
    "필요한 서류가 전혀 없다고 판단되면 빈 리스트로 두세요.\n\n"
    "정책 데이터에 없는 내용은 추측해서 지어내지 마세요."
)

# 실제 실행 로직은 없다 — provider.chat(tools=[...])의 함수 호출 스키마 계약으로만
# 쓰이고, 결과는 generate_policy_report()가 tool_call 인자를 직접 파싱해서 쓴다.
# ALL_TOOL_SPECS에는 등록하지 않는다(policy_chat.ai_search.FILTER_DELTA_SPEC과 동일한 이유).
ANALYSIS_RESULT_SPEC = ToolSpec(
    name="policy_analysis_result",
    description="사용자 프로필과 정책 조건을 대조한 개인화 분석 결과를 구조화된 형태로 반환합니다.",
    input_schema=PolicyAnalysisResult,
    output_schema=PolicyAnalysisResult,
    entrypoint=lambda input, ctx: input,
)

_FALLBACK_RESULT = PolicyAnalysisResult(
    fit="부적합",
    concerns="분석 결과를 생성하지 못했습니다. 잠시 후 다시 시도해주세요.",
    benefit_summary="",
    application_notes="",
    required_documents=[],
)


def generate_policy_report(user: User, policy: CachedPolicy) -> PolicyAnalysisResult:
    provider = get_provider()
    user_msg = f"[사용자 프로필]\n{_profile_text(user)}\n\n[정책 정보]\n{_policy_text(policy)}"
    response = provider.chat(
        [Message(role="system", content=_SYSTEM_PROMPT), Message(role="user", content=user_msg)],
        tools=[ANALYSIS_RESULT_SPEC],
    )
    if not response.tool_calls:
        return _FALLBACK_RESULT
    try:
        return PolicyAnalysisResult(**response.tool_calls[0].arguments)
    except (TypeError, ValidationError):
        return _FALLBACK_RESULT
