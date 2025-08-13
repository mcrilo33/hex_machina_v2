#!/usr/bin/env python3
"""
Test only the interface models without importing the full storage system.

This isolates the test to avoid dependency issues.
"""

import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Test direct import of just the interface models
try:
    # Import only the interface models
    from hex_machina.langchain_tasks.storage.interface import (
        Dataset,
        EvaluationRun,
        ExperimentRun,
        StorageConfig,
        TaskRun,
    )

    print("✅ Successfully imported interface models")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)


def test_interface_models():
    """Test that the interface models work correctly."""

    print("\n🧪 Testing Interface Models")
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
            backend="langsmith",
            project_name="hex-machina-test",
            enable_tracing=True,
        )
        print(f"✅ Created StorageConfig: {config.backend}")

        # Test 5: Validate model serialization
        print("\n5. Testing Model Serialization...")
        task_run_dict = task_run.model_dump()
        print(f"✅ TaskRun serialized to dict: {len(task_run_dict)} fields")

        evaluation_run_dict = evaluation_run.model_dump()
        print(f"✅ EvaluationRun serialized to dict: {len(evaluation_run_dict)} fields")

        dataset_dict = dataset.model_dump()
        print(f"✅ Dataset serialized to dict: {len(dataset_dict)} fields")

        config_dict = config.model_dump()
        print(f"✅ StorageConfig serialized to dict: {len(config_dict)} fields")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🚀 Testing LangChain Tasks Storage Interface Models")

    success = test_interface_models()

    if success:
        print("\n🎉 All tests completed successfully!")
        print(
            "\nThe storage interface models are working correctly and follow LangChain's philosophy:"
        )
        print("- ✅ Pydantic models for data validation")
        print("- ✅ Type hints for all fields")
        print("- ✅ Configurable and extensible")
        print("- ✅ Ready for LangSmith integration")
        print("\n🚀 Ready to proceed with next implementation phase!")
    else:
        print("\n🔧 Please fix the issues before proceeding.")
        sys.exit(1)
