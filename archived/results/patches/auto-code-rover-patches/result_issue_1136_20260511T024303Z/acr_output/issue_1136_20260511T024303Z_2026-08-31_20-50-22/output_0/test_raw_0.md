```python
# reproducer.py
import asyncio
import random
import sys
import traceback

from agentscope.agent import ReActAgent
from agentscope.formatter import DashScopeChatFormatter
from agentscope.memory import InMemoryMemory
from agentscope.message import Msg, TextBlock
from agentscope.model import DashScopeChatModel
from agentscope.tool import Toolkit, ToolResponse


def print_stacktrace(e: Exception):
    import traceback
    import sys
    tb = traceback.extract_tb(e.__traceback__)
    print("Traceback (most recent call last):", file=sys.stderr)
    for frame in tb:
        line_number = frame.lineno
        code_context = frame.line.strip() if frame.line else "Unknown"
        print(f'  File "{frame.filename}"', file=sys.stderr)
        print(f"    {line_number}: {code_context}", file=sys.stderr)
    print(f"{e.__class__.__name__}: {e}", file=sys.stderr)


async def calc_plus(
    num1: float,
    num2: float,
) -> ToolResponse:
    return ToolResponse(
        content=[
            TextBlock(
                type="text",
                text=str(num1 + num2),
            ),
        ]
    )


async def calc_minus(
    num1: float,
    num2: float,
) -> ToolResponse:
    return ToolResponse(
        content=[
            TextBlock(
                type="text",
                text=str(num1 - num2),
            ),
        ]
    )


async def get_weather(
    city: str,
) -> ToolResponse:
    weather_conditions = ["晴天", "多云", "雨天"]
    random_weather = random.choice(weather_conditions)
    location = city
    return ToolResponse(
        content=[
            TextBlock(
                type="text",
                text=f"{location}今天是{random_weather}。",
            ),
        ]
    )


async def creating_react_agent() -> None:
    """创建一个 ReAct 智能体并运行一个简单任务。"""
    toolkit = Toolkit()
    toolkit.register_tool_function(get_weather)
    toolkit.register_tool_function(calc_plus)
    toolkit.register_tool_function(calc_minus)

    jarvis = ReActAgent(
        name="Jarvis",
        sys_prompt="你是一个名为 Jarvis 的助手",
        model=DashScopeChatModel(
            model_name="qwen3-max",
            api_key="key",
            stream=True,
        ),
        formatter=DashScopeChatFormatter(),
        toolkit=toolkit,
        memory=InMemoryMemory(),
    )

    msg = Msg(
        name="user1",
        content="北京天气",
        role="user",
    )

    tool_calls = []

    # We override the __call__ method of ReActAgent instance to intercept tool_use events
    original_call = jarvis.__call__

    async def hook_call(message):
        # call the original __call__, which is async generator streaming responses
        # we will capture tool_use messages emitted during the stream
        async for resp in original_call(message):
            # Jarvis: {"type": "tool_use", ...} messages come from the agent
            # assume resp is a dict-like object or string that can be parsed
            # but agent may yield message string or dict-like with type
            # The safest way is to check if resp has "type" attribute or dict key

            # resp can be TextBlock or Msg or textual content depending on implementation
            # For safety, try to get dict representation if possible
            if hasattr(resp, "type") and resp.type == "tool_use":
                tool_calls.append(resp)
            elif isinstance(resp, dict) and resp.get("type") == "tool_use":
                tool_calls.append(resp)
            yield resp

    jarvis.__call__ = hook_call

    # Run conversation and consume the entire stream
    async for _ in jarvis(msg):
        pass

    # Restore original __call__ to avoid side effects
    jarvis.__call__ = original_call

    # Analyze tool_calls for repeated consecutive calls with identical parameters
    # We search for consecutive calls with identical tool name and input
    for i in range(len(tool_calls) - 1):
        c1 = tool_calls[i]
        c2 = tool_calls[i + 1]
        # For flexibility, check tool name and input equality
        # c1 and c2 might be object or dict
        try:
            name1 = c1.name if hasattr(c1, "name") else c1.get("name")
            name2 = c2.name if hasattr(c2, "name") else c2.get("name")

            input1 = c1.input if hasattr(c1, "input") else c1.get("input")
            input2 = c2.input if hasattr(c2, "input") else c2.get("input")
        except Exception as e:
            # Defensive: if cannot extract, skip
            continue

        if name1 == name2 and input1 == input2:
            raise AssertionError(
                f"Repeated consecutive tool calls detected with identical parameters:\n"
                f"Call {i}: {name1}({input1})\n"
                f"Call {i+1}: {name2}({input2})"
            )


def main():
    try:
        asyncio.run(creating_react_agent())
    except AssertionError as e:
        print_stacktrace(e)
        sys.exit(1)  # Non-zero exit indicates issue present
    except Exception as e:
        print_stacktrace(e)
        sys.exit(2)  # Other errors
    else:
        print("No repeated consecutive tool calls detected. Issue appears fixed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
```
