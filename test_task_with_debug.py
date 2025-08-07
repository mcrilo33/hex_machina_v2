#!/usr/bin/env python3
"""Test task execution with debug logging."""

import asyncio
import json
import logging

from src.hex_machina.enrichment.tasks.runner import task_runner

# Set up debug logging
logging.basicConfig(level=logging.DEBUG)


async def test_task_with_debug():
    """Test task execution with debug logging."""

    # Load test data
    with open("test_db_article_input.json", "r") as f:
        input_data = json.load(f)

    print("Input data:", input_data)

    # Test article detection
    print("\n=== Testing Article Detection ===")
    article_context = task_runner._detect_article_context(input_data)
    print("Article context:", article_context)

    # Test task execution
    print("\n=== Testing Task Execution ===")
    try:
        result = await task_runner.run_task(
            task_name="ContentCompletenessLangChainTask", input_data=input_data
        )
        print("Task result:", result)
    except Exception as e:
        print(f"Task execution error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_task_with_debug())
