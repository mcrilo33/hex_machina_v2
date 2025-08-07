# Iterative Dataset Building Workflow

This module implements a sophisticated workflow for building high-quality evaluation datasets through iterative refinement of prompts and models, perfectly aligned with LangSmith's capabilities.

## 🎯 Overview

The iterative dataset building workflow addresses the challenge of creating reliable ground truth datasets for content completeness evaluation. It implements your proposed procedure with enhanced LangSmith integration:

1. **Evaluate large dataset** (`dataset_1`) with current prompt/model
2. **Extract positive examples** and add to curated dataset (`testset_1`)
3. **Manually validate** positive examples in LangSmith
4. **Iterate prompts/models** and repeat evaluation
5. **Monitor convergence** until `testset_1` is stable
6. **Final evaluation** on the stable, high-quality dataset

## 🏗️ Architecture

```
workflows/
├── iterative_dataset_building.py    # Main workflow implementation
├── README.md                        # This documentation
└── test_iterative_dataset_building.py  # Test script
```

## 🚀 Quick Start

### 1. Basic Usage

```python
import asyncio
from langchain_openai import ChatOpenAI
from src.hex_machina.enrichment.evaluation.langsmith.workflows.iterative_dataset_building import (
    run_iterative_dataset_building,
)

# Setup LLM
llm = ChatOpenAI(
    model="openai/gpt-3.5-turbo",
    temperature=0,
    openai_api_base="https://openrouter.ai/api/v1",
    openai_api_key=os.getenv("OPENROUTER_API_KEY"),
)

# Run workflow
results = await run_iterative_dataset_building(
    source_dataset_name="dataset_1",
    target_dataset_name="testset_1",
    llm=llm,
    prompt_version="v1.0",
    max_iterations=10,
    stability_threshold=0.95,
)
```

### 2. Test the Workflow

```bash
# Run the test script
poetry run python test_iterative_dataset_building.py
```

## 📊 Workflow Steps

### **Phase 1: Initial Evaluation**
```python
# Evaluate source dataset with current prompt
iteration_results = await evaluator.evaluate_articles(source_articles)
positive_examples = extract_positive_examples(iteration_results)
```

### **Phase 2: Positive Example Extraction**
```python
# Add positive examples to target dataset
for example in positive_examples:
    target_dataset.add_example(
        inputs=example.inputs,
        outputs={"is_complete": True, "manual_review_required": True},
        metadata={"added_in_iteration": iteration}
    )
```

### **Phase 3: Stability Check**
```python
# Monitor convergence
stability_score = calculate_stability_score(iteration_history)
if stability_score >= threshold:
    dataset_stable = True
```

### **Phase 4: Manual Validation**
- Review positive examples in LangSmith dashboard
- Add corrections and feedback
- Validate ground truth quality

### **Phase 5: Prompt/Model Iteration**
```python
# Test new prompt version
results_v2 = await run_iterative_dataset_building(
    source_dataset_name="dataset_1",
    target_dataset_name="testset_1_v2",
    llm=llm,
    prompt_version="v1.1",
)
```

### **Phase 6: Final Evaluation**
```python
# Evaluate on stable dataset
final_results = await evaluator.evaluate_articles(testset_1_articles)
```

## 🔧 Key Features

### **1. Stability Detection**
- **Convergence Monitoring**: Tracks new positive examples per iteration
- **Stability Threshold**: Configurable threshold for considering dataset stable
- **Iteration History**: Complete history of all iterations with metadata

### **2. LangSmith Integration**
- **Dataset Management**: Automatic creation and management of source/target datasets
- **Run Tracking**: Every iteration tracked with detailed metadata
- **Ground Truth Collection**: Manual validation workflow in LangSmith dashboard
- **Performance Metrics**: Comprehensive tracking of accuracy and performance

### **3. Manual Validation Workflow**
- **Review Interface**: Use LangSmith dashboard for manual review
- **Feedback Collection**: Add corrections and comments to examples
- **Quality Assurance**: Ensure high-quality ground truth data

### **4. Prompt/Model Iteration**
- **Version Control**: Track different prompt versions
- **Comparison**: Compare results across different prompts/models
- **Performance Analysis**: Analyze improvements over iterations

## 📈 Metrics and Monitoring

### **Iteration Metrics**
```python
{
    "iteration": 1,
    "total_evaluated": 100,
    "new_positive_examples": 15,
    "stability_score": 0.85,
    "timestamp": "2024-01-15T10:30:00Z"
}
```

### **Stability Calculation**
```python
stability_score = stable_iterations / total_iterations
# Where stable_iterations = iterations with no new positives
```

### **Performance Tracking**
- **Accuracy**: Success rate on target dataset
- **Convergence**: Speed of reaching stability
- **Quality**: Manual validation results

## 🎛️ Configuration Options

### **Workflow Parameters**
```python
{
    "max_iterations": 10,           # Prevent infinite loops
    "stability_threshold": 0.95,    # Convergence threshold
    "prompt_version": "v1.0",       # Version tracking
    "model_name": "gpt-3.5-turbo",  # Model tracking
}
```

