"""Custom tracer for content completeness evaluation runs."""

import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional

from langchain_core.tracers import LangChainTracer

from ...models.evaluation_models import ContentCompletenessEvaluation


class EvaluationTracer:
    """Custom tracer for tracking content completeness evaluations."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the evaluation tracer.

        Args:
            logger: Optional logger instance.
        """
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.tracer = LangChainTracer()
        self.current_run_id: Optional[str] = None
        self.evaluation_metadata: Dict[str, Any] = {}

    def start_evaluation_run(
        self,
        run_name: str,
        model_name: str,
        prompt_version: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Start a new evaluation run.

        Args:
            run_name: Name of the evaluation run.
            model_name: Name of the LLM model being used.
            prompt_version: Version identifier for the prompt.
            metadata: Additional metadata for the run.

        Returns:
            str: Run ID for tracking.
        """
        self.evaluation_metadata = {
            "run_name": run_name,
            "model_name": model_name,
            "prompt_version": prompt_version,
            "start_time": datetime.now().isoformat(),
            **(metadata or {}),
        }

        self.logger.info(f"Starting evaluation run: {run_name} with {model_name}")
        return run_name

    def log_article_evaluation(
        self,
        article: Any,
        evaluation_result: ContentCompletenessEvaluation,
        processing_time: float,
        additional_metadata: Optional[Dict[str, Any]] = None,
    ):
        """Log an individual article evaluation.

        Args:
            article: The article being evaluated.
            evaluation_result: The evaluation result.
            processing_time: Time taken for evaluation.
            additional_metadata: Additional metadata for this evaluation.
        """
        article_metadata = {
            "article_id": getattr(article, "id", None),
            "article_url": getattr(article, "url", "unknown"),
            "article_title": getattr(article, "title", "unknown"),
            "content_length": len(getattr(article, "text_content", "")),
            "evaluation_result": evaluation_result.dict(),
            "processing_time_seconds": processing_time,
            **(additional_metadata or {}),
        }

        # Log to LangSmith
        if self.tracer:
            try:
                self.tracer.log(
                    name="article_evaluation",
                    inputs={
                        "article_url": article_metadata["article_url"],
                        "content_length": article_metadata["content_length"],
                        "article_title": article_metadata["article_title"],
                    },
                    outputs={
                        "is_complete": evaluation_result.is_complete,
                        "detected_issues": evaluation_result.detected_issues,
                        "processing_time": processing_time,
                    },
                    metadata=article_metadata,
                )
            except Exception as e:
                self.logger.warning(f"Failed to log to LangSmith: {e}")

        self.logger.info(
            f"Evaluated article {article_metadata['article_url']}: "
            f"{'Complete' if evaluation_result.is_complete else 'Incomplete'} "
            f"({processing_time:.2f}s)"
        )

    def end_evaluation_run(self, total_articles: int, successful_evaluations: int):
        """End the current evaluation run.

        Args:
            total_articles: Total number of articles processed.
            successful_evaluations: Number of successful evaluations.
        """
        end_time = datetime.now()
        start_time = datetime.fromisoformat(self.evaluation_metadata["start_time"])
        total_time = (end_time - start_time).total_seconds()

        run_summary = {
            **self.evaluation_metadata,
            "end_time": end_time.isoformat(),
            "total_processing_time_seconds": total_time,
            "total_articles": total_articles,
            "successful_evaluations": successful_evaluations,
            "success_rate": (
                successful_evaluations / total_articles if total_articles > 0 else 0
            ),
        }

        # Log run summary to LangSmith
        if self.tracer:
            try:
                self.tracer.log(
                    name="evaluation_run_summary",
                    inputs={"run_metadata": self.evaluation_metadata},
                    outputs=run_summary,
                    metadata=run_summary,
                )
            except Exception as e:
                self.logger.warning(f"Failed to log run summary to LangSmith: {e}")

        self.logger.info(
            f"Completed evaluation run: {run_summary['successful_evaluations']}/{run_summary['total_articles']} "
            f"articles processed in {total_time:.2f}s"
        )

        # Reset for next run
        self.evaluation_metadata = {}
        self.current_run_id = None


class TracedContentCompletenessEvaluator:
    """Wrapper for ContentCompletenessEvaluator with LangSmith tracing."""

    def __init__(self, evaluator, tracer: EvaluationTracer):
        """Initialize the traced evaluator.

        Args:
            evaluator: The underlying ContentCompletenessEvaluator.
            tracer: The evaluation tracer.
        """
        self.evaluator = evaluator
        self.tracer = tracer

    async def evaluate_article(
        self, article: Any, **kwargs
    ) -> ContentCompletenessEvaluation:
        """Evaluate a single article with tracing.

        Args:
            article: The article to evaluate.
            **kwargs: Additional arguments for evaluation.

        Returns:
            ContentCompletenessEvaluation: The evaluation result.
        """
        start_time = time.time()

        try:
            result = await self.evaluator.evaluate_article(article, **kwargs)
            processing_time = time.time() - start_time

            # Log the evaluation
            self.tracer.log_article_evaluation(
                article=article,
                evaluation_result=result,
                processing_time=processing_time,
            )

            return result

        except Exception as e:
            processing_time = time.time() - start_time
            self.tracer.logger.error(f"Evaluation failed: {e}")

            # Create error evaluation
            error_result = self.evaluator._create_error_evaluation(article, str(e))
            error_result.processing_time_seconds = processing_time

            # Log the error
            self.tracer.log_article_evaluation(
                article=article,
                evaluation_result=error_result,
                processing_time=processing_time,
                additional_metadata={"error": str(e)},
            )

            return error_result

    async def evaluate_articles(
        self, articles: list[Any], **kwargs
    ) -> list[ContentCompletenessEvaluation]:
        """Evaluate multiple articles with tracing.

        Args:
            articles: List of articles to evaluate.
            **kwargs: Additional arguments for evaluation.

        Returns:
            list[ContentCompletenessEvaluation]: List of evaluation results.
        """
        results = []
        successful_evaluations = 0

        for article in articles:
            result = await self.evaluate_article(article, **kwargs)
            results.append(result)

            if result.evaluation_status == "completed":
                successful_evaluations += 1

        # End the evaluation run
        self.tracer.end_evaluation_run(
            total_articles=len(articles), successful_evaluations=successful_evaluations
        )

        return results
