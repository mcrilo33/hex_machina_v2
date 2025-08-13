"""
Task Builder for LangChain tasks.

This builder follows LangChain's philosophy where everything is a runnable.
It creates RunnableSequence chains from YAML configuration and integrates
with the RunnableRegistry for runnable discovery.
"""

import logging
import os
from typing import Any, Dict, List, Optional, Union

from langchain_core.runnables import Runnable, RunnableSequence
from langchain_core.runnables.configurable import ConfigurableField
from pydantic import BaseModel, Field

from .datasets import StepDataset, StepDatasetManager
from .registry import RunnableRegistry


class StepConfig(BaseModel):
    """Configuration for a single step in a task."""

    name: str = Field(description="Name of the step")
    runnable: str = Field(description="Name of the runnable to use")
    inputs: Optional[Dict[str, Any]] = Field(
        default=None, description="Input mapping for this step"
    )
    outputs: Optional[Dict[str, Any]] = Field(
        default=None, description="Output mapping for this step"
    )
    config: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Configuration for the runnable (cache, fallbacks, retry, etc.)",
    )
    configurable: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Configurable fields for runtime overrides"
    )
    dataset: Optional[bool] = Field(
        default=False, description="Whether to create a dataset for this step"
    )


class TaskConfig(BaseModel):
    """Configuration for a complete task."""

    name: str = Field(description="Name of the task")
    description: Optional[str] = Field(
        default=None, description="Description of the task"
    )
    steps: List[StepConfig] = Field(description="List of steps to execute")

    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional metadata for the task"
    )
    dataset: Optional[bool] = Field(
        default=False, description="Whether to create a task-level dataset"
    )


