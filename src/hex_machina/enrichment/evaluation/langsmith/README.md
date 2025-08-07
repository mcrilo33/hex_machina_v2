# LangSmith Integration for Content Completeness Evaluation

This module provides comprehensive LangSmith integration for tracking, evaluating, and iterating on content completeness evaluation models and prompts.

## 🎯 Overview

LangSmith integration enables you to:

- **Track Evaluation Runs**: Monitor every evaluation with detailed metadata
- **Compare Models**: Test different LLM models on the same content
- **Build Ground Truth**: Collect manual corrections to create training datasets
- **Iterate Prompts**: Version control and compare different prompt strategies
- **Analyze Performance**: Get insights into model accuracy and performance

## 🏗️ Architecture

```
langsmith/
├── config.py                    # LangSmith configuration and environment setup
├── tracers/
│   └── evaluation_tracer.py     # Custom tracer for evaluation runs
├── datasets/
│   └── dataset_manager.py       # Dataset creation and management
└── README.md                    # This file
```

## 🚀 Quick Start

### 1. Setup Environment

Add your LangSmith API key to `.env`:

```bash
LANGSMITH_API_KEY="your_langsmith_api_key_here"
```

### 2. Basic Usage

```python
import asyncio
from src.hex_machina.enrichment.evaluation.langsmith import (
    setup_langsmith_environment,
    EvaluationTracer,
    TracedContentCompletenessEvaluator,
    EvaluationDatasetManager
)

# Setup LangSmith
setup_langsmith_environment()

# Create tracer and evaluator
tracer = EvaluationTracer()
base_evaluator = ContentCompletenessEvaluator(llm=llm)
traced_evaluator = TracedContentCompletenessEvaluator(base_evaluator, tracer)

# Start evaluation run
tracer.start_evaluation_run(
    run_name="my-evaluation-run",
    model_name="openai/gpt-3.5-turbo",
    prompt_version="v1.0"
)

# Evaluate articles
results = await traced_evaluator.evaluate_articles(articles)
```

### 3. Dataset Management

```python
# Create dataset manager
dataset_manager = EvaluationDatasetManager()

# Create test dataset with ground truth
dataset = dataset_manager.create_test_dataset_from_articles(
    articles=test_articles,
    ground_truth_data=ground_truth_data
)

# Run evaluation on dataset
results = await dataset_manager.run_evaluation_on_dataset(
    dataset=dataset,
    evaluator=traced_evaluator
)
```

## 📊 Key Features

### 1. Evaluation Tracking

Every evaluation is tracked with:
- **Article metadata**: URL, title, content length
- **Evaluation results**: Completeness status, detected issues
- **Performance metrics**: Processing time, success rate
- **Model information**: Model name, prompt version
- **Run metadata**: Timestamps, batch information

### 2. Dataset Management

Create and manage evaluation datasets:
- **Test datasets**: For model comparison and validation
- **Ground truth datasets**: With manual annotations
- **Version control**: Track dataset changes over time
- **Metadata tracking**: Rich article and evaluation metadata

### 3. Model Comparison

Compare different models systematically:
- **Same content**: Test multiple models on identical articles
- **Performance metrics**: Speed, accuracy, consistency
- **Cost analysis**: Track API costs per model
- **A/B testing**: Structured comparison workflows

### 4. Ground Truth Collection

Build training datasets:
- **Manual annotation**: Correct model predictions
- **Feedback collection**: Gather expert evaluations
- **Dataset building**: Create labeled training data
- **Quality metrics**: Measure model accuracy

## 🔧 Configuration

### Environment Variables

```bash
# Required
LANGSMITH_API_KEY="your_api_key"

# Optional
LANGSMITH_ENDPOINT="https://api.smith.langchain.com"
LANGCHAIN_PROJECT="hex-machina-content-evaluation"
```

### Project Settings

```python
from src.hex_machina.enrichment.evaluation.langsmith.config import LangSmithConfig

# Custom project name
project_name = LangSmithConfig.get_project_name("my-custom-project")

# Custom dataset name
dataset_name = LangSmithConfig.get_dataset_name("my-test-dataset")
```

## 📈 Workflow Examples

### 1. Model Comparison Workflow

```python
async def compare_models(articles, models):
    """Compare multiple models on the same articles."""
    
    results = {}
    
    for model in models:
        # Create evaluator for this model
        llm = create_openrouter_llm(model)
        evaluator = ContentCompletenessEvaluator(llm=llm)
        
        # Setup tracing
        tracer = EvaluationTracer()
        traced_evaluator = TracedContentCompletenessEvaluator(evaluator, tracer)
        
        # Start run
        run_name = f"model-comparison-{model}"
        tracer.start_evaluation_run(run_name, model, "v1.0")
        
        # Evaluate
        model_results = await traced_evaluator.evaluate_articles(articles)
        results[model] = model_results
    
    return results
```

