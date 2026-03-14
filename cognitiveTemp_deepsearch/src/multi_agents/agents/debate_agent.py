"""
Debate Agent - Structured Adversarial Reasoning for Publishable Insights

This agent simulates structured debate between two analytical positions to:
- Generate compelling Pro arguments
- Generate compelling Con arguments
- Identify unresolved tensions
- Estimate epistemic balance

Objective: Simulate adversarial reasoning that could generate publishable insights
through rigorous debate between opposing viewpoints.
"""

import json
import re
import logging
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, List, Dict, Tuple, Set
from collections import Counter, defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ArgumentStrength(Enum):
    """Enumeration of argument strength levels."""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


class TensionType(Enum):
    """Enumeration of unresolved tension types."""
    EMPIRICAL = "empirical_contradiction"
    THEORETICAL = "theoretical_conflict"
    METHODOLOGICAL = "methodological_difference"
    SCOPE = "scope_disagreement"
    TEMPORAL = "temporal_mismatch"
    VALUE = "value_judgment_difference"
    CAUSAL = "causal_mechanism_dispute"
    INTERPRETATION = "interpretation_difference"
    DATA_QUALITY = "data_quality_concern"
    ASSUMPTION = "assumption_divergence"


@dataclass
class Argument:
    """Represents a single argument in the debate."""
    position: str  # "pro" or "con"
    thesis: str = ""  # Main claim
    supporting_points: List[str] = field(default_factory=list)  # Key arguments
    evidence_summary: str = ""  # Summary of supporting evidence
    assumptions: List[str] = field(default_factory=list)  # Underlying assumptions
    logical_structure: str = ""  # Explanation of logical flow
    strength_assessment: ArgumentStrength = ArgumentStrength.MODERATE
    confidence_score: float = 0.5  # 0-1
    potential_weaknesses: List[str] = field(default_factory=list)  # Acknowledged weaknesses

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "position": self.position,
            "thesis": self.thesis,
            "supporting_points": self.supporting_points,
            "evidence_summary": self.evidence_summary,
            "assumptions": self.assumptions,
            "logical_structure": self.logical_structure,
            "strength": self.strength_assessment.value,
            "confidence": round(self.confidence_score, 2),
            "potential_weaknesses": self.potential_weaknesses,
        }


@dataclass
class UnresolvedTension:
    """Represents an unresolved tension between Pro and Con arguments."""
    tension_type: TensionType
    description: str  # What the tension is about
    pro_position: str  # How Pro side sees it
    con_position: str  # How Con side sees it
    severity_score: float = 0.5  # 0-1, how critical is this tension
    possible_resolution_directions: List[str] = field(default_factory=list)
    requires_further_research: bool = True

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "type": self.tension_type.value,
            "description": self.description,
            "pro_position": self.pro_position,
            "con_position": self.con_position,
            "severity": round(self.severity_score, 2),
            "possible_resolutions": self.possible_resolution_directions,
            "requires_research": self.requires_further_research,
        }


@dataclass
class DebateResult:
    """Main output structure for structured debate."""
    debate_topic: str
    pro_argument: Dict = field(default_factory=dict)
    con_argument: Dict = field(default_factory=dict)
    unresolved_issues: List[Dict] = field(default_factory=list)
    epistemic_balance_score: float = 0.5  # 0-1, how balanced is the debate
    winning_argument: Optional[str] = None  # "pro", "con", or None for balanced
    debate_quality_score: float = 0.5  # 0-1, quality of arguments
    research_frontier_insights: List[str] = field(default_factory=list)  # Publishable insights
    dominant_disagreement_dimensions: List[str] = field(default_factory=list)
    recommended_empirical_tests: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "debate_topic": self.debate_topic,
            "pro_argument": self.pro_argument,
            "con_argument": self.con_argument,
            "unresolved_issues": self.unresolved_issues,
            "epistemic_balance_score": round(self.epistemic_balance_score, 2),
            "winning_argument": self.winning_argument,
            "debate_quality_score": round(self.debate_quality_score, 2),
            "research_frontier_insights": self.research_frontier_insights,
            "dominant_disagreement_dimensions": self.dominant_disagreement_dimensions,
            "recommended_empirical_tests": self.recommended_empirical_tests,
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


