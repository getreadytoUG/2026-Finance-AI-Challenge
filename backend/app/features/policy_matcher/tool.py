from app.features.policy_matcher.matching import is_eligible, is_likely_template_region_code, is_newlywed_policy
from app.features.policy_matcher.models import CachedPolicy
from app.features.policy_matcher.schemas import PolicyMatchInput, PolicyMatchOutput, PolicyOption
from app.features.policy_matcher.status import STATUS_ORDER, compute_policy_status, today_kst
from app.tools.base import ToolContext, ToolSpec


def run(input: PolicyMatchInput, ctx: ToolContext) -> PolicyMatchOutput:
    # 온통청년 API를 매 요청마다 직접 부르는 대신, 배치가 채워 넣는 DB 캐시
    # (CachedPolicy)를 조회한다 — "정책 읽기" 탭과 동일한 데이터 소스로 통일.
    #
    # 2026-09-03 사용자 요청: 예전엔 여기서 "금융･복지･문화" 대분류로만 좁혔었는데
    # (아래 TOOL_SPEC 설명도 "금융 지원 정책만"이었음), 실제로 써보니 그 좁힌
    # 범위엔 조건에 맞는 게 아예 없는 경우가 많아서(26세/2천만원/서울 조건으로
    # 0건) "정책 전체 보기"(전 분야)로 따로 확인해야 했다. 카테고리 제한을 없애고
    # 전 분야를 다 보여주도록 바꿨다 — "정책 전체 보기"와 동일한 범위이되, 여긴
    # 라이브 검색이 아니라 프로필 기반 개인화 매칭이라는 차이만 남는다.
    #
    # 2026-09-03 사용자 지적("서울로 해놨는데 의성/창원 정책이 나온다"): zipCd에
    # 17개 시/도 코드를 전부(또는 거의 다) 나열해 사실상 지역 조건이 아니라 데이터
    # 입력 실수/기본값인 레코드가 실측상 419건(전체의 15%)이나 있다 — 그래서
    # region_matches()가 "이 정책은 서울도 포함한다"고 정직하게 답해도, 실제로는
    # 그 지자체(예: 서산시) 전용 정책이 잘못 전체 지역으로 찍힌 것뿐이다. 실제로
    # 같은 정책이 올바른 지역코드로 중복 등록된 경우도 있어(서산시청년정책네트워크
    # 운영 — 정상 44210 버전과 이 쓰레기 버전이 둘 다 캐시에 있었다), 걸러내도
    # 정보 손실은 거의 없다. is_likely_template_region_code()는 이제 제공기관이
    # 중앙부처로 확인된 경우(햇살론유스 등 진짜 전국 상품)는 걸러내지 않는다
    # (matching.py 주석 참고 — 처음엔 이 예외가 없어서 햇살론유스가 잘못 빠졌었다).
    policies = ctx.db.query(CachedPolicy).all()
    eligible_policies = [
        policy for policy in policies if is_eligible(policy, input) and not is_likely_template_region_code(policy)
    ]
    today = today_kst()
    statuses = {
        policy.policy_key: compute_policy_status(policy.apply_start_ymd, policy.apply_end_ymd, today)
        for policy in eligible_policies
    }
    # 2026-09-03 사용자 발견: 만료된 정책이 "뒤쪽으로 정렬만" 되고 목록에서 안 빠졌었다.
    # router.py(/match), ai_search.py, marriage_comparison.py, savings_simulator,
    # policy_chat/tool.py는 전부 status == "만료"를 걸러내는데 여기만 빠져있었다 —
    # 신청 자체가 불가능한 정책을 "맞춤 정책"으로 보여주는 건 의미가 없으므로 제외한다.
    eligible_policies = [policy for policy in eligible_policies if statuses[policy.policy_key][0] != "만료"]
    # 기혼자에게는 신혼부부 대상 정책을 먼저, 그 다음은 신청 상태(임박-여유-상시-예정)
    # 순으로 정렬한다 — 2026-09-02 QA에서 "신청 가능" 배지가 이미 마감된 정책에도 하드코딩
    # 돼 있던 걸 발견해 status/status_emoji를 실제로 계산해 채우게 됐다.
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
    description="온통청년 정책 전체를 대상으로 나이/소득/혼인/지역/장애·보훈 조건에 맞는 것만 추천합니다",
    input_schema=PolicyMatchInput,
    output_schema=PolicyMatchOutput,
    entrypoint=run,
)
