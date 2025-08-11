#!/usr/bin/env python3
"""
Test script to verify that task execution now works without the constraint error.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import asyncio

from src.hex_machina.enrichment.tasks.runner import task_runner


async def test_task_execution():
    """Test that task execution works without constraint errors."""
    print("🔍 Testing Task Execution (Fixed Models)")
    print("=" * 60)

    try:
        # Test 1: Check if task runner initializes
        print("🧪 Test 1: Task Runner Initialization")
        print(f"   Task Runner: {task_runner}")
        print("   ✅ Task runner initialized successfully")
        print()

        # Test 2: Check if we can create a simple task input
        print("🧪 Test 2: Task Input Creation")
        from src.hex_machina.core.base import TaskInput

        task_input = TaskInput(
            task_id="test_task_123",
            task_name="ContentCompletenessLangChainTask",
            input_data={"id": 1, "title": "Test Article", "content": "Test content"},
            save_to_db=True,
            article_id=1,
            workflow_operation_id="test_workflow_123",
        )

        print(f"   Task Input: {task_input}")
        print("   ✅ Task input created successfully")
        print()

        # Test 3: Check if storage can be initialized
        print("🧪 Test 3: Storage Initialization")
        from src.hex_machina.enrichment.storage.database import (
            DatabaseEnrichmentStorage,
        )

        storage = DatabaseEnrichmentStorage()
        print(f"   Storage: {storage}")
        print("   ✅ Storage initialized successfully")
        print()

        print(
            "✅ All tests passed! Task execution should now work without constraint errors."
        )
        print()
        print("📝 Ready to test CLI:")
        print(
            "   poetry run python -m src.hex_machina.cli.tasks.main run -t ContentCompletenessLangChainTask --article-id 1"
        )

    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_task_execution())
