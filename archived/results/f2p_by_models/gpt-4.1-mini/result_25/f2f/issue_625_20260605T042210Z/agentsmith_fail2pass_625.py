import os
import threading
import time
import pytest

from agentscope.agents import ReActAgentV2
from agentscope.message import Msg
from agentscope.service import ServiceToolkit
from agentscope.formatters import OpenAIFormatter
import agentscope


@pytest.fixture(scope="module")
def start_mcp_servers():
    """
    Start the MCP servers from examples/reactv2_agent_with_mcp/code/mcp_servers.py
    in a background thread using uvicorn.
    If uvicorn is not installed, this fixture will fail to import and cause the test to error,
    which is expected in the buggy state.
    """
    import uvicorn
    from examples.reactv2_agent_with_mcp.code.mcp_servers import main_app

    server_thread = threading.Thread(
        target=uvicorn.run,
        args=(main_app,),
        kwargs={"host": "127.0.0.1", "port": 8001, "log_level": "critical"},
        daemon=True,
    )
    server_thread.start()
    # Wait a bit for the server to start
    time.sleep(2)
    yield
    # No explicit shutdown, daemon thread will exit with process


def test_react_agent_v2_with_streamable_http_mcp(start_mcp_servers):
    """
    This test verifies that the ReActAgentV2 can correctly use MCP servers
    with streamable HTTP client support.

    It uses the example code from examples/reactv2_agent_with_mcp/code/reactv2_agent_with_http_mcp_demo.py
    but runs it as a test and asserts the correctness of the result.

    On the buggy codebase, this test should fail (e.g., by raising an exception or producing wrong output)
    because streamable_http type is not supported.
    After applying the fix, the test should pass.
    """
    # Initialize agentscope with the same configs as the example
    model_name = "qwen-plus"
    custom_api_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    agentscope.init(
        model_configs=[
            {
                "config_name": "my_config",
                "model_type": "dashscope_chat",
                "model_name": "qwen-plus",
            },
            {
                "config_name": "my_config2",
                "client_args": {
                    "base_url": custom_api_url,
                },
                "api_key": os.getenv("OPENAI_API_KEY", "dummy_api_key_for_test"),
                "model_type": "openai_chat",
                "model_name": model_name,
            },
        ],
    )
    OpenAIFormatter.supported_model_regexes.append(model_name)

    # Setup MCP servers in the toolkit
    toolkit = ServiceToolkit()
    toolkit.add_mcp_servers(
        {
            "mcpServers": {
                "add-tool": {
                    "type": "sse",
                    "url": "http://127.0.0.1:8001/sse_app/sse",
                },
                "multiply-tool": {
                    "type": "streamable_http",
                    "url": "http://127.0.0.1:8001/streamable_http_app/mcp/",
                },
            },
        },
    )

    agent = ReActAgentV2(
        name="Friday",
        max_iters=3,
        model_config_name="my_config",
        service_toolkit=toolkit,
        sys_prompt="You're a helpful assistant named Friday.",
    )

    # Compose a query that requires both tools
    query = (
        "Calculate 2345 multiplied by 3456, then add 4567 to the result, "
        "what is the final outcome?"
    )
    msg = Msg("user", query, "user")

    # Run the agent and get the response
    res_msg = agent(msg)

    # The expected result is 2345*3456 + 4567 = 8107920 + 4567 = 8112487
    expected_answer = "8112487"

    # Check that the response content contains the expected answer as a substring
    # (The agent may include explanation or formatting)
    assert expected_answer in res_msg.content, f"Expected answer {expected_answer} not found in response: {res_msg.content}"