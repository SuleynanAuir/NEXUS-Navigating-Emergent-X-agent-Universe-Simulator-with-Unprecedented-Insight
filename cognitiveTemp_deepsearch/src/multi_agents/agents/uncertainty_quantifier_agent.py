"""
Uncertainty Quantifier Agent - Epistemic Uncertainty Modeling

This agent models epistemic uncertainty across findings by:
- Aggregating evidence confidence from multiple sources
- Measuring disagreement variance between different analyses
- Estimating risk of hallucination or spurious findings
- Computing global uncertainty score for decision-making

Objective: Provide rigorous quantification of uncertainty to support
informed decision-making and appropriate epistemic caution.
"""

import json
import logging
import math
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, List, Dict, Tuple, Set
from statistics import mean, stdev, variance as calc_variance
from collections import Counter, defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConfidenceLevel(Enum):
    """Enumeration of confidence levels."""
    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


class UncertaintySource(Enum):
    """Enumeration of uncertainty sources."""
    SAMPLE_SIZE = "small_sample_size"
    METHODOLOGICAL = "methodological_limitations"
    PUBLICATION_BIAS = "publication_bias"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    MEASUREMENT_ERROR = "measurement_error"
    CONFOUNDING = "confounding_variables"
    GENERALIZATION = "generalization_limits"
    TEMPORAL_INSTABILITY = "temporal_instability"
    COGNITIVE_BIAS = "cognitive_bias"
    DATA_QUALITY = "data_quality"


@dataclass
class ConfidenceMetric:
    """Individual confidence metric from a piece of evidence."""
    source_id: str
    credibility_score: float  # 0-1
    evidence_strength: float  # 0-1
    relevance_score: float  # 0-1
    recency_score: float  # 0-1 (1 = recent, 0 = outdated)
    methodological_quality: float  # 0-1
    sample_size_adequacy: float  # 0-1
    
    def compute_confidence(self) -> float:
        """Compute combined confidence score."""
        weights = {
            "credibility": 0.25,
            "strength": 0.20,
            "relevance": 0.15,
            "recency": 0.10,
            "methodology": 0.20,
            "sample": 0.10,
        }
        
        confidence = (
            self.credibility_score * weights["credibility"]
            + self.evidence_strength * weights["strength"]
            + self.relevance_score * weights["relevance"]
            + self.recency_score * weights["recency"]
            + self.methodological_quality * weights["methodology"]
            + self.sample_size_adequacy * weights["sample"]
        )
        
        return min(1.0, max(0.0, confidence))


@dataclass
class DisagreementMetric:
    """Measures disagreement between different analyses."""
    claim_id: str
    conflicting_interpretations: List[str] = field(default_factory=list)
    confidence_spread: float = 0.0  # Range of confidences
    methodological_divergence: float = 0.5  # 0-1
    theoretical_divergence: float = 0.5  # 0-1
    empirical_contradictions: int = 0
    
    def compute_disagreement_variance(self) -> float:
        """Compute variance score from disagreement."""
        # Combine multiple disagreement sources
        variance = (
            self.confidence_spread * 0.3
            + self.methodological_divergence * 0.3
            + self.theoretical_divergence * 0.2
            + min(1.0, self.empirical_contradictions / 5.0) * 0.2
        )
        
        return min(1.0, max(0.0, variance))


@dataclass
class HallucinationRiskFactor:
    """Factors contributing to hallucination/spurious finding risk."""
    risk_type: UncertaintySource
    severity_score: float  # 0-1
    evidence_source: str
    mitigation_strategies: List[str] = field(default_factory=list)


