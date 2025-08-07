"""Custom exceptions for Hex Machina v2."""

from typing import Optional


class HexMachinaException(Exception):
    """Base exception for all Hex Machina errors."""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationException(HexMachinaException):
    """Raised when there are configuration-related errors."""

    pass


class TaskException(HexMachinaException):
    """Raised when there are task execution errors."""

    pass


class WorkflowException(HexMachinaException):
    """Raised when there are workflow execution errors."""

    pass


class EvaluationException(HexMachinaException):
    """Raised when there are evaluation-related errors."""

    pass
