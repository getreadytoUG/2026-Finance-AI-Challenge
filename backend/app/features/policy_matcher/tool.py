from app.features.policy_matcher.categories import FINANCIAL_LARGE_CATEGORY, category_tags
from app.features.policy_matcher.matching import is_eligible, is_newlywed_policy
from app.features.policy_matcher.models import CachedPolicy
from app.features.policy_matcher.schemas import PolicyMatchInput, PolicyMatchOutput, PolicyOption
from app.tools.base import ToolContext, ToolSpec


def run(input: PolicyMatchInput, ctx: ToolContext) -> PolicyMatchOutput:
    # 온통청년 API를 매 요청마다 직접 부르는 대신, 배치가 채워 넣는 DB 캐시
    # (CachedPolicy)를 조회한다 — "정책 읽기" 탭과 동일한 데이터 소스로 통일.
    policies = ctx.db.query(CachedPolicy).all()
    financial_policies = [
        policy for policy in policies if FINANCIAL_LARGE_CATEGORY in category_tags(policy.large_category)
    ]
    eligible_policies = [policy for policy in financial_policies if is_eligible(policy, input)]
    # 기혼자에게는 신혼부부 대상 정책을 목록 맨 앞으로 — 나머지 순서는 그대로 유지한다(stable sort).
    if input.is_married:
        eligible_policies.sort(key=lambda policy: not is_newlywed_policy(policy))
    options = [
        PolicyOption(
            policy_name=policy.policy_name,
            benefit_description=policy.description,
            application_period=policy.application_period,
            reference_url=policy.apply_url,
            is_newlywed_policy=is_newlywed_policy(policy),
        )
        for policy in eligible_policies
    ]
    return PolicyMatchOutput(options=options)


TOOL_SPEC = ToolSpec(
    name="policy_matcher",
    description="온통청년 정책 중 금융 지원 정책만 모아 나이/소득/혼인/지역 조건에 맞는 것만 추천합니다",
    input_schema=PolicyMatchInput,
    output_schema=PolicyMatchOutput,
    entrypoint=run,
)
