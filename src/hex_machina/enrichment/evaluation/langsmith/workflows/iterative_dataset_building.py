"""Iterative dataset building workflow for content completeness evaluation.

This module implements a sophisticated workflow for building high-quality evaluation
datasets through iterative refinement of prompts and models.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from langchain_openai import ChatOpenAI

from ...langchain.chains.evaluation_chains import ContentCompletenessEvaluator
from ..config import setup_langsmith_environment
from ..datasets.dataset_manager import EvaluationDatasetManager
from ..tracers.evaluation_tracer import (
    EvaluationTracer,
    TracedContentCompletenessEvaluator,
)


class IterativeDatasetBuilder:
    """Workflow for building high-quality evaluation datasets through iteration."""

    def __init__(
        self,
        llm: ChatOpenAI,
        logger: Optional[logging.Logger] = None,
        max_iterations: int = 10,
        stability_threshold: float = 0.95,
    ):
        """Initialize the iterative dataset builder.

        Args:
            llm: The language model to use for evaluation.
            logger: Optional logger instance.
            max_iterations: Maximum number of iterations to prevent infinite loops.
            stability_threshold: Threshold for considering the dataset stable.
        """
        self.llm = llm
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.max_iterations = max_iterations
        self.stability_threshold = stability_threshold

        # Setup LangSmith
        setup_langsmith_environment()

        # Initialize components
        self.dataset_manager = EvaluationDatasetManager(logger=self.logger)
        self.tracer = EvaluationTracer(logger=self.logger)

        # Track iteration history
        self.iteration_history: List[Dict[str, Any]] = []
        self.positive_examples_seen: Set[str] = set()

    async def build_high_quality_dataset(
        self,
        source_dataset_name: str,
        target_dataset_name: str,
        prompt_version: str = "v1.0",
        model_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build a high-quality dataset through iterative refinement.

        Args:
            source_dataset_name: Name of the source dataset to evaluate.
            target_dataset_name: Name of the target dataset for positive examples.
            prompt_version: Version identifier for the current prompt.
            model_name: Name of the model being used.

        Returns:
            Dict containing the final results and statistics.
        """
        self.logger.info("Starting iterative dataset building workflow")
        self.logger.info(f"Source: {source_dataset_name}")
        self.logger.info(f"Target: {target_dataset_name}")
        self.logger.info(f"Prompt: {prompt_version}")

        # Get source dataset
        source_dataset = self.dataset_manager.get_dataset(source_dataset_name)
        if not source_dataset:
            raise ValueError(f"Source dataset '{source_dataset_name}' not found")

        # Create or get target dataset
        target_dataset = self._get_or_create_target_dataset(target_dataset_name)

        # Initialize evaluator
        evaluator = ContentCompletenessEvaluator(llm=self.llm, logger=self.logger)
        traced_evaluator = TracedContentCompletenessEvaluator(evaluator, self.tracer)

        iteration = 0
        stable = False

        while iteration < self.max_iterations and not stable:
            iteration += 1
            self.logger.info(f"\n=== Iteration {iteration} ===")

            # Evaluate source dataset
            iteration_results = await self._evaluate_iteration(
                source_dataset=source_dataset,
                traced_evaluator=traced_evaluator,
                prompt_version=prompt_version,
                model_name=model_name,
                iteration=iteration,
            )

            # Extract positive examples
            new_positive_examples = self._extract_positive_examples(iteration_results)

            # Check stability
            stable = self._check_stability(new_positive_examples)

            # Add new positive examples to target dataset
            if new_positive_examples:
                await self._add_positive_examples_to_target(
                    target_dataset, new_positive_examples, iteration
                )

            # Record iteration results
            self.iteration_history.append(
                {
                    "iteration": iteration,
                    "total_evaluated": len(iteration_results),
                    "new_positive_examples": len(new_positive_examples),
                    "stability_score": self._calculate_stability_score(),
                    "timestamp": datetime.now().isoformat(),
                }
            )

            self.logger.info(f"Iteration {iteration} complete:")
            self.logger.info(f"  - Evaluated: {len(iteration_results)} articles")
            self.logger.info(f"  - New positives: {len(new_positive_examples)}")
            self.logger.info(f"  - Stability: {self._calculate_stability_score():.3f}")

        # Final evaluation on target dataset
        final_results = await self._evaluate_final_dataset(
            target_dataset, traced_evaluator, prompt_version, model_name
        )

        return {
            "workflow_completed": True,
            "iterations_performed": iteration,
            "final_stable": stable,
            "source_dataset": source_dataset_name,
            "target_dataset": target_dataset_name,
            "total_positive_examples": len(self.positive_examples_seen),
            "iteration_history": self.iteration_history,
            "final_evaluation": final_results,
        }

    async def _evaluate_iteration(
        self,
        source_dataset,
        traced_evaluator: TracedContentCompletenessEvaluator,
        prompt_version: str,
        model_name: Optional[str],
        iteration: int,
    ) -> List[Any]:
        """Evaluate the source dataset for one iteration."""

        # Start evaluation run
        run_name = f"iterative-build-{prompt_version}-iter-{iteration}-{int(asyncio.get_event_loop().time())}"
        self.tracer.start_evaluation_run(
            run_name=run_name,
            model_name=model_name or "unknown",
            prompt_version=prompt_version,
            metadata={
                "workflow_type": "iterative_dataset_building",
                "iteration": iteration,
                "source_dataset": source_dataset.name,
            },
        )

        # Get examples from source dataset
        examples = list(
            self.dataset_manager.client.list_examples(dataset_id=source_dataset.id)
        )

        # Evaluate each example
        results = []
        for example in examples:
            # Skip if we've already seen this as positive
            example_id = example.id
            if example_id in self.positive_examples_seen:
                continue

            # Create mock article from example
            mock_article = self.dataset_manager._create_mock_article_from_example(
                example
            )

            # Evaluate
            result = await traced_evaluator.evaluate_article(mock_article)
            results.append(
                {
                    "example_id": example_id,
                    "article": mock_article,
                    "evaluation": result,
                }
            )

        # End evaluation run
        self.tracer.end_evaluation_run(
            total_articles=len(results),
            successful_evaluations=len(
                [r for r in results if r["evaluation"].is_complete]
            ),
        )

        return results

    def _extract_positive_examples(
        self, iteration_results: List[Dict[str, Any]]
    ) -> Set[str]:
        """Extract positive example IDs from iteration results."""
        new_positives = set()

        for result in iteration_results:
            if result["evaluation"].is_complete:
                example_id = result["example_id"]
                if example_id not in self.positive_examples_seen:
                    new_positives.add(example_id)
                    self.positive_examples_seen.add(example_id)

        return new_positives

    def _check_stability(self, new_positive_examples: Set[str]) -> bool:
        """Check if the dataset has reached stability."""
        if not new_positive_examples:
            return True

        # Calculate stability based on recent iterations
        if len(self.iteration_history) < 3:
            return False

        recent_iterations = self.iteration_history[-3:]
        total_new_in_recent = sum(
            iter_data["new_positive_examples"] for iter_data in recent_iterations
        )

        if total_new_in_recent == 0:
            return True

        # Calculate stability score
        stability_score = self._calculate_stability_score()
        return stability_score >= self.stability_threshold

    def _calculate_stability_score(self) -> float:
        """Calculate stability score based on iteration history."""
        if len(self.iteration_history) < 2:
            return 0.0

        # Calculate the ratio of iterations with no new positives
        stable_iterations = sum(
            1
            for iter_data in self.iteration_history
            if iter_data["new_positive_examples"] == 0
        )

        return stable_iterations / len(self.iteration_history)

    async def _add_positive_examples_to_target(
        self, target_dataset, new_positive_examples: Set[str], iteration: int
    ):
        """Add new positive examples to the target dataset."""
        self.logger.info(
            f"Adding {len(new_positive_examples)} new positive examples to target dataset"
        )

        # Get examples from source dataset
        source_examples = list(
            self.dataset_manager.client.list_examples(dataset_id=target_dataset.id)
        )

        for example_id in new_positive_examples:
            # Find the example in source dataset
            example = next((ex for ex in source_examples if ex.id == example_id), None)
            if example:
                # Add to target dataset with manual review flag
                self.dataset_manager.client.create_example(
                    inputs=example.inputs,
                    outputs={
                        "is_complete": True,
                        "manual_review_required": True,
                        "added_in_iteration": iteration,
                        "added_timestamp": datetime.now().isoformat(),
                    },
                    dataset_id=target_dataset.id,
                    metadata={
                        "source_example_id": example_id,
                        "workflow_type": "iterative_building",
                        "iteration": iteration,
                    },
                )

    async def _evaluate_final_dataset(
        self,
        target_dataset,
        traced_evaluator: TracedContentCompletenessEvaluator,
        prompt_version: str,
        model_name: Optional[str],
    ) -> Dict[str, Any]:
        """Perform final evaluation on the target dataset."""

        self.logger.info(
            f"Performing final evaluation on target dataset: {target_dataset.name}"
        )

        # Start final evaluation run
        run_name = (
            f"final-evaluation-{prompt_version}-{int(asyncio.get_event_loop().time())}"
        )
        self.tracer.start_evaluation_run(
            run_name=run_name,
            model_name=model_name or "unknown",
            prompt_version=prompt_version,
            metadata={
                "workflow_type": "final_evaluation",
                "target_dataset": target_dataset.name,
            },
        )

        # Evaluate target dataset
        results = await self.dataset_manager.run_evaluation_on_dataset(
            dataset=target_dataset,
            evaluator=traced_evaluator,
            run_name=run_name,
        )

        # End evaluation run
        self.tracer.end_evaluation_run(
            total_articles=len(results),
            successful_evaluations=len([r for r in results if r.is_complete]),
        )

        return {
            "total_examples": len(results),
            "complete_examples": len([r for r in results if r.is_complete]),
            "incomplete_examples": len([r for r in results if not r.is_complete]),
            "success_rate": (
                len([r for r in results if r.is_complete]) / len(results)
                if results
                else 0
            ),
        }

    def _get_or_create_target_dataset(self, target_dataset_name: str):
        """Get existing target dataset or create a new one."""
        target_dataset = self.dataset_manager.get_dataset(target_dataset_name)

        if not target_dataset:
            self.logger.info(f"Creating new target dataset: {target_dataset_name}")
            target_dataset = self.dataset_manager.create_evaluation_dataset(
                dataset_name=target_dataset_name,
                description="High-quality positive examples dataset built through iterative refinement",
            )
        else:
            self.logger.info(f"Using existing target dataset: {target_dataset_name}")

        return target_dataset


async def run_iterative_dataset_building(
    source_dataset_name: str,
    target_dataset_name: str,
    llm: ChatOpenAI,
    prompt_version: str = "v1.0",
    max_iterations: int = 10,
    stability_threshold: float = 0.95,
) -> Dict[str, Any]:
    """Run the iterative dataset building workflow.

    Args:
        source_dataset_name: Name of the source dataset to evaluate.
        target_dataset_name: Name of the target dataset for positive examples.
        llm: The language model to use for evaluation.
        prompt_version: Version identifier for the current prompt.
        max_iterations: Maximum number of iterations.
        stability_threshold: Threshold for considering the dataset stable.

    Returns:
        Dict containing the workflow results and statistics.
    """
    builder = IterativeDatasetBuilder(
        llm=llm,
        max_iterations=max_iterations,
        stability_threshold=stability_threshold,
    )

    return await builder.build_high_quality_dataset(
        source_dataset_name=source_dataset_name,
        target_dataset_name=target_dataset_name,
        prompt_version=prompt_version,
        model_name=llm.model_name if hasattr(llm, "model_name") else None,
    )
