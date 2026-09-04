import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.router import get_current_user
from app.core.db import get_db
from app.features.policy_chat.ai_search import FILTER_DELTA_SPEC, search_policies
from app.features.policy_chat.analysis import _policy_text, _profile_text, generate_policy_report
from app.features.policy_chat.schemas import (
    AiSearchMessageRequest,
    AiSearchMessageResponse,
    AiSearchResultsResponse,
    ChatRequest,
    ChatResponse,
    PolicyAnalysisRequest,
    PolicyAnalysisResponse,
    PolicyChatSearchInput,
    PolicyQaRequest,
    PolicyQaResponse,
)
from app.features.policy_chat.tool import TOOL_SPEC
from app.features.policy_matcher.categories import PolicyCategoryTag
from app.features.policy_matcher.matching import PolicyRegion
from app.features.policy_matcher.models import CachedPolicy
from app.features.policy_matcher.schemas import OccupationType
from app.features.policy_matcher.status import PolicyStatusLabel
from app.llm.base import Message
from app.llm.factory import get_provider
from app.tools.base import ToolContext
from app.tools.registry import ToolRegistry, get_tool_registry

router = APIRouter()
logger = logging.getLogger(__name__)

MAX_HISTORY = 10


def _raise_as_http_500(endpoint: str, context: str, e: Exception) -> None:
    # policy_matcher/router.py와 동일한 이유: CORSMiddleware가 처리하는 예외
    # 경로를 타게 해서 브라우저가 "Failed to fetch"로 뭉개지 않고 에러를 보게 한다.
    logger.exception(f"[ERROR] {endpoint} failed{context}: {type(e).__name__}: {e}")
    raise HTTPException(status_code=500, detail=str(e))


def _build_system_prompt(user: User) -> str:
    profile_lines = []
    if user.age is not None:
        profile_lines.append(f"나이: {user.age}세")
    if user.is_married is not None:
        profile_lines.append(f"기혼 여부: {'기혼' if user.is_married else '미혼'}")
    if user.annual_income_krw is not None:
        profile_lines.append(f"연소득: {user.annual_income_krw:,}원")
    if user.is_married and user.spouse_annual_income_krw is not None:
        profile_lines.append(f"배우자 연소득: {user.spouse_annual_income_krw:,}원")
    if user.region is not None:
        profile_lines.append(f"거주 지역: {user.region}")
    profile_text = "\n".join(profile_lines) if profile_lines else "(등록된 정보 없음)"

    return (
        "당신은 청년/신혼부부를 위한 금융 지원 정책 추천 챗봇입니다. "
        "사용자가 원하는 조건을 말하면 policy_chat_search 도구를 호출해 정책을 검색하세요. "
        "사용자의 기존 프로필 정보는 아래와 같으니, 대화에서 다시 언급되지 않으면 이 값을 "
        "그대로 사용하고 되묻지 마세요. 도구가 찾지 못한 조건(예: 프로필에 없는 정보인데 "
        "질문에 필요한 경우)만 사용자에게 되물으세요. 없는 정보를 추측해서 지어내지 마세요.\n\n"
        f"[사용자 프로필]\n{profile_text}\n\n"
        "검색 결과를 받으면 정책 이름과 신청 방법(링크)을 포함해 친절한 한국어로 답변하세요. "
        "결과가 없으면 솔직히 없다고 말하세요."
    )


