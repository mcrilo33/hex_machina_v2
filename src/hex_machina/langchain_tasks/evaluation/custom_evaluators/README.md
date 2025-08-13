# Custom Evaluators

This directory contains custom evaluation functions that will be automatically discovered and registered by the `EvaluatorRegistry`.

## How It Works

1. **Auto-Discovery**: The registry automatically scans this directory for Python files
2. **Function Detection**: Functions with the signature `(run, example)` are automatically registered
3. **Instant Registration**: No manual registration needed - just add your evaluator functions here

## Evaluator Function Requirements

Your custom evaluator functions must have this signature:

```python
def your_evaluator_name(run: Any, example: Any) -> Dict[str, Any]:
    """
    Your custom evaluator function.
    
    Args:
        run: The run object from LangSmith containing execution results
        example: The example object from LangSmith containing input data
        
    Returns:
        Dictionary with evaluation results including:
        - score: float (0.0 to 1.0)
        - reasoning: str (explanation of the score)
        - criterion: str (what is being evaluated)
        - evaluator_name: str (name of this evaluator)
        - Any additional metrics you want to track
    """
    # Your evaluation logic here
    return {
        "score": 0.8,
        "reasoning": "Output meets quality criteria",
        "criterion": "quality",
        "evaluator_name": "your_evaluator_name",
        "custom_metric": "additional data"
    }
```

## Example Usage

```python
# In your YAML configuration
evaluations:
  task:
    evaluators:
      - name: your_evaluator_name
        type: "custom_function"
        description: "Your custom evaluation logic"
```

## File Naming

- Use descriptive names: `quality_evaluator.py`, `relevance_checker.py`
- Multiple evaluators can be in the same file
- Files starting with `_` or `__` are ignored

## Best Practices

1. **Clear Naming**: Use descriptive function names
2. **Documentation**: Include detailed docstrings
3. **Error Handling**: Handle edge cases gracefully
4. **Consistent Output**: Always return the same structure
5. **Testing**: Test your evaluators independently

## Available Context

The `run` object provides access to:
- `run.outputs`: Results from the task execution
- `run.inputs`: Input data passed to the task
- `run.metadata`: Additional execution metadata

The `example` object provides access to:
- `example.inputs`: Expected input format
- `example.outputs`: Expected output format
- `example.metadata`: Example-specific metadata