@dataclass
class UncertaintyQuantification:
    """Main output structure for uncertainty quantification."""
    analysis_id: str
    aggregated_confidence: float = 0.5  # 0-1, overall confidence
    confidence_level: ConfidenceLevel = ConfidenceLevel.MODERATE
    variance_score: float = 0.5  # 0-1, disagreement variance
    hallucination_risk: float = 0.5  # 0-1, risk of spurious findings
    global_uncertainty: float = 0.5  # 0-1, overall uncertainty
    confidence_intervals: Dict = field(default_factory=dict)  # Lower/upper bounds
    variance_sources: List[str] = field(default_factory=list)
    hallucination_risk_factors: List[Dict] = field(default_factory=list)
    uncertainty_sources: List[str] = field(default_factory=list)
    recommend_termination: bool = False
    termination_reason: str = ""
    confidence_sufficient_for_publication: bool = True
    recommendations: List[str] = field(default_factory=list)
    additional_evidence_needed: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "analysis_id": self.analysis_id,
            "aggregated_confidence": round(self.aggregated_confidence, 2),
            "confidence_level": self.confidence_level.value,
            "confidence_intervals": {
                k: round(v, 2) if isinstance(v, float) else v
                for k, v in self.confidence_intervals.items()
            },
            "variance_score": round(self.variance_score, 2),
            "variance_sources": self.variance_sources,
            "hallucination_risk": round(self.hallucination_risk, 2),
            "hallucination_risk_factors": [
                {
                    "type": f.get("type", "unknown"),
                    "severity": round(f.get("severity", 0), 2),
                    "mitigation": f.get("mitigation", []),
                }
                for f in self.hallucination_risk_factors
            ],
            "global_uncertainty": round(self.global_uncertainty, 2),
            "uncertainty_sources": self.uncertainty_sources,
            "recommend_termination": self.recommend_termination,
            "termination_reason": self.termination_reason,
            "confidence_sufficient": self.confidence_sufficient_for_publication,
            "recommendations": self.recommendations,
            "additional_evidence_needed": self.additional_evidence_needed,
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


