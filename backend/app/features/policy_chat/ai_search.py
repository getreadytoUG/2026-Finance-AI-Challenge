from sqlalchemy.orm import Session

from app.features.policy_chat.schemas import PolicyAiFilterDelta, PolicyChatSearchInput
from app.features.policy_chat.tool import _matches
from app.features.policy_matcher.categories import category_tags
from app.features.policy_matcher.matching import is_newlywed_policy
from app.features.policy_matcher.models import CachedPolicy
from app.features.policy_matcher.schemas import PolicyBrowseItem
from app.features.policy_matcher.status import STATUS_ORDER, compute_policy_status, today_kst
from app.tools.base import ToolSpec


def _matches_category(policy: CachedPolicy, category: str | None) -> bool:
    if not category:
        return True
    return category in category_tags(policy.large_category)


def search_policies(
    db: Session,
    filters: PolicyChatSearchInput,
    include_closed: bool,
    page: int,
    page_size: int,
) -> tuple[list[PolicyBrowseItem], int]:
    # "AI로 정책 알기" 탭은 policy_chat_search(위젯 챗봇)와 달리 금융 카테고리로
    # 한정하지 않는다 — 전 카테고리를 대상으로 대화형 필터를 적용한다.
    today = today_kst()
    # 채팅으로 "마감된 것만/곧 마감되는 것만 보여줘"라고 status를 직접 지정했다면,
    # 화면의 "마감된 정책도 보기" 체크박스가 꺼져 있어도 그 요청을 우선한다.
    effective_include_closed = include_closed or filters.status == "만료"
    matched = []
    for row in db.query(CachedPolicy).all():
        if not _matches(row, filters):
            continue
        if not _matches_category(row, filters.category):
            continue
        status, emoji = compute_policy_status(row.apply_start_ymd, row.apply_end_ymd, today)
        if status == "만료" and not effective_include_closed:
            continue
        if filters.status and status != filters.status:
            continue
        matched.append((row, status, emoji))

    if filters.is_married:
        matched.sort(key=lambda entry: (not is_newlywed_policy(entry[0]), STATUS_ORDER[entry[1]]))
    else:
        matched.sort(key=lambda entry: STATUS_ORDER[entry[1]])

    total = len(matched)
    start = (page - 1) * page_size
    page_rows = matched[start : start + page_size]

    items = [
        PolicyBrowseItem(
            policy_key=row.policy_key,
            policy_name=row.policy_name,
            benefit_description=row.description,
            application_period=row.application_period,
            reference_url=row.apply_url,
            large_category=", ".join(category_tags(row.large_category)) or "기타",
            status=status,
            status_emoji=emoji,
        )
        for row, status, emoji in page_rows
    ]
    return items, total


# 이 스펙은 provider.chat(tools=[...])의 함수-호출 스키마 계약으로만 쓰인다 —
# 실제 검색은 search_policies()가 라우터에서 직접 수행하므로 entrypoint는
# 호출될 일이 없는 더미다. ToolRegistry/ALL_TOOL_SPECS에는 일부러 등록하지
# 않는다(/tools/{name}으로 범용 호출할 필요가 없는, 이 라우터 전용 계약).
FILTER_DELTA_SPEC = ToolSpec(
    name="policy_ai_filter_delta",
    description=(
        "대화에서 사용자가 이번 턴에 새로 언급하거나 바꾸고 싶어한 검색 조건만 담아 호출합니다. "
        "언급하지 않은 필드는 생략하세요 — 생략한 필드는 이전 값이 그대로 유지됩니다. "
        "반대로 이전에 적용된 조건을 이제 없애고 싶다면(사용자가 새 값을 안 주고 그냥 지워달라고 "
        "하는 경우) 그 필드 이름을 clear_fields 배열에 넣어서 호출하세요."
    ),
    input_schema=PolicyAiFilterDelta,
    output_schema=PolicyChatSearchInput,
    entrypoint=lambda input, ctx: input,
)
