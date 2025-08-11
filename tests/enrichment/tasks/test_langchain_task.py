"""Tests for LangChain task base class functionality."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from src.hex_machina.core.base import TaskInput, TaskOutput
from src.hex_machina.enrichment.tasks.base.langchain_task import (
    LangChainTask,
    LangChainTaskConfig,
)
from src.hex_machina.core import TaskException


class TestLangChainTaskConfig:
    """Test LangChain task configuration."""

    def test_config_creation_with_required_fields(self):
        """Test creating config with required fields."""
        config = LangChainTaskConfig(
            llm_provider="openrouter",
            llm_model="anthropic/claude-3-haiku",
            prompt_template="Test template",
        )

        assert config.llm_provider == "openrouter"
        assert config.llm_model == "anthropic/claude-3-haiku"
        assert config.prompt_template == "Test template"
        assert config.temperature == 0.0
        assert config.max_tokens is None
        assert config.timeout == 30

    def test_config_creation_with_optional_fields(self):
        """Test creating config with optional fields."""
        config = LangChainTaskConfig(
            llm_provider="openai",
            llm_model="gpt-4",
            prompt_template="Test template",
            temperature=0.7,
            max_tokens=1000,
            timeout=60,
            output_parser="TestParser",
            prompt_variables={"var1": "value1"},
        )

        assert config.temperature == 0.7
        assert config.max_tokens == 1000
        assert config.timeout == 60
        assert config.output_parser == "TestParser"
        assert config.prompt_variables == {"var1": "value1"}


class TestLangChainTask:
    """Test LangChain task base class."""

    def setup_method(self):
        """Setup test environment."""
        self.config = LangChainTaskConfig(
            llm_provider="openrouter",
            llm_model="test-model",
            prompt_template="Test: {input}",
        )

    def test_task_initialization(self):
        """Test task initialization."""
        task = MockLangChainTask("test_task", self.config)

        assert task.name == "test_task"
        assert task.config == self.config
        assert task._llm is None
        assert task._prompt_template is None
        assert task._output_parser is None
        assert task._chain is None

    @patch("src.hex_machina.enrichment.tasks.base.langchain_task.ChatOpenAI")
    @patch("src.hex_machina.enrichment.tasks.base.langchain_task.EnvConfig")
    def test_initialize_with_openrouter(self, mock_env_config, mock_chat_openai):
        """Test initialization with OpenRouter LLM."""
        # Setup mocks
        mock_env = Mock()
        mock_env.get_api_key.return_value = "test-api-key"
        mock_env_config.load.return_value = mock_env

        mock_llm = Mock()
        mock_chat_openai.return_value = mock_llm

        # Create and initialize task
        task = MockLangChainTask("test_task", self.config)
        
        with patch.object(task, '_initialize_prompt_template'):
            with patch.object(task, '_initialize_output_parser'):
                with patch.object(task, '_build_chain'):
                    task.initialize()

        # Verify LLM was created correctly
        mock_chat_openai.assert_called_once_with(
            model="test-model",
            temperature=0.0,
            max_tokens=None,
            openai_api_key="test-api-key",
            openai_api_base="https://openrouter.ai/api/v1",
            timeout=30,
        )
        assert task._llm == mock_llm

    @patch("src.hex_machina.enrichment.tasks.base.langchain_task.ChatOpenAI")
    @patch("src.hex_machina.enrichment.tasks.base.langchain_task.EnvConfig")
    def test_initialize_with_openai(self, mock_env_config, mock_chat_openai):
        """Test initialization with OpenAI LLM."""
        # Setup config for OpenAI
        config = LangChainTaskConfig(
            llm_provider="openai",
            llm_model="gpt-4",
            prompt_template="Test: {input}",
        )

        # Setup mocks
        mock_env = Mock()
        mock_env.get_api_key.return_value = "test-api-key"
        mock_env_config.load.return_value = mock_env

        mock_llm = Mock()
        mock_chat_openai.return_value = mock_llm

        # Create and initialize task
        task = MockLangChainTask("test_task", config)
        
        with patch.object(task, '_initialize_prompt_template'):
            with patch.object(task, '_initialize_output_parser'):
                with patch.object(task, '_build_chain'):
                    task.initialize()

        # Verify LLM was created correctly
        mock_chat_openai.assert_called_once_with(
            model="gpt-4",
            temperature=0.0,
            max_tokens=None,
            openai_api_key="test-api-key",
            timeout=30,
        )
        assert task._llm == mock_llm

    def test_initialize_unsupported_provider(self):
        """Test initialization with unsupported LLM provider."""
        config = LangChainTaskConfig(
            llm_provider="unsupported",
            llm_model="test-model",
            prompt_template="Test: {input}",
        )

        task = MockLangChainTask("test_task", config)

        with pytest.raises(TaskException, match="Unsupported LLM provider"):
            task._initialize_llm()

    @patch("src.hex_machina.enrichment.tasks.base.langchain_task.EnvConfig")
    def test_initialize_missing_api_key(self, mock_env_config):
        """Test initialization when API key is missing."""
        # Setup mocks
        mock_env = Mock()
        mock_env.get_api_key.return_value = None
        mock_env_config.load.return_value = mock_env

        task = MockLangChainTask("test_task", self.config)

        with pytest.raises(TaskException, match="OpenRouter API key not found"):
            task._initialize_llm()

    @patch("src.hex_machina.enrichment.tasks.base.langchain_task.get_langchain_template")
    def test_initialize_prompt_template_named(self, mock_get_template):
        """Test initializing prompt template with named template."""
        mock_template = Mock()
        mock_get_template.return_value = mock_template

        task = MockLangChainTask("test_task", self.config)
        task._initialize_prompt_template()

        assert task._prompt_template == mock_template
        mock_get_template.assert_called_once_with("Test: {input}")

    @patch("src.hex_machina.enrichment.tasks.base.langchain_task.get_langchain_template")
    @patch("src.hex_machina.enrichment.tasks.base.langchain_task.create_custom_template")
    def test_initialize_prompt_template_custom(self, mock_create_template, mock_get_template):
        """Test initializing prompt template with custom template."""
        mock_get_template.side_effect = ValueError("Template not found")
        mock_template = Mock()
        mock_create_template.return_value = mock_template

        task = MockLangChainTask("test_task", self.config)
        task._initialize_prompt_template()

        assert task._prompt_template == mock_template
        mock_create_template.assert_called_once_with("Test: {input}")

    def test_initialize_prompt_template_error(self):
        """Test prompt template initialization error handling."""
        task = MockLangChainTask("test_task", self.config)
        
        with patch("src.hex_machina.enrichment.tasks.base.langchain_task.get_langchain_template") as mock_get:
            mock_get.side_effect = Exception("Template error")
            
            with pytest.raises(TaskException, match="Prompt template initialization failed"):
                task._initialize_prompt_template()

    @patch("src.hex_machina.enrichment.tasks.base.langchain_task.parser_registry")
    def test_initialize_output_parser_from_config(self, mock_registry):
        """Test initializing output parser from config."""
        config = LangChainTaskConfig(
            llm_provider="openrouter",
            llm_model="test-model",
            prompt_template="Test: {input}",
            output_parser="TestParser",
        )

        mock_parser = Mock()
        mock_registry.create_parser.return_value = mock_parser

        task = MockLangChainTask("test_task", config)
        task._initialize_output_parser()

        assert task._output_parser == mock_parser
        mock_registry.create_parser.assert_called_once_with("TestParser")

    @patch("src.hex_machina.enrichment.tasks.base.langchain_task.parser_registry")
    def test_initialize_output_parser_from_default(self, mock_registry):
        """Test initializing output parser from task default."""
        mock_parser = Mock()
        mock_registry.create_parser.return_value = mock_parser

        task = MockLangChainTask("test_task", self.config)
        task._initialize_output_parser()

        assert task._output_parser == mock_parser
        mock_registry.create_parser.assert_called_once_with("DefaultParser")

    def test_initialize_output_parser_none(self):
        """Test initializing output parser when none specified."""
        task = MockLangChainTaskNoParser("test_task", self.config)
        task._initialize_output_parser()

        assert task._output_parser is None

    @patch("src.hex_machina.enrichment.tasks.base.langchain_task.parser_registry")
    def test_initialize_output_parser_creation_failure(self, mock_registry):
        """Test output parser initialization when creation fails."""
        mock_registry.create_parser.return_value = None

        config = LangChainTaskConfig(
            llm_provider="openrouter",
            llm_model="test-model",
            prompt_template="Test: {input}",
            output_parser="TestParser",
        )

        task = MockLangChainTask("test_task", config)

        with pytest.raises(TaskException, match="Failed to create output parser"):
            task._initialize_output_parser()

    def test_build_chain_without_parser(self):
        """Test building chain without output parser."""
        task = MockLangChainTask("test_task", self.config)
        task._llm = Mock()
        task._prompt_template = Mock()
        task._output_parser = None

        task._build_chain()

        assert task._chain is not None
        # Verify chain was built correctly (prompt | llm)
        # The actual implementation would use LangChain's pipe operator

    def test_build_chain_with_parser(self):
        """Test building chain with output parser."""
        task = MockLangChainTask("test_task", self.config)
        task._llm = Mock()
        task._prompt_template = Mock()
        task._output_parser = Mock()

        task._build_chain()

        assert task._chain is not None
        # Verify chain was built correctly (prompt | llm | parser)

    def test_build_chain_missing_dependencies(self):
        """Test building chain when dependencies are missing."""
        task = MockLangChainTask("test_task", self.config)
        task._llm = None
        task._prompt_template = Mock()

        with pytest.raises(TaskException, match="LLM and prompt template must be initialized"):
            task._build_chain()

    async def test_execute_success(self):
        """Test successful task execution."""
        task = MockLangChainTask("test_task", self.config)
        
        # Mock chain execution
        mock_chain = AsyncMock()
        mock_chain.ainvoke.return_value = {"result": "success"}
        task._chain = mock_chain

        # Mock validation
        task.validate_input = Mock(return_value=True)

        # Create test input
        task_input = TaskInput(
            task_id="test",
            task_name="test_task",
            input_data={"input": "test content"},
        )

        # Execute
        result = await task.execute(task_input)

        # Assertions
        assert isinstance(result, TaskOutput)
        assert result.task_id == "test"
        assert result.output_data == {"result": "success"}
        assert result.error is None
        mock_chain.ainvoke.assert_called_once()

    async def test_execute_validation_failure(self):
        """Test task execution when input validation fails."""
        task = MockLangChainTask("test_task", self.config)
        task.validate_input = Mock(return_value=False)

        task_input = TaskInput(
            task_id="test",
            task_name="test_task",
            input_data={"input": "test content"},
        )

        result = await task.execute(task_input)

        # Should return error result
        assert isinstance(result, TaskOutput)
        assert result.error is not None
        assert "Invalid input data" in result.error

    async def test_execute_chain_error(self):
        """Test task execution when chain raises exception."""
        task = MockLangChainTask("test_task", self.config)
        
        # Mock chain to raise exception
        mock_chain = AsyncMock()
        mock_chain.ainvoke.side_effect = Exception("Chain error")
        task._chain = mock_chain

        task.validate_input = Mock(return_value=True)

        task_input = TaskInput(
            task_id="test",
            task_name="test_task",
            input_data={"input": "test content"},
        )

        result = await task.execute(task_input)

        # Should return error result
        assert isinstance(result, TaskOutput)
        assert result.error is not None
        assert "Chain error" in result.error

    def test_prepare_chain_input_basic(self):
        """Test preparing chain input with basic data."""
        task = MockLangChainTask("test_task", self.config)
        
        task_input = TaskInput(
            task_id="test",
            task_name="test_task",
            input_data={"input": "test content", "other": "data"},
        )

        result = task._prepare_chain_input(task_input)

        assert result == {"input": "test content", "other": "data"}

    def test_prepare_chain_input_with_variables(self):
        """Test preparing chain input with prompt variables."""
        config = LangChainTaskConfig(
            llm_provider="openrouter",
            llm_model="test-model",
            prompt_template="Test: {input}",
            prompt_variables={"var1": "value1", "var2": "value2"},
        )

        task = MockLangChainTask("test_task", config)
        
        task_input = TaskInput(
            task_id="test",
            task_name="test_task",
            input_data={"input": "test content"},
        )

        result = task._prepare_chain_input(task_input)

        expected = {
            "input": "test content",
            "var1": "value1",
            "var2": "value2",
        }
        assert result == expected

    def test_process_chain_result_dict(self):
        """Test processing chain result when it's a dictionary."""
        task = MockLangChainTask("test_task", self.config)
        
        result = {"key1": "value1", "key2": "value2"}
        processed = task._process_chain_result(result)

        assert processed == result

    def test_process_chain_result_pydantic(self):
        """Test processing chain result when it's a Pydantic model."""
        task = MockLangChainTask("test_task", self.config)
        
        # Mock Pydantic model
        mock_model = Mock()
        mock_model.model_dump.return_value = {"field": "value"}
        
        processed = task._process_chain_result(mock_model)

        assert processed == {"field": "value"}

    def test_process_chain_result_other(self):
        """Test processing chain result when it's other type."""
        task = MockLangChainTask("test_task", self.config)
        
        result = "simple string result"
        processed = task._process_chain_result(result)

        assert processed == {"result": "simple string result"}


# Mock implementations for testing
class MockLangChainTask(LangChainTask):
    """Mock LangChain task for testing."""

    def validate_input(self, input_data):
        """Mock validation."""
        return True

    def get_default_parser_name(self):
        """Mock default parser name."""
        return "DefaultParser"


class MockLangChainTaskNoParser(LangChainTask):
    """Mock LangChain task without default parser."""

    def validate_input(self, input_data):
        """Mock validation."""
        return True

    def get_default_parser_name(self):
        """No default parser."""
        return None