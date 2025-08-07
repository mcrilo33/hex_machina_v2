#!/usr/bin/env python3
"""Script to run LangSmith experiments comparing different models and prompts."""

import asyncio
import logging
import os
import sys
from typing import Dict

# Load environment variables
from dotenv import load_dotenv

load_dotenv()

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_model_comparison_experiment():
    """Run a model comparison experiment using LangSmith."""
    
    print("🧪 LangSmith Model Comparison Experiment")
    print("=" * 50)
    
    # Check API keys
    if not os.getenv("LANGSMITH_API_KEY") or not os.getenv("OPENROUTER_API_KEY"):
        print("❌ API keys not configured")
        print("   Please set LANGSMITH_API_KEY and OPENROUTER_API_KEY in your .env file")
        return
    
    # Setup LangSmith
    from src.hex_machina.enrichment.evaluation.langsmith import (
        EvaluationDatasetManager,
        setup_langsmith_environment,
    )
    
    setup_langsmith_environment()
    dataset_manager = EvaluationDatasetManager(logger=logger)
    
    # Get the corrected dataset
    dataset_name = "test_articles_2025-08-01_001"
    dataset = dataset_manager.get_dataset(dataset_name)
    
    if not dataset:
        print(f"❌ Dataset not found: {dataset_name}")
        return
    
    print(f"✅ Using dataset: {dataset.name}")
    print(f"📊 Dataset examples: {dataset.example_count}")
    
    # Define models to compare
    models = [
        {
            "name": "gpt-4o-mini",
            "model": "openai/gpt-4o-mini",
            "description": "GPT-4o Mini - Fast and efficient"
        },
        {
            "name": "claude-3-haiku",
            "model": "anthropic/claude-3-haiku-20240307",
            "description": "Claude 3 Haiku - Fast and accurate"
        },
        {
            "name": "gpt-3.5-turbo",
            "model": "openai/gpt-3.5-turbo",
            "description": "GPT-3.5 Turbo - Cost-effective"
        }
    ]
    
    # Define experiment parameters
    experiment_name = "content-completeness-model-comparison"
    prompt_version = "v1_0"
    
    print("\n🤖 Models to compare:")
    for i, model in enumerate(models, 1):
        print(f"   {i}. {model['name']} - {model['description']}")
    
    # Create evaluator factory
    def create_evaluator(model_config: Dict[str, str]):
        from langchain_openai import ChatOpenAI

        from src.hex_machina.enrichment.evaluation.langchain.chains.evaluation_chains import (
            ContentCompletenessEvaluator,
        )
        
        llm = ChatOpenAI(
            model=model_config["model"],
            openai_api_key=os.getenv("OPENROUTER_API_KEY"),
            openai_api_base="https://openrouter.ai/api/v1",
        )
        
        return ContentCompletenessEvaluator(llm=llm, logger=logger)
    
    # Run experiments
    from langsmith import Client
    client = Client()
    
    # Create experiment
    try:
        experiment = client.create_project(
            project_name=experiment_name,
            description=f"Comparing content completeness evaluation across {len(models)} models"
        )
        print(f"✅ Created experiment: {experiment.name}")
    except Exception as e:
        print(f"⚠️  Using existing experiment or creating new one: {e}")
        experiment = None
    
    # Run evaluations for each model
    results = {}
    
    for model_config in models:
        print(f"\n🔬 Testing {model_config['name']}...")
        
        try:
            # Create evaluator
            evaluator = create_evaluator(model_config)
            
            # Run evaluation on dataset
            evaluations = await dataset_manager.run_evaluation_on_dataset(
                dataset=dataset,
                evaluator=evaluator,
                run_name=f"{experiment_name}-{model_config['name']}"
            )
            
            # Calculate metrics
            total = len(evaluations)
            correct = sum(1 for e in evaluations if e.is_complete is not None)
            accuracy = correct / total if total > 0 else 0
            
            # Get human-labeled examples for comparison
            human_labeled = [e for e in evaluations if hasattr(e, 'metadata') and e.metadata.get('human_labeled') == 'true']
            human_accuracy = 0
            if human_labeled:
                human_correct = sum(1 for e in human_labeled if e.is_complete is not None)
                human_accuracy = human_correct / len(human_labeled)
            
            results[model_config['name']] = {
                'total_evaluations': total,
                'accuracy': accuracy,
                'human_labeled_accuracy': human_accuracy,
                'human_labeled_count': len(human_labeled),
                'evaluations': evaluations
            }
            
            print(f"   ✅ {model_config['name']}: {accuracy:.1%} accuracy ({correct}/{total})")
            print(f"   👤 Human-labeled accuracy: {human_accuracy:.1%} ({len(human_labeled)} examples)")
            
        except Exception as e:
            print(f"   ❌ {model_config['name']}: Failed - {e}")
            results[model_config['name']] = {'error': str(e)}
    
    # Display results summary
    print("\n📊 Experiment Results Summary")
    print("=" * 50)
    
    for model_name, result in results.items():
        if 'error' in result:
            print(f"❌ {model_name}: {result['error']}")
        else:
            print(f"✅ {model_name}:")
            print(f"   Overall Accuracy: {result['accuracy']:.1%}")
            print(f"   Human-labeled Accuracy: {result['human_labeled_accuracy']:.1%}")
            print(f"   Total Evaluations: {result['total_evaluations']}")
            print(f"   Human-labeled Examples: {result['human_labeled_count']}")
    
    # Save results to file
    import json
    from datetime import datetime
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"experiment_results_{experiment_name}_{timestamp}.json"
    
    # Convert evaluations to serializable format
    serializable_results = {}
    for model_name, result in results.items():
        if 'error' in result:
            serializable_results[model_name] = result
        else:
            serializable_results[model_name] = {
                'total_evaluations': result['total_evaluations'],
                'accuracy': result['accuracy'],
                'human_labeled_accuracy': result['human_labeled_accuracy'],
                'human_labeled_count': result['human_labeled_count'],
                'evaluations_count': len(result['evaluations'])
            }
    
    with open(results_file, 'w') as f:
        json.dump(serializable_results, f, indent=2)
    
    print(f"\n💾 Results saved to: {results_file}")
    print("🔗 View experiment in LangSmith: https://smith.langchain.com/")
    
    return results


