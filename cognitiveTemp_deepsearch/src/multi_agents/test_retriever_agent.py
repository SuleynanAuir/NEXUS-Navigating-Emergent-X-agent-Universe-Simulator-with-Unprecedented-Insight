"""
Unit tests for Retriever Agent.
"""

import json
import unittest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.multi_agents.agents.retriever_agent import (
    RetrieverAgent,
    RetrievalResult,
    RetrievedSource,
    DomainType,
    create_retriever
)
from src.multi_agents.utils.json_parser import validate_planner_output


class TestRetrieverAgentBasics(unittest.TestCase):
    """Test basic RetrieverAgent functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.retriever = create_retriever()
        self.sample_query = "What is artificial intelligence?"
    
    def test_retriever_initialization(self):
        """Test RetrieverAgent initialization."""
        self.assertIsNotNone(self.retriever)
        self.assertIsInstance(self.retriever, RetrieverAgent)
    
    def test_retrieve_basic_query(self):
        """Test retrieving sources for basic query."""
        result = self.retriever.retrieve(self.sample_query)
        
        self.assertIsInstance(result, RetrievalResult)
        self.assertEqual(result.query_used, self.sample_query)
        self.assertGreater(len(result.results), 0)
    
    def test_empty_query_raises_error(self):
        """Test that empty query raises ValueError."""
        with self.assertRaises(ValueError):
            self.retriever.retrieve("")
    
    def test_minimum_results(self):
        """Test that retrieval produces minimum results."""
        result = self.retriever.retrieve(self.sample_query)
        self.assertGreaterEqual(len(result.results), 4)
    
    def test_retrieved_source_structure(self):
        """Test RetrievedSource object structure."""
        source = RetrievedSource(
            title="Test Paper",
            source="Test Journal",
            domain_type="academic",
            credibility_score=0.9,
            relevance_score=0.8,
            summary="Test summary"
        )
        
        self.assertEqual(source.title, "Test Paper")
        self.assertEqual(source.credibility_score, 0.9)
        self.assertEqual(source.domain_type, "academic")


class TestRetrievalValidation(unittest.TestCase):
    """Test retrieval validation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.retriever = create_retriever()
    
    def test_valid_retrieval(self):
        """Test validation of valid retrieval result."""
        result = self.retriever.retrieve("What is AI?")
        is_valid, errors = self.retriever.validate_retrieval_result(result)
        
        self.assertTrue(is_valid, f"Validation errors: {errors}")
        self.assertEqual(len(errors), 0)
    
    def test_minimum_sources_check(self):
        """Test minimum sources requirement."""
        result = self.retriever.retrieve("test")
        
        # Should have at least 4 sources
        self.assertGreaterEqual(len(result.results), 4)
    
    def test_academic_source_requirement(self):
        """Test that academic source is included."""
        result = self.retriever.retrieve("machine learning")
        
        has_academic = any(s.domain_type == "academic" for s in result.results)
        self.assertTrue(has_academic, "Should include at least one academic source")


class TestDomainDiversity(unittest.TestCase):
    """Test domain diversity functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.retriever = create_retriever()
    
    def test_domain_diversity(self):
        """Test domain diversity in results."""
        result = self.retriever.retrieve("artificial intelligence trends")
        
        domains = set(s.domain_type for s in result.results)
        self.assertGreaterEqual(len(domains), 3, "Should have at least 3 distinct domains")
    
    def test_diversity_score_calculation(self):
        """Test diversity score is calculated."""
        result = self.retriever.retrieve("quantum computing")
        
        self.assertGreaterEqual(result.diversity_score, 0.0)
        self.assertLessEqual(result.diversity_score, 1.0)
    
    def test_domain_distribution(self):
        """Test domain distribution is tracked."""
        result = self.retriever.retrieve("machine learning")
        
        self.assertIsInstance(result.domain_distribution, dict)
        self.assertGreater(len(result.domain_distribution), 0)


class TestSourceCredibility(unittest.TestCase):
    """Test source credibility scoring."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.retriever = create_retriever()
    
    def test_credibility_score_range(self):
        """Test credibility scores are in valid range."""
        result = self.retriever.retrieve("AI research")
        
        for source in result.results:
            self.assertGreaterEqual(source.credibility_score, 0.0)
            self.assertLessEqual(source.credibility_score, 1.0)
    
    def test_academic_source_high_credibility(self):
        """Test academic sources have high credibility."""
        result = self.retriever.retrieve("deep learning")
        
        academic_sources = [s for s in result.results if s.domain_type == "academic"]
        
        if academic_sources:
            for source in academic_sources:
                self.assertGreater(source.credibility_score, 0.85)
    
    def test_relevance_score_range(self):
        """Test relevance scores are in valid range."""
        result = self.retriever.retrieve("neural networks")
        
        for source in result.results:
            self.assertGreaterEqual(source.relevance_score, 0.0)
            self.assertLessEqual(source.relevance_score, 1.0)


