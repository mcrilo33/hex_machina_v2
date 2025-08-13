#!/usr/bin/env python3
"""
Test script for the enhanced TaskBuilder with improved step tagging.

This script tests the new step-specific tags like:
- step:1:generate_greeting
- step:2:llm_response
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


def test_enhanced_tracing():
    """Test the enhanced tracing with step-specific tags."""

    print("\n🧪 Testing Enhanced TaskBuilder with Step-Specific Tags")
    print("=" * 60)

    try:
        # Load environment variables
        from dotenv import load_dotenv

        load_dotenv()
        print("✅ Environment variables loaded")

        # Create registry and builder
        registry = RunnableRegistry()
        builder = TaskBuilder(registry)
        print(f"✅ Created TaskBuilder: {builder}")

        # Load task configuration
        with open("test_task_config.yaml", "r") as file:
            config = yaml.safe_load(file)
        print(f"✅ Loaded task config: {config['name']}")

        # Show expected step tags
        print("\n📋 Expected step tags:")
        for i, step in enumerate(config["steps"], 1):
            print(f"   step:{i}:{step['name']}")

        # Test input
        test_input = {"name": "Bob"}
        print(f"\n📥 Test input: {test_input}")

        # Execute with enhanced tracing
        print("\n🚀 Executing task with enhanced tracing...")
        result = builder.invoke_with_tracing(config, test_input)

        print("✅ Task executed successfully!")
        print(f"📤 Result: {result}")

        print("\n🎯 What to check in LangSmith:")
        print("1. Go to: https://smith.langchain.com/")
        print("2. Navigate to project: hex-machina-v2")
        print("3. Look for trace: 'Task: simple_hello_task'")
        print("4. Check tags for step-specific naming:")
        print("   - step:1:generate_greeting")
        print("   - step:2:llm_response")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_enhanced_tracing()

    if success:
        print("\n🎉 Enhanced tracing test completed successfully!")
        print("Check LangSmith for the trace with step-specific tags.")
    else:
        print("\n🔧 Test failed. Please check the error messages above.")
        sys.exit(1)
