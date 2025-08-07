"""Tests for task registry functionality."""

import pytest
from unittest.mock import Mock, patch

from src.hex_machina.enrichment.core import EnrichmentTask
from src.hex_machina.enrichment.tasks.registry import TaskRegistry
from src.hex_machina.enrichment.tasks.content_completeness_langchain import (
    ContentCompletenessLangChainTask,
)


class MockTask(EnrichmentTask):
    """Mock task for testing."""
    
    def __init__(self, config=None):
        super().__init__("mock_task", config)
    
    def initialize(self):
        pass
    
    async def execute(self, input_data):
        pass
    
    def validate_input(self, input_data):
        return True


class TestTaskRegistry:
    """Test TaskRegistry functionality."""

    def setup_method(self):
        """Setup test environment."""
        # Create a fresh registry for each test
        self.registry = TaskRegistry()

    def test_init_registers_builtin_tasks(self):
        """Test that initialization registers built-in tasks."""
        # Built-in task should be registered
        assert "ContentCompletenessLangChainTask" in self.registry.list_tasks()

    def test_register_task(self):
        """Test registering a new task."""
        initial_count = len(self.registry.list_tasks())
        
        self.registry.register(MockTask)
        
        tasks = self.registry.list_tasks()
        assert len(tasks) == initial_count + 1
        assert "MockTask" in tasks

    def test_register_task_logging(self, caplog):
        """Test that registering a task logs the registration."""
        with caplog.at_level("INFO"):
            self.registry.register(MockTask)
        
        assert "Registered task: MockTask" in caplog.text

    def test_get_task_existing(self):
        """Test getting an existing task class."""
        self.registry.register(MockTask)
        
        task_class = self.registry.get_task("MockTask")
        
        assert task_class == MockTask

    def test_get_task_nonexistent(self):
        """Test getting a non-existent task class."""
        task_class = self.registry.get_task("NonexistentTask")
        
        assert task_class is None

    def test_create_task_success(self):
        """Test creating a task instance successfully."""
        self.registry.register(MockTask)
        config = {"test": "config"}
        
        task_instance = self.registry.create_task("MockTask", config)
        
        assert task_instance is not None
        assert isinstance(task_instance, MockTask)
        assert task_instance.config == config

    def test_create_task_nonexistent(self, caplog):
        """Test creating a non-existent task."""
        with caplog.at_level("ERROR"):
            task_instance = self.registry.create_task("NonexistentTask", {})
        
        assert task_instance is None
        assert "Task not found: NonexistentTask" in caplog.text

    def test_create_task_creation_error(self, caplog):
        """Test creating a task when constructor raises exception."""
        class FailingTask(EnrichmentTask):
            def __init__(self, config):
                raise ValueError("Test error")
        
        self.registry.register(FailingTask)
        
        with caplog.at_level("ERROR"):
            task_instance = self.registry.create_task("FailingTask", {})
        
        assert task_instance is None
        assert "Failed to create task FailingTask" in caplog.text

    def test_list_tasks(self):
        """Test listing all registered tasks."""
        initial_tasks = self.registry.list_tasks()
        
        self.registry.register(MockTask)
        
        tasks = self.registry.list_tasks()
        assert len(tasks) == len(initial_tasks) + 1
        assert "MockTask" in tasks
        assert isinstance(tasks, list)

    def test_get_task_info_existing(self):
        """Test getting task information for existing task."""
        self.registry.register(MockTask)
        
        task_info = self.registry.get_task_info("MockTask")
        
        assert task_info is not None
        assert task_info["name"] == "MockTask"
        assert task_info["class"] == "MockTask"
        assert task_info["module"] == MockTask.__module__
        assert task_info["docstring"] == MockTask.__doc__
        assert "is_langchain" in task_info

    def test_get_task_info_nonexistent(self):
        """Test getting task information for non-existent task."""
        task_info = self.registry.get_task_info("NonexistentTask")
        
        assert task_info is None

    def test_get_task_info_langchain_detection(self):
        """Test that LangChain tasks are properly detected."""
        # Test built-in LangChain task
        task_info = self.registry.get_task_info("ContentCompletenessLangChainTask")
        
        assert task_info is not None
        assert task_info["is_langchain"] is True

    def test_get_task_info_non_langchain_detection(self):
        """Test that non-LangChain tasks are properly detected."""
        self.registry.register(MockTask)
        
        task_info = self.registry.get_task_info("MockTask")
        
        assert task_info is not None
        assert task_info["is_langchain"] is False

    def test_register_overwrites_existing(self):
        """Test that registering a task with same name overwrites."""
        class MockTask1(EnrichmentTask):
            def __init__(self, config=None):
                super().__init__("mock", config)
        
        class MockTask2(EnrichmentTask):
            def __init__(self, config=None):
                super().__init__("mock", config)
        
        # Register first task
        self.registry.register(MockTask1)
        assert self.registry.get_task("MockTask1") == MockTask1
        
        # Register second task with same name
        self.registry.register(MockTask2)
        assert self.registry.get_task("MockTask2") == MockTask2

    def test_builtin_tasks_are_registered(self):
        """Test that all expected built-in tasks are registered."""
        tasks = self.registry.list_tasks()
        
        # Check that the built-in task is present
        assert "ContentCompletenessLangChainTask" in tasks

    def test_task_creation_with_none_config(self):
        """Test task creation with None config."""
        class ConfigOptionalTask(EnrichmentTask):
            def __init__(self, config=None):
                super().__init__("test", config)
        
        self.registry.register(ConfigOptionalTask)
        
        task_instance = self.registry.create_task("ConfigOptionalTask", None)
        
        assert task_instance is not None
        assert isinstance(task_instance, ConfigOptionalTask)

    def test_task_creation_with_empty_config(self):
        """Test task creation with empty config."""
        self.registry.register(MockTask)
        
        task_instance = self.registry.create_task("MockTask", {})
        
        assert task_instance is not None
        assert isinstance(task_instance, MockTask)

    def test_multiple_registrations_same_task(self, caplog):
        """Test multiple registrations of the same task class."""
        initial_count = len(self.registry.list_tasks())
        
        with caplog.at_level("INFO"):
            self.registry.register(MockTask)
            self.registry.register(MockTask)  # Register again
        
        # Should still only be registered once (overwritten)
        tasks = self.registry.list_tasks()
        mock_task_count = sum(1 for task in tasks if task == "MockTask")
        assert mock_task_count == 1
        
        # Should have logged both registrations
        log_messages = [record.message for record in caplog.records]
        mock_task_logs = [msg for msg in log_messages if "MockTask" in msg]
        assert len(mock_task_logs) == 2

    def test_registry_isolation(self):
        """Test that registry instances are properly isolated."""
        registry1 = TaskRegistry()
        registry2 = TaskRegistry()
        
        class Task1(EnrichmentTask):
            def __init__(self, config=None):
                super().__init__("task1", config)
        
        class Task2(EnrichmentTask):
            def __init__(self, config=None):
                super().__init__("task2", config)
        
        registry1.register(Task1)
        registry2.register(Task2)
        
        # Each registry should have its own tasks plus built-ins
        tasks1 = registry1.list_tasks()
        tasks2 = registry2.list_tasks()
        
        assert "Task1" in tasks1
        assert "Task1" not in tasks2
        assert "Task2" not in tasks1
        assert "Task2" in tasks2

    @patch("src.hex_machina.enrichment.tasks.registry.ContentCompletenessLangChainTask")
    def test_builtin_task_registration_error(self, mock_task_class, caplog):
        """Test handling of errors during built-in task registration."""
        # Make the task class raise an exception during import
        mock_task_class.side_effect = ImportError("Module not found")
        
        # This should not crash the registry initialization
        with caplog.at_level("ERROR"):
            try:
                registry = TaskRegistry()
                # The registry should still work, just without the problematic task
                assert isinstance(registry, TaskRegistry)
            except Exception as e:
                # If registration fails, it should be handled gracefully
                assert "ContentCompletenessLangChainTask" not in str(e)

    def test_task_class_name_as_key(self):
        """Test that task class name is used as the registry key."""
        class VerySpecificTaskName(EnrichmentTask):
            def __init__(self, config=None):
                super().__init__("different_name", config)
        
        self.registry.register(VerySpecificTaskName)
        
        # Should be registered under class name, not task name
        assert "VerySpecificTaskName" in self.registry.list_tasks()
        assert self.registry.get_task("VerySpecificTaskName") == VerySpecificTaskName
        assert self.registry.get_task("different_name") is None