#!/usr/bin/env python3
"""Check environment variable loading."""

import os

# Try to load .env file
try:
    from dotenv import load_dotenv

    load_dotenv()
    print("✅ .env file loaded successfully")
except ImportError:
    print("❌ python-dotenv not installed")
    print("Install with: poetry add python-dotenv")

# Check API key
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    print(f"✅ OPENAI_API_KEY found: {api_key[:20]}...")
else:
    print("❌ OPENAI_API_KEY not found")
