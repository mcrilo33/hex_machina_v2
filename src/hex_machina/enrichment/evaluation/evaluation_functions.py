"""
Evaluation functions and evaluator registry for workflow operations and datasets.
"""

import logging
from typing import Any, Dict, List, Optional

from langchain.evaluation import (
    CriteriaEvalChain,
    EmbeddingDistanceEvalChain,
    ExactMatchStringEvaluator,
    JsonValidityEvaluator,
    LabeledCriteriaEvalChain,
    QAEvalChain,
    StringDistanceEvalChain,
)

from src.hex_machina.datasets.manager import DatasetManager
from src.hex_machina.enrichment.evaluation.config import EvaluationConfig
from src.hex_machina.enrichment.evaluation.langsmith_integration import (
    create_evaluation_experiment,
)
from src.hex_machina.storage.manager import get_storage_manager
from src.hex_machina.storage.models import ArticleDB, EnrichmentDB

logger = logging.getLogger(__name__)

# Global config instance
_evaluation_config = None


def get_evaluation_config() -> EvaluationConfig:
    """Get the global evaluation configuration instance."""
    global _evaluation_config
    if _evaluation_config is None:
        _evaluation_config = EvaluationConfig()
    return _evaluation_config


# Evaluator Registry - now uses configuration
def create_evaluator(evaluator_name: str) -> Any:
    """Create an evaluator instance from the registry using configuration."""
    config = get_evaluation_config()

    try:
        evaluator_config = config.get_evaluator_config(evaluator_name)
        llm = config.get_llm_for_evaluator(evaluator_name)
        criteria = config.get_criteria_for_evaluator(evaluator_name)

        if evaluator_name.startswith("criteria_"):
            # Criteria evaluators
            if criteria:
                return CriteriaEvalChain.from_llm(llm=llm, criteria=criteria)
            else:
                raise ValueError(
                    f"Criteria evaluator '{evaluator_name}' requires criteria configuration"
                )

        elif evaluator_name == "qa":
            return QAEvalChain.from_llm(llm=llm)

        elif evaluator_name == "embedding_distance":
            return EmbeddingDistanceEvalChain.from_llm(llm=llm)

        elif evaluator_name == "string_distance":
            return StringDistanceEvalChain.from_llm(llm=llm)

        elif evaluator_name == "exact_match":
            return ExactMatchStringEvaluator()

        elif evaluator_name == "json_validity":
            return JsonValidityEvaluator()

        elif evaluator_name.startswith("labeled_criteria_"):
            # Labeled criteria evaluators
            if criteria:
                return LabeledCriteriaEvalChain.from_llm(llm=llm, criteria=criteria)
            else:
                raise ValueError(
                    f"Labeled criteria evaluator '{evaluator_name}' requires criteria configuration"
                )

        else:
            raise ValueError(f"Unknown evaluator: {evaluator_name}")

    except Exception as e:
        logger.error(f"Failed to create evaluator '{evaluator_name}': {e}")
        raise


