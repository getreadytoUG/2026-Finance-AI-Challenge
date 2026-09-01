import logging

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
logger = logging.getLogger(__name__)


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
    except KeyError as e:
        print(f"[ERROR] /tools/{name} not found: {e}")
        raise HTTPException(status_code=404, detail=f"Tool '{name}' not found")
    except ValidationError as e:
        print(f"[ERROR] /tools/{name} input validation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ToolExecutionError as e:
        logger.exception(f"[ERROR] Tool '{name}' execution failed: {e.message}")
        raise HTTPException(status_code=400, detail=f"Tool '{name}' failed to execute")
    return result
