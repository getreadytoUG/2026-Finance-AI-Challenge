from pydantic import BaseModel

from app.tools.base import ToolContext, ToolSpec
from app.tools.errors import ToolExecutionError


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        if spec.name in self._tools:
            raise ValueError(f"Tool '{spec.name}' is already registered")
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec:
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not found")
        return self._tools[name]

    def all(self) -> list[ToolSpec]:
        return list(self._tools.values())

    def execute(self, name: str, raw_input: dict, ctx: ToolContext) -> BaseModel:
        spec = self.get(name)
        parsed_input = spec.input_schema.model_validate(raw_input)
        try:
            return spec.entrypoint(parsed_input, ctx)
        except Exception as e:
            print(f"[ERROR] tool '{name}' entrypoint raised: {e}")
            raise ToolExecutionError(name, str(e)) from e


registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    return registry