def evaluate_workflow_operation(
    workflow_operation_id: str,
    evaluators: List[str],
    experiment_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Evaluate enrichments from a workflow operation using specified evaluators.

    Args:
        workflow_operation_id: The workflow operation ID to evaluate
        evaluators: List of evaluator names to run
        experiment_name: Optional name for the LangSmith experiment

    Returns:
        Dictionary of evaluation results
    """

    # Get storage manager
    storage_manager = get_storage_manager()

    # Get enrichments for this workflow operation
    with storage_manager.session() as session:
        enrichments = (
            session.query(EnrichmentDB)
            .filter(EnrichmentDB.workflow_operation_id == workflow_operation_id)
            .all()
        )

        if not enrichments:
            raise ValueError(
                f"No enrichments found for workflow operation: {workflow_operation_id}"
            )

        # Get articles for these enrichments
        article_ids = [e.article_id for e in enrichments]
        articles = session.query(ArticleDB).filter(ArticleDB.id.in_(article_ids)).all()

        # Create article lookup
        article_lookup = {a.id: a for a in articles}

    # Prepare evaluation data
    evaluation_data = []
    for enrichment in enrichments:
        article = article_lookup.get(enrichment.article_id)
        if article and enrichment.task_output:
            evaluation_data.append(
                {
                    "input": article.text_content,  # Article content as input
                    "output": enrichment.task_output,  # Task output to evaluate
                    "article_id": article.id,
                    "enrichment_id": enrichment.id,
                }
            )

    if not evaluation_data:
        raise ValueError(
            f"No valid evaluation data found for workflow operation: {workflow_operation_id}"
        )

    # Run evaluators
    results = run_evaluators(evaluation_data, evaluators, experiment_name)

    return results


def evaluate_dataset_examples(
    dataset_name: str,
    evaluators: List[str],
    split: Optional[str] = None,
    experiment_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Evaluate dataset examples using specified evaluators.

    Args:
        dataset_name: Name of the dataset to evaluate
        evaluators: List of evaluator names to run
        split: Optional split to evaluate (if None, evaluates all examples)
        experiment_name: Optional name for the LangSmith experiment

    Returns:
        Dictionary of evaluation results
    """

    # Get dataset manager
    dataset_manager = DatasetManager()

    # Get dataset examples
    examples = dataset_manager.list_articles_in_dataset(dataset_name, split=split)

    if not examples:
        raise ValueError(
            f"No examples found in dataset: {dataset_name}"
            + (f" (split: {split})" if split else "")
        )

    # Get storage manager to fetch article content
    storage_manager = get_storage_manager()

    # Prepare evaluation data
    evaluation_data = []
    with storage_manager.session() as session:
        for example in examples:
            # Get the full article to access content
            article = (
                session.query(ArticleDB)
                .filter(ArticleDB.id == example["article_id"])
                .first()
            )
            if article and article.text_content:
                evaluation_data.append(
                    {
                        "input": article.text_content,
                        "output": article.text_content,  # For dataset evaluation, we might evaluate the content itself
                        "article_id": article.id,
                        "example_id": example["example_id"],
                        "split": example["split"],
                    }
                )

    if not evaluation_data:
        raise ValueError(f"No valid evaluation data found in dataset: {dataset_name}")

    # Run evaluators
    results = run_evaluators(evaluation_data, evaluators, experiment_name)

    return results


def run_evaluators(
    evaluation_data: List[Dict[str, Any]],
    evaluators: List[str],
    experiment_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run multiple evaluators on evaluation data.

    Args:
        evaluation_data: List of dicts with 'input' and 'output' keys
        evaluators: List of evaluator names to run
        experiment_name: Optional name for the LangSmith experiment

    Returns:
        Dictionary of evaluation results
    """

    results = {}

    # Create LangSmith experiment if name provided
    experiment_id = None
    if experiment_name:
        experiment_id = create_evaluation_experiment(experiment_name)

    for evaluator_name in evaluators:
        try:
            logger.info(f"Running evaluator: {evaluator_name}")

            # Create evaluator using configuration
            evaluator = create_evaluator(evaluator_name)

            # Run evaluation
            if hasattr(evaluator, "evaluate_strings"):
                # For string-based evaluators
                eval_result = evaluator.evaluate_strings(
                    prediction=[d["output"] for d in evaluation_data],
                    input=[d["input"] for d in evaluation_data],
                    reference=None,
                )
            elif hasattr(evaluator, "evaluate"):
                # For other evaluators
                eval_result = evaluator.evaluate(
                    predictions=[d["output"] for d in evaluation_data],
                    inputs=[d["input"] for d in evaluation_data],
                    references=None,
                )
            else:
                logger.warning(
                    f"Evaluator {evaluator_name} has no known evaluation method"
                )
                continue

            results[evaluator_name] = eval_result

        except Exception as e:
            logger.error(f"Error running evaluator {evaluator_name}: {e}")
            results[evaluator_name] = {"error": str(e)}

    return results


def list_available_evaluators() -> List[Dict[str, str]]:
    """List all available evaluators with descriptions."""
    config = get_evaluation_config()
    evaluators = config.list_available_evaluators()

    return [
        {
            "name": name,
            "description": f"LangChain evaluator using {evaluator_config.get('llm', {}).get('provider', 'unknown')}",
            "provider": evaluator_config.get("llm", {}).get("provider", "unknown"),
            "model": evaluator_config.get("llm", {}).get("model", "unknown"),
        }
        for name, evaluator_config in evaluators.items()
    ]
