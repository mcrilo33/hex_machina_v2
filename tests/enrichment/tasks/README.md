# Enrichment Tasks Tests

This directory contains comprehensive tests for the enrichment tasks functionality in Hex Machina v2.

## Test Structure

### Test Files

- **`test_cli_tasks.py`** - Tests for CLI commands related to tasks
  - Command-line interface validation
  - Input/output handling
  - Error handling and edge cases
  - Results saving and formatting

- **`test_task_runner.py`** - Tests for the task runner functionality
  - Task execution workflows
  - Batch processing
  - Article source resolution
  - Database integration
  - Error handling and recovery

- **`test_task_registry.py`** - Tests for task registry functionality
  - Task registration and discovery
  - Task creation and instantiation
  - Task information retrieval
  - Registry isolation

- **`test_article_source.py`** - Tests for article source resolution
  - Single and multiple article resolution
  - Dataset and ingestion operation handling
  - Input file processing
  - Source validation

- **`test_langchain_task.py`** - Tests for LangChain task base class
  - LLM initialization (OpenRouter, OpenAI)
  - Prompt template handling
  - Output parser integration
  - Chain building and execution
  - Configuration management

- **`test_content_completeness_task.py`** - Tests for specific task implementation
  - Input validation
  - Task-specific functionality
  - Error handling
  - Output format validation

- **`test_integration.py`** - Integration tests for complete workflows
  - End-to-end task execution
  - Batch processing workflows
  - Concurrent execution
  - Error recovery scenarios
  - Database save workflows

- **`test_conftest.py`** - Pytest configuration and fixtures
  - Common test fixtures
  - Mock objects and utilities
  - Test data generators

## Test Categories

### Unit Tests
- Individual component testing
- Mock dependencies
- Focus on specific functionality
- Fast execution

### Integration Tests  
- Full workflow testing
- Real component interactions
- End-to-end scenarios
- More comprehensive but slower

### CLI Tests
- Command-line interface testing
- Input validation
- Output formatting
- Error scenarios

## Running Tests

### Run All Task Tests
```bash
# From project root
python -m pytest tests/enrichment/tasks/ -v
```

### Run Specific Test Files
```bash
# CLI tests only
python -m pytest tests/enrichment/tasks/test_cli_tasks.py -v

# Integration tests only  
python -m pytest tests/enrichment/tasks/test_integration.py -v

# Task runner tests only
python -m pytest tests/enrichment/tasks/test_task_runner.py -v
```

### Run Specific Test Classes or Methods
```bash
# Specific test class
python -m pytest tests/enrichment/tasks/test_task_runner.py::TestTaskRunner -v

# Specific test method
python -m pytest tests/enrichment/tasks/test_cli_tasks.py::TestTasksCLI::test_run_command_single_article -v
```

### Run with Coverage
```bash
python -m pytest tests/enrichment/tasks/ --cov=src.hex_machina.enrichment.tasks --cov-report=html
```

### Run Tests in Parallel
```bash
python -m pytest tests/enrichment/tasks/ -n auto
```

## Test Configuration

### Fixtures
The tests use pytest fixtures defined in `test_conftest.py` for:
- Mock configurations
- Sample data objects
- Common test utilities
- Environment setup

### Mocking Strategy
- External dependencies (APIs, databases) are mocked
- File system operations use temporary files
- LLM calls are mocked to avoid API costs
- Database operations use mock sessions

### Async Testing
Async tests are marked with `@pytest.mark.asyncio` and test:
- Task execution workflows
- Concurrent processing
- Error handling in async contexts

## Key Test Scenarios

### CLI Functionality
- ✅ Command validation and parsing
- ✅ Source option validation
- ✅ Dry run functionality
- ✅ Batch processing configuration
- ✅ Results saving and formatting
- ✅ Error handling and reporting

### Task Execution
- ✅ Single task execution
- ✅ Batch processing with concurrency
- ✅ Error handling and recovery
- ✅ Skip existing functionality
- ✅ Database save operations
- ✅ Input validation

### Article Source Resolution
- ✅ Single article lookup
- ✅ Multiple article resolution
- ✅ Dataset and operation filtering
- ✅ Input file processing
- ✅ Source validation

### LangChain Integration
- ✅ LLM provider initialization
- ✅ Prompt template handling
- ✅ Output parser integration
- ✅ Chain building and execution
- ✅ Configuration management

### Task Registry
- ✅ Task registration and discovery
- ✅ Task creation and instantiation
- ✅ Registry isolation
- ✅ Error handling

## Test Data

### Sample Articles
Tests use consistent sample ArticleDB objects with:
- Realistic titles and content
- Various domains and URLs
- Different ingestion operations
- Metadata variations

### Mock Configurations
LangChain configurations for:
- OpenRouter provider
- OpenAI provider
- Various model configurations
- Template and parser settings

### Test Inputs
Standardized task inputs covering:
- Valid content scenarios
- Edge cases (empty, malformed)
- Unicode and special characters
- Large content handling

## Debugging Tests

### Verbose Output
```bash
python -m pytest tests/enrichment/tasks/ -v -s
```

### Stop on First Failure
```bash
python -m pytest tests/enrichment/tasks/ -x
```

### Debug Specific Test
```bash
python -m pytest tests/enrichment/tasks/test_task_runner.py::TestTaskRunner::test_run_task_success -v -s --pdb
```

### Show Log Output
```bash
python -m pytest tests/enrichment/tasks/ -v --log-cli-level=DEBUG
```

## Contributing

When adding new tests:

1. **Follow naming conventions**: `test_*.py` for files, `test_*` for functions
2. **Use appropriate fixtures**: Leverage existing fixtures from `test_conftest.py`
3. **Mock external dependencies**: Don't make real API calls or database connections
4. **Test both success and failure cases**: Include error scenarios
5. **Add docstrings**: Explain what each test validates
6. **Group related tests**: Use test classes to organize related functionality
7. **Keep tests focused**: Each test should validate one specific behavior

### Test Checklist

For new functionality, ensure tests cover:
- ✅ Happy path scenarios
- ✅ Edge cases and boundary conditions
- ✅ Error handling and recovery
- ✅ Input validation
- ✅ Configuration variations
- ✅ Integration with existing components