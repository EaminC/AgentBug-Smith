import base64
import pytest

from agentscope.message import Base64Source, DataBlock
from agentscope.tool import ToolChunk, ToolResponse


def test_tool_response_merges_base64_chunks_by_bytes():
    """Base64 chunks with padding should merge as bytes, not strings."""
    response = ToolResponse()
    first = base64.b64encode(b"hello").decode("ascii")
    second = base64.b64encode(b"world").decode("ascii")

    response.append_chunk(
        ToolChunk(
            content=[
                DataBlock(
                    id="image",
                    source=Base64Source(
                        data=first,
                        media_type="image/png",
                    ),
                ),
            ],
        ),
    )
    response.append_chunk(
        ToolChunk(
            content=[
                DataBlock(
                    id="image",
                    source=Base64Source(
                        data=second,
                        media_type="image/png",
                    ),
                ),
            ],
        ),
    )

    assert len(response.content) == 1
    merged = response.content[0]
    assert isinstance(merged, DataBlock)
    # The merged base64 string should decode to b"helloworld"
    assert base64.b64decode(merged.source.data) == b"helloworld"
