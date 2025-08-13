#!/usr/bin/env python3
"""Test file to understand how to properly instantiate CriteriaEvalChain."""

print("🔍 Testing CriteriaEvalChain instantiation...")

try:
    from langchain.evaluation.criteria import CriteriaEvalChain

    print("✅ CriteriaEvalChain imported successfully")

    # Check the class signature
    import inspect

    sig = inspect.signature(CriteriaEvalChain.__init__)
    print(f"Constructor parameters: {list(sig.parameters.keys())}")

    # Try to create a simple instance
    try:
        # This should work with minimal parameters
        eval_chain = CriteriaEvalChain()
        print("✅ CriteriaEvalChain created with no parameters")
    except Exception as e:
        print(f"❌ Failed to create with no parameters: {e}")

        # Try with criterion_name
        try:
            eval_chain = CriteriaEvalChain(criterion_name="helpfulness")
            print("✅ CriteriaEvalChain created with criterion_name")
        except Exception as e:
            print(f"❌ Failed to create with criterion_name: {e}")

            # Try with criteria (old parameter name)
            try:
                eval_chain = CriteriaEvalChain(criteria="helpfulness")
                print("✅ CriteriaEvalChain created with criteria")
            except Exception as e:
                print(f"❌ Failed to create with criteria: {e}")

except Exception as e:
    print(f"❌ Import failed: {e}")
