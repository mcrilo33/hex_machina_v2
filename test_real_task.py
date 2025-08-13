#!/usr/bin/env python3
"""
Test script for the TaskBuilder with a real task.

This script:
1. Loads the task configuration
2. Builds the task using TaskBuilder
3. Executes the task with sample input
4. Shows the results
"""

import os
import sys
from typing import Any, Dict

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


def load_task_config(config_path: str) -> Dict[str, Any]:
    """Load task configuration from YAML file."""
    try:
        with open(config_path, "r") as file:
            config = yaml.safe_load(file)
        print(f"✅ Loaded task config: {config['name']}")
        return config
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        sys.exit(1)


def test_task_building(config: Dict[str, Any]):
    """Test building the task from configuration."""
    print("\n🔨 Testing Task Building")
    print("=" * 30)

    try:
        # Create registry and builder
        registry = RunnableRegistry()
        builder = TaskBuilder(registry)

        print(f"✅ Created TaskBuilder with registry: {registry}")

        # List available runnables
        available = registry.list_available_runnables()
        print("📋 Available runnables:")
        print(f"   Custom: {available['custom']}")
        print(f"   Built-in: {available['builtin']}")

        # Build the task
        task = builder.invoke(config)
        print(f"✅ Built task: {type(task).__name__}")

        # Show task metadata
        if hasattr(task, "metadata"):
            print(f"📊 Task metadata: {task.metadata}")

        return task

    except Exception as e:
        print(f"❌ Task building failed: {e}")
        import traceback

        traceback.print_exc()
        return None


def test_task_execution(task, test_input: Dict[str, Any]):
    """Test executing the built task."""
    print("\n🚀 Testing Task Execution")
    print("=" * 30)

    try:
        print(f"📥 Input: {test_input}")

        # Execute the task
        print("⏳ Executing task...")
        result = task.invoke(test_input)

        print(f"📤 Output: {result}")
        print(f"📊 Output type: {type(result)}")

        return result

    except Exception as e:
        print(f"❌ Task execution failed: {e}")
        import traceback

        traceback.print_exc()
        return None


def main():
    """Main test function."""
    print("🧪 Testing TaskBuilder with Real Task")
    print("=" * 50)

    # Load configuration
    config = load_task_config("test_task_config.yaml")

    # Test task building
    task = test_task_building(config)
    if not task:
        print("❌ Task building failed, cannot proceed")
        sys.exit(1)

    # Test task execution
    test_input = {"name": "Alice"}
    result = test_task_execution(task, test_input)

    if result:
        print("\n🎉 Task execution successful!")
        print("\n📋 Summary:")
        print(f"   Task: {config['name']}")
        print(f"   Steps: {len(config['steps'])}")
        print(f"   Input: {test_input}")
        print(f"   Output: {result}")
    else:
        print("\n❌ Task execution failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
