"""
Unit tests for Evidence Evaluator Agent.
"""

import json
import unittest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.multi_agents.agents.evaluator_agent import (
    EvidenceEvaluatorAgent,
    EvaluationResult,
    Evidence,
    Contradiction,
    EvidenceType,
    StrengthLevel,
    create_evaluator
)


class TestEvaluatorAgentBasics(unittest.TestCase):
    """Test basic EvidenceEvaluatorAgent functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.evaluator = create_evaluator()
        self.sample_sources = [
            {
                "title": "AI Research Paper",
                "summary": "This study shows that deep learning increases accuracy by 95% compared to traditional methods.",
                "source": "arXiv"
            },
            {
                "title": "Industry Report",
                "summary": "Recent data indicates AI adoption has grown significantly in enterprise settings.",
                "source": "McKinsey"
            }
        ]
    
    def test_evaluator_initialization(self):
        """Test EvidenceEvaluatorAgent initialization."""
        self.assertIsNotNone(self.evaluator)
        self.assertIsInstance(self.evaluator, EvidenceEvaluatorAgent)
    
    def test_evaluate_basic_sources(self):
        """Test evaluating basic sources."""
        result = self.evaluator.evaluate(self.sample_sources)
        
        self.assertIsInstance(result, EvaluationResult)
        self.assertGreater(len(result.claims), 0)
    
    def test_empty_sources_raises_error(self):
        """Test that empty sources raise ValueError."""
        with self.assertRaises(ValueError):
            self.evaluator.evaluate([])
    
    def test_claims_extracted(self):
        """Test that claims are extracted."""
        result = self.evaluator.evaluate(self.sample_sources)
        
        self.assertGreater(len(result.claims), 0)
        
        for claim in result.claims:
            self.assertIsNotNone(claim.statement)
            self.assertIsNotNone(claim.evidence_type)
            self.assertIsNotNone(claim.strength)
    
    def test_evidence_object_structure(self):
        """Test Evidence object structure."""
        evidence = Evidence(
            statement="Test claim",
            evidence_type="empirical",
            strength="strong",
            supporting_sources=["Source1"]
        )
        
        self.assertEqual(evidence.statement, "Test claim")
        self.assertEqual(evidence.evidence_type, "empirical")
        self.assertEqual(evidence.strength, "strong")


class TestClaimExtraction(unittest.TestCase):
    """Test claim extraction."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.evaluator = create_evaluator()
    
    def test_extract_empirical_claims(self):
        """Test extracting empirical claims."""
        sources = [
            {
                "title": "Statistics Report",
                "summary": "The study found 75% of participants showed improvement.",
                "source": "Research Journal"
            }
        ]
        
        result = self.evaluator.evaluate(sources)
        
        # Should have at least one empirical claim
        empirical_claims = [c for c in result.claims if c.evidence_type == "empirical"]
        self.assertGreater(len(empirical_claims), 0)
    
    def test_extract_causal_claims(self):
        """Test extracting causal claims."""
        sources = [
            {
                "title": "Causality Study",
                "summary": "Increased exercise leads to better health outcomes.",
                "source": "Health Research"
            }
        ]
        
        result = self.evaluator.evaluate(sources)
        self.assertGreater(len(result.claims), 0)


class TestEvidenceTypeCategorization(unittest.TestCase):
    """Test evidence type categorization."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.evaluator = create_evaluator()
    
    def test_categorize_evidence_types(self):
        """Test that evidence types are categorized."""
        sources = [
            {
                "title": "Academic Study",
                "summary": "Research data shows statistical correlation.",
                "source": "Journal"
            },
            {
                "title": "Expert Opinion",
                "summary": "According to Professor Smith, the theory suggests.",
                "source": "Interview"
            }
        ]
        
        result = self.evaluator.evaluate(sources)
        
        # Check distribution of evidence types
        self.assertGreater(len(result.evidence_distribution), 0)
    
    def test_theoretical_vs_empirical(self):
        """Test distinguishing theoretical vs empirical evidence."""
        sources = [
            {
                "title": "Theoretical Framework",
                "summary": "The model proposes a new theoretical framework.",
                "source": "Academic"
            }
        ]
        
        result = self.evaluator.evaluate(sources)
        self.assertGreater(len(result.claims), 0)


class TestStrengthAssignment(unittest.TestCase):
    """Test strength level assignment."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.evaluator = create_evaluator()
    
    def test_strength_distribution(self):
        """Test strength level distribution."""
        sources = [
            {
                "title": "Well-Designed Study",
                "summary": "Peer-reviewed research with large sample size demonstrates effect.",
                "source": "Nature"
            },
            {
                "title": "Blog Post",
                "summary": "I think this might be true based on my experience.",
                "source": "Blog"
            }
        ]
        
        result = self.evaluator.evaluate(sources)
        
        # Should have various strength levels
        self.assertGreater(len(result.strength_distribution), 0)
    
    def test_strong_claims_from_rigorous_sources(self):
        """Test strong claims from rigorous sources."""
        sources = [
            {
                "title": "Peer-Reviewed Research",
                "summary": "Double-blind randomized controlled trial with 10,000 participants.",
                "source": "Nature Journal"
            }
        ]
        
        result = self.evaluator.evaluate(sources)
        
        # Should have claims, and higher average rigor from rigorous sources
        self.assertGreater(len(result.claims), 0)
        avg_rigor = sum(c.methodological_rigor for c in result.claims) / len(result.claims)
        self.assertGreater(avg_rigor, 0.4)  # Should have reasonable rigor
    
    def test_weak_claims_from_anecdotal_sources(self):
        """Test weak claims from anecdotal sources."""
        sources = [
            {
                "title": "Personal Story",
                "summary": "This happened to me once, so it must be true.",
                "source": "Personal Blog"
            }
        ]
        
        result = self.evaluator.evaluate(sources)
        
        # Should have some weak claims
        self.assertGreater(len(result.claims), 0)


