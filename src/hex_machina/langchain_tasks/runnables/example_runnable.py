"""
Example custom runnable for demonstration.

This runnable shows how to create custom runnable classes that will be
automatically discovered and registered by the RunnableRegistry.
"""

from typing import Any, Dict, List
from langchain_core.runnables import Runnable


class ExampleCustomRunnable(Runnable):
    """
    Example custom runnable for demonstration.
    
    This runnable shows how to create custom runnable classes that will be
    automatically discovered and registered by the RunnableRegistry.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the custom runnable.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.name = self.config.get("name", "ExampleCustomRunnable")
        self.description = self.config.get("description", "An example custom runnable")
    
    def invoke(self, input_data: Any, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process the input data.
        
        Args:
            input_data: Input data to process
            config: Runtime configuration
            
        Returns:
            Dictionary containing processed results
        """
        # Simple example processing
        if isinstance(input_data, str):
            processed_text = f"Processed: {input_data.upper()}"
            word_count = len(input_data.split())
        else:
            processed_text = f"Processed: {str(input_data)}"
            word_count = 0
        
        return {
            "result": processed_text,
            "input_type": type(input_data).__name__,
            "word_count": word_count,
            "runnable_name": self.name,
            "config": self.config,
        }
    
    def get_input_schema(self):
        """Get the input schema for this runnable."""
        from pydantic import BaseModel
        
        class InputSchema(BaseModel):
            text: str = "Input text to process"
            
        return InputSchema
    
    def get_output_schema(self):
        """Get the output schema for this runnable."""
        from pydantic import BaseModel
        
        class OutputSchema(BaseModel):
            result: str = "Processed result"
            input_type: str = "Type of input data"
            word_count: int = "Number of words in input"
            runnable_name: str = "Name of the runnable"
            config: Dict[str, Any] = "Configuration used"
            
        return OutputSchema


class AnotherCustomRunnable(Runnable):
    """
    Another example custom runnable.
    
    This demonstrates that multiple runnables can be defined in the same file.
    """
    
    def __init__(self, multiplier: float = 2.0):
        """Initialize with a multiplier.
        
        Args:
            multiplier: Value to multiply numeric inputs by
        """
        self.multiplier = multiplier
    
    def invoke(self, input_data: Any, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Multiply numeric inputs by the configured multiplier.
        
        Args:
            input_data: Input data (should be numeric)
            config: Runtime configuration
            
        Returns:
            Dictionary containing multiplication results
        """
        try:
            # Convert input to float and multiply
            numeric_input = float(input_data)
            result = numeric_input * self.multiplier
            
            return {
                "result": result,
                "input_value": numeric_input,
                "multiplier": self.multiplier,
                "operation": "multiplication",
                "runnable_name": "AnotherCustomRunnable",
            }
        except (ValueError, TypeError):
            return {
                "result": None,
                "error": f"Input '{input_data}' cannot be converted to a number",
                "input_value": input_data,
                "multiplier": self.multiplier,
                "runnable_name": "AnotherCustomRunnable",
            }