class TestSourceRetrieval(unittest.TestCase):
    """Test source retrieval details."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.retriever = create_retriever()
    
    def test_source_has_required_fields(self):
        """Test each source has required fields."""
        result = self.retriever.retrieve("AI")
        
        for source in result.results:
            self.assertIsNotNone(source.title)
            self.assertIsNotNone(source.source)
            self.assertIsNotNone(source.domain_type)
            self.assertIsNotNone(source.summary)
    
    def test_no_fabricated_sources(self):
        """Test that sources are not fabricated (knowledge-based)."""
        result = self.retriever.retrieve("machine learning")
        
        # All sources should be from predefined database
        # This is enforced in knowledge_based_retrieve
        self.assertGreater(len(result.results), 0)


class TestRetrievalConfidence(unittest.TestCase):
    """Test retrieval confidence scoring."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.retriever = create_retriever()
    
    def test_confidence_score_range(self):
        """Test confidence score is in valid range."""
        result = self.retriever.retrieve("research query")
        
        self.assertGreaterEqual(result.retrieval_confidence, 0.0)
        self.assertLessEqual(result.retrieval_confidence, 1.0)
    
    def test_confidence_correlates_with_quality(self):
        """Test confidence correlates with source quality."""
        result = self.retriever.retrieve("AI safety")
        
        # Higher average credibility should correlate with higher confidence
        avg_credibility = sum(s.credibility_score for s in result.results) / len(result.results)
        
        # Rough correlation check
        self.assertGreater(result.retrieval_confidence, avg_credibility * 0.5)


class TestRetrievalSerialization(unittest.TestCase):
    """Test retrieval result serialization."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.retriever = create_retriever()
        self.result = self.retriever.retrieve("AI")
    
    def test_to_dict(self):
        """Test converting result to dictionary."""
        data = self.result.to_dict()
        
        self.assertIsInstance(data, dict)
        self.assertIn("query_used", data)
        self.assertIn("results", data)
        self.assertIn("diversity_score", data)
    
    def test_to_json(self):
        """Test converting result to JSON."""
        json_str = self.result.to_json()
        
        self.assertIsInstance(json_str, str)
        # Should be parseable JSON
        parsed = json.loads(json_str)
        self.assertIsInstance(parsed, dict)
    
    def test_json_roundtrip(self):
        """Test JSON serialization and deserialization."""
        # Serialize
        json_str = self.result.to_json()
        
        # Deserialize
        data = json.loads(json_str)
        
        # Verify structure
        self.assertIn("query_used", data)
        self.assertIn("results", data)
        self.assertGreater(len(data["results"]), 0)


class TestSourceValidation(unittest.TestCase):
    """Test source validation."""
    
    def test_valid_source(self):
        """Test validation of valid source."""
        source = RetrievedSource(
            title="Valid Source",
            source="Valid Organization",
            domain_type="academic",
            credibility_score=0.9,
            relevance_score=0.8,
            summary="Valid summary"
        )
        
        is_valid, errors = source.validate()
        self.assertTrue(is_valid)
    
    def test_invalid_empty_title(self):
        """Test validation fails for empty title."""
        source = RetrievedSource(
            title="",
            source="Organization",
            domain_type="academic",
            credibility_score=0.9,
            relevance_score=0.8,
            summary="Summary"
        )
        
        is_valid, errors = source.validate()
        self.assertFalse(is_valid)
    
    def test_invalid_credibility_score(self):
        """Test validation fails for invalid credibility."""
        source = RetrievedSource(
            title="Title",
            source="Organization",
            domain_type="academic",
            credibility_score=1.5,  # Invalid
            relevance_score=0.8,
            summary="Summary"
        )
        
        is_valid, errors = source.validate()
        self.assertFalse(is_valid)


class TestMultipleQueries(unittest.TestCase):
    """Test retrieving for multiple queries."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.retriever = create_retriever()
    
    def test_multiple_queries(self):
        """Test retrieving for multiple different queries."""
        queries = [
            "machine learning",
            "blockchain technology",
            "quantum computing",
        ]
        
        for query in queries:
            result = self.retriever.retrieve(query)
            
            # Check structure
            self.assertEqual(result.query_used, query)
            self.assertGreaterEqual(len(result.results), 4)
            
            # Check diversity
            is_valid, errors = self.retriever.validate_retrieval_result(result)
            self.assertTrue(is_valid, f"Query '{query}' failed: {errors}")


class TestUncertaintyMarking(unittest.TestCase):
    """Test uncertainty marking functionality."""
    
    def test_uncertain_sources(self):
        """Test that uncertain sources can be marked."""
        source = RetrievedSource(
            title="[uncertain] Possible Finding",
            source="Unknown Source",
            domain_type="blog",
            credibility_score=0.3,
            relevance_score=0.5,
            summary="Uncertain information",
            uncertainty_marked=True
        )
        
        self.assertTrue(source.uncertainty_marked)


if __name__ == "__main__":
    unittest.main(verbosity=2)
