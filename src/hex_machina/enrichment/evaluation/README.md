# Content Completeness Evaluation

This module provides LLM-based evaluation of article content completeness using OpenRouter.

## Setup

### 1. Install Dependencies

```bash
poetry add langchain langchain-openai
```

### 2. Configure OpenRouter API Key

Set your OpenRouter API key as an environment variable:

```bash
export OPENROUTER_API_KEY="your_api_key_here"
```

Or add it to your `.env` file:
```
OPENROUTER_API_KEY=your_api_key_here
```

Get your API key from: https://openrouter.ai/keys

### 3. Test the System

Run the example to test the evaluation:

```bash
python src/hex_machina/enrichment/evaluation/example_usage.py
```

## Usage

### Basic Usage

```python
from src.hex_machina.enrichment.llm.config import create_evaluation_llm
from src.hex_machina.enrichment.evaluation.langchain.chains.evaluation_chains import (
    ContentCompletenessEvaluator,
)

# Create LLM with OpenRouter
llm = create_evaluation_llm("gpt-3.5-turbo")

# Create evaluator
evaluator = ContentCompletenessEvaluator(llm=llm)

# Evaluate article
result = await evaluator.evaluate_article(article)
print(f"Is Complete: {result.is_complete}")
print(f"Issues: {result.detected_issues}")
```

### Available Models

The system supports multiple models through OpenRouter:

- `gpt-3.5-turbo` (default) - Fast and cost-effective
- `gpt-4` - Higher quality, more expensive
- `claude-3-haiku` - Good balance of speed and quality
- `claude-3-sonnet` - High quality reasoning
- `gemini-pro` - Google's model
- `llama-2-70b` - Open source model
- `mistral-7b` - Fast open source model

### Model Comparison

The example includes a model comparison function that tests different models on the same content to help you choose the best one for your use case.

## Architecture

### Components

1. **Models** (`evaluation_models.py`):
   - `ContentCompletenessEvaluation`: Single evaluation result
   - `BatchCompletenessResult`: Batch processing results

2. **Evaluators** (`evaluation_chains.py`):
   - `ContentCompletenessEvaluator`: Main evaluation logic
   - `BaseEvaluator`: Abstract base class

3. **LangChain Integration**:
   - **Prompts** (`evaluation_prompts.py`): LLM instructions
   - **Output Parsers** (`evaluation_parsers.py`): Response parsing
   - **Chains** (`evaluation_chains.py`): Evaluation workflow

4. **LLM Configuration** (`llm/config.py`):
   - OpenRouter integration
   - Model management
   - API key validation

### Evaluation Process

1. **Input**: Article object with text content
2. **Processing**: Smart content truncation if needed
3. **LLM Evaluation**: Send to OpenRouter with structured prompt
4. **Parsing**: Extract `is_complete` and `detected_issues`
5. **Output**: Structured evaluation result

### Detected Issues

The system can identify these issues:

- `anti_bot_page`: CAPTCHA, JavaScript requirements, access denied
- `subscription_wall`: Paywall, premium content, subscription required
- `truncated_content`: Abrupt ending, "read more" prompts
- `error_page`: 404, maintenance, server errors
- `empty_or_placeholder`: Minimal content, placeholders
- `extraneous_content`: Article surrounded by unrelated content
- `no_issues`: No problems detected

## Configuration

### Content Length Limits

The system automatically handles long content:

- **Max Length**: 8000 characters (configurable via `MAX_CONTENT_LENGTH`)
- **Smart Truncation**: Keeps beginning (1000 chars) + end (7000 chars)
- **Clear Indicators**: Shows when content is truncated

### Model Selection

Choose models based on your needs:

- **Speed**: `gpt-3.5-turbo`, `claude-3-haiku`, `mistral-7b`
- **Quality**: `gpt-4`, `claude-3-sonnet`, `claude-3-opus`
- **Cost**: `gpt-3.5-turbo`, `claude-3-haiku`, `gemini-pro`

## Integration

### With Existing Pipeline

```python
# After scraping articles
evaluator = ContentCompletenessEvaluator(llm=create_evaluation_llm())

for article in scraped_articles:
    evaluation = await evaluator.evaluate_article(article)
    
    if evaluation.is_complete:
        # Process complete article
        process_article(article)
    else:
        # Handle incomplete article
        handle_incomplete_article(article, evaluation.detected_issues)
```

### Batch Processing

```python
# Evaluate multiple articles concurrently
results = await evaluator.evaluate_articles(articles)

# Filter complete articles
complete_articles = [article for article, result in zip(articles, results) if result.is_complete]
```

## Next Steps

1. **Test with Real Data**: Use your existing article pipeline
2. **Add to Database**: Store evaluation results
3. **Create Workflows**: Integrate with Prefect3
4. **Monitor Performance**: Add LangSmith tracking
5. **Optimize Costs**: Compare models and choose best fit 