@router.post("/message", response_model=ChatResponse)
def send_chat_message(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    tool_registry: ToolRegistry = Depends(get_tool_registry),
):
    try:
        provider = get_provider()
        history = payload.messages[-MAX_HISTORY:]
        messages = [Message(role="system", content=_build_system_prompt(current_user))] + [
            Message(role=m.role, content=m.content) for m in history
        ]

        first = provider.chat(messages, tools=[TOOL_SPEC])

        if not first.tool_calls:
            return ChatResponse(reply=first.content or "", policies=[])

        call = first.tool_calls[0]
        args = dict(call.arguments)
        if args.get("age") is None and current_user.age is not None:
            args["age"] = current_user.age
        if args.get("is_married") is None and current_user.is_married is not None:
            args["is_married"] = current_user.is_married
        if args.get("annual_income_krw") is None and current_user.annual_income_krw is not None:
            args["annual_income_krw"] = current_user.annual_income_krw
        if args.get("spouse_annual_income_krw") is None and current_user.spouse_annual_income_krw is not None:
            args["spouse_annual_income_krw"] = current_user.spouse_annual_income_krw
        if args.get("region") is None and current_user.region is not None:
            args["region"] = current_user.region

        ctx = ToolContext(user_id=current_user.id, db=db)
        result = tool_registry.execute(TOOL_SPEC.name, args, ctx)

        results_json = json.dumps([o.model_dump() for o in result.options], ensure_ascii=False)
        follow_up = Message(
            role="user",
            content=(
                f"(검색 결과)\n{results_json}\n\n"
                "위 검색 결과를 바탕으로 사용자 질문에 자연스러운 한국어로 답변해줘. "
                "결과가 비어있으면 조건에 맞는 정책을 못 찾았다고 솔직히 말해줘."
            ),
        )
        second = provider.chat(messages + [follow_up], tools=[])

        return ChatResponse(reply=second.content or "", policies=result.options[:5])
    except Exception as e:
        _raise_as_http_500("/policy_chat/message", f" for user_id={current_user.id}", e)


def _profile_default_filters(user: User) -> PolicyChatSearchInput:
    return PolicyChatSearchInput(
        age=user.age,
        is_married=user.is_married,
        annual_income_krw=user.annual_income_krw,
        spouse_annual_income_krw=user.spouse_annual_income_krw,
        region=user.region,
        occupation=user.occupation,
        is_sme_employee=user.is_sme_employee,
    )


def _describe_filters(filters: PolicyChatSearchInput) -> str:
    lines = []
    if filters.age is not None:
        lines.append(f"나이: {filters.age}세")
    if filters.is_married is not None:
        lines.append(f"기혼 여부: {'기혼' if filters.is_married else '미혼'}")
    if filters.annual_income_krw is not None:
        lines.append(f"연소득: {filters.annual_income_krw:,}원")
    if filters.spouse_annual_income_krw is not None:
        lines.append(f"배우자 연소득: {filters.spouse_annual_income_krw:,}원")
    if filters.region is not None:
        lines.append(f"지역: {filters.region}")
    if filters.category is not None:
        lines.append(f"카테고리: {filters.category}")
    if filters.keyword is not None:
        lines.append(f"키워드: {filters.keyword}")
    if filters.status is not None:
        lines.append(f"신청 상태: {filters.status}")
    if filters.disability_target:
        lines.append("장애인 대상 정책만")
    if filters.veteran_target:
        lines.append("국가보훈대상자 대상 정책만")
    return "\n".join(lines) if lines else "(적용된 조건 없음 — 전체 정책 대상)"


def _build_ai_search_system_prompt(filters: PolicyChatSearchInput) -> str:
    return (
        "당신은 청년/신혼부부를 위한 정책 검색 도우미입니다. 화면 오른쪽에는 현재 적용된 "
        "검색 조건에 맞는 정책 목록이 실시간으로 표시됩니다. "
        "사용자가 조건을 새로 언급하거나 바꾸고 싶어하면 policy_ai_filter_delta 도구를 호출해 "
        "이번 턴에 바뀐 필드만 담아 넘기세요 — 언급하지 않은 필드는 생략하세요(생략하면 "
        "아래 현재 조건이 그대로 유지됩니다). 조건 변경 요청이 아니라 단순 질문이면 도구를 "
        "호출하지 말고 바로 답하세요.\n\n"
        "region/category/status는 반드시 도구 스키마에 정의된 목록 중 하나여야 합니다 — 목록에 "
        "없는 값을 만들어내지 마세요. 특히 '마감 임박', '곧 마감' 같은 표현은 keyword가 아니라 "
        "status='임박'으로, '마감된 것도/지난 것도 보여줘'는 status='만료'로 담으세요.\n\n"
        "keyword는 '지금 사용자가 찾고 있는 검색어 하나'를 뜻합니다 — 사용자가 이전과 다른 "
        "대상/단어를 새로 언급하면 이전 keyword에 더하지 말고 새 값으로 완전히 교체해서 "
        "호출하세요. 옛 keyword가 그대로 남아있으면 새 검색어와 AND로 겹쳐져서 결과가 계속 "
        "0건으로 나올 수 있습니다.\n\n"
        "사용자가 특정 조건을 새 값으로 바꾸는 게 아니라 그냥 없애고 싶어하면(예: '조건 초기화해줘', "
        "'키워드 지워줘', '전체 정책 다 보여줘', '그 조건 말고 그냥 검색해줘') 그 필드 이름을 "
        "clear_fields 배열에 담아 호출하세요. 무엇을 지워야 할지 모호하면 keyword/category/status처럼 "
        "이번 대화에서 최근에 언급된 검색 조건부터 지우는 쪽으로 판단하세요.\n\n"
        f"[현재 적용된 조건]\n{_describe_filters(filters)}\n\n"
        "답변은 짧고 친절한 한국어로, 조건이 바뀌었으면 어떻게 좁혀졌는지 한두 문장으로 알려주세요."
    )


