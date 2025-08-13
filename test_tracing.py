#!/usr/bin/env python3
"""
Test script for the enhanced TaskBuilder with LangSmith tracing.

This script tests the new invoke_with_tracing method that creates
proper traces with metadata and tags.
"""

import os
import sys

import yaml

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

try:
    from hex_machina.langchain_tasks.builder import TaskBuilder
    from hex_machina.langchain_tasks.registry import RunnableRegistry

    print("✅ Successfully imported LCEL builder modules")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)


def test_tracing():
    """Test the new tracing functionality."""

    print("\n🧪 Testing TaskBuilder with LangSmith Tracing")
    print("=" * 50)

    try:
        # Load environment variables
        from dotenv import load_dotenv

        load_dotenv()
        print("✅ Environment variables loaded")

        # Check LangSmith configuration
        import os

        tracing_enabled = os.getenv("LANGCHAIN_TRACING_V2") == "true"
        project_name = os.getenv("LANGCHAIN_PROJECT", "default")
        print(f"📊 LangSmith Tracing: {'Enabled' if tracing_enabled else 'Disabled'}")
        print(f"📊 Project: {project_name}")

        # Create registry and builder
        registry = RunnableRegistry()
        builder = TaskBuilder(registry)
        print(f"✅ Created TaskBuilder: {builder}")

        # Load task configuration
        with open("test_task_config.yaml", "r") as file:
            config = yaml.safe_load(file)
        print(f"✅ Loaded task config: {config['name']}")

        # Test input
        test_input = {"name": "Alice"}
        print(f"📥 Test input: {test_input}")

        # Execute with tracing
        print("\n🚀 Executing task with tracing...")
        result = builder.invoke_with_tracing(config, test_input)

        print("✅ Task executed successfully!")
        print(f"📤 Result: {result}")

        print("\n🎯 What to check in LangSmith:")
        print("1. Go to: https://smith.langchain.com/")
        print("2. Navigate to project: hex-machina-v2")
        print("3. Look for trace: 'Task: simple_hello_task'")
        print("4. Check metadata, tags, and nested steps")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_tracing()

    if success:
        print("\n🎉 Tracing test completed successfully!")
        print("Check LangSmith for the trace with proper metadata and tags.")
    else:
        print("\n🔧 Test failed. Please check the error messages above.")
        sys.exit(1)
