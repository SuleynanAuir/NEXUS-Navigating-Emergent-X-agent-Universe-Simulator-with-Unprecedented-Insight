"""
Unit tests for Uncertainty Quantifier Agent.

Tests cover:
- Confidence aggregation from multiple sources
- Disagreement variance measurement
- Hallucination risk estimation
- Global uncertainty computation
- Termination recommendations
- Evidence gap identification
- JSON serialization
"""

import unittest
from src.multi_agents.agents.uncertainty_quantifier_agent import (
    UncertaintyQuantifierAgent,
    UncertaintyQuantification,
    ConfidenceLevel,
    create_uncertainty_quantifier_agent,
)


class TestUncertaintyQuantifierAgent(unittest.TestCase):
    """Test Uncertainty Quantifier Agent."""

    def setUp(self):
        """Set up test fixtures."""
        self.agent = create_uncertainty_quantifier_agent(llm_client=None)

        self.sample_sources = [
            {
                "title": "Study A",
                "credibility_score": 0.8,
                "relevance_score": 0.85,
                "summary": "Finding X is significant",
                "publication_date": "2023-01-15",
                "domain_type": "academic",
            },
            {
                "title": "Study B",
                "credibility_score": 0.75,
                "relevance_score": 0.80,
                "summary": "Finding X is moderate",
                "publication_date": "2023-06-20",
                "domain_type": "industry",
            },
            {
                "title": "Study C",
                "credibility_score": 0.70,
                "relevance_score": 0.75,
                "summary": "Finding X is preliminary",
                "publication_date": "2022-12-01",
                "domain_type": "government",
            },
        ]

        self.sample_claims = [
            "Finding X exists",
            "Finding X is significant",
            "Finding X applies broadly",
        ]

    def test_agent_initialization(self):
        """Test agent initialization."""
        agent = create_uncertainty_quantifier_agent()
        self.assertIsNotNone(agent)
        self.assertIsNone(agent.llm_client)
        self.assertEqual(agent.model, "gpt-4")

    def test_agent_with_strict_mode(self):
        """Test agent with strict mode."""
        agent = create_uncertainty_quantifier_agent(strict_mode=True)
        self.assertTrue(agent.strict_mode)

    def test_basic_quantification(self):
        """Test basic uncertainty quantification."""
        result = self.agent.quantify(
            analysis_id="test_001",
            evidence_sources=self.sample_sources,
            claims=self.sample_claims,
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.analysis_id, "test_001")
        self.assertIsNotNone(result.aggregated_confidence)

    def test_aggregated_confidence_calculation(self):
        """Test confidence aggregation from multiple sources."""
        result = self.agent.quantify(
            analysis_id="test_conf",
            evidence_sources=self.sample_sources,
            claims=self.sample_claims,
        )

        # Confidence should be weighted average
        self.assertGreater(result.aggregated_confidence, 0.5)
        self.assertLess(result.aggregated_confidence, 1.0)

    def test_confidence_with_high_credibility_sources(self):
        """Test confidence aggregation with high credibility sources."""
        high_cred_sources = [
            {
                "title": "High Source",
                "credibility_score": 0.95,
                "relevance_score": 0.95,
                "summary": "Robust finding",
                "domain_type": "academic",
            },
            {
                "title": "Another High",
                "credibility_score": 0.90,
                "relevance_score": 0.90,
                "summary": "Robust finding",
                "domain_type": "industry",
            },
        ]

        result = self.agent.quantify(
            analysis_id="test_high_cred",
            evidence_sources=high_cred_sources,
            claims=self.sample_claims,
        )

        self.assertGreater(result.aggregated_confidence, 0.75)

    def test_confidence_with_low_credibility_sources(self):
        """Test confidence with low credibility sources."""
        low_cred_sources = [
            {
                "title": "Low Source",
                "credibility_score": 0.30,
                "relevance_score": 0.40,
                "summary": "Questionable finding",
                "domain_type": "unknown",
            },
        ]

        result = self.agent.quantify(
            analysis_id="test_low_cred",
            evidence_sources=low_cred_sources,
            claims=self.sample_claims,
        )

        self.assertLess(result.aggregated_confidence, 0.5)

    def test_confidence_level_classification(self):
        """Test confidence level classification."""
        # Very high
        level = self.agent._classify_confidence_level(0.9)
        self.assertEqual(level, ConfidenceLevel.VERY_HIGH)

        # High
        level = self.agent._classify_confidence_level(0.75)
        self.assertEqual(level, ConfidenceLevel.HIGH)

        # Moderate
        level = self.agent._classify_confidence_level(0.5)
        self.assertEqual(level, ConfidenceLevel.MODERATE)

        # Low
        level = self.agent._classify_confidence_level(0.35)
        self.assertEqual(level, ConfidenceLevel.LOW)

        # Very low
        level = self.agent._classify_confidence_level(0.15)
        self.assertEqual(level, ConfidenceLevel.VERY_LOW)

    def test_confidence_intervals(self):
        """Test confidence interval computation."""
        result = self.agent.quantify(
            analysis_id="test_intervals",
            evidence_sources=self.sample_sources,
            claims=self.sample_claims,
        )

        self.assertIn("lower_bound", result.confidence_intervals)
        self.assertIn("upper_bound", result.confidence_intervals)

        lower = result.confidence_intervals["lower_bound"]
        upper = result.confidence_intervals["upper_bound"]

        self.assertLess(lower, upper)
        self.assertGreaterEqual(lower, 0)
        self.assertLessEqual(upper, 1)

    def test_variance_score_with_low_disagreement(self):
        """Test variance score when sources agree."""
        similar_sources = [
            {
                "title": "Source 1",
                "credibility_score": 0.8,
                "relevance_score": 0.8,
                "summary": "Finding is significant",
                "domain_type": "academic",
            },
            {
                "title": "Source 2",
                "credibility_score": 0.81,
                "relevance_score": 0.79,
                "summary": "Finding is significant",
                "domain_type": "industry",
            },
        ]

        result = self.agent.quantify(
            analysis_id="test_low_var",
            evidence_sources=similar_sources,
            claims=self.sample_claims,
        )

        self.assertLess(result.variance_score, 0.4)

    def test_variance_score_with_high_disagreement(self):
        """Test variance score when sources disagree."""
        conflicting_sources = [
            {
                "title": "Source 1",
                "credibility_score": 0.8,
                "relevance_score": 0.8,
                "summary": "Finding is significant and positive",
                "domain_type": "academic",
            },
            {
                "title": "Source 2",
                "credibility_score": 0.75,
                "relevance_score": 0.75,
                "summary": "However, finding contradicts previous research",
                "domain_type": "industry",
            },
        ]

        result = self.agent.quantify(
            analysis_id="test_high_var",
            evidence_sources=conflicting_sources,
            claims=self.sample_claims,
        )

        self.assertGreater(result.variance_score, 0.3)

    def test_hallucination_risk_estimation(self):
        """Test hallucination risk estimation."""
        result = self.agent.quantify(
            analysis_id="test_halluc",
            evidence_sources=self.sample_sources,
            claims=self.sample_claims,
        )

        self.assertGreaterEqual(result.hallucination_risk, 0.0)
        self.assertLessEqual(result.hallucination_risk, 1.0)

    def test_hallucination_risk_with_small_sample(self):
        """Test hallucination risk with small sample."""
        small_sources = [
            {
                "title": "Single Source",
                "credibility_score": 0.8,
                "relevance_score": 0.8,
                "summary": "Finding X",
                "domain_type": "academic",
            },
        ]

        result = self.agent.quantify(
            analysis_id="test_small_sample",
            evidence_sources=small_sources,
            claims=self.sample_claims,
        )

        # Single source carries moderate risk
        self.assertGreater(result.hallucination_risk, 0.15)

    def test_hallucination_risk_with_methodological_concerns(self):
        """Test hallucination risk with methodological concerns."""
        concern_sources = [
            {
                "title": "Preliminary Study",
                "credibility_score": 0.6,
                "relevance_score": 0.7,
                "summary": "Preliminary finding with limited sample size",
                "domain_type": "academic",
            },
            {
                "title": "Another Study",
                "credibility_score": 0.65,
                "relevance_score": 0.7,
                "summary": "Small sample preliminary research",
                "domain_type": "industry",
            },
        ]

        result = self.agent.quantify(
            analysis_id="test_method_concern",
            evidence_sources=concern_sources,
            claims=self.sample_claims,
        )

        # With methodological concerns, risk should be elevated
        self.assertGreater(result.hallucination_risk, 0.20)

    def test_global_uncertainty_range(self):
        """Test global uncertainty is in valid range."""
        result = self.agent.quantify(
            analysis_id="test_global_unc",
            evidence_sources=self.sample_sources,
            claims=self.sample_claims,
        )

        self.assertGreaterEqual(result.global_uncertainty, 0.0)
        self.assertLessEqual(result.global_uncertainty, 1.0)

    def test_termination_recommendation_with_low_confidence(self):
        """Test termination recommendation with very low confidence."""
        low_conf_sources = [
            {
                "title": "Weak Source",
                "credibility_score": 0.2,
                "relevance_score": 0.3,
                "summary": "Uncertain finding",
                "domain_type": "unknown",
            },
        ]

        result = self.agent.quantify(
            analysis_id="test_low_conf_term",
            evidence_sources=low_conf_sources,
            claims=self.sample_claims,
        )

        # Should recommend termination with very low confidence
        if result.aggregated_confidence < 0.3:
            self.assertTrue(result.recommend_termination)

    def test_termination_recommendation_with_high_hallucination_risk(self):
        """Test termination with high hallucination risk."""
        risky_sources = [
            {
                "title": "Preliminary",
                "credibility_score": 0.4,
                "relevance_score": 0.5,
                "summary": "Preliminary finding limited sample",
                "domain_type": "academic",
            },
        ]

        result = self.agent.quantify(
            analysis_id="test_high_risk_term",
            evidence_sources=risky_sources,
            claims=self.sample_claims,
        )

        # Check if termination recommended when risk is high
        if result.hallucination_risk > 0.7:
            self.assertTrue(result.recommend_termination)

    def test_confidence_sufficient_for_publication(self):
        """Test publication readiness assessment."""
        result = self.agent.quantify(
            analysis_id="test_pub",
            evidence_sources=self.sample_sources,
            claims=self.sample_claims,
        )

        # Should have confidence_sufficient_for_publication flag
        self.assertIsNotNone(result.confidence_sufficient_for_publication)
        self.assertIsInstance(result.confidence_sufficient_for_publication, bool)

    def test_recommendations_generation(self):
        """Test recommendations are generated."""
        result = self.agent.quantify(
            analysis_id="test_recom",
            evidence_sources=self.sample_sources,
            claims=self.sample_claims,
        )

        self.assertIsInstance(result.recommendations, list)

    def test_uncertainty_sources_identified(self):
        """Test uncertainty sources are identified."""
        result = self.agent.quantify(
            analysis_id="test_unc_src",
            evidence_sources=self.sample_sources,
            claims=self.sample_claims,
        )

        self.assertIsInstance(result.uncertainty_sources, list)

    def test_evidence_gaps_identified(self):
        """Test evidence gaps are identified."""
        result = self.agent.quantify(
            analysis_id="test_gaps",
            evidence_sources=self.sample_sources,
            claims=self.sample_claims,
        )

        self.assertIsInstance(result.additional_evidence_needed, list)

    def test_variance_sources_identified(self):
        """Test variance sources are identified."""
        conflicting = [
            {
                "title": "Academic Study",
                "credibility_score": 0.9,
                "relevance_score": 0.85,
                "summary": "Positive quantitative findings",
                "publication_date": "2023-01-01",
                "domain_type": "academic",
            },
            {
                "title": "Industry Report",
                "credibility_score": 0.6,
                "relevance_score": 0.7,
                "summary": "However, qualitative research shows opposite",
                "publication_date": "2022-06-01",
                "domain_type": "industry",
            },
        ]

        result = self.agent.quantify(
            analysis_id="test_var_src",
            evidence_sources=conflicting,
            claims=self.sample_claims,
        )

        self.assertIsInstance(result.variance_sources, list)

    def test_hallucination_risk_factors_identified(self):
        """Test hallucination risk factors are identified."""
        result = self.agent.quantify(
            analysis_id="test_risk_factors",
            evidence_sources=self.sample_sources,
            claims=self.sample_claims,
        )

        self.assertIsInstance(result.hallucination_risk_factors, list)

    def test_termination_reason_explanation(self):
        """Test termination reason is explained."""
        low_sources = [
            {
                "title": "Very Low Quality",
                "credibility_score": 0.1,
                "relevance_score": 0.2,
                "summary": "Unreliable",
                "domain_type": "unknown",
            },
        ]

        result = self.agent.quantify(
            analysis_id="test_term_reason",
            evidence_sources=low_sources,
            claims=self.sample_claims,
        )

        if result.recommend_termination:
            self.assertIsNotNone(result.termination_reason)
            self.assertGreater(len(result.termination_reason), 0)

    def test_result_to_dict(self):
        """Test result conversion to dictionary."""
        result = self.agent.quantify(
            analysis_id="test_dict",
            evidence_sources=self.sample_sources,
            claims=self.sample_claims,
        )

        result_dict = result.to_dict()

        self.assertIsInstance(result_dict, dict)
        self.assertIn("analysis_id", result_dict)
        self.assertIn("aggregated_confidence", result_dict)
        self.assertIn("variance_score", result_dict)
        self.assertIn("hallucination_risk", result_dict)
        self.assertIn("global_uncertainty", result_dict)

    def test_result_to_json(self):
        """Test result conversion to JSON."""
        result = self.agent.quantify(
            analysis_id="test_json",
            evidence_sources=self.sample_sources,
            claims=self.sample_claims,
        )

        json_str = result.to_json()

        self.assertIsInstance(json_str, str)
        self.assertIn('"analysis_id"', json_str)
        self.assertIn('"aggregated_confidence"', json_str)

    def test_result_validation_valid(self):
        """Test validation of valid result."""
        result = self.agent.quantify(
            analysis_id="test_valid",
            evidence_sources=self.sample_sources,
            claims=self.sample_claims,
        )

        is_valid, errors = self.agent.validate_quantification(result)

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_result_validation_invalid_confidence(self):
        """Test validation catches invalid confidence."""
        result = self.agent.quantify(
            analysis_id="test_invalid",
            evidence_sources=self.sample_sources,
            claims=self.sample_claims,
        )

        # Artificially set invalid value
        result.aggregated_confidence = 1.5

        is_valid, errors = self.agent.validate_quantification(result)

        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)

    def test_with_custom_confidence_scores(self):
        """Test quantification with custom confidence scores."""
        custom_scores = [0.7, 0.75, 0.8]

        result = self.agent.quantify(
            analysis_id="test_custom_scores",
            evidence_sources=self.sample_sources,
            claims=self.sample_claims,
            confidence_scores=custom_scores,
        )

        self.assertIsNotNone(result.aggregated_confidence)
        self.assertGreater(result.aggregated_confidence, 0.5)

    def test_with_disagreement_indicators(self):
        """Test quantification with disagreement indicators."""
        disagreement = ["conflicting evidence", "methodological differences"]

        result = self.agent.quantify(
            analysis_id="test_disagreement",
            evidence_sources=self.sample_sources,
            claims=self.sample_claims,
            disagreement_indicators=disagreement,
        )

        self.assertIsNotNone(result.variance_score)

    def test_empty_sources_handling(self):
        """Test handling of empty evidence sources."""
        result = self.agent.quantify(
            analysis_id="test_empty",
            evidence_sources=[],
            claims=self.sample_claims,
        )

        self.assertIsNotNone(result)
        # Empty sources use default value
        self.assertEqual(result.aggregated_confidence, 0.5)

    def test_single_source_analysis(self):
        """Test analysis with single source."""
        single_source = [
            {
                "title": "Only Source",
                "credibility_score": 0.85,
                "relevance_score": 0.90,
                "summary": "Main finding",
                "domain_type": "academic",
            },
        ]

        result = self.agent.quantify(
            analysis_id="test_single",
            evidence_sources=single_source,
            claims=self.sample_claims,
        )

        self.assertIsNotNone(result.aggregated_confidence)
        # Lower variance with single source
        self.assertLess(result.variance_score, 0.3)


if __name__ == "__main__":
    unittest.main()
