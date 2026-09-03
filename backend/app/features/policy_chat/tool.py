from app.features.policy_chat.schemas import PolicyChatSearchInput, PolicyChatSearchOption, PolicyChatSearchOutput
from app.features.policy_matcher.categories import FINANCIAL_LARGE_CATEGORY, category_tags
from app.features.policy_matcher.matching import (
    age_matches,
    income_matches,
    is_disability_targeted_policy,
    is_married_only_policy,
    is_newlywed_policy,
    is_unmarried_only_policy,
    is_veteran_targeted_policy,
    region_matches,
)
from app.features.policy_matcher.models import CachedPolicy
from app.features.policy_matcher.status import compute_policy_status, today_kst
from app.tools.base import ToolContext, ToolSpec

MAX_RESULTS = 8


# policy_matcher.matching.is_eligible과 달리 이 조건들은 챗봇 대화에서 자연스럽게
# 다 언급되지 않을 수 있다 — 값이 주어진 필드만 체크하고, None인 필드는 그냥
# 통과시킨다(그 필드에 대해서는 아무 의견도 없다는 뜻으로 취급). 나이/소득/혼인상태
# 비교 자체는 matching.py의 공유 헬퍼를 그대로 쓴다 — 예전엔 여기 따로 복붙돼 있어서
# is_eligible만 고치고 이쪽은 못 고치는 일이 있었다(2026-09-03, 사용자 지적).
def _matches(policy: CachedPolicy, input: PolicyChatSearchInput) -> bool:
    if not age_matches(policy, input.age):
        return False
    if is_married_only_policy(policy) and input.is_married is False:
        return False
    if is_unmarried_only_policy(policy) and input.is_married is True:
        return False
    if not income_matches(policy, input.annual_income_krw, input.spouse_annual_income_krw):
        return False
    if input.region and policy.region_code:
        if not region_matches(policy.region_code, input.region):
            return False
    if input.keyword:
        haystack = policy.policy_name + policy.description
        if input.keyword not in haystack:
            return False
    if input.disability_target and not is_disability_targeted_policy(policy):
        return False
    if input.veteran_target and not is_veteran_targeted_policy(policy):
        return False
    return True


def run(input: PolicyChatSearchInput, ctx: ToolContext) -> PolicyChatSearchOutput:
    today = today_kst()
    # 온통청년 API를 매 대화 턴마다 직접 부르는 대신, 배치가 채워 넣는 DB 캐시
    # (CachedPolicy)를 조회한다 — "정책 읽기"/policy_matcher와 동일한 데이터 소스.
    policies = ctx.db.query(CachedPolicy).all()
    financial_policies = [
        policy for policy in policies if FINANCIAL_LARGE_CATEGORY in category_tags(policy.large_category)
    ]
    candidates = [policy for policy in financial_policies if _matches(policy, input)]
    matched = []
    for policy in candidates:
        status, _ = compute_policy_status(policy.apply_start_ymd, policy.apply_end_ymd, today)
        # 마감된 정책을 챗봇이 추천하면 혼란만 준다 — "만료"를 명시적으로 요청한
        # 게 아니면 "정책 읽기" 탭 기본값과 동일하게 제외한다.
        if status == "만료" and input.status != "만료":
            continue
        if input.status and status != input.status:
            continue
        matched.append(policy)
    if input.is_married:
        matched.sort(key=lambda policy: not is_newlywed_policy(policy))
    matched = matched[:MAX_RESULTS]

    options = []
    for policy in matched:
        status, status_emoji = compute_policy_status(policy.apply_start_ymd, policy.apply_end_ymd, today)
        options.append(
            PolicyChatSearchOption(
                policy_name=policy.policy_name,
                benefit_description=policy.description,
                application_period=policy.application_period,
                reference_url=policy.apply_url,
                is_newlywed_policy=is_newlywed_policy(policy),
                status=status,
                status_emoji=status_emoji,
            )
        )
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