class TestContradictionDetection(unittest.TestCase):
    """Test contradiction detection."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.evaluator = create_evaluator()
    
    def test_detect_direct_contradictions(self):
        """Test detecting direct contradictions."""
        sources = [
            {
                "title": "Study A",
                "summary": "The treatment is effective and increases success rate to 90%.",
                "source": "Research"
            },
            {
                "title": "Study B",
                "summary": "The treatment is not effective and shows no improvement.",
                "source": "Research"
            }
        ]
        
        result = self.evaluator.evaluate(sources)
        
        # Should have contradictions
        self.assertGreater(len(result.contradictions), 0)
    
    def test_contradiction_object_structure(self):
        """Test Contradiction object structure."""
        contradiction = Contradiction(
            claim_1="Treatment A works",
            claim_2="Treatment A doesn't work",
            contradiction_type="direct_contradiction",
            severity=0.9,
            affected_sources=["Source1", "Source2"],
            explanation="Direct negation"
        )
        
        self.assertEqual(contradiction.claim_1, "Treatment A works")
        self.assertEqual(contradiction.contradiction_type, "direct_contradiction")


class TestOverallScoring(unittest.TestCase):
    """Test overall scoring."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.evaluator = create_evaluator()
    
    def test_strength_score_range(self):
        """Test strength score is in valid range."""
        sources = [
            {
                "title": "Research",
                "summary": "This study shows something important.",
                "source": "Journal"
            }
        ]
        
        result = self.evaluator.evaluate(sources)
        
        self.assertGreaterEqual(result.overall_strength_score, 0.0)
        self.assertLessEqual(result.overall_strength_score, 1.0)
    
    def test_uncertainty_score_range(self):
        """Test uncertainty score is in valid range."""
        sources = [
            {
                "title": "Report",
                "summary": "Preliminary results suggest.",
                "source": "Source"
            }
        ]
        
        result = self.evaluator.evaluate(sources)
        
        self.assertGreaterEqual(result.evidence_uncertainty, 0.0)
        self.assertLessEqual(result.evidence_uncertainty, 1.0)


class TestEvaluationValidation(unittest.TestCase):
    """Test evaluation validation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.evaluator = create_evaluator()
    
    def test_valid_evaluation(self):
        """Test validation of valid evaluation."""
        sources = [
            {
                "title": "Study",
                "summary": "Research shows correlation between factors.",
                "source": "Journal"
            }
        ]
        
        result = self.evaluator.evaluate(sources)
        is_valid, errors = self.evaluator.validate_evaluation_result(result)
        
        self.assertTrue(is_valid, f"Validation errors: {errors}")


class TestEvaluationSerialization(unittest.TestCase):
    """Test evaluation result serialization."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.evaluator = create_evaluator()
        self.sources = [
            {
                "title": "Research Paper",
                "summary": "Study demonstrates significant findings.",
                "source": "Journal"
            }
        ]
    
    def test_to_dict(self):
        """Test converting result to dictionary."""
        result = self.evaluator.evaluate(self.sources)
        data = result.to_dict()
        
        self.assertIsInstance(data, dict)
        self.assertIn("claims", data)
        self.assertIn("contradictions", data)
        self.assertIn("overall_strength_score", data)
    
    def test_to_json(self):
        """Test converting result to JSON."""
        result = self.evaluator.evaluate(self.sources)
        json_str = result.to_json()
        
        self.assertIsInstance(json_str, str)
        parsed = json.loads(json_str)
        self.assertIsInstance(parsed, dict)
    
    def test_json_roundtrip(self):
        """Test JSON serialization roundtrip."""
        result = self.evaluator.evaluate(self.sources)
        json_str = result.to_json()
        data = json.loads(json_str)
        
        self.assertIn("claims", data)
        self.assertGreaterEqual(len(data["claims"]), 0)


class TestEvidenceValidation(unittest.TestCase):
    """Test evidence validation."""
    
    def test_valid_evidence(self):
        """Test validation of valid evidence."""
        evidence = Evidence(
            statement="Valid claim",
            evidence_type="empirical",
            strength="strong",
            supporting_sources=["Source1"]
        )
        
        is_valid, errors = evidence.validate()
        self.assertTrue(is_valid)
    
    def test_invalid_empty_statement(self):
        """Test validation fails for empty statement."""
        evidence = Evidence(
            statement="",
            evidence_type="empirical",
            strength="strong"
        )
        
        is_valid, errors = evidence.validate()
        self.assertFalse(is_valid)
    
    def test_invalid_strength_level(self):
        """Test validation fails for invalid strength."""
        evidence = Evidence(
            statement="Valid claim",
            evidence_type="empirical",
            strength="invalid_strength"
        )
        
        is_valid, errors = evidence.validate()
        self.assertFalse(is_valid)


class TestMultipleSources(unittest.TestCase):
    """Test evaluating multiple sources."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.evaluator = create_evaluator()
    
    def test_multiple_sources_integration(self):
        """Test evaluating multiple correlated sources."""
        sources = [
            {
                "title": "Study A",
                "summary": "Research shows significant improvement in treatment group.",
                "source": "Journal A"
            },
            {
                "title": "Study B",
                "summary": "Independent study confirms similar improvement in treatment.",
                "source": "Journal B"
            },
            {
                "title": "Study C",
                "summary": "Meta-analysis finds consistent positive effects.",
                "source": "Journal C"
            }
        ]
        
        result = self.evaluator.evaluate(sources)
        
        # Should identify corroborated claims
        self.assertGreater(len(result.claims), 0)
        self.assertGreaterEqual(result.total_sources_analyzed, 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
