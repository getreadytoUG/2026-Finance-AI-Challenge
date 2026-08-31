from pydantic import ValidationError

from app.features.policy_matcher.models import CachedPolicy
from app.features.policy_matcher.schemas import PolicyRankingInput, PolicyRankingOutput, RankedPolicyItem
from app.features.policy_matcher.status import compute_policy_status, today_kst
from app.llm.base import Message
from app.llm.factory import get_provider
from app.tools.base import ToolSpec

_SYSTEM_PROMPT = (
    "당신은 청년/신혼부부를 위한 정책 우선순위 도우미입니다. 아래 사용자 프로필과 정책 목록을 보고, "
    "이 사용자에게 실질적으로 더 도움이 되는 순서로 정책을 정렬해 반드시 policy_ranking_result 도구를 "
    "호출해 결과를 반환하세요.\n\n"
    "- ranked 배열에는 입력으로 받은 정책의 policy_key를 하나도 빠짐없이, 정확히 한 번씩만 포함하세요. "
    "목록에 없는 policy_key를 새로 만들어내지 마세요.\n"
    "- 배열 순서 자체가 우선순위입니다 — 첫 번째가 가장 우선입니다.\n"
    "- 판단 기준: 신청 마감이 임박한 정책, 신혼부부 대상으로 특화된 정책, 혜택 내용이 더 구체적이고 큰 "
    "정책을 우선하세요.\n"
    "- reason은 왜 그 순위인지 한 문장으로만 적으세요. 반드시 그 정책 정보에 실제로 나온 내용에 근거해서만 "
    "작성하고, 정책 설명에 없는 금액이나 조건을 지어내지 마세요."
)


def _profile_text(input: PolicyRankingInput) -> str:
    lines = [
        f"나이: {input.age}세",
        f"거주 지역: {input.region}",
        f"연소득: {input.annual_income_krw:,}원",
    ]
    if input.spouse_annual_income_krw is not None:
        lines.append(f"배우자(예정) 연소득: {input.spouse_annual_income_krw:,}원 (가구소득 합산 기준)")
    return "\n".join(lines)


def _policy_entry_text(policy: CachedPolicy) -> str:
    status, emoji = compute_policy_status(policy.apply_start_ymd, policy.apply_end_ymd, today_kst())
    lines = [
        f"[{policy.policy_key}] {policy.policy_name}",
        f"설명: {policy.description}",
        f"신청 기간: {policy.application_period} (현재 상태: {emoji} {status})",
    ]
    return "\n".join(lines)


# 실제 실행 로직은 없다 — analysis.ANALYSIS_RESULT_SPEC과 동일하게 provider.chat(tools=[...])의
# 함수 호출 스키마 계약으로만 쓰이고, ALL_TOOL_SPECS에는 등록하지 않는다.
RANKING_RESULT_SPEC = ToolSpec(
    name="policy_ranking_result",
    description="정책 목록을 사용자에게 도움이 되는 순서로 정렬한 결과를 구조화된 형태로 반환합니다.",
    input_schema=PolicyRankingOutput,
    output_schema=PolicyRankingOutput,
    entrypoint=lambda input, ctx: input,
)


def _fallback_output(policy_keys: list[str]) -> PolicyRankingOutput:
    # 원래 순서를 그대로 유지하되, reason으로 "AI 순위를 못 만들었다"는 걸 솔직하게 표시한다
    # (analysis.generate_policy_report의 _FALLBACK_RESULT와 동일한 방식).
    return PolicyRankingOutput(
        ranked=[RankedPolicyItem(policy_key=key, reason="AI 우선순위 분석에 실패했어요.") for key in policy_keys]
    )


def rank_policies(input: PolicyRankingInput, policies: list[CachedPolicy]) -> PolicyRankingOutput:
    if not policies:
        return PolicyRankingOutput(ranked=[])

    provider = get_provider()
    policy_list_text = "\n\n".join(_policy_entry_text(p) for p in policies)
    user_msg = (
        f"[사용자 프로필]\n{_profile_text(input)}\n\n"
        f"[정책 목록 — {input.context_label}]\n{policy_list_text}"
    )
    response = provider.chat(
        [Message(role="system", content=_SYSTEM_PROMPT), Message(role="user", content=user_msg)],
        tools=[RANKING_RESULT_SPEC],
    )

    input_keys = [p.policy_key for p in policies]
    if not response.tool_calls:
        return _fallback_output(input_keys)
    try:
        result = PolicyRankingOutput(**response.tool_calls[0].arguments)
    except (TypeError, ValidationError):
        return _fallback_output(input_keys)

    # LLM이 policy_key를 누락/중복/날조하면(모델이 종종 그럴 수 있다) 화면이 깨지거나
    # 있지도 않은 정책을 보여주게 되므로, 입력 집합과 정확히 일치하는지 검증하고
    # 어긋나면 정직하게 폴백한다.
    returned_keys = [item.policy_key for item in result.ranked]
    if set(returned_keys) != set(input_keys) or len(returned_keys) != len(input_keys):
        return _fallback_output(input_keys)

    return result
