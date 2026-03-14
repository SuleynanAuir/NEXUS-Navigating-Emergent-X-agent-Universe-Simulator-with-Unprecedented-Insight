"""
Unit tests for Planner Agent.
"""

import json
import unittest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.multi_agents.agents.planner_agent import (
    PlannerAgent, 
    ResearchDecomposition, 
    SubQuestion,
    create_planner
)
from src.multi_agents.utils.json_parser import (
    parse_json_response, 
    validate_planner_output
)


class TestPlannerAgentBasics(unittest.TestCase):
    """Test basic PlannerAgent functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.planner = create_planner()
        self.sample_query = "What is artificial intelligence?"
    
    def test_planner_initialization(self):
        """Test PlannerAgent initialization."""
        self.assertIsNotNone(self.planner)
        self.assertIsInstance(self.planner, PlannerAgent)
    
    def test_decompose_basic_query(self):
        """Test decomposing a basic query."""
        decomposition = self.planner.decompose(self.sample_query)
        
        self.assertIsInstance(decomposition, ResearchDecomposition)
        self.assertEqual(decomposition.main_question, self.sample_query)
        self.assertGreater(len(decomposition.sub_questions), 0)
    
    def test_empty_query_raises_error(self):
        """Test that empty query raises ValueError."""
        with self.assertRaises(ValueError):
            self.planner.decompose("")
    
    def test_sub_questions_minimum(self):
        """Test that decomposition produces minimum 4 sub-questions."""
        decomposition = self.planner.decompose(self.sample_query)
        self.assertGreaterEqual(len(decomposition.sub_questions), 4)
    
    def test_sub_question_structure(self):
        """Test SubQuestion object structure."""
        sub_q = SubQuestion(
            question="What is AI?",
            difficulty=3,
            expected_evidence_type="academic papers"
        )
        
        self.assertEqual(sub_q.question, "What is AI?")
        self.assertEqual(sub_q.difficulty, 3)
        self.assertEqual(sub_q.expected_evidence_type, "academic papers")


class TestDecompositionValidation(unittest.TestCase):
    """Test decomposition validation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.planner = create_planner()
    
    def test_valid_decomposition(self):
        """Test validation of valid decomposition."""
        decomposition = self.planner.decompose("What is AI?")
        is_valid, errors = self.planner.validate_decomposition(decomposition)
        
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_difficulty_range_validation(self):
        """Test difficulty range validation."""
        decomposition = self.planner.decompose("What is AI?")
        
        # All difficulties should be 1-5
        for sq in decomposition.sub_questions:
            self.assertGreaterEqual(sq.difficulty, 1)
            self.assertLessEqual(sq.difficulty, 5)
    
    def test_estimated_rounds_range(self):
        """Test estimated rounds are within valid range."""
        decomposition = self.planner.decompose("What is AI?")
        
        self.assertGreaterEqual(decomposition.estimated_total_rounds, 1)
        self.assertLessEqual(decomposition.estimated_total_rounds, 5)


class TestAssumptionDetection(unittest.TestCase):
    """Test assumption detection."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.planner = create_planner()
    
    def test_assumptions_detected(self):
        """Test that assumptions are detected."""
        decomposition = self.planner.decompose("Why is AI important?")
        
        # Should detect at least one assumption
        self.assertGreater(len(decomposition.assumptions_detected), 0)
    
    def test_assumption_is_string(self):
        """Test all assumptions are strings."""
        decomposition = self.planner.decompose("What are the impacts of AI?")
        
        for assumption in decomposition.assumptions_detected:
            self.assertIsInstance(assumption, str)
            self.assertTrue(len(assumption) > 0)


class TestDimensionExtraction(unittest.TestCase):
    """Test dimension extraction."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.planner = create_planner()
    
    def test_all_dimensions_present(self):
        """Test all required dimensions are present."""
        decomposition = self.planner.decompose("What is AI?")
        
        required_dims = ["theoretical", "empirical", "methodological", "applications"]
        for dim in required_dims:
            self.assertIn(dim, decomposition.dimensions)
    
    def test_dimension_has_content(self):
        """Test each dimension has content."""
        decomposition = self.planner.decompose("What is AI?")
        
        for dim_name, dim_content in decomposition.dimensions.items():
            self.assertIsInstance(dim_content, list)
            self.assertGreater(len(dim_content), 0)


