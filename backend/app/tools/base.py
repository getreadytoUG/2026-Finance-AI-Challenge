from typing import Any, Callable

from pydantic import BaseModel, ConfigDict


class ToolContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    user_id: int
    db: Any


class ToolSpec(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    description: str
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    entrypoint: Callable[[BaseModel, ToolContext], BaseModel]
