from app.features.policy_matcher.categories import FINANCIAL_LARGE_CATEGORY, category_tags
from app.features.policy_matcher.matching import is_eligible
from app.features.policy_matcher.schemas import PolicyMatchInput, PolicyMatchOutput, PolicyOption
from app.features.policy_matcher.youth_center_client import fetch_all_policies
from app.tools.base import ToolContext, ToolSpec


def run(input: PolicyMatchInput, ctx: ToolContext) -> PolicyMatchOutput:
    # fetch_policies()의 기본 page_size(100)로는 전체 카탈로그(~2,700여 건) 중
    # 일부만 보게 되어 금융 카테고리 정책 상당수를 놓친다 — 전체를 가져온다.
    policies = fetch_all_policies()
    financial_policies = [
        policy for policy in policies if FINANCIAL_LARGE_CATEGORY in category_tags(policy.large_category)
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
