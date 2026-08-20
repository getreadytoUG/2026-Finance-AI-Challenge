from fastapi import APIRouter, Depends
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.router import get_current_user
from app.core.db import get_db
from app.llm.base import LLMProvider, Message
from app.llm.factory import get_provider
from app.tools.base import ToolContext
from app.tools.errors import ToolExecutionError
from app.tools.registry import ToolRegistry, get_tool_registry

router = APIRouter()

MAX_TOOL_ITERATIONS = 5


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


def get_llm_provider() -> LLMProvider:
    return get_provider()


@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    provider: LLMProvider = Depends(get_llm_provider),
    tool_registry: ToolRegistry = Depends(get_tool_registry),
):
    ctx = ToolContext(user_id=current_user.id, db=db)
    tools = tool_registry.all()
    messages = [Message(role="user", content=request.message)]

    response = provider.chat(messages, tools)

    iterations = 0
    while response.tool_calls and iterations < MAX_TOOL_ITERATIONS:
        for call in response.tool_calls:
            try:
                result = tool_registry.execute(call.name, call.arguments, ctx)
                result_text = result.model_dump_json()
            except (KeyError, ValidationError, ToolExecutionError) as e:
                # A bad tool name/arguments from the LLM shouldn't 500 the
                # request — report it back into the conversation so the LLM
                # (or the user) can see what went wrong and retry.
                result_text = f"Error: {e}"
            messages.append(Message(role="assistant", content=f"[calling tool {call.name}]"))
            messages.append(Message(role="user", content=f"[tool result for {call.name}] {result_text}"))
        response = provider.chat(messages, tools)
        iterations += 1

    return ChatResponse(reply=response.content or "")
