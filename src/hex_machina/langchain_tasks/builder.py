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
                # Check if first step is ArticleFetcher - if so, use RunnableLambda.map() for remaining steps
                if config.steps[0].runnable == "ArticleFetcher" and len(runnables) > 1:
                    # First step: ArticleFetcher
                    first_step = runnables[0]

                    # Check if the last step is EnrichmentSaver - if so, implement map-reduce pattern
                    last_step = config.steps[-1]
                    if last_step.runnable == "EnrichmentSaver":
                        # Map-Reduce pattern: process articles individually, then save in batch
                        from langchain_core.runnables import RunnableLambda

                        # Map phase: process each article through enrichment steps (excluding EnrichmentSaver)
                        def process_article_through_enrichment_steps(article):
                            """Process a single article through enrichment steps (map phase)."""
                            # Start with the article data
                            current_input = article
                            result = {}

                            # Run each enrichment step sequentially (excluding EnrichmentSaver)
                            for i, runnable in enumerate(runnables[1:-1], 1):
                                step_name = config.steps[i].name
                                try:
                                    # Pass the current input to the runnable
                                    step_result = runnable.invoke(current_input)
                                    # Store the result with the step name for input_mapping
                                    result[step_name] = step_result
                                    # Update current_input for the next step
                                    current_input = step_result
                                except Exception as e:
                                    result[step_name] = {"error": str(e)}

                            # Add the original article
                            result["article"] = article
                            return result

                        # Create the enrichment processor with .map() capability
                        enrichment_processor = RunnableLambda(
                            process_article_through_enrichment_steps
                        )

                        # Reduce phase: collect all enrichments and save them in one batch operation
                        def save_all_enrichments_in_batch(enriched_articles):
                            """Save all enrichments in batch (reduce phase)."""
                            if not enriched_articles:
                                return {"saved_count": 0, "enriched_articles": []}

                            # Debug: Log the structure of enriched articles
                            self._logger.info(
                                f"Batch saver received {len(enriched_articles)} enriched articles"
                            )

                            # Get the EnrichmentSaver config from the last step
                            enrichment_saver_config = config.steps[-1].config

                            # Extract all enrichments for batch processing
                            enrichments_to_save = []
                            for enriched_article in enriched_articles:
                                try:
                                    # Extract article_id and content using the same logic as EnrichmentSaver
                                    article_id = None
                                    content = None

                                    # Extract article_id (same logic as EnrichmentSaver)
                                    if "id" in enriched_article:
                                        article_id = enriched_article["id"]
                                    elif (
                                        "article" in enriched_article
                                        and "id" in enriched_article["article"]
                                    ):
                                        # The article data is nested under the 'article' key
                                        article_id = enriched_article["article"]["id"]
                                    elif "generate_article_summary" in enriched_article:
                                        if (
                                            "id"
                                            in enriched_article[
                                                "generate_article_summary"
                                            ]
                                        ):
                                            article_id = enriched_article[
                                                "generate_article_summary"
                                            ]["id"]

                                        # Also check if the article data is nested
                                        if (
                                            "article" in enriched_article
                                            and "id" in enriched_article["article"]
                                        ):
                                            article_id = enriched_article["article"][
                                                "id"
                                            ]

                                    # Extract content using input_mapping
                                    input_mapping = enrichment_saver_config.get(
                                        "input_mapping", ""
                                    )
                                    if input_mapping:
                                        path_parts = input_mapping.split(".")
                                        current = enriched_article

                                        # Debug logging
                                        self._logger.info(
                                            f"Extracting content with path: {path_parts}"
                                        )
                                        self._logger.info(
                                            f"Available keys in enriched_article: {list(enriched_article.keys())}"
                                        )

                                        for part in path_parts:
                                            if part not in current:
                                                # Handle nested structure
                                                if (
                                                    "generate_article_summary"
                                                    in enriched_article
                                                ):
                                                    nested_content = enriched_article[
                                                        "generate_article_summary"
                                                    ]
                                                    if (
                                                        "generate_article_summary"
                                                        in nested_content
                                                        and part
                                                        in nested_content[
                                                            "generate_article_summary"
                                                        ]
                                                    ):
                                                        current = nested_content[
                                                            "generate_article_summary"
                                                        ][part]
                                                        break
                                                    summaries = nested_content.get(
                                                        "summaries", []
                                                    )
                                                    if (
                                                        summaries
                                                        and part in summaries[0]
                                                    ):
                                                        current = summaries[0][part]
                                                        break
                                                break
                                            current = current[part]

                                        content = current
                                        self._logger.info(
                                            f"Extracted content type: {type(content)}"
                                        )
                                        self._logger.info(
                                            f"Extracted content: {content}"
                                        )

                                    if article_id and content:
                                        # Handle StringPromptValue objects from PromptTemplate
                                        if hasattr(content, "to_string"):
                                            content = content.to_string()
                                        elif hasattr(content, "text"):
                                            content = content.text

                                        self._logger.info(
                                            f"Final content after conversion: {content}"
                                        )

                                        enrichments_to_save.append(
                                            {
                                                "article_id": article_id,
                                                "content": content,
                                                "enrichment_type": enrichment_saver_config.get(
                                                    "enrichment_type", "unknown"
                                                ),
                                                "db_path": enrichment_saver_config.get(
                                                    "db_path", "storage/articles14.db"
                                                ),
                                            }
                                        )
                                    else:
                                        self._logger.warning(
                                            f"Missing article_id or content: article_id={article_id}, content={content}"
                                        )

                                except Exception as e:
                                    self._logger.error(
                                        f"Failed to extract enrichment data: {e}"
                                    )

                            # Now save all enrichments in one batch operation
                            if enrichments_to_save:
                                try:
                                    # Use the database connector directly for batch saving
                                    from hex_machina.langchain_tasks.database.connector import (
                                        DatabaseConnector,
                                    )

                                    # Group by db_path for batch operations
                                    db_groups = {}
                                    for enrichment in enrichments_to_save:
                                        db_path = enrichment["db_path"]
                                        if db_path not in db_groups:
                                            db_groups[db_path] = []
                                        db_groups[db_path].append(enrichment)

                                    # Save each group in batch
                                    total_saved = 0
                                    for db_path, enrichments in db_groups.items():
                                        connector = DatabaseConnector(db_path)
                                        # Batch insert all enrichments for this database
                                        for enrichment in enrichments:
                                            connector.save_enrichment(
                                                article_id=enrichment["article_id"],
                                                content=enrichment["content"],
                                                enrichment_type=enrichment[
                                                    "enrichment_type"
                                                ],
                                            )
                                            total_saved += 1

                                    self._logger.info(
                                        f"Successfully saved {total_saved} enrichments in batch"
                                    )

                                except Exception as e:
                                    self._logger.error(
                                        f"Failed to save enrichments in batch: {e}"
                                    )

                            return {
                                "saved_count": len(enrichments_to_save),
                                "enriched_articles": enriched_articles,
                                "batch_operation": True,
                            }

                        # Create the batch saver
                        batch_saver = RunnableLambda(save_all_enrichments_in_batch)

                        # Create sequence: ArticleFetcher -> EnrichmentProcessor.map() -> BatchSaver
                        # Chain the .map() operation directly
                        task = first_step | enrichment_processor.map() | batch_saver

                        self._logger.info(
                            f"Created ArticleFetcher + Map-Reduce task: {len(runnables)-2} enrichment steps -> batch save"
                        )
                    else:
                        # Standard map pattern: process each article through all remaining steps
                        from langchain_core.runnables import RunnableLambda

                        # Create a function that processes each article through all remaining steps
                        def process_article_through_steps(article):
                            """Process a single article through all remaining steps."""
                            # Start with the article data
                            current_input = article
                            result = {}

                            # Run each step sequentially on the article
                            for i, runnable in enumerate(runnables[1:], 1):
                                step_name = config.steps[i].name
                                try:
                                    # Pass the current input to the runnable
                                    step_result = runnable.invoke(current_input)
                                    # Store the result with the step name for input_mapping
                                    result[step_name] = step_result

                                    # Record dataset example for this step if dataset is enabled
                                    if config.steps[i].dataset and self.dataset_manager:
                                        try:
                                            # Create step dataset
                                            step_dataset_config = StepDataset(
                                                enabled=True
                                            )
                                            dataset = self.dataset_manager.prepare_step_dataset(
                                                step_name=step_name,
                                                step_config=step_dataset_config,
                                            )

                                            if dataset:
                                                # Record the step execution with article-specific data
                                                self.dataset_manager.record_step_execution(
                                                    step_name=step_name,
                                                    inputs={
                                                        "step_name": step_name,
                                                        "runnable": config.steps[
                                                            i
                                                        ].runnable,
                                                        "config": config.steps[i].config
                                                        or {},
                                                        "article_id": article.get("id"),
                                                        "article_title": article.get(
                                                            "title"
                                                        ),
                                                        "article_text": article.get(
                                                            "text_content", ""
                                                        )[
                                                            :500
                                                        ],  # Truncate for dataset
                                                    },
                                                    outputs={
                                                        "result_type": type(
                                                            step_result
                                                        ).__name__,
                                                        "result_summary": str(
                                                            step_result
                                                        )[:200],
                                                        "step_output": step_result,
                                                    },
                                                    additional_metadata={
                                                        "step_runnable": config.steps[
                                                            i
                                                        ].runnable,
                                                        "article_id": article.get("id"),
                                                        "data_source": "article_processing",
                                                        "run_type": "tool",
                                                        "step_extra": config.steps[
                                                            i
                                                        ].config
                                                        or {},
                                                    },
                                                )

                                                self._logger.debug(
                                                    f"✅ Recorded dataset example for step '{step_name}' and article {article.get('id')}"
                                                )
                                        except Exception as e:
                                            self._logger.warning(
                                                f"Failed to record dataset for step {step_name}: {e}"
                                            )

                                    # Update current_input for the next step
                                    current_input = step_result
                                except Exception as e:
                                    result[step_name] = {"error": str(e)}

                            # Add the original article at the end
                            result["article"] = article
                            return result

                        # Create the article processor with .map() capability
                        article_processor = RunnableLambda(
                            process_article_through_steps
                        )

                        # Create sequence: ArticleFetcher -> ArticleProcessor.map()
                        # This will automatically map over each article from ArticleFetcher
                        task = RunnableSequence(
                            first=first_step,
                            last=article_processor.map(),  # .map() is the key!
                        )

                        self._logger.info(
                            f"Created ArticleFetcher + ArticleProcessor.map() task with {len(runnables)-1} processing steps"
                        )
                else:
                    # Standard RunnableSequence for non-ArticleFetcher tasks
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
        result, run_tree = self._execute_with_trace(task, config, inputs)

        # Generate datasets AFTER the trace has finished
        # This ensures all runs are complete and available in LangSmith
        if run_tree:
            # Wait for the run tree to be fully populated in LangSmith
            self._logger.info(
                "⏳ Waiting for traces to be fully populated in LangSmith..."
            )
            try:
                run_tree.wait()
                self._logger.info(
                    "✅ Traces are now fully populated, generating datasets..."
                )
            except Exception as e:
                self._logger.warning(f"Could not wait for traces: {e}")

            # Add additional delay to ensure all traces are fully written to LangSmith
            import time

            self._logger.info(
                "⏳ Additional delay to ensure all traces are fully written..."
            )
            time.sleep(3)  # Wait 3 seconds
            self._logger.info(
                "✅ Additional delay completed, proceeding with dataset generation..."
            )

            self._generate_datasets_from_result(config, inputs, result, run_tree)

        return result

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

                # Datasets are now generated outside the trace context
                pass

                # Log the result
                run_tree.end(outputs={"result": result})

                return result, run_tree

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

            # Generate datasets from traces
            self._generate_datasets_from_traces(config, run_tree, run_id, "step")

        except Exception as e:
            self._logger.warning(f"Dataset generation failed: {e}")

    def _generate_datasets_from_traces(
        self, config: TaskConfig, run_tree: Any, run_id: str, level: str = "step"
    ) -> None:
        """Generate datasets by querying LangSmith traces.

        Args:
            config: Task configuration
            run_tree: LangSmith run tree (for getting trace_id)
            run_id: Current run ID
            level: "task" for task-level dataset, "step" for step-level datasets
        """
        try:
            # Debug: Log what attributes are available on run_tree
            self._logger.info(f"run_tree type: {type(run_tree)}")
            self._logger.info(f"run_tree attributes: {dir(run_tree)}")

            # Try different ways to get trace_id based on LangSmith documentation
            trace_id = None

            # Method 1: Try trace_id attribute
            if hasattr(run_tree, "trace_id"):
                trace_id = getattr(run_tree, "trace_id")
                self._logger.info(f"Found trace_id: {trace_id}")

            # Method 2: Try id attribute (might be the trace_id)
            elif hasattr(run_tree, "id"):
                trace_id = getattr(run_tree, "id")
                self._logger.info(f"Using run_tree.id as trace_id: {trace_id}")

            # Method 3: Try to get from run_tree properties
            elif hasattr(run_tree, "__dict__"):
                self._logger.info(
                    f"run_tree.__dict__ keys: {list(run_tree.__dict__.keys())}"
                )
                if "trace_id" in run_tree.__dict__:
                    trace_id = run_tree.__dict__["trace_id"]
                    self._logger.info(f"Found trace_id in __dict__: {trace_id}")

            if not trace_id:
                self._logger.warning("No trace_id found, skipping dataset generation")
                return

            # Query LangSmith for runs in this trace
            from langsmith import Client

            client = Client()

            if level == "task":
                # Task-level: get all runs in the trace using trace_id
                runs = list(
                    client.list_runs(
                        trace_id=trace_id,
                        select=["name", "inputs", "outputs", "run_type"],
                    )
                )
                self._logger.info(f"Found {len(runs)} runs for task-level dataset")
                # Create single task dataset with all runs
                self._create_task_dataset(config, runs, run_id)

            else:  # step level
                # Step-level: create dataset for each step that has dataset=True

                # Get the RunnableEach's trace_id once for all steps
                if not run_tree.child_runs:
                    self._logger.warning("No child runs found in run_tree")
                    return

                runnable_sequence = run_tree.child_runs[0]
                if len(runnable_sequence.child_runs) < 2:
                    self._logger.warning(
                        "RunnableSequence doesn't have enough child runs"
                    )
                    return

                # Find the RunnableEach (child 1) which processes the articles
                runnable_each = runnable_sequence.child_runs[1]
                runnable_each_trace_id = getattr(runnable_each, "trace_id", None)
                if not runnable_each_trace_id:
                    self._logger.warning("RunnableEach has no trace_id")
                    return

                self._logger.info(
                    f"✅ Found RunnableEach trace_id: {runnable_each_trace_id}"
                )

                # Process each step that has dataset=True
                for step_config in config.steps:
                    if step_config.dataset:
                        self._logger.info(f"🔍 Processing step: {step_config.name}")

                        # Use the correct LangSmith API call to get all runs for this step
                        filter_query = f"and(eq(metadata_key, 'step_name'), eq(metadata_value, '{step_config.name}'))"
                        self._logger.info(f"🔍 Filtering runs with: {filter_query}")

                        try:
                            step_runs = list(
                                client.list_runs(
                                    trace=runnable_each_trace_id,
                                    filter=filter_query,
                                )
                            )

                            self._logger.info(
                                f"✅ Found {len(step_runs)} runs for step '{step_config.name}'"
                            )

                            if step_runs:
                                # Create step dataset first
                                step_dataset_config = StepDataset(
                                    enabled=True,
                                    description=f"Dataset for {step_config.name} step",
                                )
                                dataset = (
                                    self.dataset_manager.generator.create_step_dataset(
                                        task_name=config.name,
                                        step_name=step_config.name,
                                        step_config=step_dataset_config,
                                        run_id=run_id,
                                    )
                                )

                                if dataset:
                                    # Add each run as an example to the dataset
                                    for run in step_runs:
                                        inputs = getattr(run, "inputs", {})
                                        outputs = getattr(run, "outputs", {})

                                        self.dataset_manager.generator.add_step_example(
                                            dataset=dataset,
                                            inputs=inputs,
                                            outputs=outputs,
                                            run_id=str(run.id),
                                            step_name=step_config.name,
                                            task_name=config.name,
                                        )

                                    self._logger.info(
                                        f"✅ Step dataset '{step_config.name}' created with {len(step_runs)} examples"
                                    )
                                else:
                                    self._logger.error(
                                        f"Failed to create dataset for step '{step_config.name}'"
                                    )
                            else:
                                self._logger.warning(
                                    f"No runs found for step '{step_config.name}' with metadata filtering"
                                )

                        except Exception as e:
                            self._logger.error(
                                f"Error fetching runs for step '{step_config.name}': {e}"
                            )
                            # Continue to next step instead of returning
                            continue

        except Exception as e:
            self._logger.error(f"Failed to generate datasets from traces: {e}")
            import traceback

            self._logger.error(f"Traceback: {traceback.format_exc()}")

    def _create_task_dataset(self, config: TaskConfig, runs: list, run_id: str) -> None:
        """Create a task-level dataset with all runs."""
        try:
            dataset = self.dataset_manager.prepare_step_dataset(
                step_name=config.name, step_config=StepDataset(enabled=True)
            )

            if dataset:
                # Record each run as an example
                for run in runs:
                    self.dataset_manager.record_step_execution(
                        step_name=config.name,
                        inputs=run.inputs or {},
                        outputs=run.outputs or {},
                        additional_metadata={
                            "run_id": run_id,
                            "trace_run_id": run.id,
                            "data_source": "trace_execution",
                            "run_type": run.run_type,
                        },
                    )

                self._logger.info(
                    f"✅ Task dataset '{config.name}' created with {len(runs)} examples"
                )

        except Exception as e:
            self._logger.error(f"Failed to create task dataset: {e}")

    def _create_step_dataset(
        self, step_config: StepConfig, runs: list, run_id: str
    ) -> None:
        """Create a step-level dataset."""
        try:
            dataset = self.dataset_manager.prepare_step_dataset(
                step_name=step_config.name, step_config=StepDataset(enabled=True)
            )

            if dataset:
                # Record each run as an example
                for run in runs:
                    self.dataset_manager.record_step_execution(
                        step_name=step_config.name,
                        inputs=run.inputs or {},
                        outputs=run.outputs or {},
                        additional_metadata={
                            "step_runnable": step_config.runnable,
                            "run_id": run_id,
                            "trace_run_id": run.id,
                            "data_source": "trace_execution",
                            "run_type": run.run_type,
                            "step_extra": step_config.config or {},
                        },
                    )

                self._logger.info(
                    f"✅ Step dataset '{step_config.name}' created with {len(runs)} examples"
                )

        except Exception as e:
            self._logger.error(f"Failed to create step dataset: {e}")

    def _extract_step_data_from_result(
        self,
        step_name: str,
        step_config: StepConfig,
        inputs: Dict[str, Any],
        result: Any,
    ) -> Optional[List[Dict[str, Any]]]:
        """Extract step-specific data from the task execution result.

        This method is now simplified to be agnostic to specific runnable types.
        The actual data extraction should happen during trace analysis.

        Args:
            step_name: Name of the step
            step_config: Step configuration
            inputs: Task inputs
            result: Task execution result

        Returns:
            Basic step data structure
        """
        try:
            # Return basic step info - the actual data will come from LangSmith traces
            return [
                {
                    "inputs": {
                        "step_name": step_name,
                        "runnable": step_config.runnable,
                        "config": step_config.config or {},
                        "task_inputs": inputs,
                    },
                    "outputs": {
                        "result_type": type(result).__name__,
                        "result_summary": str(result)[:200],
                    },
                }
            ]

        except Exception as e:
            self._logger.warning(f"Failed to extract step data for {step_name}: {e}")
            return None

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

            # Create or update datasets for each step with actual trace data
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
                    # Extract actual execution data from LangSmith traces for each article
                    step_examples = self._extract_step_examples_from_traces(
                        step_name, traces
                    )

                    if step_examples:
                        # Add each example to the step dataset
                        for i, example in enumerate(step_examples):
                            self.dataset_manager.record_step_execution(
                                step_name=step_name,
                                inputs=example["inputs"],
                                outputs=example["outputs"],
                                additional_metadata={
                                    "step_runnable": example.get("runnable", "unknown"),
                                    "run_id": example.get("run_id", "unknown"),
                                    "data_source": "langsmith_trace_analysis",
                                    "run_type": example.get("run_type", "tool"),
                                    "step_extra": example.get("extra", {}),
                                    "article_index": i,
                                    "total_articles": len(step_examples),
                                },
                            )

                        self._logger.info(
                            f"✅ Step dataset '{step_name}' populated with {len(step_examples)} examples"
                        )
                    else:
                        self._logger.warning(
                            f"No examples extracted for step: {step_name}"
                        )

            # Clear pending traces
            self._pending_traces = []

            # Get final summary
            summary = self.dataset_manager.get_current_status()
            self._logger.info(f"Grouped dataset generation complete: {summary}")

            return summary

        except Exception as e:
            self._logger.error(f"Failed to generate grouped datasets: {e}")
            return {}

    def _extract_step_examples_from_traces(
        self, step_name: str, traces: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract step examples from LangSmith traces.

        Args:
            step_name: Name of the step to extract
            traces: List of trace data

        Returns:
            List of step examples with inputs/outputs
        """
        try:
            from langsmith import Client

            client = Client()
            project_name = os.getenv("LANGCHAIN_PROJECT", "hex-machina-v2")
            examples = []

            for trace_data in traces:
                run_tree = trace_data["run_tree"]
                trace_id = getattr(run_tree, "id", None)

                if not trace_id:
                    continue

                # Query LangSmith for step executions in this trace
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

                # Find runs that match our step
                for run in child_runs:
                    # Check if this run corresponds to our step
                    if self._is_run_for_step(run, step_name):
                        example = {
                            "inputs": run.inputs or {},
                            "outputs": run.outputs or {},
                            "runnable": run.name,
                            "run_id": str(run.id),
                            "run_type": run.run_type,
                            "extra": run.extra or {},
                        }
                        examples.append(example)

            return examples

        except Exception as e:
            self._logger.warning(f"Failed to extract step examples from traces: {e}")
            return []

    def _is_run_for_step(self, run: Any, step_name: str) -> bool:
        """Check if a LangSmith run corresponds to a specific step.

        Args:
            run: LangSmith run object
            step_name: Name of the step to check

        Returns:
            True if the run corresponds to the step
        """
        try:
            # Check if the run name matches the step name
            if run.name == step_name:
                return True

            # Check if the run has metadata indicating the step
            if run.extra and isinstance(run.extra, dict):
                metadata = run.extra.get("metadata", {})
                if isinstance(metadata, dict):
                    run_step_name = metadata.get("step_name")
                    if run_step_name == step_name:
                        return True

            # Check if the run has tags indicating the step
            if hasattr(run, "tags") and run.tags:
                for tag in run.tags:
                    if tag.startswith(f"step:{step_name}"):
                        return True

            return False

        except Exception as e:
            self._logger.debug(f"Error checking if run is for step {step_name}: {e}")
            return False

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

    def __repr__(self) -> str:
        """String representation of the task builder."""
        return f"TaskBuilder(registry={self.registry})"