async def run_prompt_comparison_experiment():
    """Run a prompt comparison experiment using LangSmith."""
    
    print("📝 LangSmith Prompt Comparison Experiment")
    print("=" * 50)
    
    # Check API keys
    if not os.getenv("LANGSMITH_API_KEY") or not os.getenv("OPENROUTER_API_KEY"):
        print("❌ API keys not configured")
        return
    
    # Setup LangSmith
    from src.hex_machina.enrichment.evaluation.langsmith import (
        EvaluationDatasetManager,
        setup_langsmith_environment,
    )
    
    setup_langsmith_environment()
    dataset_manager = EvaluationDatasetManager(logger=logger)
    
    # Get the corrected dataset
    dataset_name = "test_articles_2025-08-01_001"
    dataset = dataset_manager.get_dataset(dataset_name)
    
    if not dataset:
        print(f"❌ Dataset not found: {dataset_name}")
        return
    
    print(f"✅ Using dataset: {dataset.name}")
    
    # Define different prompts to test
    prompts = [
        {
            "name": "detailed_prompt",
            "description": "Detailed prompt with specific instructions",
            "template": """You are an expert content evaluator. Analyze the following article and determine if it contains complete, readable content.

Article URL: {url}
Article Title: {title}
Article Content: {content}

Please evaluate:
1. Is the content complete and readable?
2. Are there any issues like paywalls, anti-bot pages, or incomplete content?

Respond with:
- is_complete: true/false
- detected_issues: [list of issues if any]
- confidence: high/medium/low
- reasoning: brief explanation of your decision"""
        },
        {
            "name": "simple_prompt", 
            "description": "Simple, direct prompt",
            "template": """Evaluate if this article has complete, readable content:

URL: {url}
Title: {title}
Content: {content}

Is the content complete? (true/false)
Any issues? (list if any)"""
        },
        {
            "name": "structured_prompt",
            "description": "Structured prompt with clear format",
            "template": """Content Completeness Evaluation

Article Information:
- URL: {url}
- Title: {title}
- Content Length: {content_length} characters

Evaluation Criteria:
1. Content is complete and readable
2. No paywall or access restrictions
3. No anti-bot protection blocking content
4. Content provides meaningful information

Evaluation:
- Complete: [true/false]
- Issues: [list any problems]
- Confidence: [high/medium/low]"""
        }
    ]
    
    print("\n📝 Prompts to compare:")
    for i, prompt in enumerate(prompts, 1):
        print(f"   {i}. {prompt['name']} - {prompt['description']}")
    
    # Use a single model for prompt comparison
    model_name = "openai/gpt-4o-mini"
    
    # Create evaluator with custom prompt
    def create_evaluator_with_prompt(prompt_template: str):
        from langchain.prompts import PromptTemplate
        from langchain_openai import ChatOpenAI

        from src.hex_machina.enrichment.evaluation.langchain.chains.evaluation_chains import (
            ContentCompletenessEvaluator,
        )
        
        llm = ChatOpenAI(
            model=model_name,
            openai_api_key=os.getenv("OPENROUTER_API_KEY"),
            openai_api_base="https://openrouter.ai/api/v1",
        )
        
        # Create custom prompt template
        prompt = PromptTemplate(
            input_variables=["url", "title", "content", "content_length"],
            template=prompt_template
        )
        
        # Note: You might need to modify the evaluator to accept custom prompts
        # For now, we'll use the default evaluator
        return ContentCompletenessEvaluator(llm=llm, logger=logger)
    
    # Run prompt comparison
    experiment_name = "content-completeness-prompt-comparison"
    results = {}
    
    for prompt_config in prompts:
        print(f"\n🔬 Testing prompt: {prompt_config['name']}...")
        
        try:
            evaluator = create_evaluator_with_prompt(prompt_config['template'])
            
            evaluations = await dataset_manager.run_evaluation_on_dataset(
                dataset=dataset,
                evaluator=evaluator,
                run_name=f"{experiment_name}-{prompt_config['name']}"
            )
            
            # Calculate metrics
            total = len(evaluations)
            correct = sum(1 for e in evaluations if e.is_complete is not None)
            accuracy = correct / total if total > 0 else 0
            
            results[prompt_config['name']] = {
                'total_evaluations': total,
                'accuracy': accuracy,
                'evaluations': evaluations
            }
            
            print(f"   ✅ {prompt_config['name']}: {accuracy:.1%} accuracy ({correct}/{total})")
            
        except Exception as e:
            print(f"   ❌ {prompt_config['name']}: Failed - {e}")
            results[prompt_config['name']] = {'error': str(e)}
    
    # Display results
    print("\n📊 Prompt Comparison Results")
    print("=" * 40)
    
    for prompt_name, result in results.items():
        if 'error' in result:
            print(f"❌ {prompt_name}: {result['error']}")
        else:
            print(f"✅ {prompt_name}: {result['accuracy']:.1%} accuracy")
    
    return results


