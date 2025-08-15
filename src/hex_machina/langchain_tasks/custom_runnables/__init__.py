"""
Custom runnables package for LangChain tasks.

This package contains custom runnable classes and functions that can be automatically
discovered and registered with the runnable registry.
"""

# Explicit imports to ensure auto-discovery works
from .text_truncator import TextTruncatorRunnable

# This file enables auto-discovery of custom runnables
# All runnable classes in this package will be automatically registered

__all__ = ["TextTruncatorRunnable"]
