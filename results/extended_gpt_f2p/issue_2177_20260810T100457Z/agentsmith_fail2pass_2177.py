from agentscope.message import TextBlock, ToolResultState
from agentscope.tool import ToolChunk, ToolResponse


def test_toolresponse_preserves_error_state_when_appending_chunks():
    response = ToolResponse()
    response.append_chunk(
        ToolChunk(
            content=[TextBlock(text="failed")],
            state=ToolResultState.ERROR,
        ),
    )
    response.append_chunk(
        ToolChunk(
            content=[TextBlock(text="interrupted")],
            state=ToolResultState.INTERRUPTED,
        ),
    )
    # The response state should remain ERROR after appending a less severe state chunk
    assert response.state == ToolResultState.ERROR

    response = ToolResponse()
    response.append_chunk(
        ToolChunk(
            content=[TextBlock(text="failed")],
            state=ToolResultState.ERROR,
        ),
    )
    response.append_chunk(
        ToolChunk(
            content=[TextBlock(text="denied")],
            state=ToolResultState.DENIED,
        ),
    )
    # The response state should remain ERROR after appending a less severe state chunk
    assert response.state == ToolResultState.ERROR

    # Also test that if no ERROR state was set, the state updates normally
    response = ToolResponse()
    response.append_chunk(
        ToolChunk(
            content=[TextBlock(text="interrupted")],
            state=ToolResultState.INTERRUPTED,
        ),
    )
    response.append_chunk(
        ToolChunk(
            content=[TextBlock(text="denied")],
            state=ToolResultState.DENIED,
        ),
    )
    # The last state is DENIED, so the response state should be DENIED
    assert response.state == ToolResultState.DENIED

    # Test that ERROR state is set if appended chunk is ERROR even after INTERRUPTED
    response = ToolResponse()
    response.append_chunk(
        ToolChunk(
            content=[TextBlock(text="interrupted")],
            state=ToolResultState.INTERRUPTED,
        ),
    )
    response.append_chunk(
        ToolChunk(
            content=[TextBlock(text="failed")],
            state=ToolResultState.ERROR,
        ),
    )
    assert response.state == ToolResultState.ERROR
