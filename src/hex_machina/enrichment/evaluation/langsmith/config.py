"""LangSmith configuration for evaluation tracking."""

import os
from typing import Optional

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class LangSmithConfig:
    """Configuration for LangSmith integration."""

    # LangSmith API configuration
    LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
    LANGSMITH_ENDPOINT = os.getenv(
        "LANGSMITH_ENDPOINT", "https://api.smith.langchain.com"
    )

    # Project configuration
    DEFAULT_PROJECT_NAME = "hex-machina-content-evaluation"
    DEFAULT_DATASET_NAME = "content-completeness-test-set"

    # Run configuration
    DEFAULT_RUN_NAME = "content-completeness-evaluation"

    @classmethod
    def validate_config(cls) -> bool:
        """Validate that LangSmith is properly configured.

        Returns:
            bool: True if configuration is valid, False otherwise.
        """
        if not cls.LANGSMITH_API_KEY:
            print("❌ LANGSMITH_API_KEY not found in environment")
            print("   Get your API key from: https://smith.langchain.com/")
            return False

        print("✅ LangSmith API key configured")
        return True

    @classmethod
    def get_project_name(cls, project_name: Optional[str] = None) -> str:
        """Get project name for LangSmith.

        Args:
            project_name: Custom project name. If None, uses default.

        Returns:
            str: Project name to use.
        """
        return project_name or cls.DEFAULT_PROJECT_NAME

    @classmethod
    def get_dataset_name(cls, dataset_name: Optional[str] = None) -> str:
        """Get dataset name for LangSmith.

        Args:
            dataset_name: Custom dataset name. If None, uses default.

        Returns:
            str: Dataset name to use.
        """
        return dataset_name or cls.DEFAULT_DATASET_NAME

    @classmethod
    def get_run_name(cls, run_name: Optional[str] = None) -> str:
        """Get run name for LangSmith.

        Args:
            run_name: Custom run name. If None, uses default.

        Returns:
            str: Run name to use.
        """
        return run_name or cls.DEFAULT_RUN_NAME


def setup_langsmith_environment():
    """Setup LangSmith environment variables."""
    if not LangSmithConfig.LANGSMITH_API_KEY:
        print("⚠️  LangSmith API key not found. Some features will be disabled.")
        return False

    # Set environment variables for LangChain
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_ENDPOINT"] = LangSmithConfig.LANGSMITH_ENDPOINT
    os.environ["LANGCHAIN_API_KEY"] = LangSmithConfig.LANGSMITH_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = LangSmithConfig.DEFAULT_PROJECT_NAME

    print("✅ LangSmith environment configured")
    return True
