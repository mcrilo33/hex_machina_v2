#!/bin/bash
# Helper script to load environment variables from .env file
# Usage: source scripts/load_env.sh

if [ -f ".env" ]; then
    echo "Loading environment variables from .env file..."
    export $(cat .env | grep -v '^#' | xargs)
    echo "Environment variables loaded successfully!"
    echo "OPENAI_API_KEY is set: ${OPENAI_API_KEY:0:20}..."
    echo "OPENROUTER_API_KEY is set: ${OPENROUTER_API_KEY:0:20}..."
else
    echo "Error: .env file not found in current directory"
    echo "Please create a .env file with your API keys:"
    echo "OPENAI_API_KEY=your-api-key-here"
    echo "OPENROUTER_API_KEY=your-openrouter-api-key-here"
    echo "ANTHROPIC_API_KEY=your-anthropic-api-key-here"
    exit 1
fi
