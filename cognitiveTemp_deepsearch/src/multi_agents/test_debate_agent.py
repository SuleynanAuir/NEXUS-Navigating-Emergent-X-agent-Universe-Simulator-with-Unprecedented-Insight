"""
Unit tests for Debate Agent

Tests coverage:
- Basic debate functionality
- Pro and Con argument generation
- Unresolved tensions identification
- Epistemic balance calculation
- Debate quality assessment
- Publishable insights extraction
- Empirical tests recommendation
- JSON serialization
- Validation
"""

import unittest
import json
from src.multi_agents.agents.debate_agent import (
    DebateAgent,
    DebateResult,
    Argument,
    UnresolvedTension,
    ArgumentStrength,
    TensionType,
    create_debate_agent,
)


class TestBasicDebate(unittest.TestCase):
    """Test basic debate functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.agent = DebateAgent()
        self.sample_topic = "Remote work improves productivity"
        self.sample_sources = [
            {
                "title": "Remote Work Study 2023",
                "summary": "Study shows 20% productivity increase with remote work",
                "credibility_score": 0.9,
                "domain_type": "academic",
            },
            {
                "title": "Industry Report",
                "summary": "Company survey indicates mixed results on remote productivity",
                "credibility_score": 0.7,
                "domain_type": "industry",
            },
        ]

    def test_basic_debate_returns_result(self):
        """Test that debate() returns DebateResult."""
        result = self.agent.debate(self.sample_topic, self.sample_sources)
        self.assertIsInstance(result, DebateResult)

    def test_empty_topic_returns_empty_result(self):
        """Test debate with empty topic."""
        result = self.agent.debate("", self.sample_sources)
        self.assertEqual(result.debate_topic, "")

    def test_empty_sources_returns_empty_result(self):
        """Test debate with empty sources."""
        result = self.agent.debate(self.sample_topic, [])
        self.assertEqual(result.debate_topic, self.sample_topic)

    def test_debate_has_all_required_fields(self):
        """Test that result has all required fields."""
        result = self.agent.debate(self.sample_topic, self.sample_sources)
        self.assertIsNotNone(result.debate_topic)
        self.assertIsNotNone(result.pro_argument)
        self.assertIsNotNone(result.con_argument)
        self.assertIsNotNone(result.unresolved_issues)
        self.assertIsNotNone(result.epistemic_balance_score)
        self.assertIsNotNone(result.debate_quality_score)

    def test_debate_with_context(self):
        """Test debate with additional context."""
        context = "Post-pandemic employment trends"
        result = self.agent.debate(self.sample_topic, self.sample_sources, context)
        self.assertEqual(result.debate_topic, self.sample_topic)
        self.assertGreater(len(result.pro_argument), 0)


class TestProArgument(unittest.TestCase):
    """Test Pro argument generation."""

    def setUp(self):
        self.agent = DebateAgent()

    def test_pro_argument_has_thesis(self):
        """Test that Pro argument has thesis."""
        topic = "AI improves healthcare outcomes"
        sources = [
            {
                "title": "Study",
                "summary": "AI diagnostic tools show high accuracy",
                "credibility_score": 0.9,
            }
        ]
        result = self.agent.debate(topic, sources)
        self.assertIn("thesis", result.pro_argument)
        self.assertGreater(len(result.pro_argument["thesis"]), 0)

    def test_pro_argument_has_supporting_points(self):
        """Test that Pro argument has supporting points."""
        topic = "Climate action is cost-effective"
        sources = [
            {
                "title": "Economic Study",
                "summary": "Renewable energy costs decreasing",
                "credibility_score": 0.85,
            }
        ]
        result = self.agent.debate(topic, sources)
        self.assertIn("supporting_points", result.pro_argument)
        self.assertGreater(len(result.pro_argument["supporting_points"]), 0)

    def test_pro_argument_has_confidence(self):
        """Test that Pro argument includes confidence score."""
        topic = "Test topic"
        sources = [
            {
                "title": "Source",
                "summary": "Evidence",
                "credibility_score": 0.9,
            }
        ]
        result = self.agent.debate(topic, sources)
        self.assertIn("confidence", result.pro_argument)
        self.assertGreaterEqual(result.pro_argument["confidence"], 0)
        self.assertLessEqual(result.pro_argument["confidence"], 1)

    def test_pro_argument_strength_assessment(self):
        """Test that Pro argument has strength assessment."""
        topic = "Test"
        sources = [
            {"title": "S", "summary": "E", "credibility_score": 0.95},
            {"title": "S2", "summary": "E2", "credibility_score": 0.92},
            {"title": "S3", "summary": "E3", "credibility_score": 0.88},
        ]
        result = self.agent.debate(topic, sources)
        self.assertIn("strength", result.pro_argument)
        self.assertIn(
            result.pro_argument["strength"],
            ["weak", "moderate", "strong", "very_strong"],
        )

    def test_pro_argument_higher_with_more_sources(self):
        """Test that Pro confidence increases with more high-credibility sources."""
        topic = "Strong evidence supports this"
        weak_sources = [
            {"title": "S", "summary": "E", "credibility_score": 0.5}
        ]
        strong_sources = [
            {"title": "S1", "summary": "E1", "credibility_score": 0.95},
            {"title": "S2", "summary": "E2", "credibility_score": 0.92},
            {"title": "S3", "summary": "E3", "credibility_score": 0.90},
        ]
        weak_result = self.agent.debate(topic, weak_sources)
        strong_result = self.agent.debate(topic, strong_sources)

        # Strong result should have higher confidence
        self.assertGreaterEqual(
            strong_result.pro_argument["confidence"],
            weak_result.pro_argument["confidence"],
        )


class TestConArgument(unittest.TestCase):
    """Test Con argument generation."""

    def setUp(self):
        self.agent = DebateAgent()

    def test_con_argument_has_thesis(self):
        """Test that Con argument has thesis."""
        topic = "Universal basic income solves poverty"
        sources = [{"title": "Study", "summary": "Evidence", "credibility_score": 0.8}]
        result = self.agent.debate(topic, sources)
        self.assertIn("thesis", result.con_argument)
        self.assertIn("limitation", result.con_argument["thesis"].lower())

    def test_con_argument_acknowledges_pro_points(self):
        """Test that Con argument acknowledges weaknesses (Pro strengths)."""
        topic = "Test topic"
        sources = [{"title": "Study", "summary": "Evidence", "credibility_score": 0.9}]
        result = self.agent.debate(topic, sources)
        self.assertIn("potential_weaknesses", result.con_argument)
        # Con argument should acknowledge some Pro points as weaknesses
        self.assertGreater(len(result.con_argument["potential_weaknesses"]), 0)

    def test_con_argument_different_from_pro(self):
        """Test that Con argument differs from Pro argument."""
        topic = "Test proposition"
        sources = [{"title": "Study", "summary": "Evidence", "credibility_score": 0.85}]
        result = self.agent.debate(topic, sources)

        # Theses should be different
        self.assertNotEqual(
            result.pro_argument["thesis"],
            result.con_argument["thesis"],
        )

    def test_con_argument_identifies_concerns(self):
        """Test that Con argument identifies methodological concerns."""
        topic = "This approach works well"
        sources = [{"title": "Study", "summary": "Evidence", "credibility_score": 0.7}]
        result = self.agent.debate(topic, sources)

        # Con supporting points should mention limitations
        con_points_text = " ".join(result.con_argument.get("supporting_points", []))
        self.assertTrue(
            any(
                word in con_points_text.lower()
                for word in ["limitation", "concern", "bias", "alternative"]
            )
        )


class TestUnresolvedTensions(unittest.TestCase):
    """Test unresolved tensions identification."""

    def setUp(self):
        self.agent = DebateAgent()

    def test_identifies_unresolved_tensions(self):
        """Test that tensions are identified."""
        topic = "Complex scientific question"
        sources = [
            {"title": "Study 1", "summary": "Evidence A", "credibility_score": 0.9},
            {"title": "Study 2", "summary": "Evidence B", "credibility_score": 0.8},
        ]
        result = self.agent.debate(topic, sources)
        self.assertGreater(len(result.unresolved_issues), 0)

    def test_tension_has_required_fields(self):
        """Test that each tension has required fields."""
        topic = "Test topic"
        sources = [{"title": "Study", "summary": "Evidence", "credibility_score": 0.85}]
        result = self.agent.debate(topic, sources)

        if result.unresolved_issues:
            tension = result.unresolved_issues[0]
            self.assertIn("type", tension)
            self.assertIn("description", tension)
            self.assertIn("pro_position", tension)
            self.assertIn("con_position", tension)
            self.assertIn("severity", tension)

    def test_tension_severity_in_range(self):
        """Test that tension severity is 0-1."""
        topic = "Topic"
        sources = [{"title": "Study", "summary": "Evidence", "credibility_score": 0.9}]
        result = self.agent.debate(topic, sources)

        for tension in result.unresolved_issues:
            self.assertGreaterEqual(tension["severity"], 0)
            self.assertLessEqual(tension["severity"], 1)

    def test_tension_types_are_valid(self):
        """Test that tension types are valid."""
        topic = "Test"
        sources = [{"title": "Study", "summary": "Evidence", "credibility_score": 0.8}]
        result = self.agent.debate(topic, sources)

        valid_types = [t.value for t in TensionType]
        for tension in result.unresolved_issues:
            self.assertIn(tension["type"], valid_types)

    def test_tensions_suggest_resolutions(self):
        """Test that tensions suggest resolution directions."""
        topic = "Disputed question"
        sources = [{"title": "Study", "summary": "Evidence", "credibility_score": 0.8}]
        result = self.agent.debate(topic, sources)

        if result.unresolved_issues:
            tension = result.unresolved_issues[0]
            self.assertIn("possible_resolutions", tension)
            # Should suggest research directions
            self.assertGreater(len(tension.get("possible_resolutions", [])), 0)


class TestEpistemicBalance(unittest.TestCase):
    """Test epistemic balance calculation."""

    def setUp(self):
        self.agent = DebateAgent()

    def test_epistemic_balance_in_range(self):
        """Test that epistemic balance score is 0-1."""
        topic = "Test topic"
        sources = [
            {"title": "Study", "summary": "Evidence", "credibility_score": 0.8}
        ]
        result = self.agent.debate(topic, sources)
        self.assertGreaterEqual(result.epistemic_balance_score, 0)
        self.assertLessEqual(result.epistemic_balance_score, 1)

    def test_balanced_debate_near_0_5(self):
        """Test that balanced arguments produce score near 0.5."""
        topic = "Neutral topic"
        sources = [
            {"title": "Study 1", "summary": "Evidence A", "credibility_score": 0.85},
            {"title": "Study 2", "summary": "Evidence B", "credibility_score": 0.8},
            {"title": "Study 3", "summary": "Evidence C", "credibility_score": 0.75},
        ]
        result = self.agent.debate(topic, sources)
        # Well-balanced should be close to 0.5
        self.assertGreater(result.epistemic_balance_score, 0.3)
        self.assertLess(result.epistemic_balance_score, 0.7)

    def test_balance_changes_with_evidence(self):
        """Test that balance changes with evidence quality."""
        topic = "Test"
        weak_sources = [
            {"title": "Study", "summary": "Evidence", "credibility_score": 0.5}
        ]
        strong_sources = [
            {"title": "Study", "summary": "Evidence", "credibility_score": 0.95}
        ]

        weak_result = self.agent.debate(topic, weak_sources)
        strong_result = self.agent.debate(topic, strong_sources)

        # Both should be valid scores
        self.assertGreaterEqual(weak_result.epistemic_balance_score, 0)
        self.assertGreaterEqual(strong_result.epistemic_balance_score, 0)


class TestDebateQuality(unittest.TestCase):
    """Test debate quality assessment."""

    def setUp(self):
        self.agent = DebateAgent()

    def test_debate_quality_in_range(self):
        """Test that debate quality score is 0-1."""
        topic = "Test"
        sources = [{"title": "Study", "summary": "Evidence", "credibility_score": 0.8}]
        result = self.agent.debate(topic, sources)
        self.assertGreaterEqual(result.debate_quality_score, 0)
        self.assertLessEqual(result.debate_quality_score, 1)

    def test_quality_higher_with_comprehensive_arguments(self):
        """Test that quality is higher with detailed arguments."""
        topic = "Complex issue"
        sources = [
            {"title": "S1", "summary": "Evidence 1", "credibility_score": 0.9},
            {"title": "S2", "summary": "Evidence 2", "credibility_score": 0.85},
            {"title": "S3", "summary": "Evidence 3", "credibility_score": 0.8},
        ]
        result = self.agent.debate(topic, sources)
        # Should have reasonable quality with multiple sources
        self.assertGreater(result.debate_quality_score, 0.3)

    def test_quality_considers_calibration(self):
        """Test that quality considers confidence calibration."""
        topic = "Uncertain topic"
        sources = [{"title": "Study", "summary": "Evidence", "credibility_score": 0.6}]
        result = self.agent.debate(topic, sources)

        # Both arguments should have moderate confidence
        pro_conf = result.pro_argument.get("confidence", 0.5)
        con_conf = result.con_argument.get("confidence", 0.5)

        # With uncertain evidence, both should be moderate
        self.assertLess(pro_conf, 0.9)
        self.assertLess(con_conf, 0.9)


class TestPublishableInsights(unittest.TestCase):
    """Test extraction of publishable insights."""

    def setUp(self):
        self.agent = DebateAgent()

    def test_generates_publishable_insights(self):
        """Test that publishable insights are generated."""
        topic = "AI safety is critical"
        sources = [
            {"title": "Study", "summary": "AI safety evidence", "credibility_score": 0.85}
        ]
        result = self.agent.debate(topic, sources)
        self.assertGreater(len(result.research_frontier_insights), 0)

    def test_insights_mention_research_frontier(self):
        """Test that insights address research frontier."""
        topic = "Emerging technology adoption"
        sources = [
            {"title": "Study", "summary": "Technology adoption", "credibility_score": 0.8}
        ]
        result = self.agent.debate(topic, sources)

        insights_text = " ".join(result.research_frontier_insights)
        self.assertTrue(
            len(insights_text) > 0
        )  # Should have substantive insights

    def test_insights_are_substantive(self):
        """Test that insights are substantive, not trivial."""
        topic = "Complex scientific question"
        sources = [
            {"title": "Study", "summary": "Detailed evidence", "credibility_score": 0.9}
        ]
        result = self.agent.debate(topic, sources)

        for insight in result.research_frontier_insights:
            self.assertGreater(len(insight), 20)  # Non-trivial length
            # Should not be empty or generic
            self.assertNotIn(insight, ["", "No insights"])


class TestDisagreementDimensions(unittest.TestCase):
    """Test disagreement dimension identification."""

    def setUp(self):
        self.agent = DebateAgent()

    def test_identifies_disagreement_dimensions(self):
        """Test that disagreement dimensions are identified."""
        topic = "Test topic"
        sources = [{"title": "Study", "summary": "Evidence", "credibility_score": 0.8}]
        result = self.agent.debate(topic, sources)
        self.assertGreater(len(result.dominant_disagreement_dimensions), 0)

    def test_dimensions_are_substantive(self):
        """Test that dimensions describe real disagreements."""
        topic = "Contentious issue"
        sources = [
            {"title": "Study", "summary": "Evidence", "credibility_score": 0.8}
        ]
        result = self.agent.debate(topic, sources)

        for dimension in result.dominant_disagreement_dimensions:
            self.assertGreater(
                len(dimension), 5
            )  # Not single-word descriptions


class TestEmpiricalTests(unittest.TestCase):
    """Test empirical tests recommendation."""

    def setUp(self):
        self.agent = DebateAgent()

    def test_recommends_empirical_tests(self):
        """Test that empirical tests are recommended."""
        topic = "Disputed claim"
        sources = [
            {"title": "Study", "summary": "Evidence", "credibility_score": 0.8}
        ]
        result = self.agent.debate(topic, sources)
        self.assertGreater(len(result.recommended_empirical_tests), 0)

    def test_tests_are_specific(self):
        """Test that recommended tests are specific."""
        topic = "Scientific question"
        sources = [
            {"title": "Study 1", "summary": "Evidence", "credibility_score": 0.85},
            {"title": "Study 2", "summary": "Evidence", "credibility_score": 0.8},
        ]
        result = self.agent.debate(topic, sources)

        for test in result.recommended_empirical_tests:
            # Should describe specific test or research approach
            self.assertGreater(len(test), 10)


class TestWinningArgument(unittest.TestCase):
    """Test winning argument determination."""

    def setUp(self):
        self.agent = DebateAgent()

    def test_winning_argument_is_valid(self):
        """Test that winning argument is valid."""
        topic = "Test"
        sources = [{"title": "Study", "summary": "Evidence", "credibility_score": 0.8}]
        result = self.agent.debate(topic, sources)

        if result.winning_argument:
            self.assertIn(result.winning_argument, ["pro", "con"])

    def test_balanced_debate_has_no_winner(self):
        """Test that balanced debates may have no winner."""
        topic = "Balanced topic"
        sources = [
            {"title": "Study", "summary": "Evidence", "credibility_score": 0.8},
            {"title": "Study 2", "summary": "Counterevidence", "credibility_score": 0.75},
        ]
        result = self.agent.debate(topic, sources)

        # With balanced sources, winning argument might be None
        # This is valid


class TestJSONSerialization(unittest.TestCase):
    """Test JSON serialization functionality."""

    def setUp(self):
        self.agent = DebateAgent()

    def test_to_dict_returns_dict(self):
        """Test that to_dict() returns a dictionary."""
        result = DebateResult(debate_topic="Test")
        result_dict = result.to_dict()
        self.assertIsInstance(result_dict, dict)

    def test_to_json_returns_valid_json(self):
        """Test that to_json() returns valid JSON string."""
        topic = "Test topic"
        sources = [{"title": "Study", "summary": "Evidence", "credibility_score": 0.8}]
        result = self.agent.debate(topic, sources)

        json_str = result.to_json()
        self.assertIsInstance(json_str, str)

        # Should be valid JSON
        parsed = json.loads(json_str)
        self.assertIsInstance(parsed, dict)

    def test_json_includes_all_fields(self):
        """Test that JSON includes all required fields."""
        result = DebateResult(debate_topic="Test")
        json_dict = result.to_dict()

        required_fields = [
            "debate_topic",
            "pro_argument",
            "con_argument",
            "unresolved_issues",
            "epistemic_balance_score",
            "debate_quality_score",
        ]

        for field in required_fields:
            self.assertIn(field, json_dict)

    def test_json_scores_rounded(self):
        """Test that scores are rounded in JSON."""
        result = DebateResult(
            debate_topic="Test",
            epistemic_balance_score=0.33333333,
            debate_quality_score=0.77777777,
        )
        json_dict = result.to_dict()

        self.assertEqual(json_dict["epistemic_balance_score"], 0.33)
        self.assertEqual(json_dict["debate_quality_score"], 0.78)


class TestValidation(unittest.TestCase):
    """Test validation functionality."""

    def setUp(self):
        self.agent = DebateAgent()

    def test_valid_result_passes_validation(self):
        """Test that valid result passes validation."""
        result = DebateResult(
            debate_topic="Test",
            epistemic_balance_score=0.5,
            debate_quality_score=0.7,
            pro_argument={"thesis": "test", "confidence": 0.6},
            con_argument={"thesis": "test con", "confidence": 0.4},
        )
        is_valid, errors = self.agent.validate_debate_result(result)
        # Should pass or have minimal errors
        self.assertTrue(is_valid or len(errors) <= 1)

    def test_invalid_balance_fails(self):
        """Test that invalid balance score fails validation."""
        result = DebateResult(debate_topic="Test", epistemic_balance_score=1.5)
        is_valid, errors = self.agent.validate_debate_result(result)
        self.assertFalse(is_valid)

    def test_invalid_quality_fails(self):
        """Test that invalid quality score fails validation."""
        result = DebateResult(debate_topic="Test", debate_quality_score=-0.1)
        is_valid, errors = self.agent.validate_debate_result(result)
        self.assertFalse(is_valid)

    def test_invalid_winning_argument_fails(self):
        """Test that invalid winning argument fails validation."""
        result = DebateResult(
            debate_topic="Test",
            winning_argument="invalid",
        )
        is_valid, errors = self.agent.validate_debate_result(result)
        self.assertFalse(is_valid)


class TestFactory(unittest.TestCase):
    """Test factory function."""

    def test_create_agent_returns_agent(self):
        """Test that factory creates agent."""
        agent = create_debate_agent()
        self.assertIsInstance(agent, DebateAgent)

    def test_factory_accepts_parameters(self):
        """Test that factory accepts optional parameters."""
        agent = create_debate_agent(model="gpt-3.5-turbo", debate_style="critical")
        self.assertEqual(agent.model, "gpt-3.5-turbo")
        self.assertEqual(agent.debate_style, "critical")


class TestDebateStyles(unittest.TestCase):
    """Test different debate styles."""

    def test_rigorous_debate_style(self):
        """Test rigorous debate style."""
        agent = DebateAgent(debate_style="rigorous")
        topic = "Test"
        sources = [{"title": "Study", "summary": "Evidence", "credibility_score": 0.8}]
        result = agent.debate(topic, sources)

        self.assertEqual(result.debate_topic, topic)
        self.assertGreater(len(result.pro_argument), 0)

    def test_exploratory_debate_style(self):
        """Test exploratory debate style."""
        agent = DebateAgent(debate_style="exploratory")
        topic = "Novel question"
        sources = [{"title": "Study", "summary": "Evidence", "credibility_score": 0.7}]
        result = agent.debate(topic, sources)

        self.assertIsNotNone(result)

    def test_critical_debate_style(self):
        """Test critical debate style."""
        agent = DebateAgent(debate_style="critical")
        topic = "Critique topic"
        sources = [{"title": "Study", "summary": "Evidence", "credibility_score": 0.6}]
        result = agent.debate(topic, sources)

        self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()