class TestJSONParsing(unittest.TestCase):
    """Test JSON parsing utilities."""
    
    def test_parse_valid_json(self):
        """Test parsing valid JSON."""
        json_str = '{"key": "value"}'
        result = parse_json_response(json_str)
        
        self.assertEqual(result["key"], "value")
    
    def test_parse_json_with_markdown(self):
        """Test parsing JSON wrapped in markdown code blocks."""
        json_str = '```json\n{"key": "value"}\n```'
        result = parse_json_response(json_str)
        
        self.assertEqual(result["key"], "value")
    
    def test_validate_planner_output_valid(self):
        """Test validating valid planner output."""
        data = {
            "main_question": "What is AI?",
            "assumptions_detected": ["AI exists"],
            "dimensions": {
                "theoretical": ["Definition"],
                "empirical": ["Current state"],
                "methodological": ["Research methods"],
                "applications": ["Use cases"]
            },
            "sub_questions": [
                {"question": "Q1?", "difficulty": 2, "expected_evidence_type": "papers"},
                {"question": "Q2?", "difficulty": 3, "expected_evidence_type": "data"},
                {"question": "Q3?", "difficulty": 3, "expected_evidence_type": "examples"},
                {"question": "Q4?", "difficulty": 2, "expected_evidence_type": "analysis"},
            ],
            "iteration_strategy": "Start with theory",
            "estimated_total_rounds": 3
        }
        
        is_valid, errors = validate_planner_output(data)
        self.assertTrue(is_valid)
    
    def test_validate_planner_output_missing_key(self):
        """Test validation catches missing keys."""
        data = {
            "main_question": "What is AI?",
            # Missing other required fields
        }
        
        is_valid, errors = validate_planner_output(data)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)
    
    def test_validate_too_few_sub_questions(self):
        """Test validation catches too few sub-questions."""
        data = {
            "main_question": "What is AI?",
            "assumptions_detected": [],
            "dimensions": {
                "theoretical": [],
                "empirical": [],
                "methodological": [],
                "applications": []
            },
            "sub_questions": [
                {"question": "Q1?", "difficulty": 2, "expected_evidence_type": "papers"},
                {"question": "Q2?", "difficulty": 3, "expected_evidence_type": "data"},
            ],
            "iteration_strategy": "Strategy",
            "estimated_total_rounds": 2
        }
        
        is_valid, errors = validate_planner_output(data)
        self.assertFalse(is_valid)
        self.assertTrue(any("minimum 4" in str(e).lower() for e in errors))


class TestDecompositionSerialization(unittest.TestCase):
    """Test decomposition serialization."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.planner = create_planner()
        self.decomposition = self.planner.decompose("What is AI?")
    
    def test_to_dict(self):
        """Test converting decomposition to dictionary."""
        data = self.decomposition.to_dict()
        
        self.assertIsInstance(data, dict)
        self.assertIn("main_question", data)
        self.assertIn("sub_questions", data)
    
    def test_to_json(self):
        """Test converting decomposition to JSON."""
        json_str = self.decomposition.to_json()
        
        self.assertIsInstance(json_str, str)
        # Should be parseable JSON
        parsed = json.loads(json_str)
        self.assertIsInstance(parsed, dict)
    
    def test_json_roundtrip(self):
        """Test JSON serialization and deserialization."""
        # Serialize
        json_str = self.decomposition.to_json()
        
        # Deserialize
        data = json.loads(json_str)
        
        # Validate
        is_valid, errors = validate_planner_output(data)
        self.assertTrue(is_valid, f"Validation errors: {errors}")


class TestMultipleQueries(unittest.TestCase):
    """Test decomposing multiple queries."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.planner = create_planner()
    
    def test_multiple_queries_consistency(self):
        """Test that multiple queries produce consistent structure."""
        queries = [
            "What is AI?",
            "How does machine learning work?",
            "What are neural networks?",
        ]
        
        for query in queries:
            decomposition = self.planner.decompose(query)
            
            # Check structure
            self.assertEqual(decomposition.main_question, query)
            self.assertGreaterEqual(len(decomposition.sub_questions), 4)
            self.assertGreater(len(decomposition.assumptions_detected), 0)
            self.assertGreater(len(decomposition.iteration_strategy), 0)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.planner = create_planner()
    
    def test_very_short_query(self):
        """Test very short query."""
        decomposition = self.planner.decompose("AI?")
        
        self.assertIsNotNone(decomposition)
        self.assertGreater(len(decomposition.sub_questions), 0)
    
    def test_very_long_query(self):
        """Test very long query."""
        long_query = "What are the " + "very " * 50 + "long implications of AI?"
        decomposition = self.planner.decompose(long_query)
        
        self.assertIsNotNone(decomposition)
        self.assertGreater(len(decomposition.sub_questions), 0)
    
    def test_query_with_special_chars(self):
        """Test query with special characters."""
        query = "What's the impact of AI/ML on cloud computing?"
        decomposition = self.planner.decompose(query)
        
        self.assertIsNotNone(decomposition)
        self.assertEqual(decomposition.main_question, query)


if __name__ == "__main__":
    unittest.main(verbosity=2)