@router.post("/ai_search/message", response_model=AiSearchMessageResponse)
def send_ai_search_message(
    payload: AiSearchMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        base_filters = payload.filters or _profile_default_filters(current_user)

        provider = get_provider()
        history = payload.messages[-MAX_HISTORY:]
        messages = [Message(role="system", content=_build_ai_search_system_prompt(base_filters))] + [
            Message(role=m.role, content=m.content) for m in history
        ]

        first = provider.chat(messages, tools=[FILTER_DELTA_SPEC])

        new_filters = base_filters
        if first.tool_calls:
            call = first.tool_calls[0]
            raw_args = dict(call.arguments)
            clear_fields = raw_args.pop("clear_fields", None) or []
            delta = {k: v for k, v in raw_args.items() if v is not None}
            try:
                # model_copy(update=...)는 검증을 건너뛰므로, 모델이 스키마에 없는 값을
                # 잘못 내놓더라도 여기서 다시 PolicyChatSearchInput(**...)로 만들어 Literal
                # 제약을 실제로 재검증한다. 드물게 모델이 enum 밖 값을 내면(공급자가 tool
                # 스키마의 enum을 완벽히 지키지 못하는 경우) 이번 턴은 필터를 바꾸지 않는다.
                merged = {**base_filters.model_dump(), **delta}
                for field in clear_fields:
                    merged[field] = None
                new_filters = PolicyChatSearchInput(**merged)
            except ValidationError as e:
                logger.warning(f"[WARN] /policy_chat/ai_search/message got invalid filter delta {delta}: {e}")
                new_filters = base_filters

        # 도구를 호출하지 않은 턴(단순 질문)도 항상 실제 검색 결과로 답변을 재생성한다 —
        # 예전에는 이 경우 LLM의 1차 응답 텍스트를 그대로 믿고 돌려줬는데, 그 텍스트는
        # 실제 검색 결과를 전혀 보지 못한 채 나온 추측이라 화면에 뜨는 결과와 다른 말을
        # 하는 경우가 있었다(2026-08-27 실사용 중 발견 — 옛 keyword가 안 지워진 채로
        # "찾을 수 없다"고 답하는데 실제로는 다른 필터 조합 때문에 0건이었음).
        items, total = search_policies(
            db, new_filters, include_closed=payload.include_closed, page=1, page_size=payload.page_size
        )

        top_names = [item.policy_name for item in items[:3]]
        synth = Message(
            role="user",
            content=(
                f"(검색 결과) 총 {total}건을 찾았습니다. 상위 정책명: {', '.join(top_names) or '없음'}\n\n"
                "위 검색 결과를 바탕으로 사용자에게 자연스러운 한국어로 짧게 답변해줘. "
                "결과가 0건이면 조건에 맞는 정책이 없다고 솔직히 말해줘."
            ),
        )
        second = provider.chat(messages + [synth], tools=[])

        return AiSearchMessageResponse(
            reply=second.content or "",
            filters=new_filters,
            items=items,
            total=total,
            page=1,
            page_size=payload.page_size,
        )
    except Exception as e:
        _raise_as_http_500("/policy_chat/ai_search/message", f" for user_id={current_user.id}", e)


@router.get("/ai_search/results", response_model=AiSearchResultsResponse)
def get_ai_search_results(
    age: int | None = None,
    is_married: bool | None = None,
    annual_income_krw: int | None = None,
    spouse_annual_income_krw: int | None = None,
    region: PolicyRegion | None = None,
    category: PolicyCategoryTag | None = None,
    keyword: str | None = None,
    status: PolicyStatusLabel | None = None,
    disability_target: bool | None = None,
    veteran_target: bool | None = None,
    occupation: OccupationType | None = None,
    is_sme_employee: bool | None = None,
    include_closed: bool = False,
    page: int = 1,
    page_size: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        filters = PolicyChatSearchInput(
            age=age,
            is_married=is_married,
            annual_income_krw=annual_income_krw,
            spouse_annual_income_krw=spouse_annual_income_krw,
            region=region,
            category=category,
            keyword=keyword,
            status=status,
            disability_target=disability_target,
            veteran_target=veteran_target,
            occupation=occupation,
            is_sme_employee=is_sme_employee,
        )
        items, total = search_policies(db, filters, include_closed=include_closed, page=page, page_size=page_size)
        return AiSearchResultsResponse(items=items, total=total, page=page, page_size=page_size)
    except Exception as e:
        _raise_as_http_500("/policy_chat/ai_search/results", f" for user_id={current_user.id}", e)


@router.post("/ai_search/analyze", response_model=PolicyAnalysisResponse)
def analyze_ai_search_policy(
    payload: PolicyAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 카드마다 자동으로 분석을 돌리면 LLM 호출 비용이 정책 개수만큼 쌓이므로,
    # 사용자가 "AI 분석 리포트 보기" 버튼을 눌렀을 때만 1건씩 온디맨드로 호출한다.
    try:
        policy = db.query(CachedPolicy).filter(CachedPolicy.policy_key == payload.policy_key).first()
        if policy is None:
            raise HTTPException(status_code=404, detail="정책을 찾을 수 없습니다.")
        result = generate_policy_report(current_user, policy)
        return PolicyAnalysisResponse(**result.model_dump())
    except HTTPException:
        raise
    except Exception as e:
        _raise_as_http_500("/policy_chat/ai_search/analyze", f" for user_id={current_user.id}", e)


def _build_policy_qa_system_prompt(user: User, policy: CachedPolicy) -> str:
    return (
        "당신은 청년/신혼부부를 위한 정책 QA 도우미입니다. 사용자는 지금 아래 정책 하나를 보고 "
        "있고, 이 정책에 대해서만 질문합니다. 아래 정책 정보에 근거해 친절한 한국어로 답변하세요. "
        "정책 정보에 없는 내용은 추측해서 지어내지 말고 모른다고 솔직히 답하세요. 사용자 프로필을 "
        "참고해 자격 여부, 준비할 서류 같은 개인화된 조언도 자연스럽게 곁들이세요.\n\n"
        f"[정책 정보]\n{_policy_text(policy)}\n\n"
        f"[사용자 프로필]\n{_profile_text(user)}"
    )


@router.post("/policy_qa/message", response_model=PolicyQaResponse)
def send_policy_qa_message(
    payload: PolicyQaRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        policy = db.query(CachedPolicy).filter(CachedPolicy.policy_key == payload.policy_key).first()
        if policy is None:
            raise HTTPException(status_code=404, detail="정책을 찾을 수 없습니다.")

        provider = get_provider()
        history = payload.messages[-MAX_HISTORY:]
        messages = [Message(role="system", content=_build_policy_qa_system_prompt(current_user, policy))] + [
            Message(role=m.role, content=m.content) for m in history
        ]
        response = provider.chat(messages, tools=[])
        return PolicyQaResponse(reply=response.content or "")
    except HTTPException:
        raise
    except Exception as e:
        _raise_as_http_500("/policy_chat/policy_qa/message", f" for user_id={current_user.id}", e)
