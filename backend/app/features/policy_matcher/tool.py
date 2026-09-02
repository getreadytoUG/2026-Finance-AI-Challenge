from app.features.policy_matcher.categories import FINANCIAL_LARGE_CATEGORY, category_tags
from app.features.policy_matcher.matching import is_eligible, is_newlywed_policy
from app.features.policy_matcher.models import CachedPolicy
from app.features.policy_matcher.schemas import PolicyMatchInput, PolicyMatchOutput, PolicyOption
from app.features.policy_matcher.status import STATUS_ORDER, compute_policy_status, today_kst
from app.tools.base import ToolContext, ToolSpec


def run(input: PolicyMatchInput, ctx: ToolContext) -> PolicyMatchOutput:
    # 온통청년 API를 매 요청마다 직접 부르는 대신, 배치가 채워 넣는 DB 캐시
    # (CachedPolicy)를 조회한다 — "정책 읽기" 탭과 동일한 데이터 소스로 통일.
    policies = ctx.db.query(CachedPolicy).all()
    financial_policies = [
        policy for policy in policies if FINANCIAL_LARGE_CATEGORY in category_tags(policy.large_category)
    ]
    eligible_policies = [policy for policy in financial_policies if is_eligible(policy, input)]
    today = today_kst()
    statuses = {
        policy.policy_key: compute_policy_status(policy.apply_start_ymd, policy.apply_end_ymd, today)
        for policy in eligible_policies
    }
    # 기혼자에게는 신혼부부 대상 정책을 먼저, 그 다음은 신청 상태(임박-여유-상시-예정-만료)
    # 순으로 정렬한다 — 2026-09-02 QA에서 "신청 가능" 배지가 이미 마감된 정책에도 하드코딩
    # 돼 있던 걸 발견해 status/status_emoji를 실제로 계산해 채우게 됐는데, 정렬도 안 하면
    # 만료된 정책이 목록 맨 위에 남아있을 수 있어 같이 손봤다.
    eligible_policies.sort(
        key=lambda policy: (
            not is_newlywed_policy(policy) if input.is_married else False,
            STATUS_ORDER[statuses[policy.policy_key][0]],
        )
    )
    options = [
        PolicyOption(
            policy_key=policy.policy_key,
            policy_name=policy.policy_name,
            benefit_description=policy.description,
            application_period=policy.application_period,
            reference_url=policy.apply_url,
            is_newlywed_policy=is_newlywed_policy(policy),
            status=statuses[policy.policy_key][0],
            status_emoji=statuses[policy.policy_key][1],
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