class TaskBuilder(Runnable):
    """
    Builder for creating LangChain tasks from configuration.

    This follows LangChain's philosophy where everything is a runnable.
    Creates RunnableSequence chains that can be used in LCEL workflows.

    Features:
    - YAML configuration support
    - RunnableSequence creation using LCEL
    - LangChain native caching, fallbacks, retry
    - Configurable fields for runtime overrides
    """

    def __init__(
        self,
        registry: Optional[RunnableRegistry] = None,
        dataset_manager: Optional[StepDatasetManager] = None,
    ):
        """Initialize the task builder.

        Args:
            registry: Runnable registry for discovering runnables
            dataset_manager: Optional dataset manager for step-level datasets
        """
        self.registry = registry or RunnableRegistry()
        self.dataset_manager = dataset_manager
        self._logger = logging.getLogger("langchain_tasks.builder")

        self._logger.info("TaskBuilder initialized")

    def invoke(self, config: Union[TaskConfig, Dict[str, Any]]) -> Runnable:
        """Build a task from configuration.

        Args:
            config: Task configuration (TaskConfig or dict)

        Returns:
            A RunnableSequence representing the complete task

        Raises:
            ValueError: If configuration is invalid
            RuntimeError: If task building fails
        """
        # Convert dict to TaskConfig if needed
        if isinstance(config, dict):
            config = TaskConfig(**config)

        self._logger.info(f"Building task: {config.name}")

        try:
            # Build the task step by step
            runnables = []
            step_names = []

            for step_config in config.steps:
                self._logger.debug(f"Building step: {step_config.name}")

                # Get the runnable from registry
                runnable = self._build_step_runnable(step_config)

                # Add step-specific metadata to this runnable
                step_metadata = {
                    "step_name": step_config.name,
                    "step_index": len(runnables),
                    "step_runnable": step_config.runnable,
                    "step_config": step_config.config,
                    "step_dataset": step_config.dataset,
                    "task_name": config.name,
                    "task_description": config.description,
                    "task_type": config.metadata.get("task_type", "unknown"),
                    "version": config.metadata.get("version", "1.0"),
                }

                # Apply step-specific metadata using with_config
                runnable = runnable.with_config({"metadata": step_metadata})

                # Mark runnable for dataset generation (no wrapping needed)
                if step_config.dataset and self.dataset_manager:
                    self._logger.debug(
                        f"Step {step_config.name} marked for dataset generation"
                    )

                # Apply input/output transformations if specified
                if step_config.inputs or step_config.outputs:
                    runnable = self._apply_step_transformations(runnable, step_config)

                runnables.append(runnable)
                step_names.append(step_config.name)

            # Create the RunnableSequence
            if len(runnables) == 1:
                task = runnables[0]
            else:
                task = RunnableSequence(
                    first=runnables[0], middle=runnables[1:-1], last=runnables[-1]
                )

            # Add metadata if the task supports it
            if hasattr(task, "metadata"):
                task.metadata = {
                    "task_name": config.name,
                    "task_description": config.description,
                    "step_names": step_names,
                    **config.metadata,
                }
            else:
                # For RunnableSequence, we can't add metadata directly
                # Store it in a custom attribute or log it
                self._logger.info(
                    f"Task metadata: {config.name} - {config.description} - Steps: {step_names}"
                )

            self._logger.info(
                f"Successfully built task '{config.name}' with {len(runnables)} steps"
            )
            return task

        except Exception as e:
            self._logger.error(f"Failed to build task '{config.name}': {e}")
            raise RuntimeError(f"Task building failed: {e}")

    def invoke_with_tracing(
        self, config: Union[TaskConfig, Dict[str, Any]], inputs: Dict[str, Any]
    ) -> Any:
        """Execute a task with proper LangSmith tracing.

        This method follows LangChain's philosophy of using @traceable for observability.

        Args:
            config: Task configuration (TaskConfig or dict)
            inputs: Input data for the task

        Returns:
            Task execution result with proper tracing
        """
        # Convert dict to TaskConfig if needed
        if isinstance(config, dict):
            config = TaskConfig(**config)

        # Build the task
        task = self.invoke(config)

        # Execute with tracing using @traceable pattern
        return self._execute_with_trace(task, config, inputs)

    def _execute_with_trace(
        self, task: Runnable, config: TaskConfig, inputs: Dict[str, Any]
    ) -> Any:
        """Execute task with LangSmith tracing context.

        Args:
            task: The built task (Runnable)
            config: Task configuration
            inputs: Input data

        Returns:
            Task execution result
        """
        try:
            # Import langsmith for tracing
            from langsmith import trace

            # Create trace with rich metadata and tags
            trace_name = f"Task: {config.name}"
            trace_metadata = {
                "task_name": config.name,
                "task_description": config.description,
                "step_count": len(config.steps),
                "step_names": config.steps,
                "task_type": config.metadata.get("task_type", "unknown"),
                "version": config.metadata.get("version", "1.0"),
                **config.metadata,
            }

            # Execute within trace context
            with trace(
                name=trace_name,
                run_type="chain",
                project_name="hex-machina-v2",
                inputs=inputs,
                metadata=trace_metadata,
                tags=[
                    f"task:{config.name}",
                    f"type:{config.metadata.get('task_type', 'unknown')}",
                    f"version:{config.metadata.get('version', '1.0')}",
                ],
            ) as run_tree:
                # Execute the task
                result = task.invoke(inputs)

                # Generate datasets if enabled
            if self.dataset_manager:
                self._generate_datasets_from_result(config, inputs, result, run_tree)

                # Log the result
                run_tree.end(outputs={"result": result})

                return result

        except ImportError:
            # Fallback if langsmith not available
            self._logger.warning("LangSmith not available, executing without tracing")
            return task.invoke(inputs)
        except Exception as e:
            self._logger.error(f"Tracing execution failed: {e}")
            # Fallback to direct execution
            return task.invoke(inputs)

    def _build_step_runnable(self, step_config: StepConfig) -> Runnable:
        """Build a runnable for a single step.

        Args:
            step_config: Step configuration

        Returns:
            Configured runnable for the step
        """
        # Get the runnable from registry
        runnable = self.registry.invoke(
            {"runnable_name": step_config.runnable, "config": step_config.config}
        )

        # Apply configurable fields if specified
        if step_config.configurable:
            runnable = self._apply_configurable_fields(
                runnable, step_config.configurable
            )

        return runnable

    def _apply_configurable_fields(
        self, runnable: Runnable, configurable: Dict[str, Any]
    ) -> Runnable:
        """Apply configurable fields to a runnable.

        Args:
            runnable: The runnable to configure
            configurable: Configurable field specifications

        Returns:
            Runnable with configurable fields applied
        """
        try:
            # Check if the runnable supports configurable fields
            if hasattr(runnable, "configurable_fields"):
                # Apply each configurable field
                for field_name, field_config in configurable.items():
                    if isinstance(field_config, dict):
                        # Complex configurable field
                        configurable_field = ConfigurableField(
                            id=field_name,
                            name=field_config.get("name", field_name),
                            description=field_config.get(
                                "description", f"Configurable field: {field_name}"
                            ),
                        )
                        runnable = runnable.configurable_fields(
                            **{field_name: configurable_field}
                        )
                    else:
                        # Simple configurable field
                        configurable_field = ConfigurableField(
                            id=field_name,
                            name=field_name,
                            description=f"Configurable field: {field_name}",
                        )
                        runnable = runnable.configurable_fields(
                            **{field_name: configurable_field}
                        )

                self._logger.debug(f"Applied {len(configurable)} configurable fields")

        except Exception as e:
            self._logger.warning(f"Failed to apply configurable fields: {e}")

        return runnable

    def _apply_step_transformations(
        self, runnable: Runnable, step_config: StepConfig
    ) -> Runnable:
        """Apply input/output transformations to a step runnable.

        Args:
            runnable: The runnable to transform
            step_config: Step configuration with input/output mappings

        Returns:
            Transformed runnable
        """
        # This is a simplified implementation
        # In practice, you might want to use LangChain's RunnableMap or similar
        # for more complex input/output transformations

        if step_config.inputs or step_config.outputs:
            self._logger.debug(f"Applying transformations to step: {step_config.name}")
            # For now, just return the runnable as-is
            # TODO: Implement proper input/output transformation logic

        return runnable

    def _generate_datasets_from_result(
        self, config: TaskConfig, inputs: Dict[str, Any], result: Any, run_tree: Any
    ) -> None:
        """Generate datasets from task execution results.

        Args:
            config: Task configuration
            inputs: Task inputs
            result: Task execution result
            run_tree: LangSmith run tree for metadata
        """
        if not self.dataset_manager:
            return

        try:
            # Start dataset tracking for this task execution
            run_id = self.dataset_manager.start_task_execution(config.name)

            # Store the run_tree for later trace gathering
            if not hasattr(self, "_pending_traces"):
                self._pending_traces = []

            trace_data = {
                "config": config,
                "inputs": inputs,
                "result": result,
                "run_tree": run_tree,
                "run_id": run_id,
            }

            self._pending_traces.append(trace_data)

        except Exception as e:
            self._logger.warning(f"Dataset generation failed: {e}")

    def generate_grouped_datasets(self, config: TaskConfig) -> Dict[str, Any]:
        """Generate grouped datasets from all pending traces.

        This method should be called after multiple task executions to group
        all examples by step into shared datasets.

        Args:
            config: Task configuration

        Returns:
            Summary of grouped dataset generation
        """

        if not hasattr(self, "_pending_traces") or not self._pending_traces:
            print("🔍 DEBUG: No pending traces to group")
            self._logger.warning("No pending traces to group")
            return {}

        if not self.dataset_manager:
            self._logger.warning("No dataset manager available")
            return {}

        try:
            self._logger.info(
                f"Generating grouped datasets from {len(self._pending_traces)} traces"
            )

            # Group traces by step
            step_traces = {}
            for trace_data in self._pending_traces:
                for step_config in trace_data["config"].steps:
                    if step_config.dataset:
                        step_name = step_config.name
                        if step_name not in step_traces:
                            step_traces[step_name] = []
                        step_traces[step_name].append(trace_data)

            # Create or update task-level dataset
            if config.dataset:
                task_dataset = self.dataset_manager.prepare_task_dataset()
                if task_dataset:
                    # Add task-level examples from all traces
                    for trace_data in self._pending_traces:
                        self._add_task_trace_to_dataset(trace_data, task_dataset)

            # Create or update datasets for each step
            for step_name, traces in step_traces.items():
                self._logger.info(
                    f"Processing {len(traces)} traces for step: {step_name}"
                )

                # Create the step dataset
                step_dataset_config = StepDataset(enabled=True)
                dataset = self.dataset_manager.prepare_step_dataset(
                    step_name=step_name, step_config=step_dataset_config
                )

                if dataset:
                    # Add examples from all traces for this step
                    for trace_data in traces:
                        self._add_trace_to_dataset(step_name, trace_data, dataset)

            # Clear pending traces
            self._pending_traces = []

            # Get final summary
            summary = self.dataset_manager.get_current_status()
            self._logger.info(f"Grouped dataset generation complete: {summary}")

            return summary

        except Exception as e:
            self._logger.error(f"Failed to generate grouped datasets: {e}")
            return {}

    def _add_task_trace_to_dataset(
        self, trace_data: Dict[str, Any], task_dataset: Any
    ) -> None:
        """Add a task trace to the task-level dataset.

        Args:
            trace_data: Trace data containing config, inputs, result, etc.
            task_dataset: The task-level dataset to add to
        """
        try:
            # Extract task-level inputs and outputs
            task_inputs = trace_data["inputs"]
            task_outputs = {"result": trace_data["result"]}

            # Add task-level metadata
            task_metadata = {
                "task_name": trace_data["config"].name,
                "task_description": trace_data["config"].description,
                "step_count": len(trace_data["config"].steps),
                "step_names": [step.name for step in trace_data["config"].steps],
                "run_id": trace_data["run_id"],
            }

            # Record in task-level dataset
            self.dataset_manager.record_task_execution(
                inputs=task_inputs,
                outputs=task_outputs,
                metadata=task_metadata,
            )

            self._logger.debug(f"Added task trace to dataset: {task_dataset.name}")

        except Exception as e:
            self._logger.error(f"Failed to add task trace to dataset: {e}")

    def _add_trace_to_dataset(
        self, step_name: str, trace_data: Dict[str, Any], dataset: Any
    ) -> None:
        """Add a single trace's data to a step dataset.

        Args:
            step_name: Name of the step
            trace_data: Trace execution data
            dataset: The dataset to add to
        """
        try:
            # Extract step-specific data from the trace
            step_data = self._extract_step_data_from_trace(step_name, trace_data)

            if step_data:
                # Add to dataset
                self.dataset_manager.record_step_execution(
                    step_name=step_name,
                    inputs=step_data["inputs"],
                    outputs=step_data["outputs"],
                    additional_metadata={
                        "step_runnable": step_data.get("runnable"),
                        "run_tree_id": str(trace_data["run_tree"].id),
                        "data_source": "grouped_trace_analysis",
                        "run_type": step_data.get("run_type"),
                        "step_extra": step_data.get("extra", {}),
                        "execution_run_id": trace_data["run_id"],
                    },
                )

        except Exception as e:
            self._logger.warning(
                f"Failed to add trace to dataset for step {step_name}: {e}"
            )

    def _extract_step_data_from_trace(
        self, step_name: str, trace_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Extract step-specific data from a trace.

        Args:
            step_name: Name of the step to extract
            trace_data: Trace execution data

        Returns:
            Step data if found, None otherwise
        """
        try:
            # Query LangSmith for this specific trace
            run_tree = trace_data["run_tree"]
            trace_id = getattr(run_tree, "id", None)

            if not trace_id:
                return None

            # Query LangSmith for step executions in this trace
            from langsmith import Client

            client = Client()
            project_name = os.getenv("LANGCHAIN_PROJECT", "hex-machina-v2")

            filter_query = f'eq(trace_id, "{trace_id}")'
            trace_runs = client.list_runs(
                project_name=project_name,
                filter=filter_query,
                select=[
                    "name",
                    "inputs",
                    "outputs",
                    "run_type",
                    "extra",
                    "parent_run_id",
                    "id",
                ],
            )

            trace_runs_list = list(trace_runs)
            child_runs = [run for run in trace_runs_list if run.id != trace_id]

            # Find the run that matches our step
            for run in child_runs:
                if run.extra and isinstance(run.extra, dict):
                    metadata = run.extra.get("metadata", {})
                    if metadata and isinstance(metadata, dict):
                        run_step_name = metadata.get("step_name")
                        if run_step_name == step_name:
                            return {
                                "inputs": run.inputs,
                                "outputs": run.outputs,
                                "run_type": run.run_type,
                                "extra": run.extra or {},
                                "runnable": metadata.get("step_runnable"),
                            }

            return None

        except Exception as e:
            self._logger.warning(f"Failed to extract step data from trace: {e}")
            return None

    async def ainvoke(self, config: Union[TaskConfig, Dict[str, Any]]) -> Runnable:
        """Async version of invoke."""
        return self.invoke(config)

    def build_from_yaml(self, yaml_data: Dict[str, Any]) -> Runnable:
        """Build a task from YAML data.

        Args:
            yaml_data: YAML data as a dictionary

        Returns:
            A RunnableSequence representing the complete task
        """
        return self.invoke(yaml_data)

    def __repr__(self) -> str:
        """String representation of the task builder."""
        return f"TaskBuilder(registry={self.registry})"
