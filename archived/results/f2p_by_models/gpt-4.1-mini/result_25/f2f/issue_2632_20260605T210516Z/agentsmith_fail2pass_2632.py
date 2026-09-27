import os
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from src.crewai.crew import Crew


def test_multithreaded_crew_kickoff_no_crash_and_valid_output():
    """
    Test that running multiple Crew kickoff calls concurrently using ThreadPoolExecutor
    does not crash and returns valid outputs.
    This test should fail on the buggy codebase due to segmentation fault or crashes,
    and pass after the fix.
    """
    payloads = [
        {"inputs": {"query": "Hello world 1"}},
        {"inputs": {"query": "Hello world 2"}},
        {"inputs": {"query": "Hello world 3"}},
        {"inputs": {"query": "Hello world 4"}},
        {"inputs": {"query": "Hello world 5"}},
    ]

    def generate_response(payload):
        try:
            # Use environment variables if needed inside Crew initialization or methods
            crew = Crew()
            output = crew.kickoff(inputs=payload["inputs"])
        except Exception:
            output = None
        return output

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(generate_response, payload) for payload in payloads]
        results = []
        for future in as_completed(futures):
            result = future.result()
            results.append(result)

    # Assert that all results are not None and have expected structure
    assert len(results) == len(payloads)
    for res in results:
        assert res is not None
        assert isinstance(res, dict)
        # Expecting the output dict to have a 'result' key or similar
        assert "result" in res or "outputs" in res or "choices" in res


@pytest.mark.asyncio
async def test_asyncio_crew_kickoff_no_crash_and_valid_output():
    """
    Test that running multiple Crew kickoff_async calls concurrently using asyncio
    does not crash and returns valid outputs.
    This test should fail on the buggy codebase due to segmentation fault or crashes,
    and pass after the fix.
    """
    payloads = [
        {"inputs": {"query": "Hello async 1"}},
        {"inputs": {"query": "Hello async 2"}},
        {"inputs": {"query": "Hello async 3"}},
        {"inputs": {"query": "Hello async 4"}},
        {"inputs": {"query": "Hello async 5"}},
    ]

    sem = asyncio.Semaphore(5)

    async def generate_response(payload):
        async with sem:
            try:
                crew = Crew()
                output = await crew.kickoff_async(inputs=payload["inputs"])
            except Exception:
                output = None
            return output

    tasks = [generate_response(payload) for payload in payloads]
    results = await asyncio.gather(*tasks)

    # Assert that all results are not None and have expected structure
    assert len(results) == len(payloads)
    for res in results:
        assert res is not None
        assert isinstance(res, dict)
        # Expecting the output dict to have a 'result' key or similar
        assert "result" in res or "outputs" in res or "choices" in res