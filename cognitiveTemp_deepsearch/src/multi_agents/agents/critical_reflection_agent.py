"""
Critical Reflection Agent - Epistemic Gap Detector and Logical Vulnerability Identifier

This agent stress-tests reasoning and detects epistemological gaps through:
- Missing perspective identification
- Confirmation bias detection
- Over-generalization detection
- Counterfactual question generation
- Additional search requirement assessment

Objective: Ensure comprehensive, unbiased analysis with identified reasoning limitations
"""

import json
import re
import logging
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, List, Dict, Set, Tuple
from collections import Counter, defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BiasType(Enum):
    """Enumeration of detected bias types."""
    CONFIRMATION = "confirmation_bias"
    SELECTION = "selection_bias"
    AVAILABILITY = "availability_bias"
    ANCHORING = "anchoring_bias"
    RECENCY = "recency_bias"
    FRAMING = "framing_bias"
    GROUPTHINK = "groupthink_bias"
    SURVIVORSHIP = "survivorship_bias"
    OTHER = "other_bias"


class VulnerabilityType(Enum):
    """Enumeration of logical vulnerability types."""
    CIRCULAR_REASONING = "circular_reasoning"
    FALSE_DICHOTOMY = "false_dichotomy"
    HASTY_GENERALIZATION = "hasty_generalization"
    APPEAL_TO_AUTHORITY = "appeal_to_authority"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    CORRELATION_CAUSATION = "correlation_causation_confusion"
    SLIPPERY_SLOPE = "slippery_slope"
    EQUIVOCATION = "equivocation"
    BEGGING_THE_QUESTION = "begging_the_question"
    STRAW_MAN = "straw_man_argument"
    POST_HOC = "post_hoc_ergo_propter_hoc"
    OTHER = "other_vulnerability"


@dataclass
class LogicalVulnerability:
    """Represents a detected logical vulnerability in reasoning."""
    vulnerability_type: VulnerabilityType
    description: str
    affected_claims: List[str] = field(default_factory=list)
    severity_score: float = 0.5  # 0-1, higher = more severe
    suggested_remediation: str = ""
    confidence: float = 0.8  # 0-1, confidence in detection


@dataclass
class BiasDetection:
    """Represents a detected bias in the evidence or reasoning."""
    bias_type: BiasType
    description: str
    affected_sources: List[str] = field(default_factory=list)
    severity_score: float = 0.5  # 0-1, higher = more severe
    evidence: str = ""
    confidence: float = 0.8


@dataclass
class CounterfactualQuestion:
    """Represents a counterfactual question for testing assumptions."""
    question: str
    rationale: str  # Why this question challenges current understanding
    related_assumption: str  # Which assumption does it challenge
    expected_impact: str  # How would answer change current conclusions
    priority: int = 1  # 1=high, 2=medium, 3=low


@dataclass
class ReflectionResult:
    """Main output structure for critical reflection."""
    missing_perspectives: List[str] = field(default_factory=list)
    logical_vulnerabilities: List[Dict] = field(default_factory=list)
    bias_detections: List[Dict] = field(default_factory=list)
    bias_risk_level: float = 0.5  # 0-1, overall bias risk
    counterfactual_questions: List[Dict] = field(default_factory=list)
    requires_additional_retrieval: bool = False
    additional_search_directions: List[str] = field(default_factory=list)
    reflection_confidence: float = 0.8  # 0-1, confidence in reflection
    reasoning_gaps: List[str] = field(default_factory=list)
    recommended_perspectives: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "missing_perspectives": self.missing_perspectives,
            "logical_vulnerabilities": self.logical_vulnerabilities,
            "bias_detections": self.bias_detections,
            "bias_risk_level": round(self.bias_risk_level, 2),
            "counterfactual_questions": self.counterfactual_questions,
            "requires_additional_retrieval": self.requires_additional_retrieval,
            "additional_search_directions": self.additional_search_directions,
            "reflection_confidence": round(self.reflection_confidence, 2),
            "reasoning_gaps": self.reasoning_gaps,
            "recommended_perspectives": self.recommended_perspectives,
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


