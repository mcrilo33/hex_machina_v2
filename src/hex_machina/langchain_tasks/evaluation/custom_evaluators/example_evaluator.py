"""
Example custom evaluator for demonstration.

This evaluator shows how to create custom evaluation functions that will be
automatically discovered and registered by the EvaluatorRegistry.
"""

from typing import Dict, Any


def example_custom_evaluator(run: Any, example: Any) -> Dict[str, Any]:
    """
    Example custom evaluator function.
    
    This function will be automatically discovered and registered because it:
    1. Takes 'run' and 'example' parameters
    2. Is in the custom_evaluators package
    3. Returns a dictionary with evaluation results
    
    Args:
        run: The run object from LangSmith
        example: The example object from LangSmith
        
    Returns:
        Dictionary containing evaluation results
    """
    # Extract output from the run
    output = run.outputs.get("result", "") if hasattr(run, 'outputs') else ""
    
    # Simple example evaluation logic
    if isinstance(output, str):
        # Score based on output length
        length = len(output)
        if length < 50:
            score = 0.3
            reasoning = "Output is too short"
        elif length < 100:
            score = 0.6
            reasoning = "Output is moderately sized"
        else:
            score = 0.9
            reasoning = "Output has good length"
    else:
        score = 0.5
        reasoning = "Non-string output, default score"
    
    return {
        "score": score,
        "reasoning": reasoning,
        "criterion": "example_custom",
        "evaluator_name": "example_custom_evaluator",
        "output_length": len(str(output)) if output else 0,
    }


def another_custom_evaluator(run: Any, example: Any) -> Dict[str, Any]:
    """
    Another example custom evaluator.
    
    This demonstrates that multiple evaluators can be defined in the same file.
    """
    # Extract input and output
    input_data = run.inputs.get("text", "") if hasattr(run, 'inputs') else ""
    output = run.outputs.get("result", "") if hasattr(run, 'outputs') else ""
    
    # Simple relevance check
    if isinstance(input_data, str) and isinstance(output, str):
        # Check if output contains words from input
        input_words = set(input_data.lower().split())
        output_words = set(output.lower().split())
        
        if input_words and output_words:
            overlap = len(input_words.intersection(output_words))
            relevance_score = min(1.0, overlap / len(input_words))
        else:
            relevance_score = 0.0
    else:
        relevance_score = 0.5
    
    return {
        "score": relevance_score,
        "reasoning": f"Relevance score based on word overlap between input and output",
        "criterion": "relevance",
        "evaluator_name": "another_custom_evaluator",
        "input_word_count": len(input_data.split()) if isinstance(input_data, str) else 0,
        "output_word_count": len(output.split()) if isinstance(output, str) else 0,
    }
