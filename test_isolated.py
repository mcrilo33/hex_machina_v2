#!/usr/bin/env python3
"""
Test the interface models from an isolated file.
"""

import os
import sys

# Add the src directory to the path for pydantic
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Import from the isolated file
sys.path.insert(0, "/tmp")

try:
    from test_interface import (
        Dataset,
        EvaluationRun,
        ExperimentRun,
        StorageConfig,
        TaskRun,
    )

    print("✅ Successfully imported interface models from isolated file")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)


def test_models():
    """Test the models work correctly."""

    print("\n🧪 Testing Isolated Interface Models")
    print("=" * 40)

    try:
        # Test TaskRun
        task_run = TaskRun(
            run_id="test_123",
            task_name="test_task",
            inputs={"input": "test"},
            outputs={"output": "result"},
        )
        print(f"✅ Created TaskRun: {task_run.run_id}")

        # Test EvaluationRun
        eval_run = EvaluationRun(
            evaluation_id="eval_123",
            task_run_id="test_123",
            evaluator_name="test_evaluator",
            criteria={"accuracy": 0.9},
            scores={"accuracy": 0.95},
        )
        print(f"✅ Created EvaluationRun: {eval_run.evaluation_id}")

        # Test Dataset
        dataset = Dataset(
            dataset_id="dataset_123",
            name="test_dataset",
            examples=[{"inputs": {}, "outputs": {}}],
        )
        print(f"✅ Created Dataset: {dataset.dataset_id}")

        # Test StorageConfig
        config = StorageConfig(backend="langsmith")
        print(f"✅ Created StorageConfig: {config.backend}")

        print("\n🎉 All tests passed!")
        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_models()
    if not success:
        sys.exit(1)
