"""LangChain chains for content completeness evaluation."""

import asyncio
import time
from typing import Any, List, Optional

from langchain.chains import LLMChain
from langchain.llms.base import BaseLLM

from src.hex_machina.enrichment.evaluation.evaluators.base_evaluator import (
    BaseEvaluator,
)
from src.hex_machina.enrichment.evaluation.langchain.output_parsers.evaluation_parsers import (
    ContentCompletenessOutputParser,
)
from src.hex_machina.enrichment.evaluation.langchain.prompts.evaluation_prompts import (
    ARTICLE_COMPLETENESS_EVALUATION_PROMPT,
)
from src.hex_machina.enrichment.evaluation.models.evaluation_models import (
    ContentCompletenessEvaluation,
    EvaluationStatus,
)

# Configuration constants
MAX_CONTENT_LENGTH = 8000  # Maximum content length to send to LLM


class ContentCompletenessEvaluator(BaseEvaluator):
    """Evaluator for determining if article content is complete using LangChain."""

    def __init__(
        self,
        llm: BaseLLM,
        logger: Optional[Any] = None,
    ):
        """Initialize the evaluator.

        Args:
            llm: LangChain LLM instance to use for evaluation.
            logger: Optional logger instance.
        """
        super().__init__(logger)
        self.llm = llm

        # Create the parser
        self.parser = ContentCompletenessOutputParser(logger=self.logger)

        # Create the LangChain chain
        self.chain = LLMChain(
            llm=self.llm,
            prompt=ARTICLE_COMPLETENESS_EVALUATION_PROMPT,
            output_parser=self.parser,
        )

    async def evaluate_article(
        self, article: Any, **kwargs
    ) -> ContentCompletenessEvaluation:
        """Evaluate a single article for content completeness.

        Args:
            article: The article object to evaluate.
            **kwargs: Additional arguments for evaluation.

        Returns:
            ContentCompletenessEvaluation: The evaluation result.
        """
        start_time = time.time()

        try:
            # Extract article information
            title = self._extract_article_title(article)
            content = self._extract_article_text(article)

            # Validate we have content to evaluate
            if not content or len(content.strip()) < 50:
                return self._create_error_evaluation(
                    article,
                    "Insufficient content to evaluate (less than 50 characters)",
                )

            # Prepare content for evaluation (smart truncation)
            processed_content = self._process_content_for_evaluation(content)

            # Prepare input for the chain
            chain_input = {
                "title": title or "No title available",
                "content": processed_content,
            }

            # Run the evaluation
            self.logger.info(
                f"Evaluating article: {getattr(article, 'url', 'unknown')}"
            )

            # Use asyncio to run the chain (LangChain chains are sync by default)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self.chain.run, chain_input)

            processing_time = time.time() - start_time

            # Convert to ContentCompletenessEvaluation
            evaluation = ContentCompletenessEvaluation(
                article_id=(
                    str(getattr(article, "id", None))
                    if getattr(article, "id", None) is not None
                    else None
                ),
                url=getattr(article, "url", "No URL available"),
                is_complete=result.is_complete,
                detected_issues=result.detected_issues,
                evaluation_status=EvaluationStatus.COMPLETED,
                llm_model_used=str(self.llm),
                processing_time_seconds=processing_time,
            )

            self.logger.info(
                f"Evaluation completed: {getattr(article, 'url', 'unknown')} -> "
                f"{'Complete' if result.is_complete else 'Incomplete'} "
                f"(issues: {result.detected_issues})"
            )

            return evaluation

        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(
                f"Evaluation failed for article {getattr(article, 'url', 'unknown')}: {e}"
            )

            error_evaluation = self._create_error_evaluation(article, str(e))
            error_evaluation.processing_time_seconds = processing_time
            return error_evaluation

    async def evaluate_articles(
        self, articles: List[Any], **kwargs
    ) -> List[ContentCompletenessEvaluation]:
        """Evaluate multiple articles for content completeness.

        Args:
            articles: List of article objects to evaluate.
            **kwargs: Additional arguments for evaluation.

        Returns:
            List[ContentCompletenessEvaluation]: List of evaluation results.
        """
        self.logger.info(f"Starting batch evaluation of {len(articles)} articles")

        # Evaluate articles concurrently
        tasks = [self.evaluate_article(article, **kwargs) for article in articles]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions that occurred during evaluation
        evaluations = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Article {i} evaluation failed: {result}")
                error_eval = self._create_error_evaluation(
                    articles[i], f"Evaluation failed: {result}"
                )
                evaluations.append(error_eval)
            else:
                evaluations.append(result)

        self.logger.info(f"Batch evaluation completed: {len(evaluations)} results")
        return evaluations

    def _process_content_for_evaluation(self, content: str) -> str:
        """Process content for evaluation with smart truncation.

        Args:
            content: Raw content to process.

        Returns:
            str: Processed content ready for evaluation.
        """
        content = content.strip()

        # If content is within limit, return as is
        if len(content) <= MAX_CONTENT_LENGTH:
            return content

        # Smart truncation: keep beginning and end, add separator
        beginning = content[:1000]
        end = content[-7000:]

        return f"{beginning}...\n\n[...]\n\n...{end}"
