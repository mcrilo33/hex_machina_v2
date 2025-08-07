"""LangChain-aligned task base class."""

import logging
import time
from abc import abstractmethod
from typing import Any, Dict, Optional

from langchain_core.language_models import BaseLLM
from langchain_core.output_parsers import BaseOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence
from pydantic import Field

from src.hex_machina.core import TaskException, TaskInput, TaskOutput
from src.hex_machina.enrichment.core import EnrichmentConfig, EnrichmentTask
from src.hex_machina.enrichment.tracing.langsmith_integration import (
    get_langsmith_tracer,
)


class LangChainTaskConfig(EnrichmentConfig):
    """Configuration for LangChain-aligned tasks."""

    # LLM settings
    llm_provider: str = Field(
        description="LLM provider (openrouter, openai, anthropic)"
    )
    llm_model: str = Field(description="Model name/identifier")
    api_key: Optional[str] = Field(default=None, description="API key for the provider")

    # Generation settings
    temperature: float = Field(default=0.0, description="Model temperature")
    max_tokens: Optional[int] = Field(
        default=None, description="Maximum tokens for response"
    )
    timeout: int = Field(default=30, description="Request timeout in seconds")

    # Prompt settings
    prompt_template: str = Field(description="Prompt template string or template name")
    prompt_variables: Optional[Dict[str, str]] = Field(
        default=None, description="Prompt variables"
    )

    # Output settings
    output_parser: Optional[str] = Field(
        default=None, description="Output parser to use"
    )


