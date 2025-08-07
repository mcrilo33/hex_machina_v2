"""LangSmith integration for tracing and observability."""

import logging
import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from langsmith import Client
from langsmith.run_helpers import trace

from src.hex_machina.core import TaskInput, TaskOutput
from src.hex_machina.core.exceptions import TaskException

# Load environment variables at module level
load_dotenv()

# Enable LangChain tracing for proper nesting
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "hex-machina-v2"


class LangSmithTracer:
    """LangSmith tracer for enrichment tasks."""

    def __init__(self, project_name: str = "hex-machina-v2"):
        """Initialize LangSmith tracer.

        Args:
            project_name: LangSmith project name
        """
        self.project_name = project_name
        self._logger = logging.getLogger("enrichment.tracing.langsmith")
        self._client = None

        # Initialize LangSmith client if API key is available
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize LangSmith client."""
        api_key = os.getenv("LANGSMITH_API_KEY")
        if api_key:
            # Ensure LANGSMITH_PROJECT is set
            if not os.getenv("LANGSMITH_PROJECT"):
                os.environ["LANGSMITH_PROJECT"] = self.project_name
                self._logger.info(f"Set LANGSMITH_PROJECT to: {self.project_name}")

            self._client = Client(api_key=api_key)
            self._logger.info(
                f"LangSmith client initialized for project: {self.project_name}"
            )
        else:
            self._logger.warning(
                "LANGSMITH_API_KEY not found. LangSmith tracing will be limited."
            )

    def trace_task_execution(
        self,
        task_name: str,
        task_input: TaskInput,
        task_output: TaskOutput,
        chain_result: Any = None,
    ) -> None:
        """Trace task execution in LangSmith.

        Args:
            task_name: Name of the task
            task_input: Task input data
            task_output: Task output data
        """
        if not self._client:
            return

        # Create trace metadata - ensure all values are strings for LangSmith compatibility
        metadata = {
            "task_name": str(task_name),
            "task_id": str(task_input.task_id),
            "execution_time": str(task_output.execution_time),
            "success": str(not bool(task_output.error)),
            "project": str(self.project_name),
        }

        # Add task-specific metadata - convert all values to strings
        if task_output.metadata:
            for key, value in task_output.metadata.items():
                metadata[str(key)] = str(value)

        # Debug: Log the metadata we're about to send
        self._logger.info(f"Tracing task with metadata: {metadata}")

        # Create parent trace for task execution
        with trace(
            project_name=self.project_name,
            run_type="chain",
            name=task_input.task_id,  # task_id already includes task_name
            inputs={
                "task_input": task_input.model_dump(),
            },
            outputs={
                "task_output": task_output.model_dump(),
                "chain_result": str(chain_result) if chain_result is not None else None,
            },
            error=task_output.error,
            tags=[
                f"task:{task_name}",
                f"provider:{task_output.metadata.get('llm_provider', 'unknown')}",
            ],
            metadata=metadata,
            langsmith_extra={
                "metadata": metadata,
                "tags": [
                    f"task:{task_name}",
                    f"provider:{task_output.metadata.get('llm_provider', 'unknown')}",
                ],
            },
        ) as parent_run:
            # Add metadata to the parent run
            parent_run.metadata.update(metadata)
            self._logger.debug(f"Traced task execution: {parent_run.id}")

            # Execute the chain within the parent trace context
            # This will make LangChain's traces appear as children of our trace
            if chain_result is not None:
                # The chain has already been executed, but we can still show the relationship
                self._logger.debug(
                    f"Chain result available in parent trace: {parent_run.id}"
                )

    def trace_llm_call(
        self, prompt: str, response: str, metadata: Dict[str, Any]
    ) -> None:
        """Trace LLM call in LangSmith.

        Args:
            prompt: Input prompt
            response: LLM response
            metadata: Additional metadata
        """
        if not self._client:
            return

        # Create trace for LLM call - ensure metadata values are strings
        string_metadata = {str(k): str(v) for k, v in metadata.items()}

        with trace(
            project_name=self.project_name,
            run_type="llm",
            name="llm_call",
            metadata=string_metadata,
            inputs={"prompt": prompt},
            outputs={"response": response},
        ) as run:
            self._logger.debug(f"Traced LLM call: {run.id}")

    def get_run_url(self, run_id: str) -> Optional[str]:
        """Get LangSmith run URL.

        Args:
            run_id: LangSmith run ID

        Returns:
            URL to view the run in LangSmith, or None if not available
        """
        if not self._client:
            return None

        # This would need to be implemented based on LangSmith API
        # For now, return a placeholder
        return f"https://smith.langchain.com/runs/{run_id}"

    def list_recent_runs(self, limit: int = 10) -> list[Dict[str, Any]]:
        """List recent runs from LangSmith.

        Args:
            limit: Maximum number of runs to return

        Returns:
            List of recent runs
        """
        if not self._client:
            return []

        # This would need to be implemented based on LangSmith API
        # For now, return empty list
        return []

    async def execute_task_with_tracing(
        self, task, task_input: TaskInput, task_name: str
    ) -> TaskOutput:
        """Execute a task within a parent trace context with granular spans.

        Args:
            task: The task to execute
            task_input: Task input data
            task_name: Name of the task

        Returns:
            Task output with results
        """
        if not self._client:
            # Fallback to normal execution if LangSmith is not available
            return await task.execute(task_input)

        # Use LangChain's tracing context for proper nesting
        # This ensures that LangChain components (ChatPromptTemplate, ChatOpenAI)
        # are properly nested within our parent trace
        from langchain_core.tracers.context import tracing_v2_enabled

        with tracing_v2_enabled():
            with trace(
                project_name=self.project_name,
                run_type="chain",
                name=task_input.task_id,
                inputs={"task_input": task_input.model_dump()},
                tags=[f"task:{task_name}"],
                metadata={"task_name": task_name, "task_id": task_input.task_id},
            ) as parent_run:

                # Span 1: Input Validation
                with trace(
                    project_name=self.project_name,
                    run_type="tool",
                    name="input_validation",
                    inputs={"task_input": task_input.model_dump()},
                    tags=[f"task:{task_name}", "phase:validation"],
                    metadata={"task_name": task_name, "phase": "input_validation"},
                ) as validation_span:
                    # Validate input
                    if not task.validate_input(task_input):
                        validation_span.end(
                            outputs={"validation_result": "failed"},
                            error="Invalid input data",
                        )
                        raise TaskException("Invalid input data")

                    validation_span.end(outputs={"validation_result": "success"})

                # Span 2: LLM Execution (handled by LangChain's RunnableSequence)
                # With tracing_v2_enabled(), LangChain components will automatically nest
                # as child spans within the parent trace
                task_output = await task.execute(task_input)

                # Span 3: Output Parsing
                with trace(
                    project_name=self.project_name,
                    run_type="tool",
                    name="output_parsing",
                    inputs={
                        "raw_output": str(getattr(task, "_last_chain_result", None))
                    },
                    tags=[f"task:{task_name}", "phase:parsing"],
                    metadata={"task_name": task_name, "phase": "output_parsing"},
                ) as parsing_span:
                    # Process and validate the result
                    chain_result = getattr(task, "_last_chain_result", None)
                    parsing_success = chain_result is not None and not task_output.error

                    parsing_span.end(
                        outputs={
                            "parsing_result": (
                                "success" if parsing_success else "failed"
                            ),
                            "parsed_output": task_output.output_data,
                            "has_error": bool(task_output.error),
                        },
                        error=task_output.error,
                    )

                # Update parent trace with final results
                parent_run.end(
                    outputs={
                        "task_output": task_output.model_dump(),
                        "chain_result": str(getattr(task, "_last_chain_result", None)),
                    },
                    error=task_output.error,
                )

                return task_output


# Global LangSmith tracer instance (lazy initialization)
_langsmith_tracer = None


def get_langsmith_tracer() -> LangSmithTracer:
    """Get the global LangSmith tracer instance with lazy initialization."""
    global _langsmith_tracer
    if _langsmith_tracer is None:
        _langsmith_tracer = LangSmithTracer()
    return _langsmith_tracer
