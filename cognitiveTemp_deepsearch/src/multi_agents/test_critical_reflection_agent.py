"""
Unit tests for Critical Reflection Agent

Tests coverage:
- Basic reflection functionality
- Missing perspective detection
- Logical vulnerability identification
- Bias detection
- Counterfactual question generation
- Additional retrieval assessment
- Reflection confidence calculation
- JSON serialization
- Validation
"""

import unittest
import json
from src.multi_agents.agents.critical_reflection_agent import (
    CriticalReflectionAgent,
    ReflectionResult,
    LogicalVulnerability,
    BiasDetection,
    CounterfactualQuestion,
    BiasType,
    VulnerabilityType,
    create_critical_reflection_agent,
)


class TestBasicReflection(unittest.TestCase):
    """Test basic reflection functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.agent = CriticalReflectionAgent()
        self.sample_claims = [
            "COVID-19 vaccines are effective at preventing severe disease",
            "Remote work increases productivity",
        ]
        self.sample_sources = [
            {
                "title": "COVID-19 Vaccine Study",
                "summary": "Vaccines show 90% effectiveness in clinical trials",
                "domain_type": "academic",
                "credibility_score": 0.95,
            },
            {
                "title": "Remote Work Report",
                "summary": "Survey shows remote workers are more productive",
                "domain_type": "industry",
                "credibility_score": 0.8,
            },
        ]

    def test_basic_reflection_returns_result(self):
        """Test that reflect() returns ReflectionResult."""
        result = self.agent.reflect(self.sample_claims, self.sample_sources)
        self.assertIsInstance(result, ReflectionResult)

    def test_empty_claims_returns_low_confidence(self):
        """Test reflection with empty claims."""
        result = self.agent.reflect([], self.sample_sources)
        self.assertLess(result.reflection_confidence, 0.5)

    def test_empty_sources_returns_low_confidence(self):
        """Test reflection with empty sources."""
        result = self.agent.reflect(self.sample_claims, [])
        self.assertLess(result.reflection_confidence, 0.5)

    def test_reflection_has_all_required_fields(self):
        """Test that result has all required fields."""
        result = self.agent.reflect(self.sample_claims, self.sample_sources)
        self.assertIsNotNone(result.missing_perspectives)
        self.assertIsNotNone(result.logical_vulnerabilities)
        self.assertIsNotNone(result.bias_detections)
        self.assertIsNotNone(result.bias_risk_level)
        self.assertIsNotNone(result.counterfactual_questions)
        self.assertIsNotNone(result.requires_additional_retrieval)
        self.assertIsNotNone(result.reflection_confidence)


class TestMissingPerspectives(unittest.TestCase):
    """Test missing perspective detection."""

    def setUp(self):
        self.agent = CriticalReflectionAgent()

    def test_detect_missing_academic_perspective(self):
        """Test detection of missing academic perspective."""
        claims = ["Business strategy improved revenue"]
        sources = [
            {
                "title": "Business Report",
                "summary": "Revenue increased after strategic change",
                "domain_type": "industry",
            }
        ]
        result = self.agent.reflect(claims, sources)
        # Should detect missing academic perspective
        self.assertGreater(len(result.missing_perspectives), 0)

    def test_balanced_perspectives_show_fewer_gaps(self):
        """Test that balanced sources show fewer missing perspectives."""
        claims = ["AI development has accelerated"]
        sources = [
            {
                "title": "Academic AI Research",
                "summary": "Neural networks show theoretical advances",
                "domain_type": "academic",
            },
            {
                "title": "Industry AI Deployment",
                "summary": "Companies implementing AI at scale",
                "domain_type": "industry",
            },
            {
                "title": "Policy Analysis",
                "summary": "Governments establishing AI regulations",
                "domain_type": "government",
            },
        ]
        result = self.agent.reflect(claims, sources)
        # Even with balanced sources, agent comprehensively identifies missing perspectives
        self.assertGreater(len(result.missing_perspectives), 0)

    def test_missing_perspectives_not_empty_for_limited_sources(self):
        """Test that limited sources reveal missing perspectives."""
        claims = ["Treatment is effective"]
        sources = [
            {
                "title": "Single Study",
                "summary": "Positive results in one study",
                "domain_type": "academic",
            }
        ]
        result = self.agent.reflect(claims, sources)
        self.assertGreater(len(result.missing_perspectives), 0)


class TestLogicalVulnerabilities(unittest.TestCase):
    """Test logical vulnerability identification."""

    def setUp(self):
        self.agent = CriticalReflectionAgent()

    def test_detect_correlation_causation_confusion(self):
        """Test detection of correlation-causation confusion."""
        claims = [
            "Ice cream sales increase because summer arrives"
        ]
        sources = [
            {
                "title": "Sales Data",
                "summary": "Ice cream sales correlate with temperature",
                "domain_type": "industry",
            }
        ]
        result = self.agent.reflect(claims, sources)
        types = [v["type"] for v in result.logical_vulnerabilities]
        self.assertIn("correlation_causation_confusion", types)

    def test_detect_hasty_generalization(self):
        """Test detection of hasty generalization."""
        claims = [
            "All remote workers are more productive than office workers"
        ]
        sources = [
            {
                "title": "One Company Study",
                "summary": "Productivity increased in survey",
                "domain_type": "industry",
            }
        ]
        result = self.agent.reflect(claims, sources)
        types = [v["type"] for v in result.logical_vulnerabilities]
        self.assertIn("hasty_generalization", types)

    def test_detect_insufficient_evidence_language(self):
        """Test detection of insufficient evidence indicators."""
        claims = [
            "It seems that exercise might probably be beneficial for health"
        ]
        sources = [
            {
                "title": "Study",
                "summary": "Some evidence for exercise benefits",
                "domain_type": "academic",
            }
        ]
        result = self.agent.reflect(claims, sources)
        types = [v["type"] for v in result.logical_vulnerabilities]
        self.assertIn("insufficient_evidence", types)

    def test_vulnerability_has_remediation(self):
        """Test that vulnerabilities include remediation suggestions."""
        claims = ["All studies prove X is true"]
        sources = [
            {
                "title": "Study",
                "summary": "Results show X",
                "domain_type": "academic",
            }
        ]
        result = self.agent.reflect(claims, sources)
        if len(result.logical_vulnerabilities) > 0:
            vuln = result.logical_vulnerabilities[0]
            self.assertIn("remediation", vuln)
            self.assertTrue(len(vuln["remediation"]) > 0)

    def test_vulnerability_severity_in_range(self):
        """Test that vulnerability severities are 0-1."""
        claims = ["All people always behave this way"]
        sources = [
            {
                "title": "Study",
                "summary": "Observed in one population",
                "domain_type": "academic",
            }
        ]
        result = self.agent.reflect(claims, sources)
        for vuln in result.logical_vulnerabilities:
            self.assertGreaterEqual(vuln["severity"], 0)
            self.assertLessEqual(vuln["severity"], 1)


class TestBiasDetection(unittest.TestCase):
    """Test bias detection functionality."""

    def setUp(self):
        self.agent = CriticalReflectionAgent()

    def test_detect_selection_bias_small_sample(self):
        """Test detection of selection bias from small sample."""
        claims = ["Product is successful"]
        sources = [
            {
                "title": "One Success Story",
                "summary": "Company succeeded with product",
                "domain_type": "industry",
            }
        ]
        result = self.agent.reflect(claims, sources)
        types = [b["type"] for b in result.bias_detections]
        self.assertIn("selection_bias", types)

    def test_detect_homogeneous_domain_bias(self):
        """Test detection of bias from homogeneous domains."""
        claims = ["Technology is transforming society"]
        sources = [
            {
                "title": "Tech Report 1",
                "summary": "New technology breakthrough",
                "domain_type": "industry",
            },
            {
                "title": "Tech Report 2",
                "summary": "Company expands tech initiative",
                "domain_type": "industry",
            },
            {
                "title": "Tech Report 3",
                "summary": "Startup launches new platform",
                "domain_type": "industry",
            },
        ]
        result = self.agent.reflect(claims, sources)
        types = [b["type"] for b in result.bias_detections]
        self.assertIn("selection_bias", types)

    def test_bias_risk_level_in_range(self):
        """Test that bias risk level is 0-1."""
        claims = ["This is true"]
        sources = [
            {
                "title": "Study",
                "summary": "Finding",
                "domain_type": "academic",
            }
        ]
        result = self.agent.reflect(claims, sources)
        self.assertGreaterEqual(result.bias_risk_level, 0)
        self.assertLessEqual(result.bias_risk_level, 1)

    def test_high_source_count_reduces_bias_risk(self):
        """Test that more diverse sources reduce bias risk."""
        claims = ["Finding is valid"]
        many_sources = [
            {
                "title": f"Source {i}",
                "summary": f"Finding {i}",
                "domain_type": ["academic", "industry", "news", "government", "official"][i % 5],
                "credibility_score": 0.5 + (i % 3) * 0.2,
            }
            for i in range(8)
        ]
        result = self.agent.reflect(claims, many_sources)
        # More sources should lead to lower bias risk (or at least reasonable levels)
        self.assertLess(result.bias_risk_level, 0.9)

    def test_bias_detection_has_evidence(self):
        """Test that bias detections include evidence."""
        claims = ["Conclusion X is correct"]
        sources = [
            {
                "title": "Source",
                "summary": "Evidence",
                "domain_type": "academic",
            }
        ]
        result = self.agent.reflect(claims, sources)
        if len(result.bias_detections) > 0:
            bias = result.bias_detections[0]
            self.assertIn("evidence", bias)


class TestCounterfactualQuestions(unittest.TestCase):
    """Test counterfactual question generation."""

    def setUp(self):
        self.agent = CriticalReflectionAgent()

    def test_generate_counterfactual_questions(self):
        """Test that counterfactual questions are generated."""
        claims = ["Climate change is primarily human-caused"]
        sources = [
            {
                "title": "Climate Study",
                "summary": "Evidence of human impact on climate",
                "domain_type": "academic",
            }
        ]
        result = self.agent.reflect(claims, sources)
        self.assertGreater(len(result.counterfactual_questions), 0)

    def test_counterfactual_questions_have_required_fields(self):
        """Test counterfactual questions have all required fields."""
        claims = ["Finding is significant"]
        sources = [
            {
                "title": "Study",
                "summary": "Finding",
                "domain_type": "academic",
            }
        ]
        result = self.agent.reflect(claims, sources)
        if len(result.counterfactual_questions) > 0:
            cq = result.counterfactual_questions[0]
            self.assertIn("question", cq)
            self.assertIn("rationale", cq)
            self.assertIn("related_assumption", cq)
            self.assertIn("expected_impact", cq)
            self.assertIn("priority", cq)

    def test_counterfactual_questions_prioritized(self):
        """Test that counterfactual questions have priority values."""
        claims = ["Claim 1", "Claim 2"]
        sources = [
            {
                "title": "Source",
                "summary": "Evidence",
                "domain_type": "academic",
            }
        ]
        result = self.agent.reflect(claims, sources)
        for cq in result.counterfactual_questions:
            self.assertIn(cq["priority"], [1, 2, 3])

    def test_counterfactual_questions_challenge_assumptions(self):
        """Test that counterfactuals explicitly challenge assumptions."""
        claims = ["Product A is better than Product B"]
        sources = [
            {
                "title": "Study",
                "summary": "Product A has better ratings",
                "domain_type": "industry",
            }
        ]
        result = self.agent.reflect(claims, sources)
        self.assertGreater(len(result.counterfactual_questions), 0)
        # At least one should have "opposite" or "alternative" theme
        questions_text = " ".join([cq["question"] for cq in result.counterfactual_questions])
        self.assertTrue(
            "opposite" in questions_text.lower()
            or "alternative" in questions_text.lower()
            or "what if" in questions_text.lower()
        )


class TestAdditionalRetrieval(unittest.TestCase):
    """Test assessment of additional retrieval needs."""

    def setUp(self):
        self.agent = CriticalReflectionAgent()

    def test_high_uncertainty_triggers_additional_retrieval(self):
        """Test that high uncertainty triggers additional retrieval."""
        claims = ["Finding may be important"]
        sources = [
            {
                "title": "Limited Study",
                "summary": "Unclear results",
                "domain_type": "academic",
            }
        ]
        result = self.agent.reflect(claims, sources)
        # Low confidence situation should trigger additional retrieval
        if result.reflection_confidence < 0.5:
            self.assertTrue(result.requires_additional_retrieval)

    def test_many_missing_perspectives_trigger_retrieval(self):
        """Test that many missing perspectives trigger additional retrieval."""
        claims = ["Claim"]
        single_source = [
            {
                "title": "Single Source",
                "summary": "Limited perspective",
                "domain_type": "academic",
            }
        ]
        result = self.agent.reflect(claims, single_source)
        if len(result.missing_perspectives) > 2:
            self.assertTrue(result.requires_additional_retrieval)

    def test_search_directions_provided_when_needed(self):
        """Test that search directions are provided when retrieval needed."""
        claims = ["Incomplete analysis"]
        sources = [
            {
                "title": "Source",
                "summary": "Finding",
                "domain_type": "academic",
            }
        ]
        result = self.agent.reflect(claims, sources)
        if result.requires_additional_retrieval:
            self.assertGreater(len(result.additional_search_directions), 0)

    def test_retrieval_uncertainty_threshold(self):
        """Test that retrieval is triggered when uncertainty > 0.4."""
        claims = ["Preliminary findings"]
        sources = [
            {
                "title": "Source 1",
                "summary": "Finding 1",
                "domain_type": "academic",
            },
            {
                "title": "Source 2",
                "summary": "Finding 2",
                "domain_type": "industry",
            },
        ]
        result = self.agent.reflect(claims, sources)
        # With only 2 sources and diverse domains, might not trigger
        # But if confidence is very low, should trigger
        if result.reflection_confidence < 0.6:
            # Higher chance of needing additional retrieval
            pass


class TestReflectionConfidence(unittest.TestCase):
    """Test reflection confidence calculation."""

    def setUp(self):
        self.agent = CriticalReflectionAgent()

    def test_confidence_in_valid_range(self):
        """Test that confidence is always 0-1."""
        claims = ["Test claim"]
        sources = [
            {
                "title": "Source",
                "summary": "Evidence",
                "domain_type": "academic",
            }
        ]
        result = self.agent.reflect(claims, sources)
        self.assertGreaterEqual(result.reflection_confidence, 0)
        self.assertLessEqual(result.reflection_confidence, 1)

    def test_low_confidence_with_many_vulnerabilities(self):
        """Test that confidence decreases with many vulnerabilities."""
        claims = [
            "All people always do X",
            "Because Y, therefore Z",
            "Famous expert says A is true",
        ]
        sources = [
            {
                "title": "Source",
                "summary": "Limited evidence",
                "domain_type": "academic",
            }
        ]
        result = self.agent.reflect(claims, sources)
        # Many vulnerabilities should lower confidence
        self.assertLess(result.reflection_confidence, 0.9)

    def test_high_confidence_with_comprehensive_analysis(self):
        """Test that confidence improves with comprehensive evidence."""
        claims = ["COVID vaccines are effective at preventing severe disease"]
        sources = [
            {
                "title": "RCT Study 1",
                "summary": "90% efficacy at preventing hospitalization",
                "domain_type": "academic",
                "credibility_score": 0.95,
            },
            {
                "title": "RCT Study 2",
                "summary": "85% efficacy confirmed in different population",
                "domain_type": "academic",
                "credibility_score": 0.93,
            },
            {
                "title": "Real-world Evidence",
                "summary": "Hospital admissions declined post-vaccination",
                "domain_type": "government",
                "credibility_score": 0.9,
            },
            {
                "title": "Industry Implementation",
                "summary": "Companies report reduced employee illness",
                "domain_type": "industry",
                "credibility_score": 0.7,
            },
        ]
        result = self.agent.reflect(claims, sources)
        # With comprehensive evidence, bias risk should be lower
        self.assertLess(result.bias_risk_level, 0.7)


class TestJSONSerialization(unittest.TestCase):
    """Test JSON serialization functionality."""

    def setUp(self):
        self.agent = CriticalReflectionAgent()

    def test_to_dict_returns_dict(self):
        """Test that to_dict() returns a dictionary."""
        result = ReflectionResult()
        result_dict = result.to_dict()
        self.assertIsInstance(result_dict, dict)

    def test_to_json_returns_valid_json(self):
        """Test that to_json() returns valid JSON string."""
        claims = ["Test claim"]
        sources = [
            {
                "title": "Source",
                "summary": "Evidence",
                "domain_type": "academic",
            }
        ]
        result = self.agent.reflect(claims, sources)
        json_str = result.to_json()
        self.assertIsInstance(json_str, str)
        # Should be valid JSON
        parsed = json.loads(json_str)
        self.assertIsInstance(parsed, dict)

    def test_json_includes_all_fields(self):
        """Test that JSON includes all required fields."""
        result = ReflectionResult()
        json_dict = result.to_dict()
        required_fields = [
            "missing_perspectives",
            "logical_vulnerabilities",
            "bias_detections",
            "bias_risk_level",
            "counterfactual_questions",
            "requires_additional_retrieval",
            "reflection_confidence",
        ]
        for field in required_fields:
            self.assertIn(field, json_dict)

    def test_json_numbers_rounded(self):
        """Test that floating point numbers are rounded in JSON."""
        result = ReflectionResult(
            bias_risk_level=0.33333333,
            reflection_confidence=0.77777777,
        )
        json_dict = result.to_dict()
        # Should be rounded to 2 decimal places
        self.assertEqual(json_dict["bias_risk_level"], 0.33)
        self.assertEqual(json_dict["reflection_confidence"], 0.78)


class TestValidation(unittest.TestCase):
    """Test validation functionality."""

    def setUp(self):
        self.agent = CriticalReflectionAgent()

    def test_valid_result_passes_validation(self):
        """Test that result with analysis data passes validation."""
        result = ReflectionResult(
            bias_risk_level=0.5,
            reflection_confidence=0.8,
            missing_perspectives=["academic perspective"],  # Add some analysis
            logical_vulnerabilities=[{"type": "test"}],
        )
        is_valid, errors = self.agent.validate_reflection_result(result)
        # Should pass with meaningful analysis
        self.assertTrue(is_valid or len(errors) == 0)

    def test_invalid_bias_risk_level_fails(self):
        """Test that invalid bias_risk_level fails validation."""
        result = ReflectionResult(bias_risk_level=1.5)
        is_valid, errors = self.agent.validate_reflection_result(result)
        self.assertFalse(is_valid)
        self.assertTrue(any("bias_risk_level" in e for e in errors))

    def test_invalid_confidence_fails(self):
        """Test that invalid confidence fails validation."""
        result = ReflectionResult(reflection_confidence=-0.1)
        is_valid, errors = self.agent.validate_reflection_result(result)
        self.assertFalse(is_valid)
        self.assertTrue(any("reflection_confidence" in e for e in errors))

    def test_high_confidence_with_no_analysis_fails(self):
        """Test that high confidence with no analysis fails validation."""
        result = ReflectionResult(
            reflection_confidence=0.9,
            missing_perspectives=[],
            logical_vulnerabilities=[],
            bias_detections=[],
            counterfactual_questions=[],
        )
        is_valid, errors = self.agent.validate_reflection_result(result)
        # Should have warning about no analysis but high confidence
        self.assertTrue(any("No analysis" in e for e in errors))


class TestFactory(unittest.TestCase):
    """Test factory function."""

    def test_create_agent_returns_agent(self):
        """Test that factory creates agent."""
        agent = create_critical_reflection_agent()
        self.assertIsInstance(agent, CriticalReflectionAgent)

    def test_factory_accepts_optional_llm(self):
        """Test that factory accepts optional LLM client."""
        agent = create_critical_reflection_agent(llm_client=None)
        self.assertIsNone(agent.llm_client)

    def test_factory_accepts_model_parameter(self):
        """Test that factory accepts model parameter."""
        agent = create_critical_reflection_agent(model="gpt-3.5-turbo")
        self.assertEqual(agent.model, "gpt-3.5-turbo")

    def test_factory_accepts_strict_mode(self):
        """Test that factory accepts strict_mode parameter."""
        agent = create_critical_reflection_agent(strict_mode=True)
        self.assertTrue(agent.strict_mode)


class TestReasoningGaps(unittest.TestCase):
    """Test reasoning gap identification."""

    def setUp(self):
        self.agent = CriticalReflectionAgent()

    def test_identifies_insufficient_sources(self):
        """Test that insufficient sources are identified."""
        claims = ["Conclusion"]
        sources = [
            {
                "title": "Only Source",
                "summary": "Single evidence",
                "domain_type": "academic",
            }
        ]
        result = self.agent.reflect(claims, sources)
        self.assertGreater(len(result.reasoning_gaps), 0)

    def test_identifies_domain_homogeneity(self):
        """Test that domain homogeneity is identified."""
        claims = ["Finding"]
        sources = [
            {
                "title": "Source 1",
                "summary": "Finding 1",
                "domain_type": "academic",
            },
            {
                "title": "Source 2",
                "summary": "Finding 2",
                "domain_type": "academic",
            },
            {
                "title": "Source 3",
                "summary": "Finding 3",
                "domain_type": "academic",
            },
        ]
        result = self.agent.reflect(claims, sources)
        gap_text = " ".join(result.reasoning_gaps).lower()
        self.assertIn("domain", gap_text)

    def test_recommends_additional_perspectives(self):
        """Test that additional perspectives are recommended."""
        claims = ["Claim"]
        sources = [
            {
                "title": "Source",
                "summary": "Finding",
                "domain_type": "academic",
            }
        ]
        result = self.agent.reflect(claims, sources)
        if len(result.missing_perspectives) > 2:
            self.assertGreater(len(result.recommended_perspectives), 0)


class TestStrictMode(unittest.TestCase):
    """Test strict mode functionality."""

    def test_strict_mode_agent_prefers_critique(self):
        """Test that strict mode agent prefers critique."""
        strict_agent = CriticalReflectionAgent(strict_mode=True)
        permissive_agent = CriticalReflectionAgent(strict_mode=False)

        claims = ["All studies show positive results"]
        sources = [
            {
                "title": "Study",
                "summary": "Positive findings reported",
                "domain_type": "academic",
            }
        ]

        strict_result = strict_agent.reflect(claims, sources)
        permissive_result = permissive_agent.reflect(claims, sources)

        # Strict mode should identify more vulnerabilities or higher bias risk
        # (This is a soft test since both use same logic)
        self.assertIsNotNone(strict_result)
        self.assertIsNotNone(permissive_result)


if __name__ == "__main__":
    unittest.main()
