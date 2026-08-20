from app.features.policy_matcher.schemas import PolicyMatchInput, PolicyMatchOutput, PolicyOption
from app.tools.base import ToolContext, ToolSpec

YOUTH_MAX_AGE = 34


def run(input: PolicyMatchInput, ctx: ToolContext) -> PolicyMatchOutput:
    eligible = input.age <= YOUTH_MAX_AGE
    rate = 1.5 if input.is_married else 2.0
    return PolicyMatchOutput(
        options=[
            PolicyOption(
                policy_name="청년 전세자금대출 (샘플 데이터)",
                eligible=eligible,
                preferential_rate_percent=rate,
                reference_url="https://www.molit.go.kr",
            )
        ]
    )


TOOL_SPEC = ToolSpec(
    name="policy_matcher",
    description="청년/신혼부부 정책을 비교하고 가/불가·우대금리를 판단합니다",
    input_schema=PolicyMatchInput,
    output_schema=PolicyMatchOutput,
    entrypoint=run,
)
