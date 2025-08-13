# Custom Runnables

This directory contains custom runnable classes that will be automatically discovered and registered by the `RunnableRegistry`.

## How It Works

1. **Auto-Discovery**: The registry automatically scans this directory for Python files
2. **Class Detection**: Classes that inherit from `Runnable` are automatically registered
3. **Instant Registration**: No manual registration needed - just add your runnable classes here

## Runnable Class Requirements

Your custom runnable classes must:

1. **Inherit from `Runnable`**: `from langchain_core.runnables import Runnable`
2. **Implement `invoke` method**: Handle the core logic
3. **Be in this directory**: Placed in any `.py` file

## Basic Example

```python
from langchain_core.runnables import Runnable
from typing import Any, Dict

class MyCustomRunnable(Runnable):
    """My custom runnable for processing text."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
    
    def invoke(self, input_data: Any, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process the input data.
        
        Args:
            input_data: Input data to process
            config: Runtime configuration
            
        Returns:
            Dictionary containing processed results
        """
        # Your processing logic here
        result = f"Processed: {input_data}"
        
        return {
            "result": result,
            "input": input_data,
            "runnable_name": "MyCustomRunnable"
        }
```

## Advanced Example with Schemas

```python
from langchain_core.runnables import Runnable
from pydantic import BaseModel
from typing import Any, Dict

class MyAdvancedRunnable(Runnable):
    """Advanced runnable with input/output schemas."""
    
    def __init__(self, model_name: str = "default"):
        self.model_name = model_name
    
    def invoke(self, input_data: Any, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process input with advanced logic."""
        # Your advanced processing here
        return {"result": f"Advanced processing of {input_data}"}
    
    def get_input_schema(self):
        """Define expected input format."""
        class InputSchema(BaseModel):
            text: str = "Text to process"
            options: Dict[str, Any] = "Processing options"
        return InputSchema
    
    def get_output_schema(self):
        """Define output format."""
        class OutputSchema(BaseModel):
            result: str = "Processing result"
            metadata: Dict[str, Any] = "Additional metadata"
        return OutputSchema
```

## Usage in YAML Configuration

```yaml
task:
  steps:
    - name: custom_processing
      runnable: MyCustomRunnable  # Automatically discovered!
      config:
        custom_param: "value"
      dataset: true
```

## File Organization

- **Single Class per File**: `my_runnable.py` → `MyRunnable` class
- **Multiple Classes**: `text_processors.py` → Multiple related classes
- **Descriptive Names**: Use clear, descriptive file names
- **Ignore Files**: Files starting with `_` or `__` are ignored

## Best Practices

1. **Clear Inheritance**: Always inherit from `Runnable`
2. **Proper Naming**: Use descriptive class names
3. **Documentation**: Include comprehensive docstrings
4. **Error Handling**: Handle errors gracefully
5. **Type Hints**: Use proper type annotations
6. **Testing**: Test your runnables independently

## Available Features

Your runnables automatically get:
- **Registry Integration**: Available in task configurations
- **Configuration Support**: Accept config dictionaries
- **Error Handling**: Built-in error management
- **Logging**: Automatic logging integration
- **LCEL Compatibility**: Can be used in LangChain chains

## Testing Your Runnables

```python
# Test your runnable
runnable = MyCustomRunnable({"param": "value"})
result = runnable.invoke("test input")
print(result)
```