class CriticalReflectionAgent:
    """
    Critical Reflection Agent - Stress-tests reasoning and detects epistemic gaps.
    
    This agent analyzes evidence, claims, and sources to identify:
    - Missing perspectives and viewpoints
    - Logical vulnerabilities in reasoning
    - Potential biases in evidence selection
    - Over-generalizations
    - Blind spots requiring additional retrieval
    
    Key Features:
    - Confirms bias detection through pattern analysis
    - Identifies over-generalization from limited samples
    - Generates counterfactual questions
    - Recommends additional search directions
    - Provides high confidence scores only when appropriate
    """

    # Known perspectives across domains
    COMMON_PERSPECTIVES = {
        "academic_research": [
            "theoretical perspective",
            "empirical perspective",
            "literature review",
            "meta-analysis perspective",
            "case study perspective",
        ],
        "business": [
            "profit/cost perspective",
            "stakeholder perspective",
            "market perspective",
            "long-term sustainability",
            "short-term ROI",
            "competitive landscape",
        ],
        "technology": [
            "technical feasibility",
            "user experience",
            "security perspective",
            "scalability perspective",
            "cost-benefit analysis",
            "ethical implications",
        ],
        "policy": [
            "policy maker perspective",
            "implementation perspective",
            "cost perspective",
            "equity perspective",
            "political feasibility",
            "stakeholder impact",
        ],
        "health": [
            "patient perspective",
            "medical provider perspective",
            "public health perspective",
            "economic perspective",
            "ethical perspective",
            "long-term outcomes",
        ],
        "environmental": [
            "environmental impact",
            "economic impact",
            "social impact",
            "indigenous perspective",
            "future generations perspective",
            "regional context",
        ],
    }

    # Bias indicators - keywords suggesting potential bias
    BIAS_INDICATORS = {
        "confirmation_bias": [
            "confirms", "supports our hypothesis", "as expected",
            "only found positive", "selective evidence", "cherry-picked"
        ],
        "selection_bias": [
            "limited sample", "convenience sampling", "self-selected",
            "opt-in", "only included", "excluded most", "only studied"
        ],
        "availability_bias": [
            "recent", "widely reported", "commonly known",
            "top results", "all sources mention", "everyone knows"
        ],
        "anchoring_bias": [
            "first study showed", "initial estimate", "baseline assumption",
            "starting point", "anchored at", "locked into"
        ],
        "recency_bias": [
            "latest", "most recent", "recent studies", "new evidence",
            "just discovered", "only since"
        ],
        "survivorship_bias": [
            "successful companies", "winners", "those that survived",
            "best performers", "outliers", "exceptional cases"
        ],
    }

    # Over-generalization indicators
    OVERGENERALIZATION_PATTERNS = [
        r"always",
        r"never",
        r"all\s+\w+",
        r"everyone",
        r"universal",
        r"proves that",
        r"definitive",
        r"conclusive proof",
        r"the truth",
        r"obviously",
        r"clearly",
    ]

    # Logical vulnerability patterns
    LOGICAL_VULNERABILITY_PATTERNS = {
        "correlation_causation": [
            r"because",
            r"caused by",
            r"leads to",
            r"results in",
            r"is the reason",
            r"is due to",
        ],
        "hasty_generalization": [
            r"one\s+case",
            r"single\s+example",
            r"anecdote",
            r"shows",
            r"proves",
            r"therefore all",
        ],
        "appeal_to_authority": [
            r"expert says",
            r"famous",
            r"renowned",
            r"claims",
            r"argues",
            r"celebrity",
        ],
        "insufficient_evidence": [
            r"seems",
            r"appears",
            r"likely",
            r"probably",
            r"might",
            r"could be",
        ],
    }

    def __init__(
        self,
        llm_client: Optional[object] = None,
        model: str = "gpt-4",
        strict_mode: bool = True,
    ):
        """
        Initialize Critical Reflection Agent.

        Args:
            llm_client: Optional LLM client for enhanced reflection
            model: LLM model name (default: gpt-4)
            strict_mode: If True, prefer strict critique
        """
        self.llm_client = llm_client
        self.model = model
        self.strict_mode = strict_mode
        logger.info(f"Initialized Critical Reflection Agent (strict_mode={strict_mode})")

    def reflect(
        self,
        claims: List[str],
        evidence_sources: List[Dict],
        initial_conclusions: Optional[str] = None,
    ) -> ReflectionResult:
        """
        Reflect critically on claims and evidence.

        Args:
            claims: List of main claims to evaluate
            evidence_sources: List of dicts with evidence source information
            initial_conclusions: Optional summary of current conclusions

        Returns:
            ReflectionResult with comprehensive reflection analysis
        """
        logger.info(f"Reflecting critically on {len(claims)} claims from {len(evidence_sources)} sources")

        if not claims or not evidence_sources:
            return ReflectionResult(
                reflection_confidence=0.3,
                bias_risk_level=0.5,
            )

        # Use LLM if available, otherwise use local reflection
        if self.llm_client is not None:
            return self._llm_reflect(claims, evidence_sources, initial_conclusions)

        return self._local_reflect(claims, evidence_sources, initial_conclusions)

    def _local_reflect(
        self,
        claims: List[str],
        evidence_sources: List[Dict],
        initial_conclusions: Optional[str] = None,
    ) -> ReflectionResult:
        """Local reflection strategy without LLM."""
        logger.info("No LLM client provided. Using local reflection strategy.")

        result = ReflectionResult()

        # Step 1: Detect missing perspectives
        result.missing_perspectives = self._detect_missing_perspectives(claims, evidence_sources)

        # Step 2: Identify logical vulnerabilities
        vulnerabilities = self._identify_logical_vulnerabilities(claims, initial_conclusions)
        result.logical_vulnerabilities = [
            {
                "type": v.vulnerability_type.value,
                "description": v.description,
                "affected_claims": v.affected_claims,
                "severity": round(v.severity_score, 2),
                "remediation": v.suggested_remediation,
                "confidence": round(v.confidence, 2),
            }
            for v in vulnerabilities
        ]

        # Step 3: Detect biases
        biases = self._detect_biases(claims, evidence_sources)
        result.bias_detections = [
            {
                "type": b.bias_type.value,
                "description": b.description,
                "affected_sources": b.affected_sources,
                "severity": round(b.severity_score, 2),
                "evidence": b.evidence,
                "confidence": round(b.confidence, 2),
            }
            for b in biases
        ]
        result.bias_risk_level = self._calculate_bias_risk(biases)

        # Step 4: Generate counterfactual questions
        counterfactuals = self._generate_counterfactuals(claims, evidence_sources)
        result.counterfactual_questions = [
            {
                "question": cq.question,
                "rationale": cq.rationale,
                "related_assumption": cq.related_assumption,
                "expected_impact": cq.expected_impact,
                "priority": cq.priority,
            }
            for cq in counterfactuals
        ]

        # Step 5: Assess additional retrieval needs
        uncertainty = max(result.bias_risk_level, 1 - len(evidence_sources) / 10)
        result.requires_additional_retrieval = uncertainty > 0.4 or len(result.missing_perspectives) > 2

        result.additional_search_directions = self._recommend_search_directions(
            result.missing_perspectives,
            counterfactuals,
            vulnerabilities,
        )

        # Step 6: Identify reasoning gaps
        result.reasoning_gaps = self._identify_reasoning_gaps(claims, evidence_sources)

        # Step 7: Recommend perspectives
        result.recommended_perspectives = self._recommend_perspectives(
            evidence_sources,
            len(result.missing_perspectives)
        )

        # Calculate overall confidence
        result.reflection_confidence = self._calculate_reflection_confidence(
            len(result.missing_perspectives),
            result.bias_risk_level,
            result.requires_additional_retrieval,
        )

        return result

    def _llm_reflect(
        self,
        claims: List[str],
        evidence_sources: List[Dict],
        initial_conclusions: Optional[str] = None,
    ) -> ReflectionResult:
        """LLM-based reflection strategy."""
        logger.info("Using LLM-based reflection strategy.")

        prompt = self._build_reflection_prompt(claims, evidence_sources, initial_conclusions)

        try:
            response = self.llm_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            result_json = json.loads(response.choices[0].message.content)
            return self._parse_reflection_response(result_json)

        except Exception as e:
            logger.warning(f"LLM reflection failed: {e}. Falling back to local strategy.")
            return self._local_reflect(claims, evidence_sources, initial_conclusions)

    def _build_reflection_prompt(
        self,
        claims: List[str],
        evidence_sources: List[Dict],
        initial_conclusions: Optional[str] = None,
    ) -> str:
        """Build prompt for LLM reflection."""
        sources_text = "\n".join([
            f"- {s.get('title', 'Unknown')}: {s.get('summary', '')[:100]}"
            for s in evidence_sources[:5]
        ])

        claims_text = "\n".join([f"- {c}" for c in claims[:5]])

        prompt = f"""You are a critical reflection agent. Analyze the following claims and evidence for logical vulnerabilities, biases, and missing perspectives.

Claims:
{claims_text}

Evidence Sources (sample):
{sources_text}

{f"Initial Conclusions: {initial_conclusions}" if initial_conclusions else ""}

Provide a strict JSON response with:
- missing_perspectives: List of unrepresented viewpoints
- logical_vulnerabilities: List of logical flaws (type, description, severity 0-1)
- bias_detections: List of detected biases (type, description, severity 0-1)
- bias_risk_level: Overall bias risk (0-1)
- counterfactual_questions: List of challenging questions
- requires_additional_retrieval: Boolean
- reflection_confidence: Your confidence (0-1)

Be strict and identify real vulnerabilities."""

        return prompt

    def _detect_missing_perspectives(
        self,
        claims: List[str],
        evidence_sources: List[Dict],
    ) -> List[str]:
        """Detect perspectives not represented in current evidence."""
        missing = []
        sources_text = " ".join([
            f"{s.get('title', '')} {s.get('summary', '')}"
            for s in evidence_sources
        ])

        for category, perspectives in self.COMMON_PERSPECTIVES.items():
            for perspective in perspectives:
                # Simple keyword matching
                keywords = perspective.lower().split()
                if not any(keyword in sources_text.lower() for keyword in keywords):
                    missing.append(f"{category}: {perspective}")

        # Limit to top missing perspectives
        return missing[:5]

    def _identify_logical_vulnerabilities(
        self,
        claims: List[str],
        initial_conclusions: Optional[str] = None,
    ) -> List[LogicalVulnerability]:
        """Identify logical vulnerabilities in claims."""
        vulnerabilities = []
        text_to_analyze = " ".join(claims)
        if initial_conclusions:
            text_to_analyze += f" {initial_conclusions}"

        # Check for correlation-causation confusion
        for pattern in self.LOGICAL_VULNERABILITY_PATTERNS["correlation_causation"]:
            if re.search(pattern, text_to_analyze, re.IGNORECASE):
                vulnerabilities.append(LogicalVulnerability(
                    vulnerability_type=VulnerabilityType.CORRELATION_CAUSATION,
                    description="Potential confusion between correlation and causation detected",
                    affected_claims=claims[:2],
                    severity_score=0.7,
                    suggested_remediation="Verify causal mechanism, not just statistical correlation",
                    confidence=0.6,
                ))
                break

        # Check for hasty generalization
        overgeneralization_found = False
        for pattern in self.OVERGENERALIZATION_PATTERNS:
            if re.search(pattern, text_to_analyze, re.IGNORECASE):
                overgeneralization_found = True
                break

        if overgeneralization_found:
            vulnerabilities.append(LogicalVulnerability(
                vulnerability_type=VulnerabilityType.HASTY_GENERALIZATION,
                description="Possible over-generalization from limited evidence",
                affected_claims=claims[:2],
                severity_score=0.65,
                suggested_remediation="Qualify claims with appropriate scope limitations",
                confidence=0.7,
            ))

        # Check for insufficient evidence
        weak_indicators = ["seems", "appears", "likely", "probably", "might"]
        if any(indicator in text_to_analyze.lower() for indicator in weak_indicators):
            vulnerabilities.append(LogicalVulnerability(
                vulnerability_type=VulnerabilityType.INSUFFICIENT_EVIDENCE,
                description="Language suggests insufficient evidence for strong claims",
                affected_claims=claims[:1],
                severity_score=0.5,
                suggested_remediation="Provide stronger empirical evidence or qualify uncertainty",
                confidence=0.6,
            ))

        # Check for appeal to authority
        if re.search(r"expert|famous|renowned|celebrity|claims", text_to_analyze, re.IGNORECASE):
            vulnerabilities.append(LogicalVulnerability(
                vulnerability_type=VulnerabilityType.APPEAL_TO_AUTHORITY,
                description="Potential reliance on authority rather than evidence",
                affected_claims=claims[:1],
                severity_score=0.4,
                suggested_remediation="Evaluate claims on empirical merit, not just source authority",
                confidence=0.5,
            ))

        return vulnerabilities

    def _detect_biases(
        self,
        claims: List[str],
        evidence_sources: List[Dict],
    ) -> List[BiasDetection]:
        """Detect potential biases in evidence and claims."""
        biases = []
        sources_text = " ".join([
            f"{s.get('title', '')} {s.get('summary', '')} {s.get('domain_type', '')}"
            for s in evidence_sources
        ])
        claims_text = " ".join(claims)

        # Detection 1: Selection bias
        if len(evidence_sources) < 4:
            biases.append(BiasDetection(
                bias_type=BiasType.SELECTION,
                description="Limited sample size may indicate selection bias",
                affected_sources=[s.get("title", "Unknown") for s in evidence_sources],
                severity_score=0.6,
                evidence=f"Only {len(evidence_sources)} sources examined",
                confidence=0.7,
            ))

        # Detection 2: Check for domain homogeneity
        domains = [s.get("domain_type", "unknown") for s in evidence_sources]
        domain_counts = Counter(domains)
        if len(domain_counts) < 2:
            biases.append(BiasDetection(
                bias_type=BiasType.SELECTION,
                description="Homogeneous source domains may indicate selection bias",
                affected_sources=list(domain_counts.keys()),
                severity_score=0.65,
                evidence=f"All sources from similar domains: {domain_counts}",
                confidence=0.75,
            ))

        # Detection 3: Confirmation bias indicators
        confirmation_keywords = self.BIAS_INDICATORS.get("confirmation_bias", [])
        if any(keyword in claims_text.lower() for keyword in confirmation_keywords):
            biases.append(BiasDetection(
                bias_type=BiasType.CONFIRMATION,
                description="Language patterns suggest confirmation bias",
                affected_sources=[],
                severity_score=0.55,
                evidence="Confirmation bias keywords detected in claims",
                confidence=0.6,
            ))

        # Detection 4: Recency bias
        recent_keywords = ["latest", "most recent", "new evidence", "just discovered"]
        if any(keyword in sources_text.lower() for keyword in recent_keywords):
            biases.append(BiasDetection(
                bias_type=BiasType.RECENCY,
                description="Over-reliance on recent evidence may indicate recency bias",
                affected_sources=[s.get("title", "Unknown") for s in evidence_sources],
                severity_score=0.4,
                evidence="Significant emphasis on recent sources",
                confidence=0.5,
            ))

        # Detection 5: Availability bias
        if len(evidence_sources) > 0:
            top_sources = [s.get("credibility_score", 0) for s in evidence_sources[:3]]
            if top_sources and max(top_sources) > 0.8:
                biases.append(BiasDetection(
                    bias_type=BiasType.AVAILABILITY,
                    description="Heavy reliance on high-credibility sources may indicate availability bias",
                    affected_sources=[s.get("title", "Unknown") for s in evidence_sources[:3]],
                    severity_score=0.45,
                    evidence="Top sources have very high credibility scores",
                    confidence=0.55,
                ))

        return biases

    def _calculate_bias_risk(self, biases: List[BiasDetection]) -> float:
        """Calculate overall bias risk level."""
        if not biases:
            return 0.3

        avg_severity = sum(b.severity_score for b in biases) / len(biases)
        return min(avg_severity * 1.2, 1.0)

    def _generate_counterfactuals(
        self,
        claims: List[str],
        evidence_sources: List[Dict],
    ) -> List[CounterfactualQuestion]:
        """Generate counterfactual questions to challenge assumptions."""
        counterfactuals = []

        # Counterfactual 1: Opposite scenario
        if len(claims) > 0:
            counterfactuals.append(CounterfactualQuestion(
                question="What if the opposite were true? How would the evidence need to differ?",
                rationale="Tests whether current evidence would still support opposite conclusions",
                related_assumption="Current interpretation of evidence",
                expected_impact="Reveals how locked-in we are to current interpretation",
                priority=1,
            ))

        # Counterfactual 2: Alternative causation
        counterfactuals.append(CounterfactualQuestion(
            question="What alternative explanations could account for the observed patterns?",
            rationale="Identifies confirmation bias by exploring alternative hypotheses",
            related_assumption="Assumed causal mechanism",
            expected_impact="May reveal confounding variables or overlooked factors",
            priority=1,
        ))

        # Counterfactual 3: Time dimension
        counterfactuals.append(CounterfactualQuestion(
            question="How might these conclusions change if we examined a different time period?",
            rationale="Tests temporal validity of claims (recency bias check)",
            related_assumption="Findings generalize across time",
            expected_impact="May reveal trends or cyclical patterns",
            priority=2,
        ))

        # Counterfactual 4: Scope expansion
        counterfactuals.append(CounterfactualQuestion(
            question="Would these conclusions hold true for different populations, regions, or contexts?",
            rationale="Tests generalizability and scope of claims",
            related_assumption="Findings apply universally",
            expected_impact="May identify important boundary conditions",
            priority=2,
        ))

        # Counterfactual 5: Missing evidence
        if len(evidence_sources) < 6:
            counterfactuals.append(CounterfactualQuestion(
                question="What would change if we had evidence from underrepresented perspectives?",
                rationale="Highlights gaps in current evidence base",
                related_assumption="Current sources are representative",
                expected_impact="May shift conclusions significantly",
                priority=1,
            ))

        return counterfactuals

    def _identify_reasoning_gaps(
        self,
        claims: List[str],
        evidence_sources: List[Dict],
    ) -> List[str]:
        """Identify gaps in reasoning chain."""
        gaps = []

        if len(evidence_sources) < 4:
            gaps.append("Insufficient number of sources for robust conclusions")

        # Check for domain diversity
        domains = set(s.get("domain_type", "unknown") for s in evidence_sources)
        if len(domains) < 3:
            gaps.append(f"Limited domain diversity (only {len(domains)} domains represented)")

        # Check for methodological diversity
        if all(s.get("evidence_type", "") == "documentary" for s in evidence_sources):
            gaps.append("Over-reliance on documentary evidence; missing empirical/experimental evidence")

        # Check for temporal coverage
        dates = [s.get("publication_date", "") for s in evidence_sources if s.get("publication_date")]
        if len(set(dates)) == 1:
            gaps.append("All sources from same time period; temporal trends unclear")

        # Check for opposing viewpoints
        summaries = " ".join([s.get("summary", "") for s in evidence_sources]).lower()
        if not any(word in summaries for word in ["however", "but", "contradicts", "opposes", "differs"]):
            gaps.append("No evidence of conflicting viewpoints or counterarguments")

        return gaps[:5]

    def _recommend_perspectives(
        self,
        evidence_sources: List[Dict],
        missing_count: int,
    ) -> List[str]:
        """Recommend additional perspectives to pursue."""
        recommendations = []

        # If we have many missing perspectives
        if missing_count > 3:
            recommendations.append("Seek diverse stakeholder perspectives (affected parties, critics, beneficiaries)")

        # If sources are all academic
        domain_types = [s.get("domain_type", "") for s in evidence_sources]
        if all(d == "academic" for d in domain_types if d):
            recommendations.append("Include practitioner/industry perspectives to validate real-world applicability")

        # If all sources are recent
        if all(s.get("publication_date", "2025")[:4] == "202" for s in evidence_sources):
            recommendations.append("Review historical context and long-term trends")

        # If mostly positive findings
        positive_keywords = ["success", "effective", "improved", "positive"]
        negative_keywords = ["failure", "ineffective", "declined", "negative"]
        positive_count = sum(1 for s in evidence_sources 
                           if any(k in s.get("summary", "").lower() for k in positive_keywords))
        negative_count = sum(1 for s in evidence_sources 
                           if any(k in s.get("summary", "").lower() for k in negative_keywords))

        if positive_count > negative_count * 3:
            recommendations.append("Seek critical analyses and counterarguments to balance perspective")

        return recommendations[:3]

    def _recommend_search_directions(
        self,
        missing_perspectives: List[str],
        counterfactuals: List[CounterfactualQuestion],
        vulnerabilities: List[LogicalVulnerability],
    ) -> List[str]:
        """Recommend specific directions for additional searches."""
        directions = []

        # From missing perspectives
        if len(missing_perspectives) > 0:
            directions.append(f"Research {missing_perspectives[0].split(':')[1].strip()} to fill perspective gap")

        # From counterfactuals
        if any("causation" in cq.rationale.lower() for cq in counterfactuals):
            directions.append("Search for alternative causal mechanisms and confounding variables")

        # From vulnerabilities
        for vuln in vulnerabilities:
            if vuln.vulnerability_type == VulnerabilityType.CORRELATION_CAUSATION:
                directions.append("Search for mechanistic evidence explaining observed correlations")
            elif vuln.vulnerability_type == VulnerabilityType.HASTY_GENERALIZATION:
                directions.append("Search for scope-limited studies in specific contexts")

        return directions[:4]

    def _calculate_reflection_confidence(
        self,
        missing_perspective_count: int,
        bias_risk_level: float,
        requires_additional_retrieval: bool,
    ) -> float:
        """Calculate overall confidence in reflection."""
        # Base confidence
        confidence = 0.8

        # Reduce confidence if many missing perspectives
        confidence -= missing_perspective_count * 0.05

        # Reduce confidence if high bias risk
        confidence -= bias_risk_level * 0.2

        # Reduce confidence if more retrieval needed
        if requires_additional_retrieval:
            confidence -= 0.15

        return max(0.3, min(1.0, confidence))

    def _parse_reflection_response(self, response_dict: Dict) -> ReflectionResult:
        """Parse LLM reflection response into ReflectionResult."""
        result = ReflectionResult()

        result.missing_perspectives = response_dict.get("missing_perspectives", [])
        result.logical_vulnerabilities = response_dict.get("logical_vulnerabilities", [])
        result.bias_detections = response_dict.get("bias_detections", [])
        result.bias_risk_level = response_dict.get("bias_risk_level", 0.5)
        result.counterfactual_questions = response_dict.get("counterfactual_questions", [])
        result.requires_additional_retrieval = response_dict.get("requires_additional_retrieval", False)
        result.reflection_confidence = response_dict.get("reflection_confidence", 0.8)

        return result

    def validate_reflection_result(self, result: ReflectionResult) -> Tuple[bool, List[str]]:
        """Validate the reflection result."""
        errors = []

        # Check bias_risk_level range
        if not 0 <= result.bias_risk_level <= 1:
            errors.append(f"bias_risk_level must be 0-1, got {result.bias_risk_level}")

        # Check reflection_confidence range
        if not 0 <= result.reflection_confidence <= 1:
            errors.append(f"reflection_confidence must be 0-1, got {result.reflection_confidence}")

        # Check for at least some analysis
        total_analysis = (
            len(result.missing_perspectives)
            + len(result.logical_vulnerabilities)
            + len(result.bias_detections)
            + len(result.counterfactual_questions)
        )
        if total_analysis == 0 and result.reflection_confidence > 0.5:
            errors.append("No analysis performed but confidence is high")

        # Check vulnerability severity scores
        for vuln in result.logical_vulnerabilities:
            if "severity" in vuln and not 0 <= vuln["severity"] <= 1:
                errors.append(f"Vulnerability severity must be 0-1, got {vuln['severity']}")

        # Check bias severity scores
        for bias in result.bias_detections:
            if "severity" in bias and not 0 <= bias["severity"] <= 1:
                errors.append(f"Bias severity must be 0-1, got {bias['severity']}")

        is_valid = len(errors) == 0
        return is_valid, errors


def create_critical_reflection_agent(
    llm_client: Optional[object] = None,
    model: str = "gpt-4",
    strict_mode: bool = True,
) -> CriticalReflectionAgent:
    """
    Factory function to create a Critical Reflection Agent.

    Args:
        llm_client: Optional LLM client
        model: LLM model name
        strict_mode: Whether to prefer strict critique

    Returns:
        CriticalReflectionAgent instance
    """
    return CriticalReflectionAgent(
        llm_client=llm_client,
        model=model,
        strict_mode=strict_mode,
    )