class UncertaintyQuantifierAgent:
    """
    Uncertainty Quantifier Agent - Models epistemic uncertainty across findings.

    This agent provides comprehensive uncertainty quantification including:
    - Aggregated confidence scoring
    - Disagreement variance measurement
    - Hallucination risk estimation
    - Global uncertainty computation
    - Termination recommendations

    Key Features:
    - Multi-source confidence aggregation
    - Variance analysis from conflicting evidence
    - Hallucination risk profiling
    - Publication readiness assessment
    - Evidence gap identification
    """

    # Hallucination risk thresholds
    HALLUCINATION_RISK_THRESHOLDS = {
        "very_low": 0.1,
        "low": 0.25,
        "moderate": 0.5,
        "high": 0.75,
        "very_high": 1.0,
    }

    # Uncertainty thresholds
    UNCERTAINTY_THRESHOLDS = {
        "very_certain": 0.8,
        "certain": 0.65,
        "moderate": 0.5,
        "uncertain": 0.35,
        "very_uncertain": 0.0,
    }

    def __init__(
        self,
        llm_client: Optional[object] = None,
        model: str = "gpt-4",
        strict_mode: bool = True,
    ):
        """
        Initialize Uncertainty Quantifier Agent.

        Args:
            llm_client: Optional LLM client
            model: LLM model name
            strict_mode: If True, use strict uncertainty thresholds
        """
        self.llm_client = llm_client
        self.model = model
        self.strict_mode = strict_mode
        logger.info(f"Initialized Uncertainty Quantifier Agent (strict_mode={strict_mode})")

    def quantify(
        self,
        analysis_id: str,
        evidence_sources: List[Dict],
        claims: List[str],
        confidence_scores: Optional[List[float]] = None,
        disagreement_indicators: Optional[List[str]] = None,
    ) -> UncertaintyQuantification:
        """
        Quantify uncertainty across findings.

        Args:
            analysis_id: Unique identifier for this analysis
            evidence_sources: List of evidence sources with metadata
            claims: List of main claims made
            confidence_scores: Optional list of confidence scores per claim
            disagreement_indicators: Optional indicators of disagreement

        Returns:
            UncertaintyQuantification with comprehensive uncertainty metrics
        """
        logger.info(
            f"Quantifying uncertainty for analysis: {analysis_id} "
            f"with {len(evidence_sources)} sources"
        )

        if not evidence_sources or not claims:
            return UncertaintyQuantification(analysis_id=analysis_id)

        if self.llm_client is not None:
            return self._llm_quantify(
                analysis_id, evidence_sources, claims, confidence_scores, disagreement_indicators
            )

        return self._local_quantify(
            analysis_id, evidence_sources, claims, confidence_scores, disagreement_indicators
        )

    def _local_quantify(
        self,
        analysis_id: str,
        evidence_sources: List[Dict],
        claims: List[str],
        confidence_scores: Optional[List[float]] = None,
        disagreement_indicators: Optional[List[str]] = None,
    ) -> UncertaintyQuantification:
        """Local quantification strategy without LLM."""
        logger.info("Using local uncertainty quantification strategy.")

        result = UncertaintyQuantification(analysis_id=analysis_id)

        # Step 1: Aggregate confidence from evidence
        aggregated_conf = self._aggregate_confidence(evidence_sources, confidence_scores)
        result.aggregated_confidence = aggregated_conf
        result.confidence_level = self._classify_confidence_level(aggregated_conf)

        # Step 2: Compute confidence intervals
        result.confidence_intervals = self._compute_confidence_intervals(
            evidence_sources, aggregated_conf
        )

        # Step 3: Measure disagreement variance
        variance = self._measure_disagreement_variance(
            evidence_sources, claims, disagreement_indicators
        )
        result.variance_score = variance
        result.variance_sources = self._identify_variance_sources(evidence_sources, claims)

        # Step 4: Estimate hallucination risk
        hallucination_risk = self._estimate_hallucination_risk(
            evidence_sources, claims, aggregated_conf, variance
        )
        result.hallucination_risk = hallucination_risk
        result.hallucination_risk_factors = self._identify_risk_factors(
            evidence_sources, claims
        )

        # Step 5: Compute global uncertainty
        global_unc = self._compute_global_uncertainty(
            aggregated_conf, variance, hallucination_risk
        )
        result.global_uncertainty = global_unc
        result.uncertainty_sources = self._identify_uncertainty_sources(
            evidence_sources, claims
        )

        # Step 6: Determine termination recommendation
        result.recommend_termination = self._should_terminate(
            aggregated_conf, variance, hallucination_risk, global_unc
        )
        if result.recommend_termination:
            result.termination_reason = self._explain_termination(
                aggregated_conf, variance, hallucination_risk
            )

        # Step 7: Assess publication readiness
        result.confidence_sufficient_for_publication = aggregated_conf >= 0.5

        # Step 8: Generate recommendations
        result.recommendations = self._generate_recommendations(result)

        # Step 9: Identify evidence gaps
        result.additional_evidence_needed = self._identify_evidence_gaps(
            evidence_sources, claims
        )

        return result

    def _llm_quantify(
        self,
        analysis_id: str,
        evidence_sources: List[Dict],
        claims: List[str],
        confidence_scores: Optional[List[float]] = None,
        disagreement_indicators: Optional[List[str]] = None,
    ) -> UncertaintyQuantification:
        """LLM-based quantification strategy."""
        logger.info("Using LLM-based uncertainty quantification.")

        prompt = self._build_quantification_prompt(
            analysis_id, evidence_sources, claims, confidence_scores, disagreement_indicators
        )

        try:
            response = self.llm_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                response_format={"type": "json_object"},
            )

            result_json = json.loads(response.choices[0].message.content)
            return self._parse_quantification_response(analysis_id, result_json)

        except Exception as e:
            logger.warning(f"LLM quantification failed: {e}. Falling back to local strategy.")
            return self._local_quantify(
                analysis_id, evidence_sources, claims, confidence_scores, disagreement_indicators
            )

    def _build_quantification_prompt(
        self,
        analysis_id: str,
        evidence_sources: List[Dict],
        claims: List[str],
        confidence_scores: Optional[List[float]] = None,
        disagreement_indicators: Optional[List[str]] = None,
    ) -> str:
        """Build prompt for LLM quantification."""
        sources_text = "\n".join([
            f"- {s.get('title', 'Unknown')} "
            f"(credibility: {s.get('credibility_score', 0):.2f}): "
            f"{s.get('summary', '')[:100]}"
            for s in evidence_sources[:6]
        ])

        claims_text = "\n".join([f"- {c}" for c in claims[:5]])

        prompt = f"""Quantify epistemic uncertainty for this analysis:

Analysis ID: {analysis_id}

Claims:
{claims_text}

Evidence Sources:
{sources_text}

{f"Reported confidence scores: {confidence_scores}" if confidence_scores else ""}
{f"Disagreement indicators: {disagreement_indicators}" if disagreement_indicators else ""}

Provide a JSON response with:
1. aggregated_confidence: 0-1
2. confidence_intervals: {{lower: X, upper: Y}}
3. variance_score: 0-1 (disagreement between sources)
4. hallucination_risk: 0-1 (risk of spurious findings)
5. global_uncertainty: 0-1
6. recommend_termination: boolean
7. recommendations: [list of suggestions]

Be rigorous and conservative in uncertainty estimation."""

        return prompt

    def _aggregate_confidence(
        self,
        evidence_sources: List[Dict],
        confidence_scores: Optional[List[float]] = None,
    ) -> float:
        """Aggregate confidence from multiple sources."""
        if not evidence_sources:
            return 0.3

        # Extract credibility scores
        credibilities = [
            s.get("credibility_score", 0.5) for s in evidence_sources
        ]

        # Weight by relevance and credibility
        weights = []
        for source in evidence_sources:
            relevance = source.get("relevance_score", 0.7)
            credibility = source.get("credibility_score", 0.5)
            weight = (relevance * 0.6 + credibility * 0.4)
            weights.append(weight)

        # Normalize weights
        total_weight = sum(weights)
        if total_weight > 0:
            normalized_weights = [w / total_weight for w in weights]
        else:
            normalized_weights = [1.0 / len(credibilities)] * len(credibilities)

        # Calculate weighted average
        aggregated = sum(c * w for c, w in zip(credibilities, normalized_weights))

        # Adjust for number of sources (more sources = higher confidence)
        source_adjustment = min(0.1, len(evidence_sources) * 0.02)
        aggregated = min(1.0, aggregated + source_adjustment)

        # Apply custom confidence scores if provided
        if confidence_scores:
            mean_custom = mean(confidence_scores)
            aggregated = aggregated * 0.7 + mean_custom * 0.3

        return max(0.0, min(1.0, aggregated))

    def _classify_confidence_level(self, confidence: float) -> ConfidenceLevel:
        """Classify confidence into levels."""
        if confidence >= 0.85:
            return ConfidenceLevel.VERY_HIGH
        elif confidence >= 0.70:
            return ConfidenceLevel.HIGH
        elif confidence >= 0.50:
            return ConfidenceLevel.MODERATE
        elif confidence >= 0.30:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW

    def _compute_confidence_intervals(
        self,
        evidence_sources: List[Dict],
        aggregated_confidence: float,
    ) -> Dict:
        """Compute confidence intervals."""
        credibilities = [s.get("credibility_score", 0.5) for s in evidence_sources]

        if len(credibilities) < 2:
            margin = 0.15
        else:
            margin = stdev(credibilities) if len(credibilities) > 1 else 0.1

        lower = max(0.0, aggregated_confidence - margin)
        upper = min(1.0, aggregated_confidence + margin)

        return {
            "lower_bound": lower,
            "upper_bound": upper,
            "margin_of_error": margin,
            "point_estimate": aggregated_confidence,
        }

    def _measure_disagreement_variance(
        self,
        evidence_sources: List[Dict],
        claims: List[str],
        disagreement_indicators: Optional[List[str]] = None,
    ) -> float:
        """Measure variance from disagreement between sources."""
        if not evidence_sources or len(evidence_sources) < 2:
            return 0.2  # Low variance with limited sources

        variance_score = 0.0

        # Check for contradicting assessments in summaries
        summaries = [s.get("summary", "").lower() for s in evidence_sources]

        # Look for explicit contradictions
        contradictory_keywords = ["but", "however", "contrary", "contradicts", "opposes", "conflicting", "conflict"]
        contradiction_count = 0

        for summary in summaries:
            if any(keyword in summary for keyword in contradictory_keywords):
                contradiction_count += 1

        if contradiction_count > 0:
            variance_score += min(1.0, (contradiction_count / len(summaries)) * 0.7)

        # Check for disagreement indicators
        if disagreement_indicators:
            variance_score += min(0.5, len(disagreement_indicators) * 0.15)

        # Calculate variance in credibility scores
        credibilities = [s.get("credibility_score", 0.5) for s in evidence_sources]
        if len(credibilities) > 1:
            cred_variance = calc_variance(credibilities)
            variance_score += cred_variance * 0.3

        return min(1.0, max(0.0, variance_score))

    def _estimate_hallucination_risk(
        self,
        evidence_sources: List[Dict],
        claims: List[str],
        aggregated_confidence: float,
        variance_score: float,
    ) -> float:
        """Estimate risk of hallucination or spurious findings."""
        # Base risk from low confidence
        confidence_risk = 1.0 - aggregated_confidence

        # Risk from high variance
        variance_risk = variance_score

        # Risk from small sample size
        sample_risk = 0.0
        if len(evidence_sources) == 1:
            sample_risk = 0.5
        elif len(evidence_sources) < 3:
            sample_risk = 0.35
        elif len(evidence_sources) < 5:
            sample_risk = 0.15

        # Risk from methodological concerns
        method_risk = 0.0
        if any(
            keyword in " ".join([s.get("summary", "") for s in evidence_sources]).lower()
            for keyword in ["limited", "small sample", "single study", "preliminary"]
        ):
            method_risk = 0.3

        # Combine risks
        hallucination_risk = (
            confidence_risk * 0.35
            + variance_risk * 0.25
            + sample_risk * 0.25
            + method_risk * 0.15
        )

        return min(1.0, max(0.0, hallucination_risk))

    def _compute_global_uncertainty(
        self,
        aggregated_confidence: float,
        variance_score: float,
        hallucination_risk: float,
    ) -> float:
        """Compute global uncertainty score."""
        # Global uncertainty is opposite of confidence, weighted by variance and risk
        confidence_uncertainty = 1.0 - aggregated_confidence
        
        global_unc = (
            confidence_uncertainty * 0.4
            + variance_score * 0.3
            + hallucination_risk * 0.3
        )

        return min(1.0, max(0.0, global_unc))

    def _should_terminate(
        self,
        aggregated_confidence: float,
        variance_score: float,
        hallucination_risk: float,
        global_uncertainty: float,
    ) -> bool:
        """Determine if analysis should be terminated."""
        # Terminate if any critical threshold is exceeded
        if aggregated_confidence < 0.3:
            return True

        if hallucination_risk > 0.7:
            return True

        if variance_score > 0.8 and aggregated_confidence < 0.5:
            return True

        if global_uncertainty > 0.8:
            return True

        return False

    def _explain_termination(
        self,
        aggregated_confidence: float,
        variance_score: float,
        hallucination_risk: float,
    ) -> str:
        """Explain why analysis should be terminated."""
        reasons = []

        if aggregated_confidence < 0.3:
            reasons.append("Confidence too low (below 0.3)")

        if hallucination_risk > 0.7:
            reasons.append("Hallucination risk too high (above 0.7)")

        if variance_score > 0.8:
            reasons.append("High disagreement between sources (variance > 0.8)")

        return " | ".join(reasons) if reasons else "Multiple uncertainty thresholds exceeded"

    def _identify_uncertainty_sources(
        self,
        evidence_sources: List[Dict],
        claims: List[str],
    ) -> List[str]:
        """Identify specific sources of uncertainty."""
        sources = []

        if len(evidence_sources) < 3:
            sources.append("Limited number of evidence sources")

        # Check for methodological concerns
        summaries_text = " ".join([s.get("summary", "") for s in evidence_sources]).lower()

        if any(word in summaries_text for word in ["preliminary", "limited", "small sample"]):
            sources.append("Methodological limitations noted in sources")

        if any(word in summaries_text for word in ["disagreement", "contradicts", "however"]):
            sources.append("Conflicting evidence identified")

        # Check for temporal issues
        recent_dates = sum(
            1 for s in evidence_sources if s.get("publication_date", "")[:4] >= "2023"
        )
        if recent_dates < len(evidence_sources) / 2:
            sources.append("Evidence may be outdated")

        # Check for domain homogeneity
        domains = set(s.get("domain_type", "unknown") for s in evidence_sources)
        if len(domains) < 2:
            sources.append("Limited domain diversity in sources")

        return sources[:5]

    def _identify_variance_sources(
        self,
        evidence_sources: List[Dict],
        claims: List[str],
    ) -> List[str]:
        """Identify specific sources of variance."""
        sources = []

        if len(evidence_sources) > 1:
            credibilities = [s.get("credibility_score", 0.5) for s in evidence_sources]
            if max(credibilities) - min(credibilities) > 0.3:
                sources.append("Variable credibility scores across sources")

        # Check for methodological differences
        if any(
            keyword in " ".join([s.get("summary", "") for s in evidence_sources]).lower()
            for keyword in ["qualitative", "quantitative", "survey", "experiment"]
        ):
            sources.append("Different methodological approaches in sources")

        # Check for temporal differences
        dates = set(s.get("publication_date", "")[:4] for s in evidence_sources if s.get("publication_date"))
        if len(dates) > 1:
            sources.append("Sources from different time periods")

        return sources[:3]

    def _identify_risk_factors(
        self,
        evidence_sources: List[Dict],
        claims: List[str],
    ) -> List[Dict]:
        """Identify hallucination risk factors."""
        factors = []

        # Small sample size risk
        if len(evidence_sources) < 3:
            factors.append({
                "type": "small_sample_size",
                "severity": 0.6,
                "mitigation": ["Retrieve additional sources", "Conduct larger studies"],
            })

        # Methodological risk
        summaries_text = " ".join([s.get("summary", "") for s in evidence_sources]).lower()
        if "preliminary" in summaries_text or "limited" in summaries_text:
            factors.append({
                "type": "methodological_limitations",
                "severity": 0.5,
                "mitigation": ["Seek rigorous replication studies", "Pre-registered research"],
            })

        # Publication bias risk
        if all(
            keyword in summaries_text
            for keyword in ["positive", "success", "effective"]
        ):
            factors.append({
                "type": "publication_bias",
                "severity": 0.4,
                "mitigation": ["Search for null results", "Grey literature review"],
            })

        # Conflicting evidence risk
        if any(keyword in summaries_text for keyword in ["contradicts", "controversy"]):
            factors.append({
                "type": "conflicting_evidence",
                "severity": 0.55,
                "mitigation": ["Identify resolution mechanisms", "Conduct meta-analysis"],
            })

        return factors[:4]

    def _generate_recommendations(
        self,
        result: UncertaintyQuantification,
    ) -> List[str]:
        """Generate recommendations based on uncertainty."""
        recommendations = []

        if result.global_uncertainty > 0.6:
            recommendations.append("High uncertainty: Exercise caution in decision-making")

        if result.variance_score > 0.5:
            recommendations.append("Reconcile disagreement between evidence sources")

        if result.hallucination_risk > 0.5:
            recommendations.append("Conduct independent replication before implementation")

        if result.aggregated_confidence < 0.5:
            recommendations.append("Seek additional high-credibility evidence")

        if not result.confidence_sufficient_for_publication:
            recommendations.append("Insufficient confidence for publication without additional evidence")

        return recommendations[:5]

    def _identify_evidence_gaps(
        self,
        evidence_sources: List[Dict],
        claims: List[str],
    ) -> List[str]:
        """Identify what additional evidence is needed."""
        gaps = []

        if len(evidence_sources) < 5:
            gaps.append("More diverse evidence sources needed")

        domains = set(s.get("domain_type", "unknown") for s in evidence_sources)
        if len(domains) < 3:
            gaps.append("Evidence from additional domains (academic, industry, government)")

        recent_count = sum(
            1 for s in evidence_sources if s.get("publication_date", "")[:4] >= "2023"
        )
        if recent_count < len(evidence_sources) / 2:
            gaps.append("More recent evidence from 2023 onwards")

        # Check for missing methodological approaches
        summaries_text = " ".join([s.get("summary", "") for s in evidence_sources]).lower()
        if "experiment" not in summaries_text and "empirical" not in summaries_text:
            gaps.append("Empirical/experimental evidence needed")

        return gaps[:4]

    def _parse_quantification_response(
        self,
        analysis_id: str,
        response_dict: Dict,
    ) -> UncertaintyQuantification:
        """Parse LLM quantification response."""
        result = UncertaintyQuantification(analysis_id=analysis_id)

        result.aggregated_confidence = response_dict.get("aggregated_confidence", 0.5)
        result.confidence_level = self._classify_confidence_level(result.aggregated_confidence)
        result.confidence_intervals = response_dict.get("confidence_intervals", {})
        result.variance_score = response_dict.get("variance_score", 0.5)
        result.hallucination_risk = response_dict.get("hallucination_risk", 0.5)
        result.global_uncertainty = response_dict.get("global_uncertainty", 0.5)
        result.recommend_termination = response_dict.get("recommend_termination", False)
        result.recommendations = response_dict.get("recommendations", [])

        return result

    def validate_quantification(
        self,
        result: UncertaintyQuantification,
    ) -> Tuple[bool, List[str]]:
        """Validate uncertainty quantification."""
        errors = []

        # Check score ranges
        if not 0 <= result.aggregated_confidence <= 1:
            errors.append(f"aggregated_confidence must be 0-1, got {result.aggregated_confidence}")

        if not 0 <= result.variance_score <= 1:
            errors.append(f"variance_score must be 0-1, got {result.variance_score}")

        if not 0 <= result.hallucination_risk <= 1:
            errors.append(f"hallucination_risk must be 0-1, got {result.hallucination_risk}")

        if not 0 <= result.global_uncertainty <= 1:
            errors.append(f"global_uncertainty must be 0-1, got {result.global_uncertainty}")

        # Check internal consistency
        # Global uncertainty should generally increase with variance and hallucination risk
        expected_min_uncertainty = max(
            result.variance_score * 0.2,
            result.hallucination_risk * 0.2,
        )
        if result.global_uncertainty < expected_min_uncertainty - 0.2:
            errors.append(
                f"global_uncertainty inconsistently low given variance and risk scores"
            )

        is_valid = len(errors) == 0
        return is_valid, errors


def create_uncertainty_quantifier_agent(
    llm_client: Optional[object] = None,
    model: str = "gpt-4",
    strict_mode: bool = True,
) -> UncertaintyQuantifierAgent:
    """
    Factory function to create an Uncertainty Quantifier Agent.

    Args:
        llm_client: Optional LLM client
        model: LLM model name
        strict_mode: Whether to use strict uncertainty thresholds

    Returns:
        UncertaintyQuantifierAgent instance
    """
    return UncertaintyQuantifierAgent(
        llm_client=llm_client,
        model=model,
        strict_mode=strict_mode,
    )
