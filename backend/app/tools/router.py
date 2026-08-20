from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.router import get_current_user
from app.core.db import get_db
from app.tools.base import ToolContext
from app.tools.errors import ToolExecutionError
from app.tools.registry import ToolRegistry, get_tool_registry

router = APIRouter()


@router.post("/{name}")
def run_tool(
    name: str,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tool_registry: ToolRegistry = Depends(get_tool_registry),
):
    ctx = ToolContext(user_id=current_user.id, db=db)
    try:
        result = tool_registry.execute(name, payload, ctx)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Tool '{name}' not found")
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ToolExecutionError as e:
        raise HTTPException(status_code=400, detail=e.message)
    return result
