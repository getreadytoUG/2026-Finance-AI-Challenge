from app.features.policy_matcher.matching import is_eligible
from app.features.policy_matcher.schemas import PolicyMatchInput, PolicyMatchOutput, PolicyOption
from app.features.policy_matcher.youth_center_client import fetch_policies
from app.tools.base import ToolContext, ToolSpec


def run(input: PolicyMatchInput, ctx: ToolContext) -> PolicyMatchOutput:
    policies = fetch_policies()
    options = [
        PolicyOption(
            policy_name=policy.policy_name,
            eligible=is_eligible(policy, input),
            benefit_description=policy.description,
            application_period=policy.application_period,
            reference_url=policy.apply_url,
        )
        for policy in policies
    ]
    options.sort(key=lambda option: not option.eligible)
    return PolicyMatchOutput(options=options)


TOOL_SPEC = ToolSpec(
    name="policy_matcher",
    description="청년/신혼부부 정책을 비교하고 가/불가를 판단합니다",
    input_schema=PolicyMatchInput,
    output_schema=PolicyMatchOutput,
    entrypoint=run,
)
