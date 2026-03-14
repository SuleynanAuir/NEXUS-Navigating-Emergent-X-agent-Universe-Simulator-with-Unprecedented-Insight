"""
Examples demonstrating Planner Agent usage.
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.multi_agents.agents.planner_agent import create_planner
from src.multi_agents.utils.json_parser import format_decomposition_output, validate_planner_output


def example_basic_usage():
    """Basic usage example without LLM."""
    print("=" * 80)
    print("EXAMPLE 1: Basic Usage (Local Decomposition)")
    print("=" * 80)
    
    # Create planner without LLM
    planner = create_planner()
    
    # Example query
    query = "What are the latest developments in artificial intelligence and their potential impact on the job market in 2026?"
    
    print(f"\n📝 Analyzing Query: {query}\n")
    
    # Decompose
    decomposition = planner.decompose(query)
    
    # Validate
    is_valid, errors = planner.validate_decomposition(decomposition)
    
    if not is_valid:
        print("❌ Validation errors:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("✅ Decomposition validated successfully!")
    
    # Display results
    print(format_decomposition_output(decomposition.to_dict(), verbose=True))
    
    # Output JSON
    print("\n" + "=" * 80)
    print("JSON Output:")
    print("=" * 80)
    print(decomposition.to_json())


def example_multiple_queries():
    """Example with multiple different queries."""
    print("\n\n" + "=" * 80)
    print("EXAMPLE 2: Multiple Queries Analysis")
    print("=" * 80)
    
    planner = create_planner()
    
    queries = [
        "How does blockchain technology work and what are its real-world applications?",
        "What are the causes and potential solutions to climate change?",
        "How can quantum computing revolutionize drug discovery?",
    ]
    
    results = []
    for i, query in enumerate(queries, 1):
        print(f"\n--- Query {i} ---")
        print(f"📝 {query}\n")
        
        decomposition = planner.decompose(query)
        results.append(decomposition)
        
        # Show summary
        print(f"✅ Decomposed into {len(decomposition.sub_questions)} sub-questions")
        print(f"📊 Estimated rounds: {decomposition.estimated_total_rounds}")
        print(f"🔍 Assumptions detected: {len(decomposition.assumptions_detected)}")
    
    return results


def example_detailed_analysis():
    """Detailed analysis of a single query."""
    print("\n\n" + "=" * 80)
    print("EXAMPLE 3: Detailed Analysis")
    print("=" * 80)
    
    planner = create_planner()
    
    query = "What are the ethical implications of artificial general intelligence?"
    print(f"\n📝 Query: {query}\n")
    
    decomposition = planner.decompose(query)
    
    # Detailed breakdown
    print("DECOMPOSITION BREAKDOWN:")
    print("-" * 80)
    
    print(f"\n1. MAIN QUESTION:\n   {decomposition.main_question}")
    
    print(f"\n2. ASSUMPTIONS DETECTED ({len(decomposition.assumptions_detected)}):")
    for i, assumption in enumerate(decomposition.assumptions_detected, 1):
        print(f"   {i}. {assumption}")
    
    print(f"\n3. RESEARCH DIMENSIONS:")
    for dimension, aspects in decomposition.dimensions.items():
        print(f"\n   {dimension.upper()}:")
        for aspect in aspects:
            print(f"   • {aspect}")
    
    print(f"\n4. SUB-QUESTIONS ({len(decomposition.sub_questions)}):")
    for i, sq in enumerate(decomposition.sub_questions, 1):
        print(f"\n   Q{i}: {sq.question}")
        print(f"   Difficulty: {sq.difficulty}/5 | Evidence: {sq.expected_evidence_type}")
    
    print(f"\n5. ITERATION STRATEGY:")
    print(f"   {decomposition.iteration_strategy}")
    
    print(f"\n6. ESTIMATED ROUNDS: {decomposition.estimated_total_rounds}")


def example_export_json():
    """Example showing JSON export capabilities."""
    print("\n\n" + "=" * 80)
    print("EXAMPLE 4: JSON Export")
    print("=" * 80)
    
    planner = create_planner()
    query = "What is the current state of quantum computing technology?"
    
    decomposition = planner.decompose(query)
    
    # Save to file
    output_path = Path(__file__).parent / "decomposition_example.json"
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(decomposition.to_json())
    
    print(f"\n✅ Decomposition saved to: {output_path}")
    print(f"📊 File size: {output_path.stat().st_size} bytes")
    print(f"\n📄 Preview:")
    print(decomposition.to_json()[:500] + "...")


def example_validation():
    """Example showing validation functionality."""
    print("\n\n" + "=" * 80)
    print("EXAMPLE 5: Validation Examples")
    print("=" * 80)
    
    from multi_agents.utils.json_parser import validate_planner_output, print_validation_errors
    
    # Valid example
    valid_data = {
        "main_question": "What is AI?",
        "assumptions_detected": ["AI exists", "People care about it"],
        "dimensions": {
            "theoretical": ["Definition"],
            "empirical": ["Current state"],
            "methodological": ["How to study"],
            "applications": ["Use cases"]
        },
        "sub_questions": [
            {"question": "Q1?", "difficulty": 2, "expected_evidence_type": "papers"},
            {"question": "Q2?", "difficulty": 3, "expected_evidence_type": "data"},
            {"question": "Q3?", "difficulty": 3, "expected_evidence_type": "examples"},
            {"question": "Q4?", "difficulty": 2, "expected_evidence_type": "analysis"},
        ],
        "iteration_strategy": "Start with theory, then empirical",
        "estimated_total_rounds": 3
    }
    
    print("\n✅ Testing VALID data:")
    is_valid, errors = validate_planner_output(valid_data)
    print_validation_errors(errors)
    
    # Invalid example - too few sub-questions
    invalid_data = {
        "main_question": "What is AI?",
        "assumptions_detected": [],
        "dimensions": {"theoretical": [], "empirical": [], "methodological": [], "applications": []},
        "sub_questions": [
            {"question": "Q1?", "difficulty": 2, "expected_evidence_type": "papers"},
            {"question": "Q2?", "difficulty": 3, "expected_evidence_type": "data"},
        ],
        "iteration_strategy": "Strategy",
        "estimated_total_rounds": 2
    }
    
    print("\n❌ Testing INVALID data (too few sub-questions):")
    is_valid, errors = validate_planner_output(invalid_data)
    print_validation_errors(errors)


if __name__ == "__main__":
    # Run all examples
    example_basic_usage()
    example_multiple_queries()
    example_detailed_analysis()
    example_export_json()
    example_validation()
    
    print("\n" + "=" * 80)
    print("✅ All examples completed!")
    print("=" * 80)
