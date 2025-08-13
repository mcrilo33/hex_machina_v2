#!/usr/bin/env python3
"""
Debug script to check what's in the registry and what runnables are available.
"""

from dotenv import load_dotenv

from src.hex_machina.langchain_tasks.registry import RunnableRegistry


def main():
    """Debug the registry to see what's available."""
    print("🔍 Debugging Runnable Registry")
    print("=" * 40)

    # Load environment variables
    load_dotenv()

    # Create registry
    registry = RunnableRegistry()

    # List available runnables
    print("\n📋 Available runnables:")
    runnables = registry.list_available_runnables()
    for category, items in runnables.items():
        print(f"\n{category}:")
        for item in items:
            print(f"  - {item}")

    # Test specific runnables
    print("\n🧪 Testing specific runnables:")

    # Test PromptTemplate
    try:
        prompt = registry.invoke(
            {
                "runnable_name": "PromptTemplate",
                "config": {"template": "Hello {name}!", "input_variables": ["name"]},
            }
        )
        print("✅ PromptTemplate: Success")
        print(f"   Type: {type(prompt)}")
        print(f"   Template: {prompt.template}")
    except Exception as e:
        print(f"❌ PromptTemplate: Failed - {e}")

    # Test ChatOpenAI
    try:
        llm = registry.invoke(
            {
                "runnable_name": "ChatOpenAI",
                "config": {"temperature": 0.7, "model": "gpt-3.5-turbo"},
            }
        )
        print("✅ ChatOpenAI: Success")
        print(f"   Type: {type(llm)}")
        print(f"   Model: {llm.model_name}")
    except Exception as e:
        print(f"❌ ChatOpenAI: Failed - {e}")


if __name__ == "__main__":
    main()
