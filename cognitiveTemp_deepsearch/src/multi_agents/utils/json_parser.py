"""JSON parsing and validation utilities for multi-agent system."""

import json
import re
from typing import Dict, Any, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


def parse_json_response(response_text: str) -> Dict[str, Any]:
    """
    Parse JSON from LLM response, handling common formatting issues.
    
    Args:
        response_text: Raw response text from LLM
        
    Returns:
        Parsed JSON dictionary
        
    Raises:
        ValueError: If JSON cannot be parsed
    """
    # Try direct parsing first
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass
    
    # Try to extract JSON from markdown code blocks
    json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', response_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Try to find JSON object in the text
    json_start = response_text.find('{')
    json_end = response_text.rfind('}')
    if json_start != -1 and json_end > json_start:
        try:
            return json.loads(response_text[json_start:json_end+1])
        except json.JSONDecodeError:
            pass
    
    raise ValueError(f"Could not parse JSON from response: {response_text[:200]}")


def validate_planner_output(data: Dict[str, Any]) -> Tuple[bool, list[str]]:
    """
    Validate Planner Agent output format.
    
    Args:
        data: Dictionary to validate
        
    Returns:
        Tuple of (is_valid, list of error messages)
    """
    errors = []
    
    # Check required top-level keys
    required_keys = [
        "main_question",
        "assumptions_detected",
        "dimensions",
        "sub_questions",
        "iteration_strategy",
        "estimated_total_rounds"
    ]
    
    for key in required_keys:
        if key not in data:
            errors.append(f"Missing required key: {key}")
    
    # Validate main_question
    if "main_question" in data:
        if not isinstance(data["main_question"], str) or not data["main_question"].strip():
            errors.append("main_question must be a non-empty string")
    
    # Validate assumptions_detected
    if "assumptions_detected" in data:
        if not isinstance(data["assumptions_detected"], list):
            errors.append("assumptions_detected must be a list")
        elif not all(isinstance(a, str) for a in data["assumptions_detected"]):
            errors.append("All assumptions must be strings")
    
    # Validate dimensions
    if "dimensions" in data:
        if not isinstance(data["dimensions"], dict):
            errors.append("dimensions must be a dictionary")
        else:
            expected_dims = ["theoretical", "empirical", "methodological", "applications"]
            for dim in expected_dims:
                if dim not in data["dimensions"]:
                    errors.append(f"Missing dimension: {dim}")
                elif not isinstance(data["dimensions"][dim], list):
                    errors.append(f"dimension '{dim}' must be a list")
    
    # Validate sub_questions
    if "sub_questions" in data:
        if not isinstance(data["sub_questions"], list):
            errors.append("sub_questions must be a list")
        elif len(data["sub_questions"]) < 4:
            errors.append(f"Minimum 4 sub-questions required, got {len(data['sub_questions'])}")
        else:
            for i, sq in enumerate(data["sub_questions"]):
                if not isinstance(sq, dict):
                    errors.append(f"Sub-question {i+1} must be a dictionary")
                    continue
                
                # Check required fields in sub-question
                if "question" not in sq or not isinstance(sq["question"], str):
                    errors.append(f"Sub-question {i+1}: missing or invalid 'question'")
                
                if "difficulty" not in sq:
                    errors.append(f"Sub-question {i+1}: missing 'difficulty'")
                else:
                    try:
                        diff = int(sq["difficulty"])
                        if not 1 <= diff <= 5:
                            errors.append(f"Sub-question {i+1}: difficulty must be 1-5, got {diff}")
                    except (ValueError, TypeError):
                        errors.append(f"Sub-question {i+1}: difficulty must be an integer")
                
                if "expected_evidence_type" not in sq or not isinstance(sq["expected_evidence_type"], str):
                    errors.append(f"Sub-question {i+1}: missing or invalid 'expected_evidence_type'")
    
    # Validate iteration_strategy
    if "iteration_strategy" in data:
        if not isinstance(data["iteration_strategy"], str) or not data["iteration_strategy"].strip():
            errors.append("iteration_strategy must be a non-empty string")
    
    # Validate estimated_total_rounds
    if "estimated_total_rounds" in data:
        try:
            rounds = int(data["estimated_total_rounds"])
            if not 1 <= rounds <= 5:
                errors.append(f"estimated_total_rounds must be 1-5, got {rounds}")
        except (ValueError, TypeError):
            errors.append("estimated_total_rounds must be an integer")
    
    return len(errors) == 0, errors


def print_validation_errors(errors: list[str]) -> None:
    """Pretty print validation errors."""
    if errors:
        print("\n❌ Validation Errors:")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")
    else:
        print("\n✅ Validation passed!")


def format_decomposition_output(data: Dict[str, Any], verbose: bool = True) -> str:
    """
    Format decomposition output for display.
    
    Args:
        data: Decomposition data
        verbose: Whether to include all details
        
    Returns:
        Formatted string
    """
    lines = []
    
    # Main question
    lines.append(f"\n📋 Main Question:\n{data.get('main_question', 'N/A')}")
    
    # Assumptions
    if verbose:
        lines.append(f"\n🔍 Detected Assumptions:")
        for assumption in data.get("assumptions_detected", []):
            lines.append(f"  • {assumption}")
    
    # Dimensions
    if verbose:
        lines.append(f"\n📊 Research Dimensions:")
        for dim, items in data.get("dimensions", {}).items():
            lines.append(f"  {dim.upper()}:")
            for item in items[:2]:  # Show first 2 items per dimension
                lines.append(f"    - {item}")
    
    # Sub-questions
    lines.append(f"\n❓ Sub-Questions ({len(data.get('sub_questions', []))}):")
    for i, sq in enumerate(data.get("sub_questions", []), 1):
        difficulty = "🟢" if sq.get("difficulty", 0) <= 2 else "🟡" if sq.get("difficulty", 0) <= 3 else "🔴"
        lines.append(f"  {i}. {difficulty} {sq.get('question', 'N/A')}")
        lines.append(f"     Difficulty: {sq.get('difficulty', 'N/A')}/5")
    
    # Iteration strategy
    if verbose:
        lines.append(f"\n🔄 Iteration Strategy:")
        lines.append(data.get("iteration_strategy", "N/A"))
    
    # Estimated rounds
    lines.append(f"\n⏱️  Estimated Total Rounds: {data.get('estimated_total_rounds', 'N/A')}")
    
    return "\n".join(lines)