### 2. Ground Truth Collection Workflow

```python
async def collect_ground_truth(articles):
    """Collect ground truth data for articles."""
    
    # Create dataset
    dataset_manager = EvaluationDatasetManager()
    dataset = dataset_manager.create_evaluation_dataset("ground-truth-collection")
    
    # Add articles without ground truth
    for article in articles:
        dataset_manager.add_article_to_dataset(dataset, article)
    
    # Run initial evaluation
    llm = create_openrouter_llm("openai/gpt-3.5-turbo")
    evaluator = ContentCompletenessEvaluator(llm=llm)
    tracer = EvaluationTracer()
    traced_evaluator = TracedContentCompletenessEvaluator(evaluator, tracer)
    
    results = await traced_evaluator.evaluate_articles(articles)
    
    # Now manually review and correct in LangSmith dashboard
    print(f"Review results at: https://smith.langchain.com/")
    print(f"Dataset: {dataset.name}")
    
    return dataset, results
```

### 3. Prompt Iteration Workflow

```python
async def iterate_prompts(articles, prompt_versions):
    """Test different prompt versions."""
    
    results = {}
    
    for version in prompt_versions:
        # Create evaluator with this prompt version
        evaluator = ContentCompletenessEvaluator(
            llm=llm,
            prompt_version=version
        )
        
        # Setup tracing
        tracer = EvaluationTracer()
        traced_evaluator = TracedContentCompletenessEvaluator(evaluator, tracer)
        
        # Start run
        run_name = f"prompt-iteration-{version}"
        tracer.start_evaluation_run(run_name, "openai/gpt-3.5-turbo", version)
        
        # Evaluate
        version_results = await traced_evaluator.evaluate_articles(articles)
        results[version] = version_results
    
    return results
```

## 📊 LangSmith Dashboard

After running evaluations, view results at: https://smith.langchain.com/

### Key Dashboard Sections:

1. **Projects**: View your evaluation project
2. **Runs**: See individual evaluation runs
3. **Datasets**: Manage your test datasets
4. **Examples**: Review individual article evaluations
5. **Feedback**: Add manual corrections and feedback

### Useful Dashboard Features:

- **Run Comparison**: Compare different models/prompts side-by-side
- **Performance Metrics**: View accuracy, speed, and cost metrics
- **Ground Truth**: Add manual corrections to build training data
- **Export**: Download results for further analysis
- **Sharing**: Share results with team members

## 🔍 Best Practices

### 1. Run Naming

Use descriptive run names:
```python
# Good
run_name = "gpt-4-vs-claude-comparison-2024-01-15"

# Bad
run_name = "test-1"
```

### 2. Metadata

Include rich metadata for analysis:
```python
metadata = {
    "test_type": "model_comparison",
    "dataset_name": "content-completeness-benchmark",
    "ground_truth_available": True,
    "content_domains": ["tech", "news", "blog"],
    "evaluation_criteria": ["completeness", "accuracy"]
}
```

### 3. Dataset Organization

Organize datasets by purpose:
```python
# Test datasets
"content-completeness-test-set-v1"
"model-comparison-benchmark-2024"

# Ground truth datasets
"ground-truth-collection-phase-1"
"expert-annotated-benchmark"
```

### 4. Regular Evaluation

Set up regular evaluation cycles:
```python
# Weekly model evaluation
async def weekly_evaluation():
    # Get latest articles
    articles = await get_recent_articles()
    
    # Run evaluation
    results = await run_evaluation(articles)
    
    # Compare with previous week
    await compare_with_previous_week(results)
```

## 🛠️ Troubleshooting

### Common Issues:

1. **API Key Not Found**
   ```bash
   # Check environment variable
   echo $LANGSMITH_API_KEY
   
   # Or check .env file
   cat .env | grep LANGSMITH
   ```

2. **Connection Issues**
   ```python
   # Verify LangSmith setup
   from src.hex_machina.enrichment.evaluation.langsmith.config import LangSmithConfig
   print(LangSmithConfig.validate_config())
   ```

3. **Missing Dependencies**
   ```bash
   poetry add langsmith
   ```

### Debug Mode:

Enable debug logging for detailed information:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📚 Next Steps

1. **Get LangSmith API Key**: Sign up at https://smith.langchain.com/
2. **Run Test Script**: Execute `test_langsmith_integration.py`
3. **Create First Dataset**: Build a test dataset with your articles
4. **Collect Ground Truth**: Manually review and correct evaluations
5. **Compare Models**: Test different models on your content
6. **Iterate Prompts**: Improve prompts based on results

## 🤝 Contributing

When adding new features:

1. **Add Tracing**: Ensure new evaluators use the tracer
2. **Rich Metadata**: Include detailed metadata for analysis
3. **Documentation**: Update this README with new features
4. **Testing**: Add tests for new functionality

---

For more information, visit the [LangSmith Documentation](https://docs.smith.langchain.com/). 