class DebateAgent:
    """
    Debate Agent - Structured Adversarial Reasoning for Publishable Insights.

    This agent simulates structured debate between two opposing analytical positions
    to generate publishable insights through rigorous examination of both sides.

    Key Features:
    - Generates compelling Pro and Con arguments
    - Identifies unresolved tensions between positions
    - Estimates epistemic balance (fairness of debate)
    - Highlights publishable research frontier insights
    - Recommends empirical tests to resolve disagreements
    - Assesses argument quality and strength
    """

    # Common debate framings
    DEBATE_TEMPLATES = {
        "validity": {
            "pro_framing": "The claim/approach is fundamentally valid",
            "con_framing": "The claim/approach has fundamental flaws",
        },
        "effectiveness": {
            "pro_framing": "The intervention/method is effective",
            "con_framing": "The intervention/method is ineffective",
        },
        "scalability": {
            "pro_framing": "The approach is scalable",
            "con_framing": "The approach has fundamental scalability limits",
        },
        "relevance": {
            "pro_framing": "The finding is highly relevant and generalizable",
            "con_framing": "The finding is limited in scope and relevance",
        },
    }

    # Pro argument generators (patterns and themes)
    PRO_ARGUMENT_THEMES = [
        "Empirical evidence shows positive results",
        "Theoretical mechanisms are well-established",
        "Practical applications demonstrate success",
        "Recent advances overcome previous limitations",
        "Multiple independent lines of evidence converge",
        "The approach aligns with established principles",
    ]

    # Con argument generators
    CON_ARGUMENT_THEMES = [
        "Methodological limitations undermine conclusions",
        "Alternative explanations are overlooked",
        "Generalization claims exceed available evidence",
        "Theoretical assumptions are questionable",
        "Previous failures suggest inherent limitations",
        "High-risk factors are underestimated",
    ]

    def __init__(
        self,
        llm_client: Optional[object] = None,
        model: str = "gpt-4",
        debate_style: str = "rigorous",  # rigorous, exploratory, critical
    ):
        """
        Initialize Debate Agent.

        Args:
            llm_client: Optional LLM client
            model: LLM model name
            debate_style: Style of debate (rigorous, exploratory, critical)
        """
        self.llm_client = llm_client
        self.model = model
        self.debate_style = debate_style
        logger.info(f"Initialized Debate Agent (style={debate_style})")

    def debate(
        self,
        topic: str,
        evidence_sources: List[Dict],
        context: Optional[str] = None,
    ) -> DebateResult:
        """
        Conduct structured debate on a topic.

        Args:
            topic: The topic to debate
            evidence_sources: List of evidence sources to inform debate
            context: Optional context/background information

        Returns:
            DebateResult with Pro/Con arguments and tensions
        """
        logger.info(f"Initiating debate on: {topic}")

        if not topic or not evidence_sources:
            return DebateResult(debate_topic=topic)

        if self.llm_client is not None:
            return self._llm_debate(topic, evidence_sources, context)

        return self._local_debate(topic, evidence_sources, context)

    def _local_debate(
        self,
        topic: str,
        evidence_sources: List[Dict],
        context: Optional[str] = None,
    ) -> DebateResult:
        """Local debate strategy without LLM."""
        logger.info("No LLM client provided. Using local debate strategy.")

        result = DebateResult(debate_topic=topic)

        # Step 1: Generate Pro argument
        pro_arg = self._generate_pro_argument(topic, evidence_sources, context)
        result.pro_argument = pro_arg.to_dict()

        # Step 2: Generate Con argument
        con_arg = self._generate_con_argument(topic, evidence_sources, context)
        result.con_argument = con_arg.to_dict()

        # Step 3: Identify unresolved tensions
        tensions = self._identify_tensions(pro_arg, con_arg, evidence_sources)
        result.unresolved_issues = [t.to_dict() for t in tensions]

        # Step 4: Calculate epistemic balance
        result.epistemic_balance_score = self._calculate_epistemic_balance(
            pro_arg, con_arg, tensions
        )

        # Step 5: Determine winning argument (if any)
        result.winning_argument = self._determine_winner(pro_arg, con_arg)

        # Step 6: Assess debate quality
        result.debate_quality_score = self._assess_debate_quality(pro_arg, con_arg)

        # Step 7: Extract publishable insights
        result.research_frontier_insights = self._extract_publishable_insights(
            pro_arg, con_arg, tensions
        )

        # Step 8: Identify disagreement dimensions
        result.dominant_disagreement_dimensions = self._identify_disagreement_dimensions(
            pro_arg, con_arg
        )

        # Step 9: Recommend empirical tests
        result.recommended_empirical_tests = self._recommend_empirical_tests(
            tensions, result.dominant_disagreement_dimensions
        )

        return result

    def _llm_debate(
        self,
        topic: str,
        evidence_sources: List[Dict],
        context: Optional[str] = None,
    ) -> DebateResult:
        """LLM-based debate strategy."""
        logger.info("Using LLM-based debate strategy.")

        prompt = self._build_debate_prompt(topic, evidence_sources, context)

        try:
            response = self.llm_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                response_format={"type": "json_object"},
            )

            debate_json = json.loads(response.choices[0].message.content)
            return self._parse_debate_response(topic, debate_json)

        except Exception as e:
            logger.warning(f"LLM debate failed: {e}. Falling back to local strategy.")
            return self._local_debate(topic, evidence_sources, context)

    def _build_debate_prompt(
        self,
        topic: str,
        evidence_sources: List[Dict],
        context: Optional[str] = None,
    ) -> str:
        """Build prompt for LLM debate."""
        sources_text = "\n".join([
            f"- {s.get('title', 'Unknown')}: {s.get('summary', '')[:100]}"
            for s in evidence_sources[:5]
        ])

        prompt = f"""You are a debate moderator. Conduct a structured debate on this topic:

TOPIC: {topic}

{f"CONTEXT: {context}" if context else ""}

EVIDENCE SOURCES:
{sources_text}

Generate a rigorous debate with:
1. Pro argument (thesis, supporting points, evidence, assumptions, acknowledged weaknesses)
2. Con argument (thesis, supporting points, evidence, assumptions, acknowledged weaknesses)
3. Unresolved tensions between the positions
4. Epistemic balance assessment (0-1)

Respond in strict JSON format with these fields:
{{
  "pro_argument": {{
    "thesis": "...",
    "supporting_points": [...],
    "evidence_summary": "...",
    "assumptions": [...],
    "strength": "weak|moderate|strong|very_strong",
    "confidence": 0-1,
    "weaknesses": [...]
  }},
  "con_argument": {{ ... same structure ... }},
  "unresolved_issues": [
    {{
      "type": "...",
      "description": "...",
      "severity": 0-1
    }}
  ],
  "epistemic_balance_score": 0-1,
  "winning_argument": "pro|con|null",
  "debate_quality_score": 0-1,
  "research_frontier_insights": [...]
}}

Be rigorous and identify genuine tensions."""

        return prompt

    def _generate_pro_argument(
        self,
        topic: str,
        evidence_sources: List[Dict],
        context: Optional[str] = None,
    ) -> Argument:
        """Generate Pro argument for the topic."""
        arg = Argument(position="pro")

        # Extract supporting information from sources
        summaries = " ".join([s.get("summary", "") for s in evidence_sources])

        # Determine thesis based on topic and evidence
        arg.thesis = f"The proposition '{topic}' is fundamentally sound and well-supported by evidence."

        # Generate supporting points
        if "effective" in topic.lower() or "successful" in topic.lower():
            arg.supporting_points = [
                "Empirical evidence demonstrates positive outcomes",
                "Multiple independent studies show consistent results",
                "Practical implementation validates theoretical predictions",
                "Comparison with alternatives shows relative advantage",
            ]
        else:
            arg.supporting_points = [
                "Theoretical framework is logically coherent",
                "Evidence converges on supporting conclusions",
                "Underlying mechanisms are well-established",
                "Generalization is supported by diverse contexts",
            ]

        # Evidence summary from sources
        high_credibility_sources = [
            s for s in evidence_sources if s.get("credibility_score", 0) > 0.8
        ]
        arg.evidence_summary = f"Based on {len(high_credibility_sources)} high-credibility sources showing consistent support"

        # Extract assumptions
        if "general" in topic.lower() or "all" in topic.lower():
            arg.assumptions = [
                "The phenomenon generalizes across contexts",
                "Underlying mechanisms are universal",
            ]
        else:
            arg.assumptions = [
                "Relevant variables have been identified",
                "Evidence quality is sufficient for conclusions",
            ]

        # Strength assessment
        if len(high_credibility_sources) >= 3:
            arg.strength_assessment = ArgumentStrength.STRONG
            arg.confidence_score = 0.75
        else:
            arg.strength_assessment = ArgumentStrength.MODERATE
            arg.confidence_score = 0.55

        # Acknowledged weaknesses
        arg.potential_weaknesses = [
            "Sample sizes may be limited in some studies",
            "Alternative mechanisms not fully ruled out",
            "Long-term effects remain uncertain",
        ]

        arg.logical_structure = "Evidence → Supporting conclusions → General principle"

        return arg

    def _generate_con_argument(
        self,
        topic: str,
        evidence_sources: List[Dict],
        context: Optional[str] = None,
    ) -> Argument:
        """Generate Con argument for the topic."""
        arg = Argument(position="con")

        # Determine thesis based on topic
        arg.thesis = f"The proposition '{topic}' has fundamental limitations and is not universally supported."

        # Generate counter-points
        arg.supporting_points = [
            "Methodological limitations in supporting studies",
            "Selection bias in evidence sources",
            "Alternative explanations for observed patterns",
            "Contradictory evidence is underweighted",
            "Generalization claims exceed the data",
        ]

        # Evidence summary - emphasize limitations
        low_credibility_sources = [
            s for s in evidence_sources if s.get("credibility_score", 0) < 0.7
        ]
        if low_credibility_sources:
            arg.evidence_summary = f"Some sources ({len(low_credibility_sources)}) have credibility concerns, and counterevidence is often overlooked"
        else:
            arg.evidence_summary = "Even strong evidence may reflect specific contexts rather than universal principles"

        # Counter-assumptions
        arg.assumptions = [
            "Evidence selection may be biased toward supporting evidence",
            "Confounding variables are inadequately controlled",
            "Publication bias affects which results are visible",
        ]

        # Strength assessment - typically more moderate for con
        arg.strength_assessment = ArgumentStrength.MODERATE
        if len(low_credibility_sources) > 0:
            arg.confidence_score = 0.65
        else:
            arg.confidence_score = 0.50

        # Acknowledged weaknesses
        arg.potential_weaknesses = [
            "Some evidence does support the proposition",
            "May be overly skeptical of positive findings",
            "Real benefits may exist in specific contexts",
        ]

        arg.logical_structure = "Limitations identified → Alternative explanations → Scope restrictions"

        return arg

    def _identify_tensions(
        self,
        pro_arg: Argument,
        con_arg: Argument,
        evidence_sources: List[Dict],
    ) -> List[UnresolvedTension]:
        """Identify unresolved tensions between Pro and Con arguments."""
        tensions = []

        # Tension 1: Generalization vs. Contextualization
        tensions.append(UnresolvedTension(
            tension_type=TensionType.SCOPE,
            description="Whether findings generalize universally or are context-dependent",
            pro_position=f"{pro_arg.supporting_points[0] if pro_arg.supporting_points else 'Findings are universal'}",
            con_position="Findings are limited to specific contexts",
            severity_score=0.7,
            possible_resolution_directions=[
                "Multi-context replication studies",
                "Mechanism identification to explain boundary conditions",
                "Population sampling across diverse groups",
            ],
            requires_further_research=True,
        ))

        # Tension 2: Methodological concerns
        tensions.append(UnresolvedTension(
            tension_type=TensionType.METHODOLOGICAL,
            description="Whether supporting evidence has adequate methodological rigor",
            pro_position="Methodology is sound and conclusions are valid",
            con_position="Methodological limitations undermine confidence",
            severity_score=0.65,
            possible_resolution_directions=[
                "Pre-registered replication studies",
                "Methodological critique and response",
                "Independent verification by skeptical researchers",
            ],
            requires_further_research=True,
        ))

        # Tension 3: Mechanism vs. Pattern
        tensions.append(UnresolvedTension(
            tension_type=TensionType.THEORETICAL,
            description="Whether observed patterns reflect true mechanisms or statistical artifacts",
            pro_position="Underlying mechanisms explain the pattern",
            con_position="Alternative mechanisms could produce same pattern",
            severity_score=0.60,
            possible_resolution_directions=[
                "Direct mechanism testing",
                "Causal inference studies",
                "Experimental manipulation of proposed mechanism",
            ],
            requires_further_research=True,
        ))

        # Tension 4: Evidence strength
        if len(evidence_sources) < 4:
            tensions.append(UnresolvedTension(
                tension_type=TensionType.EMPIRICAL,
                description="Whether available evidence is sufficient for strong conclusions",
                pro_position="Existing evidence is sufficient",
                con_position="Evidence base is too limited",
                severity_score=0.55,
                possible_resolution_directions=[
                    "Additional empirical studies",
                    "Meta-analysis of existing evidence",
                    "Large-scale replication efforts",
                ],
                requires_further_research=True,
            ))

        # Tension 5: Publication bias
        tensions.append(UnresolvedTension(
            tension_type=TensionType.DATA_QUALITY,
            description="Whether selection bias affects which evidence is visible",
            pro_position="Published evidence is representative",
            con_position="Publication bias skews available evidence",
            severity_score=0.50,
            possible_resolution_directions=[
                "Analysis of unpublished/grey literature",
                "Study registry review for unreported results",
                "Assessment of effect size patterns",
            ],
            requires_further_research=True,
        ))

        return tensions[:5]  # Return top 5 tensions

    def _calculate_epistemic_balance(
        self,
        pro_arg: Argument,
        con_arg: Argument,
        tensions: List[UnresolvedTension],
    ) -> float:
        """Calculate epistemic balance of the debate (0-1, 0.5 = perfectly balanced)."""
        # Start at 0.5 (balanced)
        balance = 0.5

        # Adjust based on argument strengths
        pro_strength = {
            ArgumentStrength.WEAK: 0.2,
            ArgumentStrength.MODERATE: 0.5,
            ArgumentStrength.STRONG: 0.8,
            ArgumentStrength.VERY_STRONG: 0.95,
        }[pro_arg.strength_assessment]

        con_strength = {
            ArgumentStrength.WEAK: 0.2,
            ArgumentStrength.MODERATE: 0.5,
            ArgumentStrength.STRONG: 0.8,
            ArgumentStrength.VERY_STRONG: 0.95,
        }[con_arg.strength_assessment]

        # Calculate difference
        strength_diff = (pro_strength - con_strength) / 2
        balance += strength_diff

        # Adjust for tension severity
        avg_tension_severity = sum(t.severity_score for t in tensions) / len(
            tensions
        ) if tensions else 0.5
        
        # High tension severity should push toward 0.5 (balanced)
        balance = balance * (1 - avg_tension_severity * 0.2) + 0.5 * avg_tension_severity * 0.2

        return max(0.0, min(1.0, balance))

    def _determine_winner(self, pro_arg: Argument, con_arg: Argument) -> Optional[str]:
        """Determine if one argument is stronger (or None for balanced)."""
        pro_score = pro_arg.confidence_score
        con_score = con_arg.confidence_score

        difference = abs(pro_score - con_score)

        if difference < 0.15:
            return None  # Balanced

        return "pro" if pro_score > con_score else "con"

    def _assess_debate_quality(self, pro_arg: Argument, con_arg: Argument) -> float:
        """Assess overall quality of the debate."""
        # Quality based on argument complexity and comprehensiveness
        pro_complexity = (
            len(pro_arg.supporting_points) * 0.3
            + len(pro_arg.assumptions) * 0.2
            + len(pro_arg.potential_weaknesses) * 0.2
        )

        con_complexity = (
            len(con_arg.supporting_points) * 0.3
            + len(con_arg.assumptions) * 0.2
            + len(con_arg.potential_weaknesses) * 0.2
        )

        avg_complexity = (pro_complexity + con_complexity) / 2

        # Quality also depends on confidence calibration
        pro_calibration = 1.0 - abs(pro_arg.confidence_score - 0.5)
        con_calibration = 1.0 - abs(con_arg.confidence_score - 0.5)
        avg_calibration = (pro_calibration + con_calibration) / 2

        quality = (avg_complexity / 3.0) * 0.6 + avg_calibration * 0.4
        return min(1.0, quality)

    def _extract_publishable_insights(
        self,
        pro_arg: Argument,
        con_arg: Argument,
        tensions: List[UnresolvedTension],
    ) -> List[str]:
        """Extract publishable insights from the debate."""
        insights = []

        # Insight 1: Meta-finding about disagreement
        if tensions:
            main_tension = tensions[0]
            insights.append(
                f"The key scientific disagreement centers on {main_tension.description}, "
                "suggesting this is a productive research frontier."
            )

        # Insight 2: Methodological contributions
        insights.append(
            "This debate highlights the importance of distinguishing between "
            f"observed patterns and their underlying mechanisms."
        )

        # Insight 3: Future research directions
        if len(tensions) > 1:
            insights.append(
                f"Resolving the {len(tensions)} major tensions requires "
                "complementary research approaches: empirical, theoretical, and methodological."
            )

        # Insight 4: Practical implications
        insights.append(
            "While disagreement persists on theoretical aspects, "
            "practical applications may still benefit from conditional adoption strategies."
        )

        return insights[:4]

    def _identify_disagreement_dimensions(
        self,
        pro_arg: Argument,
        con_arg: Argument,
    ) -> List[str]:
        """Identify the main dimensions of disagreement."""
        dimensions = []

        # Look for conflicting assumptions
        pro_assumptions = set(pro_arg.assumptions)
        con_assumptions = set(con_arg.assumptions)
        conflicting = pro_assumptions & con_assumptions

        if conflicting:
            dimensions.append(f"Assumption conflict: {list(conflicting)[0]}")

        # Look for scope differences
        if "general" in pro_arg.thesis.lower() and "limit" in con_arg.thesis.lower():
            dimensions.append("Scope and generalizability")

        # Look for evidence weighting differences
        if "evidence" in pro_arg.evidence_summary.lower():
            dimensions.append("Evidence interpretation and weighting")

        # Methodological dimension
        dimensions.append("Methodological rigor and validity")

        return dimensions[:4]

    def _recommend_empirical_tests(
        self,
        tensions: List[UnresolvedTension],
        disagreement_dimensions: List[str],
    ) -> List[str]:
        """Recommend empirical tests to resolve disagreements."""
        tests = []

        for tension in tensions[:3]:
            tests.extend(tension.possible_resolution_directions[:2])

        # Add dimension-specific tests
        if "generalizability" in " ".join(disagreement_dimensions).lower():
            tests.append("Cross-cultural and cross-population replication studies")

        if "methodology" in " ".join(disagreement_dimensions).lower():
            tests.append("Pre-registered replication with methodological improvements")

        return tests[:6]

    def _parse_debate_response(self, topic: str, debate_dict: Dict) -> DebateResult:
        """Parse LLM debate response into DebateResult."""
        result = DebateResult(debate_topic=topic)

        result.pro_argument = debate_dict.get("pro_argument", {})
        result.con_argument = debate_dict.get("con_argument", {})
        result.unresolved_issues = debate_dict.get("unresolved_issues", [])
        result.epistemic_balance_score = debate_dict.get("epistemic_balance_score", 0.5)
        result.winning_argument = debate_dict.get("winning_argument")
        result.debate_quality_score = debate_dict.get("debate_quality_score", 0.5)
        result.research_frontier_insights = debate_dict.get("research_frontier_insights", [])

        return result

    def validate_debate_result(self, result: DebateResult) -> Tuple[bool, List[str]]:
        """Validate the debate result."""
        errors = []

        # Check epistemic balance range
        if not 0 <= result.epistemic_balance_score <= 1:
            errors.append(
                f"epistemic_balance_score must be 0-1, got {result.epistemic_balance_score}"
            )

        # Check debate quality range
        if not 0 <= result.debate_quality_score <= 1:
            errors.append(
                f"debate_quality_score must be 0-1, got {result.debate_quality_score}"
            )

        # Check for both arguments
        if not result.pro_argument and not result.con_argument:
            errors.append("Must have at least one argument (Pro or Con)")

        # Check tensions have required fields
        for tension in result.unresolved_issues:
            if "type" not in tension or "description" not in tension:
                errors.append("Each tension must have 'type' and 'description'")

        # Check winning argument is valid
        if result.winning_argument and result.winning_argument not in ["pro", "con"]:
            errors.append(
                f"winning_argument must be 'pro', 'con', or None, got {result.winning_argument}"
            )

        is_valid = len(errors) == 0
        return is_valid, errors


def create_debate_agent(
    llm_client: Optional[object] = None,
    model: str = "gpt-4",
    debate_style: str = "rigorous",
) -> DebateAgent:
    """
    Factory function to create a Debate Agent.

    Args:
        llm_client: Optional LLM client
        model: LLM model name
        debate_style: Style of debate (rigorous, exploratory, critical)

    Returns:
        DebateAgent instance
    """
    return DebateAgent(
        llm_client=llm_client,
        model=model,
        debate_style=debate_style,
    )
