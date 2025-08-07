"""OpenRouter client implementation."""

import json
import logging
from typing import Any, Dict, Optional

import openai
from openai import AsyncOpenAI

from src.hex_machina.core import TaskException
from src.hex_machina.enrichment.config import EnvConfig


class OpenRouterClient:
    """OpenRouter client for LLM interactions."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://openrouter.ai/api/v1",
    ):
        """Initialize OpenRouter client.

        Args:
            api_key: OpenRouter API key (will load from env if not provided)
            base_url: OpenRouter API base URL
        """
        self._logger = logging.getLogger("enrichment.llm.openrouter")

        # Load API key
        if api_key:
            self.api_key = api_key
        else:
            env_config = EnvConfig.load()
            self.api_key = env_config.get_api_key("openrouter")

        if not self.api_key:
            raise TaskException(
                "OpenRouter API key not found. Set OPENROUTER_API_KEY in .env file"
            )

        # Initialize OpenAI client with OpenRouter configuration
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=base_url,
        )

        self._logger.info("OpenRouter client initialized")

    async def generate(
        self,
        prompt: str,
        model: str = "anthropic/claude-3.5-sonnet",
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        timeout: int = 30,
    ) -> str:
        """Generate text using OpenRouter.

        Args:
            prompt: The prompt to send to the model
            model: Model to use (e.g., "anthropic/claude-3.5-sonnet")
            temperature: Model temperature (0.0 = deterministic)
            max_tokens: Maximum tokens to generate
            timeout: Request timeout in seconds

        Returns:
            Generated text response

        Raises:
            TaskException: If the request fails
        """
        try:
            self._logger.debug(f"Generating with model: {model}")

            # Prepare request parameters
            params: Dict[str, Any] = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "timeout": timeout,
            }

            if max_tokens:
                params["max_tokens"] = max_tokens

            # Make request
            response = await self.client.chat.completions.create(**params)

            # Extract response content
            if response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content
                if content:
                    self._logger.debug(f"Generated response: {len(content)} characters")
                    return content
                else:
                    raise TaskException("Empty response from OpenRouter")
            else:
                raise TaskException("No choices in OpenRouter response")

        except openai.RateLimitError as e:
            self._logger.error(f"OpenRouter rate limit exceeded: {e}")
            raise TaskException(f"Rate limit exceeded: {e}")

        except openai.APIError as e:
            self._logger.error(f"OpenRouter API error: {e}")
            raise TaskException(f"API error: {e}")

        except Exception as e:
            self._logger.error(f"Unexpected error calling OpenRouter: {e}")
            raise TaskException(f"Unexpected error: {e}")

    async def generate_json(
        self,
        prompt: str,
        model: str = "anthropic/claude-3.5-sonnet",
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """Generate JSON response using OpenRouter.

        Args:
            prompt: The prompt to send to the model
            model: Model to use
            temperature: Model temperature
            max_tokens: Maximum tokens to generate
            timeout: Request timeout in seconds

        Returns:
            Parsed JSON response

        Raises:
            TaskException: If the request fails or response is not valid JSON
        """
        try:
            # Generate text response
            response_text = await self.generate(
                prompt=prompt,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )

            # Parse JSON response
            try:
                parsed_response = json.loads(response_text)
                return parsed_response
            except json.JSONDecodeError as e:
                self._logger.error(f"Failed to parse JSON response: {e}")
                self._logger.error(f"Response text: {response_text}")
                raise TaskException(f"Invalid JSON response: {e}")

        except Exception as e:
            self._logger.error(f"Error generating JSON response: {e}")
            raise TaskException(f"JSON generation failed: {e}")

    def get_available_models(self) -> list:
        """Get list of available models.

        Returns:
            List of available model names
        """
        # Common OpenRouter models
        return [
            "anthropic/claude-3.5-sonnet",
            "anthropic/claude-3-opus",
            "openai/gpt-4",
            "openai/gpt-4-turbo",
            "openai/gpt-3.5-turbo",
            "meta-llama/llama-3.1-8b-instruct",
            "meta-llama/llama-3.1-70b-instruct",
        ]
