import pytest
from pydantic import BaseModel

from app.tools.base import ToolSpec, ToolContext
from app.tools.errors import ToolExecutionError
from app.tools.registry import ToolRegistry


class SampleInput(BaseModel):
    x: int


class SampleOutput(BaseModel):
    doubled: int


def sample_run(input: SampleInput, ctx: ToolContext) -> SampleOutput:
    return SampleOutput(doubled=input.x * 2)


def failing_run(input: SampleInput, ctx: ToolContext) -> SampleOutput:
    raise ValueError("boom")


def make_spec(entrypoint=sample_run) -> ToolSpec:
    return ToolSpec(
        name="sample_tool",
        description="doubles a number",
        input_schema=SampleInput,
        output_schema=SampleOutput,
        entrypoint=entrypoint,
    )


def test_register_and_get_returns_same_spec():
    reg = ToolRegistry()
    spec = make_spec()
    reg.register(spec)
    assert reg.get("sample_tool") is spec


def test_register_duplicate_name_raises():
    reg = ToolRegistry()
    reg.register(make_spec())
    with pytest.raises(ValueError):
        reg.register(make_spec())


def test_get_unknown_tool_raises_keyerror():
    reg = ToolRegistry()
    with pytest.raises(KeyError):
        reg.get("does_not_exist")


def test_all_returns_every_registered_spec():
    reg = ToolRegistry()
    reg.register(make_spec())
    assert [s.name for s in reg.all()] == ["sample_tool"]


def test_execute_validates_input_and_runs_entrypoint():
    reg = ToolRegistry()
    reg.register(make_spec())
    ctx = ToolContext(user_id=1, db=None)
    result = reg.execute("sample_tool", {"x": 21}, ctx)
    assert result == SampleOutput(doubled=42)


def test_execute_wraps_entrypoint_exception_in_tool_execution_error():
    reg = ToolRegistry()
    reg.register(make_spec(entrypoint=failing_run))
    ctx = ToolContext(user_id=1, db=None)
    with pytest.raises(ToolExecutionError) as exc_info:
        reg.execute("sample_tool", {"x": 1}, ctx)
    assert exc_info.value.tool_name == "sample_tool"
