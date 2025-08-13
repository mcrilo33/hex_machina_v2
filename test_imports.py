#!/usr/bin/env python3
"""Test file to check what evaluators are available."""

print("🔍 Checking available evaluators...")

# Try langsmith.evaluation
try:
    from langsmith.evaluation import *

    print("✅ langsmith.evaluation imported successfully")

    import inspect

    evaluators = [
        name
        for name, obj in inspect.getmembers(langsmith.evaluation)
        if inspect.isclass(obj) and "Eval" in name
    ]
    print(f"Available evaluators in langsmith.evaluation: {evaluators}")

except Exception as e:
    print(f"❌ langsmith.evaluation import failed: {e}")

# Try langchain.evaluation
try:
    from langchain.evaluation import *

    print("✅ langchain.evaluation imported successfully")

    import inspect

    evaluators = [
        name
        for name, obj in inspect.getmembers(langchain.evaluation)
        if inspect.isclass(obj) and "Eval" in name
    ]
    print(f"Available evaluators in langchain.evaluation: {evaluators}")

except Exception as e:
    print(f"❌ langchain.evaluation import failed: {e}")

# Try specific imports
try:
    print("✅ CriteriaEvalChain found in langchain.evaluation.criteria")
except Exception as e:
    print(f"❌ CriteriaEvalChain not found: {e}")

try:
    print("✅ QAEvalChain found in langchain.evaluation.qa")
except Exception as e:
    print(f"❌ QAEvalChain not found: {e}")

try:
    print("✅ RAGEvalChain found in langchain.evaluation.rag")
except Exception as e:
    print(f"❌ RAGEvalChain not found: {e}")
