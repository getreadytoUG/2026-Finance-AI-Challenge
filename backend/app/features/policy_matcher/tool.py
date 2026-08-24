from app.features.policy_matcher.categories import FINANCIAL_MID_CATEGORY, category_tags
from app.features.policy_matcher.matching import is_eligible
from app.features.policy_matcher.schemas import PolicyMatchInput, PolicyMatchOutput, PolicyOption
from app.features.policy_matcher.youth_center_client import fetch_policies
from app.tools.base import ToolContext, ToolSpec


def run(input: PolicyMatchInput, ctx: ToolContext) -> PolicyMatchOutput:
    policies = fetch_policies()
    financial_policies = [
        policy for policy in policies if FINANCIAL_MID_CATEGORY in category_tags(policy.mid_category)
    ]
    options = [
        PolicyOption(
            policy_name=policy.policy_name,
            benefit_description=policy.description,
            application_period=policy.application_period,
            reference_url=policy.apply_url,
        )
        for policy in financial_policies
        if is_eligible(policy, input)
    ]
    return PolicyMatchOutput(options=options)


TOOL_SPEC = ToolSpec(
    name="policy_matcher",
    description="온통청년 정책 중 금융 지원 정책만 모아 나이/소득/혼인/지역 조건에 맞는 것만 추천합니다",
    input_schema=PolicyMatchInput,
    output_schema=PolicyMatchOutput,
    entrypoint=run,
)
