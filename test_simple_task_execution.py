#!/usr/bin/env python3
"""
Simple test to execute a task step by step and see what's happening.
"""

from dotenv import load_dotenv

from src.hex_machina.langchain_tasks.builder import TaskBuilder
from src.hex_machina.langchain_tasks.config.models import TaskConfig


def main():
    """Test simple task execution step by step."""
    print("🧪 Testing Simple Task Execution")
    print("=" * 50)

    # Load environment variables
    load_dotenv()
    print("✅ Environment variables loaded")

    # Create a simple task config
    task_config = TaskConfig(
        name="debug_task",
        steps=[
            {
                "name": "generate_greeting",
                "runnable": "PromptTemplate",
                "dataset": True,
                "config": {
                    "template": "Generate a greeting for {name}. Make it {style}.",
                    "input_variables": ["name", "style"],
                },
            },
            {
                "name": "llm_response",
                "runnable": "ChatOpenAI",
                "dataset": True,
                "config": {"temperature": 0.7, "model": "gpt-3.5-turbo"},
            },
        ],
    )

    print(f"✅ Created task config: {task_config.name}")
    print(f"✅ Steps: {len(task_config.steps)}")

    # Create builder
    builder = TaskBuilder()
    print("✅ Created TaskBuilder")

    # Build the task
    print("\n🔧 Building task...")
    try:
        task = builder.invoke(task_config)
        print("✅ Task built successfully")
        print(f"   Type: {type(task)}")
        print(
            f"   Steps: {len(task.steps) if hasattr(task, 'steps') else 'No steps attribute'}"
        )

        # Test with simple input
        test_input = {"name": "Alice", "style": "formal"}
        print(f"\n📝 Testing with input: {test_input}")

        result = task.invoke(test_input)
        print("✅ Task executed successfully")
        print(f"   Result type: {type(result)}")
        print(f"   Result: {result}")

    except Exception as e:
        print(f"❌ Task execution failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
