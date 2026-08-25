import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.router import get_current_user
from app.core.db import get_db
from app.features.policy_chat.schemas import ChatRequest, ChatResponse
from app.features.policy_chat.tool import TOOL_SPEC
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
