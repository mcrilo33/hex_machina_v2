"""Environment configuration management."""

from typing import Optional

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings


class EnvConfig(BaseSettings):
    """Environment configuration for enrichment tasks."""

    # API Keys
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    openrouter_api_key: Optional[str] = Field(
        default=None, description="OpenRouter API key"
    )

    # Application Settings
    app_name: str = Field(default="Hex Machina v2", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Log level")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from .env

    @classmethod
    def load(cls) -> "EnvConfig":
        """Load environment configuration from .env file."""
        # Load .env file if it exists
        load_dotenv()

        # Create config instance
        return cls()

    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for a specific provider.

        Args:
            provider: Provider name (openai, openrouter, etc.)

        Returns:
            API key if available, None otherwise
        """
        provider_lower = provider.lower()

        if provider_lower == "openai":
            return self.openai_api_key
        elif provider_lower == "openrouter":
            return self.openrouter_api_key
        else:
            return None

    def has_api_key(self, provider: str) -> bool:
        """Check if API key is available for a provider.

        Args:
            provider: Provider name

        Returns:
            True if API key is available, False otherwise
        """
        api_key = self.get_api_key(provider)
        return api_key is not None and api_key.strip() != ""
