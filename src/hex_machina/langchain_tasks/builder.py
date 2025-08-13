"""
Task Builder for LangChain tasks.

This builder follows LangChain's philosophy where everything is a runnable.
It creates RunnableSequence chains from YAML configuration and integrates
with the RunnableRegistry for runnable discovery.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from langchain_core.runnables import Runnable, RunnableSequence
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


class TaskStrategy(ABC):
    """Abstract base class for different task building strategies."""

    @abstractmethod
    def build_task(self, config: TaskConfig, runnables: List[Runnable]) -> Runnable:
        """Build a task using the specific strategy."""
        pass


class StandardTaskStrategy(TaskStrategy):
    """Standard sequential task building strategy."""

    def build_task(self, config: TaskConfig, runnables: List[Runnable]) -> Runnable:
        """Build a standard sequential task."""
        if len(runnables) == 1:
            return runnables[0]
        return RunnableSequence(*runnables)


class ArticleFetcherTaskStrategy(TaskStrategy):
    """Strategy for ArticleFetcher + enrichment steps + batch save tasks."""

    def build_task(self, config: TaskConfig, runnables: List[Runnable]) -> Runnable:
        """Build an ArticleFetcher task with map-reduce pattern."""
        from langchain_core.runnables import RunnableLambda

        # First step: ArticleFetcher
        article_fetcher = runnables[0]

        # Middle steps: enrichment processors
        enrichment_steps = runnables[1:-1]
        enrichment_step_names = [step.name for step in config.steps[1:-1]]

        # Last step: EnrichmentSaver
        enrichment_saver = runnables[-1]

        # Map phase: process each article through enrichment steps
        def process_article_through_enrichment_steps(article):
            """Process a single article through enrichment steps."""
            current_input = article
            result = {}

            for runnable, step_name in zip(enrichment_steps, enrichment_step_names):
                try:
                    step_result = runnable.invoke(current_input)
                    result[step_name] = step_result
                    current_input = step_result
                except Exception as e:
                    result[step_name] = {"error": str(e)}

            result["article"] = article
            return result

        # Reduce phase: batch save all enrichments
        def save_all_enrichments_in_batch(enriched_articles):
            """Save all enrichments in batch."""
            if not enriched_articles:
                return {"saved_count": 0, "enriched_articles": []}

            try:
                # Prepare enrichments for batch saving
                enrichments_to_save = []
                for enriched_article in enriched_articles:
                    # Extract article_id
                    article_id = enriched_article.get("article", {}).get("id")
                    if not article_id:
                        continue

                    # Extract content from the last enrichment step
                    last_step_name = enrichment_step_names[-1]
                    if last_step_name in enriched_article:
                        content = enriched_article[last_step_name]

                        # Convert content to string if it's a message object
                        if hasattr(content, "text"):
                            content = content.text
                        elif hasattr(content, "content"):
                            content = content.content

                        # Create enrichment data
                        enrichment_data = {
                            "article_id": article_id,
                            "content": content,
                            "enrichment_type": config.steps[-1].config.get(
                                "enrichment_type", "keywords"
                            ),
                            "db_path": config.steps[-1].config.get(
                                "db_path", "storage/articles14.db"
                            ),
                        }
                        enrichments_to_save.append(enrichment_data)

                # Save all enrichments in batch
                if enrichments_to_save:
                    batch_result = enrichment_saver.invoke(
                        {"enrichments": enrichments_to_save}
                    )
                    return batch_result
                else:
                    return {"saved_count": 0, "enriched_articles": enriched_articles}

            except Exception as e:
                return {
                    "error": f"Batch save failed: {e}",
                    "saved_count": 0,
                    "enriched_articles": enriched_articles,
                }

        # Create the map-reduce pipeline
        enrichment_processor = RunnableLambda(process_article_through_enrichment_steps)
        batch_saver = RunnableLambda(save_all_enrichments_in_batch)

        # Chain: ArticleFetcher -> Map(Enrichment) -> Reduce(Batch Save)
        return article_fetcher | enrichment_processor.map() | batch_saver


class TaskStrategyFactory:
    """Factory for creating appropriate task building strategies."""

    def create_strategy(self, config: TaskConfig) -> TaskStrategy:
        """Create the appropriate strategy based on task configuration."""
        if (
            config.steps
            and config.steps[0].runnable == "ArticleFetcher"
            and len(config.steps) > 1
            and config.steps[-1].runnable == "EnrichmentSaver"
        ):
            return ArticleFetcherTaskStrategy()
        return StandardTaskStrategy()


class TaskBuilder(Runnable):
    """
    Builder for creating LangChain tasks from configuration.

    This follows LangID principles where everything is a runnable.
    Creates RunnableSequence chains that can be used in LCEL workflows.

    Features:
    - YAML configuration support
    - RunnableSequence creation using LCEL
    - LangChain native caching, fallbacks, retry
    - Configurable fields for runtime overrides
    - Strategy pattern for different task types
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
        self.strategy_factory = TaskStrategyFactory()
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
            # Build individual step runnables
            runnables = self._build_step_runnables(config)

            # Create appropriate strategy and build task
            strategy = self.strategy_factory.create_strategy(config)
            task = strategy.build_task(config, runnables)

            self._logger.info(
                f"Successfully built task '{config.name}' with {len(config.steps)} steps"
            )
            return task

        except Exception as e:
            self._logger.error(f"Failed to build task '{config.name}': {e}")
            raise RuntimeError(f"Task building failed: {e}")

    def _build_step_runnables(self, config: TaskConfig) -> List[Runnable]:
        """Build runnables for each step in the task."""
        runnables = []

        for step_config in config.steps:
            self._logger.debug(f"Building step: {step_config.name}")

            # Get the runnable from registry
            runnable = self._build_step_runnable(step_config)

            # Add step-specific metadata
            runnable = self._add_step_metadata(runnable, step_config, config)

            # Apply input/output transformations if specified
            if step_config.inputs or step_config.outputs:
                runnable = self._apply_step_transformations(runnable, step_config)

            runnables.append(runnable)

        return runnables

    def _build_step_runnable(self, step_config: StepConfig) -> Runnable:
        """Build a single step runnable."""
        try:
            # Use the registry's invoke method with proper input format
            input_data = {
                "runnable_name": step_config.runnable,
                "config": step_config.config or {},
            }
            runnable = self.registry.invoke(input_data)

            return runnable

        except Exception as e:
            raise ValueError(f"Failed to build step '{step_config.name}': {e}")

    def _add_step_metadata(
        self, runnable: Runnable, step_config: StepConfig, task_config: TaskConfig
    ) -> Runnable:
        """Add metadata to a runnable."""
        metadata = {
            "step_name": step_config.name,
            "step_runnable": step_config.runnable,
            "step_config": step_config.config,
            "step_dataset": step_config.dataset,
            "task_name": task_config.name,
            "task_description": task_config.description,
            "task_type": task_config.metadata.get("task_type", "unknown"),
            "version": task_config.metadata.get("version", "1.0"),
        }

        return runnable.with_config({"metadata": metadata})

    def _apply_step_transformations(
        self, runnable: Runnable, step_config: StepConfig
    ) -> Runnable:
        """Apply input/output transformations to a runnable."""
        # This can be extended for more complex transformations
        return runnable

    def invoke_with_tracing(
        self, config: Union[TaskConfig, Dict[str, Any]], inputs: Dict[str, Any]
    ) -> Any:
        """Execute a task with proper LangSmith tracing."""
        # Convert dict to TaskConfig if needed
        if isinstance(config, dict):
            config = TaskConfig(**config)

        # Build the task
        task = self.invoke(config)

        # Execute with tracing
        result, run_tree = self._execute_with_trace(task, config, inputs)

        # Generate datasets AFTER the trace has finished
        if run_tree and self.dataset_manager:
            self._wait_for_traces_and_generate_datasets(config, run_tree)

        return result

    def _execute_with_trace(
        self, task: Runnable, config: TaskConfig, inputs: Dict[str, Any]
    ) -> tuple[Any, Any]:
        """Execute task with LangSmith tracing context."""
        try:
            from langsmith import trace

            # Create trace with rich metadata
            trace_name = f"Task: {config.name}"
            trace_metadata = {
                "task_name": config.name,
                "task_description": config.description,
                "step_count": len(config.steps),
                "step_names": [step.name for step in config.steps],
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
                result = task.invoke(inputs)
                run_tree.end(outputs={"result": result})
                return result, run_tree

        except ImportError:
            self._logger.warning("LangSmith not available, executing without tracing")
            return task.invoke(inputs), None
        except Exception as e:
            self._logger.error(f"Tracing execution failed: {e}")
            return task.invoke(inputs), None

    def _wait_for_traces_and_generate_datasets(
        self, config: TaskConfig, run_tree: Any
    ) -> None:
        """Wait for traces to be populated and generate datasets."""
        try:
            # Wait for traces to be fully populated
            self._logger.info(
                "⏳ Waiting for traces to be fully populated in LangSmith..."
            )
            run_tree.wait()
            self._logger.info(
                "✅ Traces are now fully populated, generating datasets..."
            )

            # Additional delay to ensure all traces are written
            import time

            time.sleep(5)
            self._logger.info(
                "✅ Additional delay completed, proceeding with dataset generation..."
            )

            # Generate datasets from traces
            self._generate_datasets_from_traces(config, run_tree)

        except Exception as e:
            self._logger.warning(f"Could not wait for traces: {e}")

    def _generate_datasets_from_traces(self, config: TaskConfig, run_tree: Any) -> None:
        """Generate datasets by querying LangSmith traces."""
        try:
            from langsmith import Client

            client = Client()

            # Find the RunnableEach trace_id for step-level datasets
            runnable_each_trace_id = self._find_runnable_each_trace_id(run_tree)
            if not runnable_each_trace_id:
                self._logger.warning(
                    "No RunnableEach trace_id found, skipping step dataset generation."
                )
                return

            # Process each step that has dataset=True
            for step_config in config.steps:
                if not step_config.dataset:
                    continue

                self._logger.info(f"🔍 Processing step: {step_config.name}")
                self._create_step_dataset_from_traces(
                    config, step_config, runnable_each_trace_id, client
                )

        except Exception as e:
            self._logger.error(f"Error generating datasets from traces: {e}")

    def _find_runnable_each_trace_id(self, run_tree: Any) -> Optional[str]:
        """Find the RunnableEach trace_id by exploring the nested structure."""
        if not run_tree.child_runs:
            return None

        # Look for RunnableEach in the nested structure
        for child in run_tree.child_runs:
            if hasattr(child, "child_runs"):
                for grandchild in child.child_runs:
                    if hasattr(grandchild, "name") and "RunnableEach" in str(
                        grandchild.name
                    ):
                        trace_id = getattr(grandchild, "trace_id", None)
                        if trace_id:
                            self._logger.info(
                                f"✅ Found RunnableEach trace_id: {trace_id}"
                            )
                            return trace_id

        return None

    def _create_step_dataset_from_traces(
        self, config: TaskConfig, step_config: StepConfig, trace_id: str, client: Any
    ) -> None:
        """Create a step dataset from LangSmith traces."""
        try:
            # Query LangSmith for runs in this trace
            matching_runs = list(
                client.list_runs(
                    trace=trace_id,
                    select=["name", "inputs", "outputs", "run_type", "extra"],
                    filter=f"and(eq(metadata_key, 'step_name'), eq(metadata_value, '{step_config.name}'))",
                )
            )

            if not matching_runs:
                self._logger.warning(
                    f"⚠️ No matching runs found for step '{step_config.name}', skipping dataset creation."
                )
                return

            self._logger.info(
                f"✅ Found {len(matching_runs)} runs for step '{step_config.name}'"
            )

            # Create step dataset
            step_dataset_config = StepDataset(
                enabled=True,
                description=f"Dataset for {step_config.name} step",
            )
            dataset = self.dataset_manager.generator.create_step_dataset(
                task_name=config.name,
                step_name=step_config.name,
                step_config=step_dataset_config,
                run_id=str(trace_id),
            )

            if dataset:
                # Add each run as an example
                for run in matching_runs:
                    self.dataset_manager.generator.add_step_example(
                        dataset=dataset,
                        inputs=getattr(run, "inputs", {}),
                        outputs=getattr(run, "outputs", {}),
                        run_id=str(run.id),
                        step_name=step_config.name,
                        task_name=config.name,
                    )

                self._logger.info(
                    f"✅ Step dataset '{step_config.name}' created with {len(matching_runs)} examples"
                )

        except Exception as e:
            self._logger.error(
                f"Error creating dataset for step '{step_config.name}': {e}"
            )

    async def ainvoke(self, config: Union[TaskConfig, Dict[str, Any]]) -> Runnable:
        """Async version of invoke."""
        return self.invoke(config)

    def build_from_yaml(self, yaml_data: Dict[str, Any]) -> Runnable:
        """Build a task from YAML data."""
        return self.invoke(yaml_data)

    def __repr__(self) -> str:
        """String representation of the task builder."""
        return f"TaskBuilder(registry={self.registry})"
