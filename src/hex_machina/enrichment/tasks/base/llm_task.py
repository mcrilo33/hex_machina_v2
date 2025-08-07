"""Base class for LLM-based tasks."""

import logging
import time
from abc import abstractmethod
from typing import Any, Dict, Optional

from pydantic import Field

from src.hex_machina.core import TaskException, TaskInput, TaskOutput
from src.hex_machina.enrichment.core import EnrichmentConfig, EnrichmentTask
from src.hex_machina.enrichment.llm import OpenRouterClient
from src.hex_machina.enrichment.output_parsers import parser_registry
from src.hex_machina.enrichment.prompts.prompt_manager import prompt_manager


class LLMConfig(EnrichmentConfig):
    """Configuration for LLM-based tasks."""

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
    prompt_template: str = Field(description="Prompt template name or path")
    prompt_variables: Optional[Dict[str, str]] = Field(
        default=None, description="Prompt variables"
    )

    # Output settings
    output_format: str = Field(default="json", description="Expected output format")
    output_parser: Optional[str] = Field(
        default=None, description="Output parser to use"
    )


class LLMTask(EnrichmentTask):
    """Base class for all LLM-based tasks."""

    def __init__(self, name: str, config: LLMConfig):
        """Initialize the LLM task.

        Args:
            name: Task name
            config: LLM configuration
        """
        super().__init__(name, config)
        self._logger = logging.getLogger(f"enrichment.task.llm.{name}")
        self._llm_client = None
        self._output_parser = None

    def initialize(self) -> None:
        """Initialize the LLM task and client."""
        super().initialize()
        self._initialize_llm_client()
        self._initialize_output_parser()

    def _initialize_llm_client(self) -> None:
        """Initialize the LLM client based on configuration."""
        if not self.config:
            raise TaskException("LLM configuration is required")

        provider = self.config.llm_provider.lower()

        if provider == "openrouter":
            self._llm_client = self._create_openrouter_client()
        elif provider == "openai":
            self._llm_client = self._create_openai_client()
        else:
            raise TaskException(f"Unsupported LLM provider: {provider}")

        self._logger.info(
            f"Initialized {provider} client for model: {self.config.llm_model}"
        )

    def _initialize_output_parser(self) -> None:
        """Initialize the output parser based on configuration."""
        if not self.config:
            raise TaskException("LLM configuration is required")

        # Get parser name from config or use task default
        parser_name = self.config.output_parser
        if not parser_name:
            # Try to get default from task
            if hasattr(self, "get_default_parser_name"):
                parser_name = self.get_default_parser_name()
            else:
                # Default to JSON parser if none specified
                parser_name = "JSONOutputParser"

        # Create parser instance
        self._output_parser = parser_registry.create_parser(parser_name)
        if not self._output_parser:
            raise TaskException(f"Failed to create output parser: {parser_name}")

        self._logger.info(f"Initialized output parser: {parser_name}")

    def _create_openrouter_client(self):
        """Create OpenRouter client."""
        try:
            return OpenRouterClient()
        except Exception as e:
            self._logger.error(f"Failed to create OpenRouter client: {e}")
            raise TaskException(f"OpenRouter client initialization failed: {e}")

    def _create_openai_client(self):
        """Create OpenAI client."""
        # TODO: Implement OpenAI client
        self._logger.info("OpenAI client placeholder - implement actual client")
        return None

    async def execute(self, input_data: TaskInput) -> TaskOutput:
        """Execute the LLM task.

        Args:
            input_data: Task input data

        Returns:
            Task output with LLM results
        """
        start_time = time.time()

        try:
            # Validate input
            if not self.validate_input(input_data):
                raise TaskException("Invalid input data")

            # Format prompt
            prompt = await self._format_prompt(input_data)

            # Call LLM
            llm_response = await self._call_llm(prompt)

            # Parse and validate output
            parsed_output = await self._parse_output(llm_response)

            # Create task output
            execution_time = time.time() - start_time

            return TaskOutput(
                task_id=input_data.task_id,
                output_data=parsed_output,
                metadata={
                    "task_name": self.name,
                    "llm_provider": self.config.llm_provider,
                    "llm_model": self.config.llm_model,
                    "prompt_length": len(prompt),
                    "response_length": len(llm_response),
                },
                execution_time=execution_time,
                created_at=input_data.created_at,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            self._logger.error(f"LLM task execution failed: {e}")

            return TaskOutput(
                task_id=input_data.task_id,
                output_data={},
                metadata={"task_name": self.name, "error": str(e)},
                execution_time=execution_time,
                error=str(e),
                created_at=input_data.created_at,
            )

    async def _format_prompt(self, input_data: TaskInput) -> str:
        """Format the prompt with input data.

        Args:
            input_data: Task input data

        Returns:
            Formatted prompt string
        """
        if not self.config:
            raise TaskException("LLM configuration is required")

        try:
            # Get prompt template name from config
            prompt_template = self.config.prompt_template

            # Format prompt with input data
            formatted_prompt = prompt_manager.format_prompt(
                prompt_template, **input_data.input_data
            )

            return formatted_prompt

        except Exception as e:
            self._logger.error(f"Failed to format prompt: {e}")
            raise TaskException(f"Prompt formatting failed: {e}")

    async def _call_llm(self, prompt: str) -> str:
        """Call the LLM with the given prompt.

        Args:
            prompt: The prompt to send to the LLM

        Returns:
            LLM response as string
        """
        if not self._llm_client:
            raise TaskException("LLM client not initialized")

        if not self.config:
            raise TaskException("LLM configuration is required")

        try:
            # Call the appropriate LLM client
            if isinstance(self._llm_client, OpenRouterClient):
                response = await self._llm_client.generate(
                    prompt=prompt,
                    model=self.config.llm_model,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    timeout=self.config.timeout,
                )
                return response
            else:
                raise TaskException(
                    f"Unsupported LLM client type: {type(self._llm_client)}"
                )

        except Exception as e:
            self._logger.error(f"LLM call failed: {e}")
            raise TaskException(f"LLM call failed: {e}")

    async def _parse_output(self, llm_response: str) -> Dict[str, Any]:
        """Parse and validate the LLM response.

        Args:
            llm_response: Raw LLM response

        Returns:
            Parsed and validated output
        """
        if not self._output_parser:
            raise TaskException("Output parser not initialized")

        try:
            # Use the configured output parser
            parsed_output = self._output_parser.parse(llm_response)
            return parsed_output

        except Exception as e:
            self._logger.error(f"Output parsing failed: {e}")
            raise TaskException(f"Output parsing failed: {e}")

    @abstractmethod
    def validate_input(self, input_data: TaskInput) -> bool:
        """Validate the input data for this specific task."""
        pass