class LangChainTask(EnrichmentTask):
    """Base class for LangChain-aligned tasks using LCEL patterns."""

    def __init__(self, name: str, config: LangChainTaskConfig):
        """Initialize the LangChain task.

        Args:
            name: Task name
            config: LangChain task configuration
        """
        super().__init__(name, config)
        self._logger = logging.getLogger(f"enrichment.task.langchain.{name}")
        self._llm: Optional[BaseLLM] = None
        self._prompt_template: Optional[PromptTemplate] = None
        self._output_parser: Optional[BaseOutputParser] = None
        self._chain: Optional[RunnableSequence] = None

    def initialize(self) -> None:
        """Initialize the LangChain task components."""
        super().initialize()
        self._initialize_llm()
        self._initialize_prompt_template()
        self._initialize_output_parser()
        self._build_chain()

    def _initialize_llm(self) -> None:
        """Initialize the LangChain LLM."""
        if not self.config:
            raise TaskException("LangChain task configuration is required")

        provider = self.config.llm_provider.lower()

        if provider == "openrouter":
            self._llm = self._create_openrouter_llm()
        elif provider == "openai":
            self._llm = self._create_openai_llm()
        else:
            raise TaskException(f"Unsupported LLM provider: {provider}")

        self._logger.info(f"Initialized {provider} LLM: {self.config.llm_model}")

    def _initialize_prompt_template(self) -> None:
        """Initialize the LangChain prompt template."""
        if not self.config:
            raise TaskException("LangChain task configuration is required")

        try:
            # Check if it's a named template first
            from src.hex_machina.enrichment.prompts.langchain_templates import (
                create_custom_template,
                get_langchain_template,
            )

            template_str = self.config.prompt_template

            try:
                # Try to get a named template
                self._prompt_template = get_langchain_template(template_str)
                self._logger.info(f"Loaded named template: {template_str}")
            except ValueError:
                # Create custom template from string
                self._prompt_template = create_custom_template(template_str)
                self._logger.info("Created custom template from string")

        except Exception as e:
            self._logger.error(f"Failed to initialize prompt template: {e}")
            raise TaskException(f"Prompt template initialization failed: {e}")

    def _initialize_output_parser(self) -> None:
        """Initialize the LangChain output parser."""
        if not self.config:
            raise TaskException("LangChain task configuration is required")

        # Get parser name from config or use task default
        parser_name = self.config.output_parser
        if not parser_name:
            if hasattr(self, "get_default_parser_name"):
                parser_name = self.get_default_parser_name()
            else:
                # Default to no parser (raw text output)
                self._output_parser = None
                return

        # Create parser using our registry (which supports LangChain parsers)
        from src.hex_machina.enrichment.output_parsers import parser_registry

        self._output_parser = parser_registry.create_parser(parser_name)

        if not self._output_parser:
            raise TaskException(f"Failed to create output parser: {parser_name}")

        self._logger.info(f"Initialized output parser: {parser_name}")

    def _build_chain(self) -> None:
        """Build the LangChain LCEL chain."""
        if not self._llm or not self._prompt_template:
            raise TaskException("LLM and prompt template must be initialized")

        try:
            # Build the chain: prompt | llm | parser
            chain = self._prompt_template | self._llm

            if self._output_parser:
                chain = chain | self._output_parser

            # Set a clean chain name and metadata for LangSmith tracing
            chain_name = self.name
            chain_config = {
                "name": chain_name,
                "metadata": {
                    "llm_provider": self.config.llm_provider,
                    "llm_model": self.config.llm_model,
                    "prompt_template": self.config.prompt_template,
                    "output_parser": self.config.output_parser or "none",
                    "temperature": str(self.config.temperature),
                    "timeout": str(self.config.timeout),
                },
                "tags": [
                    f"provider:{self.config.llm_provider}",
                    f"model:{self.config.llm_model}",
                    f"parser:{self.config.output_parser or 'none'}",
                ],
            }
            self._chain = chain.with_config(chain_config)
            self._logger.info(f"Built LangChain LCEL chain: {chain_name}")

        except Exception as e:
            self._logger.error(f"Failed to build chain: {e}")
            raise TaskException(f"Chain building failed: {e}")

    def _create_openrouter_llm(self) -> BaseLLM:
        """Create OpenRouter LLM using LangChain."""
        try:
            from langchain_openai import ChatOpenAI

            from src.hex_machina.enrichment.config import EnvConfig

            env_config = EnvConfig.load()
            api_key = env_config.get_api_key("openrouter")

            if not api_key:
                raise TaskException("OpenRouter API key not found")

            return ChatOpenAI(
                model=self.config.llm_model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                openai_api_key=api_key,
                openai_api_base="https://openrouter.ai/api/v1",
                timeout=self.config.timeout,
            )

        except Exception as e:
            self._logger.error(f"Failed to create OpenRouter LLM: {e}")
            raise TaskException(f"OpenRouter LLM creation failed: {e}")

    def _create_openai_llm(self) -> BaseLLM:
        """Create OpenAI LLM using LangChain."""
        try:
            from langchain_openai import ChatOpenAI

            from src.hex_machina.enrichment.config import EnvConfig

            env_config = EnvConfig.load()
            api_key = env_config.get_api_key("openai")

            if not api_key:
                raise TaskException("OpenAI API key not found")

            return ChatOpenAI(
                model=self.config.llm_model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                openai_api_key=api_key,
                timeout=self.config.timeout,
            )

        except Exception as e:
            self._logger.error(f"Failed to create OpenAI LLM: {e}")
            raise TaskException(f"OpenAI LLM creation failed: {e}")

    async def execute(self, input_data: TaskInput) -> TaskOutput:
        """Execute the LangChain task using LCEL.

        Args:
            input_data: Task input data

        Returns:
            Task output with results
        """
        start_time = time.time()

        try:
            # Validate input
            if not self.validate_input(input_data):
                raise TaskException("Invalid input data")

            # Prepare input for LangChain
            chain_input = self._prepare_chain_input(input_data)

            # Execute the chain with LangSmith tracing
            result = await self._chain.ainvoke(chain_input)

            # Process the result
            output_data = self._process_chain_result(result)

            # Store the raw chain result for custom tracing
            self._last_chain_result = result

            # Trace LLM call in LangSmith if available
            if hasattr(result, "content") and hasattr(chain_input, "get"):
                # This is a simplified approach - in practice, you'd want to capture
                # the actual prompt and response from the chain
                get_langsmith_tracer().trace_llm_call(
                    prompt=str(chain_input),
                    response=str(result),
                    metadata={
                        "task_name": self.name,
                        "llm_provider": self.config.llm_provider,
                        "llm_model": self.config.llm_model,
                    },
                )

            # Create task output
            execution_time = time.time() - start_time

            return TaskOutput(
                task_id=input_data.task_id,
                output_data=output_data,
                metadata={
                    "task_name": self.name,
                    "llm_provider": self.config.llm_provider,
                    "llm_model": self.config.llm_model,
                    "prompt_template": self.config.prompt_template,
                    "output_parser": self.config.output_parser or "none",
                    "temperature": self.config.temperature,
                    "timeout": self.config.timeout,
                    "chain_type": self._chain.__class__.__name__,
                },
                execution_time=execution_time,
                created_at=input_data.created_at,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            self._logger.error(f"LangChain task execution failed: {e}")

            return TaskOutput(
                task_id=input_data.task_id,
                output_data={},
                metadata={"task_name": self.name, "error": str(e)},
                execution_time=execution_time,
                error=str(e),
                created_at=input_data.created_at,
            )

    def _prepare_chain_input(self, input_data: TaskInput) -> Dict[str, Any]:
        """Prepare input data for LangChain chain.

        Args:
            input_data: Task input data

        Returns:
            Input dictionary for LangChain chain
        """
        # Convert our TaskInput to LangChain-compatible format
        chain_input = input_data.input_data.copy()

        # Add any additional variables from config
        if self.config.prompt_variables:
            chain_input.update(self.config.prompt_variables)

        return chain_input

    def _process_chain_result(self, result: Any) -> Dict[str, Any]:
        """Process the result from LangChain chain.

        Args:
            result: Result from LangChain chain

        Returns:
            Processed output data
        """
        # Convert result to dictionary format
        if isinstance(result, dict):
            return result
        elif hasattr(result, "model_dump"):
            # Pydantic model
            return result.model_dump()
        else:
            # Other types - wrap in result key
            return {"result": result}

    @abstractmethod
    def validate_input(self, input_data: TaskInput) -> bool:
        """Validate the input data for this specific task."""
        pass

    def get_default_parser_name(self) -> Optional[str]:
        """Get the default output parser name for this task.

        Returns:
            Default parser name, or None for no parser
        """
        return None