### **Dataset Configuration**
```python
{
    "source_dataset_name": "dataset_1",
    "target_dataset_name": "testset_1",
    "description": "High-quality positive examples",
    "tags": ["iterative_building", "positive_examples"]
}
```

## 🔍 LangSmith Dashboard Features

### **Dataset Management**
- **Source Dataset**: Large dataset for evaluation
- **Target Dataset**: Curated positive examples
- **Version Tracking**: Different prompt/model versions

### **Run Analysis**
- **Iteration Runs**: Each iteration tracked separately
- **Comparison**: Side-by-side comparison of different versions
- **Performance**: Accuracy and convergence metrics

### **Manual Validation**
- **Review Interface**: Easy review of positive examples
- **Feedback**: Add corrections and comments
- **Quality Control**: Ensure ground truth accuracy

## 📋 Best Practices

### **1. Dataset Preparation**
```python
# Ensure source dataset has diverse content types
source_articles = [
    complete_articles,      # Should be positive
    incomplete_articles,    # Should be negative
    borderline_cases,       # Interesting for iteration
]
```

### **2. Manual Validation**
- **Regular Reviews**: Review positive examples after each iteration
- **Quality Checks**: Ensure examples are truly positive
- **Feedback Loop**: Use feedback to improve prompts

### **3. Prompt Iteration**
```python
# Test different prompt versions systematically
prompt_versions = ["v1.0", "v1.1", "v1.2", "v2.0"]
for version in prompt_versions:
    results = await run_iterative_dataset_building(
        prompt_version=version,
        # ... other parameters
    )
```

### **4. Stability Monitoring**
- **Convergence Tracking**: Monitor when dataset becomes stable
- **Quality Assurance**: Ensure stability indicates quality, not overfitting
- **Iteration Limits**: Set reasonable max_iterations

## 🛠️ Advanced Usage

### **Custom Stability Criteria**
```python
class CustomIterativeBuilder(IterativeDatasetBuilder):
    def _check_stability(self, new_positive_examples):
        # Custom stability logic
        return custom_stability_calculation()
```

### **Multi-Model Comparison**
```python
models = ["gpt-3.5-turbo", "gpt-4", "claude-3"]
for model in models:
    llm = create_llm(model)
    results = await run_iterative_dataset_building(
        llm=llm,
        model_name=model,
        # ... other parameters
    )
```

### **Domain-Specific Workflows**
```python
# Customize for specific content domains
domain_config = {
    "tech_articles": {"stability_threshold": 0.9},
    "news_articles": {"stability_threshold": 0.85},
    "research_papers": {"stability_threshold": 0.95},
}
```

## 📊 Expected Results

### **Typical Workflow Output**
```
=== Iteration 1 ===
✅ Evaluated: 100 articles
✅ New positives: 15
📊 Stability: 0.000

=== Iteration 2 ===
✅ Evaluated: 85 articles
✅ New positives: 8
📊 Stability: 0.000

=== Iteration 3 ===
✅ Evaluated: 77 articles
✅ New positives: 3
📊 Stability: 0.000

=== Iteration 4 ===
✅ Evaluated: 74 articles
✅ New positives: 0
📊 Stability: 0.250

=== Iteration 5 ===
✅ Evaluated: 74 articles
✅ New positives: 0
📊 Stability: 0.400

🎯 Dataset stable! Final positive examples: 26
```

### **LangSmith Dashboard Results**
- **Source Dataset**: 100 examples
- **Target Dataset**: 26 high-quality positive examples
- **Iteration Runs**: 5 tracked runs with metadata
- **Manual Validation**: Ready for human review

## 🔄 Iteration Process

### **Your Original Procedure (Enhanced)**
1. ✅ **Evaluate dataset_1** with current prompt
2. ✅ **Extract positive examples** automatically
3. ✅ **Add to testset_1** with manual review flags
4. ✅ **Manual validation** in LangSmith dashboard
5. ✅ **Iterate prompts/models** systematically
6. ✅ **Monitor stability** with convergence metrics
7. ✅ **Final evaluation** on stable dataset

### **LangSmith Integration Benefits**
- **Automated Tracking**: Every step tracked in LangSmith
- **Version Control**: Prompt and model versions tracked
- **Performance Analysis**: Comprehensive metrics and comparison
- **Manual Workflow**: Seamless integration with human review
- **Quality Assurance**: Built-in validation and feedback loops

## 🎯 Conclusion

This workflow perfectly implements your proposed procedure while leveraging LangSmith's full capabilities for:

- **Automated Dataset Building**: Systematic extraction of positive examples
- **Quality Assurance**: Manual validation workflow
- **Performance Tracking**: Comprehensive metrics and analysis
- **Iteration Management**: Version control and comparison
- **Stability Monitoring**: Convergence detection and stopping criteria

The result is a high-quality, manually validated dataset that can be used for reliable evaluation of content completeness models. 