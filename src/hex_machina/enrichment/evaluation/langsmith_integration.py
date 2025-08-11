"""
LangSmith integration for evaluation experiments and tracing.
"""

import os
import logging
from typing import Optional
from dotenv import load_dotenv
from langsmith import Client

logger = logging.getLogger(__name__)


def setup_langsmith_environment():
    """Setup LangSmith environment variables."""
    load_dotenv()
    
    # Ensure required environment variables are set
    required_vars = ["LANGSMITH_API_KEY", "LANGSMITH_PROJECT"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.warning(f"Missing LangSmith environment variables: {missing_vars}")
        logger.warning("LangSmith integration may not work properly")


def create_evaluation_experiment(experiment_name: str) -> Optional[str]:
    """
    Create a LangSmith experiment for evaluation.
    
    Args:
        experiment_name: Name of the experiment
        
    Returns:
        Experiment ID if successful, None otherwise
    """
    try:
        api_key = os.getenv("LANGSMITH_API_KEY")
        project_name = os.getenv("LANGSMITH_PROJECT")
        
        if not api_key or not project_name:
            logger.warning("LangSmith API key or project not configured")
            return None
        
        client = Client(api_key=api_key)
        
        # Create experiment
        experiment = client.create_project(
            project_name=experiment_name,
            description=f"Evaluation experiment: {experiment_name}"
        )
        
        logger.info(f"Created LangSmith experiment: {experiment_name}")
        return experiment.id
        
    except Exception as e:
        logger.error(f"Failed to create LangSmith experiment: {e}")
        return None


def log_evaluation_result(
    experiment_id: str,
    evaluator_name: str,
    result: dict,
    metadata: Optional[dict] = None
):
    """
    Log evaluation result to LangSmith.
    
    Args:
        experiment_id: LangSmith experiment ID
        evaluator_name: Name of the evaluator
        result: Evaluation result
        metadata: Optional metadata
    """
    try:
        api_key = os.getenv("LANGSMITH_API_KEY")
        if not api_key:
            logger.warning("LangSmith API key not configured")
            return
        
        client = Client(api_key=api_key)
        
        # Log the evaluation result
        client.log_feedback(
            run_id=experiment_id,
            key=evaluator_name,
            score=result.get("score", 0),
            comment=str(result),
            metadata=metadata or {}
        )
        
        logger.debug(f"Logged evaluation result for {evaluator_name}")
        
    except Exception as e:
        logger.error(f"Failed to log evaluation result: {e}")


def get_experiment_url(experiment_id: str) -> str:
    """Get the URL for a LangSmith experiment."""
    base_url = "https://smith.langchain.com"
    return f"{base_url}/experiments/{experiment_id}"
