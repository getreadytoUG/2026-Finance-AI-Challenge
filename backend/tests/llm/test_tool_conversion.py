from pydantic import BaseModel

from app.llm.claude_provider import _to_claude_tools
from app.llm.openai_provider import _to_openai_tools
from app.tools.base import ToolSpec


class SampleInput(BaseModel):
    x: int


class SampleOutput(BaseModel):
    y: int


def _sample_spec() -> ToolSpec:
    return ToolSpec(
        name="sample_tool",
        description="a sample tool",
        input_schema=SampleInput,
        output_schema=SampleOutput,
        entrypoint=lambda i, ctx: SampleOutput(y=i.x),
    )


def test_to_claude_tools_produces_name_description_input_schema():
    result = _to_claude_tools([_sample_spec()])
    assert result == [
        {
            "name": "sample_tool",
            "description": "a sample tool",
            "input_schema": SampleInput.model_json_schema(),
        }
    ]


def test_to_openai_tools_produces_function_wrapper():
    result = _to_openai_tools([_sample_spec()])
    assert result == [
        {
            "type": "function",
            "function": {
                "name": "sample_tool",
                "description": "a sample tool",
                "parameters": SampleInput.model_json_schema(),
            },
        }
    ]
