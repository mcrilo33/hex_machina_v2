"""
Entry point for running langchain_tasks as a module.

This allows the CLI to be run with:
    python -m src.hex_machina.langchain_tasks <command> [options]
"""

from .cli import main

if __name__ == "__main__":
    main()
