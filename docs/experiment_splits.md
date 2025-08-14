# Experiment Split Functionality

The experiment runner now supports specifying dataset splits for evaluation, allowing you to run experiments on specific subsets of your data.

## Overview

When running experiments, you can now specify which dataset splits to use for evaluation by adding a `split` field to your experiment configuration. This enables more targeted evaluation and better control over your experimental data.

## Configuration

### Basic Usage

Add a `split` field to your experiment configuration:

```yaml
name: my_experiment
description: "Experiment with specific dataset splits"
target_dataset: "my_dataset"

# Specify which splits to use
split: ["test", "training"]

# ... rest of your experiment configuration
```

### Split Field Options

The `split` field accepts several formats:

1. **Single split**: Use only one dataset split
   ```yaml
   split: "test"
   ```

2. **Multiple splits**: Use multiple dataset splits
   ```yaml
   split: ["test", "training", "validation"]
   ```

3. **No splits**: Use the entire dataset (default behavior)
   ```yaml
   split: null  # or omit the field entirely
   ```

## How It Works

When you specify splits in your experiment configuration:

1. The experiment runner uses `client.list_examples()` to fetch examples from the specified splits
2. The examples are passed directly to LangSmith's `aevaluate()` function
3. This ensures evaluation only runs on the data from your specified splits

## Example Configuration

Here's a complete example showing how to use splits:

```yaml
name: example_experiment
description: "Example experiment with split specification"
target_dataset: "ExampleTask_llm_keywords_20250814_145420"

# Use both test and training splits
split: ["test", "training"]

task:
  name: "ExampleTask"
  steps:
    - name: prompt_template
      runnable: PromptTemplate
      config:
        template: "Extract keywords from the following text: {text_content}"
        input_variables: ["text_content"]

    - name: llm_processor
      runnable: ChatOpenAI
      config:
        model: "gpt-3.5-turbo"
        temperature: 0.0
        max_tokens: 4000

evaluators:
  - name: criteria_accuracy
    type: "criteria"
    description: "Evaluate if the LLM output is accurate"
    config:
      criteria: ["accuracy"]
      threshold: 0.8
      model: "gpt-4o-mini"
      temperature: 0.0

metadata:
  category: "example"
  tags:
    - "example_experiment"
```

## Backward Compatibility

- If no `split` field is specified, the experiment runner will use the entire dataset (existing behavior)
- This ensures that existing experiment configurations continue to work without modification

## Use Cases

- **Model validation**: Run experiments only on test data to avoid data leakage
- **Split-specific analysis**: Compare model performance across different data splits
- **Resource optimization**: Use smaller splits for faster experimentation
- **Production validation**: Test on specific splits before full deployment

## Technical Details

The split functionality is implemented in the `ExperimentRunner._load_existing_dataset()` method, which:

1. Checks if splits are specified in the configuration
2. If splits are specified, calls `client.list_examples()` with the split parameters
3. Returns the filtered examples for evaluation
4. If no splits are specified, returns the dataset name for backward compatibility

This approach ensures that LangSmith's `aevaluate()` function receives exactly the data you want to evaluate, giving you precise control over your experimental setup.
