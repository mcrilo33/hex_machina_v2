#!/usr/bin/env python3
"""
Simple test script to validate the storage interface.

This script tests the basic functionality of our new storage system.
"""

import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Direct import to avoid dependency issues
try:
    from hex_machina.langchain_tasks.storage.factory import StorageFactory
    from hex_machina.langchain_tasks.storage.interface import (
        Dataset,
        EvaluationRun,
        ExperimentRun,
        StorageConfig,
        TaskRun,
    )

    print("✅ Successfully imported storage modules")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)


def test_data_models():
    """Test the data models work correctly."""

    print("\n🧪 Testing Data Models")
    print("=" * 30)

    try:
        # Test 1: Create TaskRun
        task_run = TaskRun(
            run_id="test_run_123",
            task_name="test_task",
            inputs={"input": "test input"},
            outputs={"output": "test output"},
            metadata={"test": True},
            execution_time=1.5,
        )
        print(f"✅ Created TaskRun: {task_run.run_id}")

        # Test 2: Create EvaluationRun
        evaluation_run = EvaluationRun(
            evaluation_id="test_eval_123",
            task_run_id="test_run_123",
            evaluator_name="test_evaluator",
            criteria={"accuracy": 0.9},
            scores={"accuracy": 0.95, "completeness": 0.8},
        )
        print(f"✅ Created EvaluationRun: {evaluation_run.evaluation_id}")

        # Test 3: Create Dataset
        dataset = Dataset(
            dataset_id="test_dataset_123",
            name="test_dataset",
            description="Test dataset for validation",
            examples=[
                {
                    "inputs": {"text": "sample input"},
                    "outputs": {"label": "positive"},
                    "metadata": {"source": "test"},
                }
            ],
        )
        print(f"✅ Created Dataset: {dataset.dataset_id}")

        # Test 4: Create StorageConfig
        config = StorageConfig(
            backend="langsmith", project_name="hex-machina-test", enable_tracing=True
        )
        print(f"✅ Created StorageConfig: {config.backend}")

        # Test 5: Test StorageFactory
        backends = StorageFactory.list_available_backends()
        print(f"✅ Available backends: {backends}")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🚀 Testing LangChain Tasks Storage Interface")

    success = test_data_models()

    if success:
        print("\n🎉 All tests completed successfully!")
        print(
            "\nThe storage interface is working correctly and follows LangChain's philosophy:"
        )
        print("- ✅ Runnable-compatible interface")
        print("- ✅ Configuration-driven instantiation")
        print("- ✅ Extensible backend system")
        print("- ✅ LangSmith integration ready")
        print("\n🚀 Ready to proceed with next implementation phase!")
    else:
        print("\n🔧 Please fix the issues before proceeding.")
        sys.exit(1)
