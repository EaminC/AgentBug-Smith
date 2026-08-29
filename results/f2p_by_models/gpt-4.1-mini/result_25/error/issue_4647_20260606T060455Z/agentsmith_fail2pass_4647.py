import os
import pytest
import asyncio

from crewai.llms.providers.gemini import completion
from google.genai import types


@pytest.mark.asyncio
async def test_gemini_completion_thoughts_in_stream():
    """
    Test that GeminiCompletion with a thinking model includes thought parts in streaming output.

    This test verifies that when using a thinking Gemini model (gemini-3.1-pro-preview),
    the streaming response includes thought content and that the thought chunks are emitted
    as LLMThinkingChunkEvent events.

    Expected behavior:
    - The thought content parts are emitted as separate thinking chunk events.
    - The full text response includes the concatenated text parts excluding thought parts.
    """

    # Use a GeminiCompletion instance with a thinking model (gemini-3.1-pro-preview)
    # This model version triggers thinking_config to include thoughts.
    model_name = "gemini/gemini-3.1-pro-preview"

    # Create the GeminiCompletion instance
    gemini = completion.GeminiCompletion(model=model_name)

    # Prepare a prompt that would trigger some reasoning/thought output
    prompt = "Explain the reasoning steps to solve 2+2."

    # We will collect emitted events by patching the event bus emit method
    emitted_thought_chunks = []
    emitted_stream_chunks = []

    # Patch the crewai_event_bus.emit method to capture emitted events
    # We do not mock the GeminiCompletion methods, only capture events.
    original_emit = completion.crewai_event_bus.emit

    def emit_capture(sender, event):
        # Capture thought chunk events separately
        if event.type == "llm_thinking_chunk":
            emitted_thought_chunks.append(event.chunk)
        elif event.type == "llm_stream_chunk":
            emitted_stream_chunks.append(event.chunk)
        # Call original emit to not break any logic
        return original_emit(sender, event)

    completion.crewai_event_bus.emit = emit_capture

    # Run the streaming completion call asynchronously
    # We use acall with stream=True to get streaming chunks
    # Collect the full text response returned by the method
    full_response = ""
    try:
        async for chunk in gemini.acall(
            prompt,
            stream=True,
        ):
            # chunk is a string text chunk from the stream
            full_response += chunk

    finally:
        # Restore the original emit method
        completion.crewai_event_bus.emit = original_emit

    # Assertions:

    # 1. The full response should be a non-empty string
    assert isinstance(full_response, str)
    assert len(full_response) > 0

    # 2. There should be at least one thought chunk emitted
    assert len(emitted_thought_chunks) > 0, "No thought chunks emitted from thinking model"

    # 3. Each thought chunk should be a non-empty string
    for thought_chunk in emitted_thought_chunks:
        assert isinstance(thought_chunk, str)
        assert len(thought_chunk) > 0

    # 4. The thought chunks should not be included in the normal stream chunks
    # (i.e., no overlap of thought chunk text in stream chunks)
    for thought_chunk in emitted_thought_chunks:
        for stream_chunk in emitted_stream_chunks:
            assert thought_chunk not in stream_chunk, "Thought chunk text found in normal stream chunks"

    # 5. The full response should contain the concatenated text parts excluding thought parts
    # This is a weak check: full_response should contain some expected text from prompt or reasoning
    assert "2+2" in full_response or "4" in full_response or "reasoning" in full_response.lower()


@pytest.mark.asyncio
async def test_prepare_generation_config_includes_thinking_config():
    """
    Test that _prepare_generation_config sets thinking_config for thinking models.

    This verifies that the thinking_config attribute is included in the GenerateContentConfig
    returned by _prepare_generation_config when the model version is >= 2.5.
    """

    model_name = "gemini/gemini-3.1-pro-preview"
    gemini = completion.GeminiCompletion(model=model_name)

    config = gemini._prepare_generation_config(system_instruction="test")

    # The returned config should be a GenerateContentConfig instance
    assert isinstance(config, types.GenerateContentConfig)

    # The thinking_config attribute should be set and include_thoughts should be True
    assert hasattr(config, "thinking_config")
    assert config.thinking_config is not None
    assert config.thinking_config.include_thoughts is True


def test_extract_text_from_response_excludes_thought_parts():
    """
    Test that _extract_text_from_response excludes thought parts from the returned text.
    """

    # Create a dummy GenerateContentResponse with parts including thought and non-thought parts
    from google.genai import types as genai_types

    part1 = genai_types.ContentPart(text="Hello ", thought=False)
    part2 = genai_types.ContentPart(text="this is a thought", thought=True)
    part3 = genai_types.ContentPart(text="world!", thought=False)

    candidate = genai_types.GenerateContentCandidate(content=genai_types.Content(parts=[part1, part2, part3]))
    response = genai_types.GenerateContentResponse(candidates=[candidate])

    # Call the method under test
    text = completion._extract_text_from_response(response)

    # The returned text should include only non-thought parts concatenated
    assert text == "Hello world!"
    # It should not include the thought part text
    assert "thought" not in text


@pytest.mark.asyncio
async def test_process_stream_chunk_emits_thought_events(monkeypatch):
    """
    Test that _process_stream_chunk emits LLMThinkingChunkEvent for thought parts.

    This test mocks a stream chunk with thought parts and verifies that the thinking chunk event is emitted.
    """

    # Create a GeminiCompletion instance with thinking_config enabled
    model_name = "gemini/gemini-3.1-pro-preview"
    gemini = completion.GeminiCompletion(model=model_name)

    # Prepare a dummy chunk with candidates including thought parts
    from google.genai import types as genai_types

    thought_text = "This is a reasoning step."
    normal_text = "Normal text chunk."

    thought_part = genai_types.ContentPart(text=thought_text, thought=True)
    normal_part = genai_types.ContentPart(text=normal_text, thought=False)
    candidate = genai_types.GenerateContentCandidate(content=genai_types.Content(parts=[thought_part, normal_part]))
    chunk = genai_types.GenerateContentResponse(candidates=[candidate])

    # Variables to capture emitted events
    emitted_thought_chunks = []
    emitted_stream_chunks = []

    # Patch the event bus emit method to capture emitted events
    original_emit = completion.crewai_event_bus.emit

    def emit_capture(sender, event):
        if event.type == "llm_thinking_chunk":
            emitted_thought_chunks.append(event.chunk)
        elif event.type == "llm_stream_chunk":
            emitted_stream_chunks.append(event.chunk)
        return original_emit(sender, event)

    completion.crewai_event_bus.emit = emit_capture

    # Call _process_stream_chunk with the dummy chunk
    full_response = ""
    function_calls = []
    usage_data = {}

    try:
        # _process_stream_chunk is a synchronous method, run in thread to await
        full_response, function_calls, usage_data = await asyncio.to_thread(
            gemini._process_stream_chunk,
            chunk,
            full_response,
            function_calls,
            usage_data,
            None,
            None,
        )
    finally:
        completion.crewai_event_bus.emit = original_emit

    # Assertions
    # The thought chunk should be emitted
    assert any(thought_text in chunk for chunk in emitted_thought_chunks), "Thought chunk event not emitted"

    # The normal text should be included in stream chunks and full_response
    assert any(normal_text in chunk for chunk in emitted_stream_chunks), "Normal text chunk event not emitted"
    assert normal_text in full_response

    # The thought text should not be included in full_response
    assert thought_text not in full_response