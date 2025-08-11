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
from langchain_core.language_models import BaseLLM
from langchain_openai import ChatOpenAI

from src.hex_machina.datasets.manager import DatasetManager
from src.hex_machina.enrichment.evaluation.langsmith import create_evaluation_experiment
from src.hex_machina.storage.manager import get_storage_manager
from src.hex_machina.storage.models import ArticleDB, EnrichmentDB

logger = logging.getLogger(__name__)


# Evaluator Registry - specific evaluators with predefined criteria
EVALUATOR_REGISTRY = {
    # Criteria evaluators (specific criteria)
    "criteria_completeness": lambda llm: CriteriaEvalChain.from_llm(
        llm=llm, criteria={"completeness": "Is the output complete and comprehensive?"}
    ),
    "criteria_accuracy": lambda llm: CriteriaEvalChain.from_llm(
        llm=llm, criteria={"accuracy": "Is the output accurate and correct?"}
    ),
    "criteria_relevance": lambda llm: CriteriaEvalChain.from_llm(
        llm=llm, criteria={"relevance": "Is the output relevant to the input?"}
    ),
    "criteria_clarity": lambda llm: CriteriaEvalChain.from_llm(
        llm=llm, criteria={"clarity": "Is the output clear and well-written?"}
    ),
    "criteria_coherence": lambda llm: CriteriaEvalChain.from_llm(
        llm=llm,
        criteria={"coherence": "Is the output logically coherent and well-structured?"},
    ),
    # Other evaluators
    "qa": lambda llm: QAEvalChain.from_llm(llm=llm),
    "embedding_distance": lambda llm: EmbeddingDistanceEvalChain.from_llm(llm=llm),
    "string_distance": lambda llm: StringDistanceEvalChain.from_llm(llm=llm),
    "exact_match": lambda llm: ExactMatchStringEvaluator(),
    "json_validity": lambda llm: JsonValidityEvaluator(),
    # Ground truth evaluators
    "labeled_criteria_completeness": lambda llm: LabeledCriteriaEvalChain.from_llm(
        llm=llm, criteria=["completeness"]
    ),
    "labeled_criteria_accuracy": lambda llm: LabeledCriteriaEvalChain.from_llm(
        llm=llm, criteria=["accuracy"]
    ),
    "labeled_criteria_relevance": lambda llm: LabeledCriteriaEvalChain.from_llm(
        llm=llm, criteria=["relevance"]
    ),
}


def create_evaluator(evaluator_name: str, llm: BaseLLM):
    """Create an evaluator instance from the registry."""
    if evaluator_name not in EVALUATOR_REGISTRY:
        raise ValueError(f"Unknown evaluator: {evaluator_name}")

    return EVALUATOR_REGISTRY[evaluator_name](llm)


def get_llm() -> BaseLLM:
    """Get the LLM instance for evaluation."""
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        openai_api_key="ollama",
        openai_api_base="http://localhost:11434/v1",
    )


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
                    "input": article.content,  # Article content as input
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

    # Prepare evaluation data
    evaluation_data = []
    for example in examples:
        if example.article and example.article.content:
            evaluation_data.append(
                {
                    "input": example.article.content,
                    "output": example.article.content,  # For dataset evaluation, we might evaluate the content itself
                    "article_id": example.article.id,
                    "example_id": example.id,
                    "split": example.split,
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

    llm = get_llm()
    results = {}

    # Create LangSmith experiment if name provided
    experiment_id = None
    if experiment_name:
        experiment_id = create_evaluation_experiment(experiment_name)

    for evaluator_name in evaluators:
        try:
            logger.info(f"Running evaluator: {evaluator_name}")

            # Create evaluator
            evaluator = create_evaluator(evaluator_name, llm)

            # Run evaluation
            if hasattr(evaluator, "evaluate_strings"):
                # For string-based evaluators
                eval_result = evaluator.evaluate_strings(
                    prediction_strings=[d["output"] for d in evaluation_data],
                    input_strings=[d["input"] for d in evaluation_data],
                    reference_strings=None,
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
    return [
        {"name": name, "description": "LangChain evaluator"}
        for name in EVALUATOR_REGISTRY.keys()
    ]