async def show_experiment_status():
    """Show the status of existing experiments."""
    
    print("📊 LangSmith Experiments Status")
    print("=" * 40)
    
    if not os.getenv("LANGSMITH_API_KEY"):
        print("❌ LANGSMITH_API_KEY not found")
        return
    
    from langsmith import Client
    client = Client()
    
    try:
        # List recent projects (experiments)
        projects = list(client.list_projects())
        
        if not projects:
            print("❌ No experiments found")
            return
        
        print(f"Found {len(projects)} experiments:")
        
        for project in projects[:10]:  # Show first 10
            print(f"\n🔬 {project.name}")
            print(f"   ID: {project.id}")
            print(f"   Description: {project.description or 'No description'}")
            print(f"   Created: {project.created_at}")
            
            # Get run count
            runs = list(client.list_runs(project_name=project.name))
            print(f"   Runs: {len(runs)}")
            
    except Exception as e:
        print(f"❌ Failed to fetch experiments: {e}")


async def main():
    """Main function."""
    print("🧪 LangSmith Experiments Tool")
    print("=" * 40)
    
    # Show available options
    print("\nAvailable experiments:")
    print("1. Model comparison experiment")
    print("2. Prompt comparison experiment") 
    print("3. Show experiment status")
    print("4. Exit")
    
    choice = input("\nSelect experiment (1-4): ").strip()
    
    if choice == "1":
        await run_model_comparison_experiment()
    elif choice == "2":
        await run_prompt_comparison_experiment()
    elif choice == "3":
        await show_experiment_status()
    elif choice == "4":
        print("👋 Goodbye!")
    else:
        print("❌ Invalid choice")


if __name__ == "__main__":
    asyncio.run(main()) 