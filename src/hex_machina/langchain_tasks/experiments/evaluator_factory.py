"""
Evaluator factory for creating evaluator functions based on YAML configuration.

This module provides a factory pattern for creating evaluator functions
that can be used with LangSmith's aevaluate.
"""

import logging
from typing import Any, Callable, Dict

from .config_models import EvaluatorConfig


class EvaluatorFactory:
    """Factory for creating evaluator functions from configuration."""

    def __init__(self):
        """Initialize the evaluator factory."""
        self._logger = logging.getLogger(
            "langchain_tasks.experiments.evaluator_factory"
        )
        self._registered_evaluators: Dict[str, Callable] = {}
        self._register_builtin_evaluators()

    def _register_builtin_evaluators(self):
        """Register built-in evaluator functions."""
        self._registered_evaluators.update(
            {
                "helpfulness_scorer": self._create_helpfulness_scorer,
                "conciseness_scorer": self._create_conciseness_scorer,
                "relevance_scorer": self._create_relevance_scorer,
                "length_scorer": self._create_length_scorer,
                "content_scorer": self._create_content_scorer,
            }
        )
        self._logger.info(
            f"Registered {len(self._registered_evaluators)} built-in evaluators"
        )

    def register_evaluator(self, name: str, evaluator_func: Callable):
        """Register a custom evaluator function."""
        self._registered_evaluators[name] = evaluator_func
        self._logger.info(f"Registered custom evaluator: {name}")

    def create_evaluator(self, config: EvaluatorConfig) -> Callable:
        """Create an evaluator function from configuration."""
        evaluator_name = config.name

        if evaluator_name in self._registered_evaluators:
            # Use registered evaluator
            evaluator_func = self._registered_evaluators[evaluator_name]
            return evaluator_func(config.parameters or {})
        else:
            # Try to create from type
            return self._create_evaluator_by_type(config)

    def _create_evaluator_by_type(self, config: EvaluatorConfig) -> Callable:
        """Create evaluator based on type."""
        evaluator_type = config.type

        if evaluator_type == "custom_function":
            return self._create_custom_evaluator(config)
        elif evaluator_type == "helpfulness":
            return self._create_helpfulness_scorer(config.parameters or {})
        elif evaluator_type == "conciseness":
            return self._create_conciseness_scorer(config.parameters or {})
        elif evaluator_type == "relevance":
            return self._create_relevance_scorer(config.parameters or {})
        else:
            raise ValueError(f"Unknown evaluator type: {evaluator_type}")

    def _create_custom_evaluator(self, config: EvaluatorConfig) -> Callable:
        """Create a custom evaluator based on configuration."""

        # This is a placeholder - in practice, you might load custom functions
        # from modules or create them dynamically
        def custom_evaluator(run, example):
            return {
                "score": 0.5,
                "reasoning": f"Custom evaluator: {config.name}",
                "criterion": config.name,
                "type": "custom",
            }

        return custom_evaluator

    def _create_helpfulness_scorer(self, params: Dict[str, Any]) -> Callable:
        """Create a helpfulness scorer based on parameters."""
        min_length = params.get("min_length_threshold", 50)
        max_length = params.get("max_length_threshold", 200)
        length_weight = params.get("length_weight", 0.7)
        content_weight = params.get("content_weight", 0.3)
        bonus_for_details = params.get("bonus_for_details", False)

        def helpfulness_evaluator(run, example):
            output = run.outputs.get("result", "")
            if isinstance(output, str):
                length = len(output)

                # Length-based scoring
                if length < min_length:
                    length_score = 0.0
                elif length > max_length:
                    length_score = 0.5
                else:
                    length_score = 1.0

                # Content-based scoring (simple heuristic)
                content_score = 0.5
                if bonus_for_details and length > min_length + 50:
                    content_score = 0.8

                # Combined score
                final_score = (length_score * length_weight) + (
                    content_score * content_weight
                )

                return {
                    "score": min(1.0, final_score),
                    "reasoning": f"Length: {length} chars (score: {length_score:.2f}), Content: {content_score:.2f}",
                    "criterion": "helpfulness",
                    "parameters": {
                        "min_length": min_length,
                        "max_length": max_length,
                        "length_weight": length_weight,
                        "content_weight": content_weight,
                    },
                }
            else:
                return {
                    "score": 0.5,
                    "reasoning": "Non-string output",
                    "criterion": "helpfulness",
                }

        return helpfulness_evaluator

    def _create_conciseness_scorer(self, params: Dict[str, Any]) -> Callable:
        """Create a conciseness scorer based on parameters."""
        optimal_length = params.get("optimal_length", 100)
        length_tolerance = params.get("length_tolerance", 50)
        max_score_length = params.get("max_score_length", 150)
        penalty_for_verbosity = params.get("penalty_for_verbosity", False)

        def conciseness_evaluator(run, example):
            output = run.outputs.get("result", "")
            if isinstance(output, str):
                length = len(output)

                # Calculate conciseness score
                if length <= optimal_length:
                    score = 1.0
                elif length <= optimal_length + length_tolerance:
                    score = 0.8
                elif length <= max_score_length:
                    score = 0.5
                else:
                    score = 0.2

                # Apply penalty for verbosity
                if penalty_for_verbosity and length > max_score_length:
                    score *= 0.8

                return {
                    "score": max(0.0, score),
                    "reasoning": f"Length: {length} chars, Optimal: {optimal_length}±{length_tolerance}",
                    "criterion": "conciseness",
                    "parameters": {
                        "optimal_length": optimal_length,
                        "length_tolerance": length_tolerance,
                        "max_score_length": max_score_length,
                    },
                }
            else:
                return {
                    "score": 0.5,
                    "reasoning": "Non-string output",
                    "criterion": "conciseness",
                }

        return conciseness_evaluator

    def _create_relevance_scorer(self, params: Dict[str, Any]) -> Callable:
        """Create a relevance scorer based on parameters."""
        context_keywords = params.get("context_keywords", [])
        keyword_weight = params.get("keyword_weight", 0.8)
        context_weight = params.get("context_weight", 0.2)

        def relevance_evaluator(run, example):
            output = run.outputs.get("result", "")
            input_data = run.inputs

            if isinstance(output, str) and input_data:
                # Check if output contains input context
                output_lower = output.lower()
                input_lower = str(input_data).lower()

                # Keyword matching
                keyword_score = 0.0
                for keyword in context_keywords:
                    if keyword.lower() in output_lower:
                        keyword_score += 1.0

                if context_keywords:
                    keyword_score /= len(context_keywords)

                # Context relevance
                context_score = 0.5
                if any(keyword.lower() in input_lower for keyword in context_keywords):
                    context_score = 0.8

                # Combined score
                final_score = (keyword_score * keyword_weight) + (
                    context_score * context_weight
                )

                return {
                    "score": min(1.0, final_score),
                    "reasoning": f"Keywords: {keyword_score:.2f}, Context: {context_score:.2f}",
                    "criterion": "relevance",
                    "parameters": {
                        "context_keywords": context_keywords,
                        "keyword_weight": keyword_weight,
                        "context_weight": context_weight,
                    },
                }
            else:
                return {
                    "score": 0.5,
                    "reasoning": "Missing output or input data",
                    "criterion": "relevance",
                }

        return relevance_evaluator

    def _create_length_scorer(self, params: Dict[str, Any]) -> Callable:
        """Create a simple length-based scorer."""

        def length_evaluator(run, example):
            output = run.outputs.get("result", "")
            if isinstance(output, str):
                length = len(output)
                score = min(1.0, length / 100.0)

                return {
                    "score": score,
                    "reasoning": f"Length: {length} characters",
                    "criterion": "length",
                }
            else:
                return {
                    "score": 0.5,
                    "reasoning": "Non-string output",
                    "criterion": "length",
                }

        return length_evaluator

    def _create_content_scorer(self, params: Dict[str, Any]) -> Callable:
        """Create a content-based scorer."""

        def content_evaluator(run, example):
            output = run.outputs.get("result", "")
            if isinstance(output, str):
                # Simple content scoring based on variety
                words = output.split()
                unique_words = len(set(words))
                total_words = len(words)

                if total_words > 0:
                    diversity = unique_words / total_words
                    score = min(1.0, diversity * 2)  # Scale to 0-1
                else:
                    score = 0.0

                return {
                    "score": score,
                    "reasoning": f"Word diversity: {diversity:.2f} ({unique_words}/{total_words})",
                    "criterion": "content_quality",
                }
            else:
                return {
                    "score": 0.5,
                    "reasoning": "Non-string output",
                    "criterion": "content_quality",
                }

        return content_evaluator


# Global factory instance
evaluator_factory = EvaluatorFactory()
