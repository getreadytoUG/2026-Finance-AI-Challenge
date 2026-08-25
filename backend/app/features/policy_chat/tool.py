from app.features.policy_chat.schemas import PolicyChatSearchInput, PolicyChatSearchOption, PolicyChatSearchOutput
from app.features.policy_matcher.categories import FINANCIAL_LARGE_CATEGORY, category_tags
from app.features.policy_matcher.matching import is_newlywed_policy, region_matches
from app.features.policy_matcher.youth_center_client import RawYouthPolicy, fetch_all_policies
from app.tools.base import ToolContext, ToolSpec

MAX_RESULTS = 8


# policy_matcher.matching.is_eligible과 달리 이 조건들은 챗봇 대화에서 자연스럽게
# 다 언급되지 않을 수 있다 — 값이 주어진 필드만 체크하고, None인 필드는 그냥
# 통과시킨다(그 필드에 대해서는 아무 의견도 없다는 뜻으로 취급).
def _matches(policy: RawYouthPolicy, input: PolicyChatSearchInput) -> bool:
    if input.age is not None:
        if policy.min_age is not None and input.age < policy.min_age:
            return False
        if policy.max_age is not None and input.age > policy.max_age:
            return False
    if policy.marital_status == "기혼" and input.is_married is False:
        return False
    if policy.marital_status == "미혼" and input.is_married is True:
        return False
    if input.annual_income_krw is not None:
        household_income = input.annual_income_krw + (input.spouse_annual_income_krw or 0)
        if policy.min_income_krw is not None and household_income < policy.min_income_krw:
            return False
        if policy.max_income_krw is not None and household_income > policy.max_income_krw:
            return False
    if input.region and policy.region_code:
        if not region_matches(policy.region_code, input.region):
            return False
    if input.keyword:
        haystack = policy.policy_name + policy.description
        if input.keyword not in haystack:
            return False
    return True


def run(input: PolicyChatSearchInput, ctx: ToolContext) -> PolicyChatSearchOutput:
    policies = fetch_all_policies()
    financial_policies = [
        policy for policy in policies if FINANCIAL_LARGE_CATEGORY in category_tags(policy.large_category)
    ]
    matched = [policy for policy in financial_policies if _matches(policy, input)]
    if input.is_married:
        matched.sort(key=lambda policy: not is_newlywed_policy(policy))
    matched = matched[:MAX_RESULTS]

    options = [
        PolicyChatSearchOption(
            policy_name=policy.policy_name,
            benefit_description=policy.description,
            application_period=policy.application_period,
            reference_url=policy.apply_url,
            is_newlywed_policy=is_newlywed_policy(policy),
        )
        for policy in matched
    ]
    return PolicyChatSearchOutput(options=options)


TOOL_SPEC = ToolSpec(
    name="policy_chat_search",
    description=(
        "자연어 대화에서 언급된 조건(나이/기혼여부/소득/지역/키워드 중 일부만 있어도 됨)으로 "
        "금융 지원 정책을 검색합니다. 언급되지 않은 조건은 생략해도 됩니다."
    ),
    input_schema=PolicyChatSearchInput,
    output_schema=PolicyChatSearchOutput,
    entrypoint=run,
)
