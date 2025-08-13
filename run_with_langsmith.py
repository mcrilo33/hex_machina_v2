#!/usr/bin/env python3
"""
Script to run the LLM processing test with LangSmith environment variables set.
This will enable proper tracing to LangSmith.
"""

import os
import sys
from pathlib import Path

# Set LangSmith environment variables
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGCHAIN_API_KEY"] = (
    "your-api-key-here"  # Replace with your actual API key
)
os.environ["LANGCHAIN_PROJECT"] = "hex-machina-v2"

print("🔧 Setting LangSmith environment variables...")
print(f"   LANGCHAIN_TRACING_V2: {os.getenv('LANGCHAIN_TRACING_V2')}")
print(f"   LANGCHAIN_ENDPOINT: {os.getenv('LANGCHAIN_ENDPOINT')}")
print(
    f"   LANGCHAIN_API_KEY: {os.getenv('LANGCHAIN_API_KEY')[:10]}..."
    if os.getenv("LANGCHAIN_API_KEY")
    else "NOT SET"
)
print(f"   LANGCHAIN_PROJECT: {os.getenv('LANGCHAIN_PROJECT')}")
print()

# Check if API key is set
if os.getenv("LANGCHAIN_API_KEY") == "your-api-key-here":
    print("❌ ERROR: Please set your actual LangSmith API key in this script!")
    print("   You can get it from: https://smith.langchain.com/")
    print("   Replace 'your-api-key-here' with your actual API key")
    sys.exit(1)

# Add the src directory to the Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Now run the test
print("🚀 Running test with LangSmith tracing enabled...")
print("=" * 60)

# Import and run the test
from test_llm_processing import main

main()
