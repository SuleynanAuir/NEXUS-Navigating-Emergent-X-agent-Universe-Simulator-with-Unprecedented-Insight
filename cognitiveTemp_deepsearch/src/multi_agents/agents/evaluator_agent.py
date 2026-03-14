"""
Evidence Evaluation Agent

Evaluates strength and consistency of retrieved evidence.
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict, field
from enum import Enum
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class EvidenceType(Enum):
    """Types of evidence."""
    EMPIRICAL = "empirical"  # Data, statistics, measurements
    THEORETICAL = "theoretical"  # Conceptual frameworks, models
    EXPERT_OPINION = "expert_opinion"  # Expert statements, citations
    CASE_STUDY = "case_study"  # Specific case examples
    COMPARATIVE = "comparative"  # Comparisons between entities
    METHODOLOGICAL = "methodological"  # Research methods, approaches
    DOCUMENTARY = "documentary"  # Historical documents, records
    TESTIMONIAL = "testimonial"  # Personal accounts, interviews
    ANECDOTAL = "anecdotal"  # Stories, examples
    OTHER = "other"


class StrengthLevel(Enum):
    """Evidence strength levels."""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"


@dataclass
class Evidence:
    """Represents a piece of evidence."""
    statement: str
    evidence_type: str  # EvidenceType enum value
    strength: str  # StrengthLevel enum value
    supporting_sources: List[str] = field(default_factory=list)
    source_count: int = 0
    corroboration_level: float = 0.0  # 0-1, how much other evidence supports this
    methodological_rigor: float = 0.5  # 0-1, how rigorous the method is
    uncertainty: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate the evidence."""
        errors = []
        
        if not self.statement or not self.statement.strip():
            errors.append("statement cannot be empty")
        
        if self.evidence_type not in [et.value for et in EvidenceType]:
            errors.append(f"evidence_type must be one of {[et.value for et in EvidenceType]}")
        
        if self.strength not in [sl.value for sl in StrengthLevel]:
            errors.append(f"strength must be one of {[sl.value for sl in StrengthLevel]}")
        
        if not 0 <= self.corroboration_level <= 1:
            errors.append(f"corroboration_level must be 0-1, got {self.corroboration_level}")
        
        if not 0 <= self.methodological_rigor <= 1:
            errors.append(f"methodological_rigor must be 0-1, got {self.methodological_rigor}")
        
        return len(errors) == 0, errors


@dataclass
class Contradiction:
    """Represents a contradiction between evidence."""
    claim_1: str
    claim_2: str
    contradiction_type: str  # "direct_contradiction", "weak_contradiction", "contextual"
    severity: float  # 0-1, how severe the contradiction is
    affected_sources: List[str] = field(default_factory=list)
    explanation: str = ""


@dataclass
class EvaluationResult:
    """Complete evidence evaluation result."""
    claims: List[Evidence]
    contradictions: List[Contradiction]
    overall_strength_score: float  # 0-1
    evidence_uncertainty: float  # 0-1
    evidence_distribution: Dict[str, int] = field(default_factory=dict)
    strength_distribution: Dict[str, int] = field(default_factory=dict)
    total_sources_analyzed: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "claims": [c.to_dict() for c in self.claims],
            "contradictions": [
                {
                    "claim_1": c.claim_1,
                    "claim_2": c.claim_2,
                    "contradiction_type": c.contradiction_type,
                    "severity": c.severity,
                    "affected_sources": c.affected_sources,
                    "explanation": c.explanation,
                }
                for c in self.contradictions
            ],
            "overall_strength_score": self.overall_strength_score,
            "evidence_uncertainty": self.evidence_uncertainty,
            "evidence_distribution": self.evidence_distribution,
            "strength_distribution": self.strength_distribution,
            "total_sources_analyzed": self.total_sources_analyzed,
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class EvidenceEvaluatorAgent:
    """
    Evidence Evaluation Agent.
    
    Evaluates strength and consistency of retrieved evidence.
    Features:
    - Extract claims from sources
    - Categorize evidence type
    - Evaluate methodological rigor
    - Detect contradictions
    - Assign strength levels
    - No hallucination guarantee
    """
    
    SYSTEM_PROMPT = """You are an Evidence Evaluation Agent in a multi-agent deep search system.

Your task is to evaluate the strength and consistency of retrieved evidence.

Objectives:
1. Extract clear claims/statements from provided material
2. Categorize evidence type (empirical, theoretical, expert_opinion, case_study, etc.)
3. Evaluate methodological rigor of the evidence
4. Detect contradictions between claims
5. Assign strength levels (weak, moderate, strong)

Critical Rules:
- ONLY evaluate material provided to you
- NEVER hallucinate or fabricate facts
- NEVER add information not in the source material
- Mark uncertainty explicitly where appropriate
- Base strength assessment on methodology and corroboration

Evidence Types:
- empirical: Data, statistics, measurements, quantitative results
- theoretical: Conceptual frameworks, models, theories
- expert_opinion: Expert statements, professional opinions, citations
- case_study: Specific case examples, detailed examples
- comparative: Comparisons between entities or approaches
- methodological: Research methods, approaches, techniques
- documentary: Historical documents, records, archives
- testimonial: Personal accounts, interviews, witness statements
- anecdotal: Stories, personal examples, informal accounts
- other: Other types not fitting above

Strength Assessment Criteria:

STRONG (score 0.7-1.0):
- Multiple independent sources corroborate
- Based on rigorous methodology
- Recent data with large sample size
- Peer-reviewed sources
- Clear methodology described

MODERATE (score 0.4-0.7):
- Some corroboration from sources
- Reasonable methodology
- Adequate sample size
- Mixed evidence quality
- Some methodological limitations

WEAK (score 0.0-0.4):
- Limited or no corroboration
- Poor or unclear methodology
- Small sample size
- Anecdotal or testimonial only
- Significant methodological concerns

Output MUST be valid JSON:
{
  "claims": [
    {
      "statement": "specific claim or finding",
      "evidence_type": "one of the types above",
      "strength": "weak|moderate|strong",
      "supporting_sources": ["source 1", "source 2"],
      "source_count": number,
      "corroboration_level": 0-1,
      "methodological_rigor": 0-1,
      "uncertainty": false
    }
  ],
  "contradictions": [
    {
      "claim_1": "first claim",
      "claim_2": "conflicting claim",
      "contradiction_type": "direct_contradiction|weak_contradiction|contextual",
      "severity": 0-1,
      "affected_sources": ["source1", "source2"],
      "explanation": "why this is a contradiction"
    }
  ],
  "overall_strength_score": 0-1,
  "evidence_uncertainty": 0-1
}"""
    
    # Patterns for extracting claims
    CLAIM_PATTERNS = {
        "quantitative": r"(\d+(?:\.\d+)?)\s*(?:%|percent|points?|times?|fold|million|billion|thousand)",
        "comparative": r"(?:more|less|higher|lower|greater|smaller|better|worse|faster|slower|larger)\s+than",
        "causal": r"(?:causes?|leads?\s+to|results?\s+in|because|due\s+to|caused\s+by)",
        "existence": r"(?:is|are|exists?|found|discovered|identified|observed)",
        "relationship": r"(?:correlates?\s+with|related\s+to|associated\s+with|links?\s+to|connected\s+to)",
    }
    
    def __init__(self, llm_client=None, model: str = "gpt-4"):
        """
        Initialize Evidence Evaluator Agent.
        
        Args:
            llm_client: Optional LLM client
            model: Model name to use
        """
        self.llm_client = llm_client
        self.model = model
    
    def evaluate(self, sources: List[Dict[str, Any]]) -> EvaluationResult:
        """
        Evaluate evidence from sources.
        
        Args:
            sources: List of source dictionaries with title, summary, content
            
        Returns:
            EvaluationResult with evaluated claims and contradictions
        """
        if not sources:
            raise ValueError("Sources cannot be empty")
        
        # If no LLM client provided, use local evaluation
        if self.llm_client is None:
            logger.warning("No LLM client provided. Using local evaluation strategy.")
            return self._local_evaluate(sources)
        
        # Use LLM for evaluation
        return self._llm_evaluate(sources)
    
    def _llm_evaluate(self, sources: List[Dict[str, Any]]) -> EvaluationResult:
        """
        Use LLM to evaluate evidence.
        
        Args:
            sources: List of sources to evaluate
            
        Returns:
            EvaluationResult
        """
        try:
            # Prepare material for evaluation
            material = self._format_sources_for_evaluation(sources)
            
            # Call LLM
            response = self.llm_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": f"Evaluate this evidence material:\n\n{material}"}
                ],
                temperature=0.5,
                response_format={"type": "json_object"}
            )
            
            # Parse response
            response_text = response.choices[0].message.content
            evaluation_data = json.loads(response_text)
            
            return self._parse_evaluation(evaluation_data, sources)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            raise ValueError(f"Invalid JSON response from LLM: {e}")
        except Exception as e:
            logger.error(f"LLM evaluation failed: {e}")
            raise
    
    def _local_evaluate(self, sources: List[Dict[str, Any]]) -> EvaluationResult:
        """
        Local evaluation strategy without LLM.
        
        Args:
            sources: List of sources to evaluate
            
        Returns:
            EvaluationResult
        """
        # Extract claims
        claims = self._extract_claims(sources)
        
        # Categorize evidence types
        self._categorize_evidence_types(claims, sources)
        
        # Evaluate methodological rigor
        self._evaluate_rigor(claims, sources)
        
        # Assign strength levels
        self._assign_strength_levels(claims)
        
        # Detect contradictions
        contradictions = self._detect_contradictions(claims)
        
        # Calculate overall score
        overall_score = self._calculate_overall_strength(claims, contradictions)
        uncertainty = self._calculate_uncertainty(claims, contradictions)
        
        # Distribution stats
        evidence_dist = defaultdict(int)
        strength_dist = defaultdict(int)
        for claim in claims:
            evidence_dist[claim.evidence_type] += 1
            strength_dist[claim.strength] += 1
        
        return EvaluationResult(
            claims=claims,
            contradictions=contradictions,
            overall_strength_score=overall_score,
            evidence_uncertainty=uncertainty,
            evidence_distribution=dict(evidence_dist),
            strength_distribution=dict(strength_dist),
            total_sources_analyzed=len(sources)
        )
    
    def _extract_claims(self, sources: List[Dict[str, Any]]) -> List[Evidence]:
        """
        Extract claims from sources.
        
        Args:
            sources: List of sources
            
        Returns:
            List of extracted claims
        """
        claims = []
        source_names = {i: s.get("title", f"Source {i+1}") for i, s in enumerate(sources)}
        
        for idx, source in enumerate(sources):
            content = f"{source.get('title', '')} {source.get('summary', '')}"
            
            # Extract sentences as potential claims
            sentences = re.split(r'[.!?]+', content)
            
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) < 10:  # Skip very short phrases
                    continue
                
                # Check if sentence contains claim indicators
                claim_type = self._identify_claim_type(sentence)
                
                if claim_type:
                    evidence = Evidence(
                        statement=sentence[:100],  # Truncate for clarity
                        evidence_type="empirical" if "%" in sentence or any(c.isdigit() for c in sentence) else "theoretical",
                        strength="moderate",  # Default, will be updated
                        supporting_sources=[source_names[idx]],
                        source_count=1,
                        corroboration_level=0.5
                    )
                    claims.append(evidence)
        
        # Remove duplicate claims
        unique_claims = self._deduplicate_claims(claims)
        
        return unique_claims[:10]  # Limit to top 10 claims
    
    def _identify_claim_type(self, sentence: str) -> bool:
        """
        Identify if sentence contains a claim.
        
        Args:
            sentence: Sentence to analyze
            
        Returns:
            True if sentence contains a claim
        """
        sentence_lower = sentence.lower()
        
        # Check for claim indicators
        for pattern in self.CLAIM_PATTERNS.values():
            if re.search(pattern, sentence_lower, re.IGNORECASE):
                return True
        
        # Check for common claim keywords
        claim_keywords = [
            "shows", "demonstrates", "proves", "indicates", "suggests",
            "finds", "discovers", "reveals", "confirms", "establishes",
            "causes", "leads", "results", "increases", "decreases",
            "research", "study", "analysis", "evidence", "data",
            "study", "shows", "indicates", "suggest", "propose",
            "effective", "improvement", "significant", "correlation",
            "relationship", "associated", "linked", "causes",
            "affects", "influences", "impacts", "related"
        ]
        
        for keyword in claim_keywords:
            if keyword in sentence_lower:
                return True
        
        # Also return true for any sentence with reasonable length
        return len(sentence) > 15
    
    def _deduplicate_claims(self, claims: List[Evidence]) -> List[Evidence]:
        """
        Remove duplicate claims.
        
        Args:
            claims: List of claims
            
        Returns:
            Deduplicated claims
        """
        seen = set()
        unique = []
        
        for claim in claims:
            # Simple deduplication based on statement similarity
            stmt_hash = claim.statement[:30]  # Use first 30 chars as hash
            if stmt_hash not in seen:
                seen.add(stmt_hash)
                unique.append(claim)
        
        return unique
    
    def _categorize_evidence_types(self, claims: List[Evidence], sources: List[Dict]) -> None:
        """
        Categorize evidence types.
        
        Args:
            claims: List of claims to categorize
            sources: List of sources
        """
        for claim in claims:
            statement_lower = claim.statement.lower()
            
            # Categorize based on keywords and patterns
            if any(keyword in statement_lower for keyword in ["data", "statistic", "number", "%", "million", "billion"]):
                claim.evidence_type = "empirical"
            elif any(keyword in statement_lower for keyword in ["theory", "model", "framework", "concept", "principle"]):
                claim.evidence_type = "theoretical"
            elif any(keyword in statement_lower for keyword in ["expert", "researcher", "professor", "scientist", "according"]):
                claim.evidence_type = "expert_opinion"
            elif any(keyword in statement_lower for keyword in ["case", "example", "instance", "study"]):
                claim.evidence_type = "case_study"
            elif any(keyword in statement_lower for keyword in ["compared", "compared to", "versus", "versus", "more than", "less than"]):
                claim.evidence_type = "comparative"
            elif any(keyword in statement_lower for keyword in ["method", "approach", "technique", "research design"]):
                claim.evidence_type = "methodological"
            else:
                claim.evidence_type = "other"
    
    def _evaluate_rigor(self, claims: List[Evidence], sources: List[Dict]) -> None:
        """
        Evaluate methodological rigor.
        
        Args:
            claims: List of claims
            sources: List of sources
        """
        for claim in claims:
            rigor = 0.5  # Default medium rigor
            
            # Increase rigor if from academic source
            source_text = " ".join(s.get("title", "") + s.get("summary", "") for s in sources)
            if any(keyword in source_text.lower() for keyword in ["arxiv", "journal", "published", "peer-reviewed", "academic"]):
                rigor = min(1.0, rigor + 0.2)
            
            # Decrease rigor if from blog/opinion
            if any(keyword in source_text.lower() for keyword in ["blog", "opinion", "commentary", "anecdote"]):
                rigor = max(0.2, rigor - 0.2)
            
            # Check for specificity (more specific = higher rigor)
            if len(claim.statement) > 80 and claim.evidence_type == "empirical":
                rigor = min(1.0, rigor + 0.1)
            
            claim.methodological_rigor = round(rigor, 2)
    
    def _assign_strength_levels(self, claims: List[Evidence]) -> None:
        """
        Assign strength levels to claims.
        
        Args:
            claims: List of claims to assess
        """
        for claim in claims:
            # Calculate strength based on multiple factors
            factors = []
            
            # Rigor factor (30%)
            factors.append(claim.methodological_rigor * 0.3)
            
            # Corroboration factor (40%)
            factors.append(claim.corroboration_level * 0.4)
            
            # Evidence type factor (30%)
            type_scores = {
                "empirical": 0.9,
                "theoretical": 0.7,
                "expert_opinion": 0.8,
                "case_study": 0.6,
                "comparative": 0.7,
                "methodological": 0.7,
                "documentary": 0.8,
                "testimonial": 0.5,
                "anecdotal": 0.3,
                "other": 0.4,
            }
            type_score = type_scores.get(claim.evidence_type, 0.5)
            factors.append(type_score * 0.3)
            
            strength_score = sum(factors)
            
            # Assign strength level
            if strength_score >= 0.7:
                claim.strength = "strong"
            elif strength_score >= 0.4:
                claim.strength = "moderate"
            else:
                claim.strength = "weak"
    
    def _detect_contradictions(self, claims: List[Evidence]) -> List[Contradiction]:
        """
        Detect contradictions between claims.
        
        Args:
            claims: List of claims
            
        Returns:
            List of detected contradictions
        """
        contradictions = []
        
        for i, claim1 in enumerate(claims):
            for claim2 in claims[i+1:]:
                contradiction = self._check_contradiction(claim1, claim2)
                if contradiction:
                    contradictions.append(contradiction)
        
        return contradictions
    
    def _check_contradiction(self, claim1: Evidence, claim2: Evidence) -> Optional[Contradiction]:
        """
        Check if two claims contradict each other.
        
        Args:
            claim1: First claim
            claim2: Second claim
            
        Returns:
            Contradiction object if found, None otherwise
        """
        stmt1_lower = claim1.statement.lower()
        stmt2_lower = claim2.statement.lower()
        
        # Check for direct negation patterns
        negation_words = ["not", "no", "non", "unable", "ineffective", "doesn't", "doesn't"]
        
        negation_in_1 = any(word in stmt1_lower for word in negation_words)
        negation_in_2 = any(word in stmt2_lower for word in negation_words)
        
        # If one has negation and other doesn't, might be contradiction
        if negation_in_1 != negation_in_2:
            # Try to find similarity without negation
            core1 = stmt1_lower
            core2 = stmt2_lower
            
            for word in negation_words:
                core1 = core1.replace(word, "")
                core2 = core2.replace(word, "")
            
            core1 = core1.strip()
            core2 = core2.strip()
            
            # Check for similarity
            if len(core1) > 15 and len(core2) > 15:
                common_words = set(core1.split()) & set(core2.split())
                if len(common_words) >= 3:  # At least 3 common words
                    return Contradiction(
                        claim_1=claim1.statement,
                        claim_2=claim2.statement,
                        contradiction_type="direct_contradiction",
                        severity=0.8,
                        affected_sources=claim1.supporting_sources + claim2.supporting_sources,
                        explanation="One claim affirms what the other denies"
                    )
        
        # Check for opposing quantitative claims (high vs low)
        nums1 = re.findall(r'\d+(?:\.\d+)?', claim1.statement)
        nums2 = re.findall(r'\d+(?:\.\d+)?', claim2.statement)
        
        if nums1 and nums2:
            try:
                val1 = float(nums1[0])
                val2 = float(nums2[0])
                
                # If one is high percentage and other is low
                if (val1 > 70 and val2 < 30) or (val1 < 30 and val2 > 70):
                    # Check if they talk about same thing
                    common_words = set(stmt1_lower.split()) & set(stmt2_lower.split())
                    if len(common_words) >= 2:
                        return Contradiction(
                            claim_1=claim1.statement,
                            claim_2=claim2.statement,
                            contradiction_type="weak_contradiction",
                            severity=0.6,
                            affected_sources=claim1.supporting_sources + claim2.supporting_sources,
                            explanation="Opposing quantitative values (high vs low)"
                        )
            except (ValueError, IndexError):
                pass
        
        # Check for explicit contradictory keywords
        if ("effective" in stmt1_lower or "works" in stmt1_lower) and \
           ("ineffective" in stmt2_lower or "doesn't work" in stmt2_lower):
            return Contradiction(
                claim_1=claim1.statement,
                claim_2=claim2.statement,
                contradiction_type="direct_contradiction",
                severity=0.85,
                affected_sources=claim1.supporting_sources + claim2.supporting_sources,
                explanation="Claims explicitly contradict each other"
            )
        
        return None
    
    def _calculate_overall_strength(self, claims: List[Evidence], contradictions: List[Contradiction]) -> float:
        """
        Calculate overall strength score.
        
        Args:
            claims: List of claims
            contradictions: List of contradictions
            
        Returns:
            Overall strength score (0-1)
        """
        if not claims:
            return 0.0
        
        # Average strength of claims
        strength_map = {"strong": 1.0, "moderate": 0.5, "weak": 0.0}
        avg_claim_strength = sum(strength_map.get(c.strength, 0.5) for c in claims) / len(claims)
        
        # Penalty for contradictions
        contradiction_penalty = len(contradictions) * 0.1
        
        overall_score = avg_claim_strength - contradiction_penalty
        
        return round(min(1.0, max(0.0, overall_score)), 2)
    
    def _calculate_uncertainty(self, claims: List[Evidence], contradictions: List[Contradiction]) -> float:
        """
        Calculate evidence uncertainty.
        
        Args:
            claims: List of claims
            contradictions: List of contradictions
            
        Returns:
            Uncertainty score (0-1)
        """
        # Base uncertainty from weak claims
        weak_claims = sum(1 for c in claims if c.strength == "weak")
        weak_penalty = (weak_claims / max(len(claims), 1)) * 0.3
        
        # Uncertainty from contradictions
        contradiction_penalty = len(contradictions) * 0.1
        
        # Uncertainty from unknown sources
        unknown_penalty = 0.1 if any(c.uncertainty for c in claims) else 0.0
        
        uncertainty = weak_penalty + contradiction_penalty + unknown_penalty
        
        return round(min(1.0, uncertainty), 2)
    
    def _format_sources_for_evaluation(self, sources: List[Dict]) -> str:
        """Format sources for LLM evaluation."""
        formatted = []
        for i, source in enumerate(sources, 1):
            formatted.append(f"Source {i}: {source.get('title', 'Unknown')}")
            formatted.append(f"Content: {source.get('summary', '')}")
            formatted.append("")
        
        return "\n".join(formatted)
    
    def _parse_evaluation(self, data: Dict[str, Any], sources: List[Dict]) -> EvaluationResult:
        """
        Parse LLM response into EvaluationResult.
        
        Args:
            data: Dictionary from LLM response
            sources: Original sources
            
        Returns:
            EvaluationResult object
        """
        # Parse claims
        claims_data = data.get("claims", [])
        claims = [
            Evidence(
                statement=c.get("statement", ""),
                evidence_type=c.get("evidence_type", "other"),
                strength=c.get("strength", "moderate"),
                supporting_sources=c.get("supporting_sources", []),
                source_count=c.get("source_count", 1),
                corroboration_level=min(1.0, max(0.0, c.get("corroboration_level", 0.5))),
                methodological_rigor=min(1.0, max(0.0, c.get("methodological_rigor", 0.5))),
                uncertainty=c.get("uncertainty", False)
            )
            for c in claims_data
        ]
        
        # Parse contradictions
        contradictions_data = data.get("contradictions", [])
        contradictions = [
            Contradiction(
                claim_1=c.get("claim_1", ""),
                claim_2=c.get("claim_2", ""),
                contradiction_type=c.get("contradiction_type", "weak_contradiction"),
                severity=min(1.0, max(0.0, c.get("severity", 0.5))),
                affected_sources=c.get("affected_sources", []),
                explanation=c.get("explanation", "")
            )
            for c in contradictions_data
        ]
        
        overall_score = min(1.0, max(0.0, data.get("overall_strength_score", 0.5)))
        uncertainty = min(1.0, max(0.0, data.get("evidence_uncertainty", 0.5)))
        
        # Calculate distributions
        evidence_dist = defaultdict(int)
        strength_dist = defaultdict(int)
        for claim in claims:
            evidence_dist[claim.evidence_type] += 1
            strength_dist[claim.strength] += 1
        
        return EvaluationResult(
            claims=claims,
            contradictions=contradictions,
            overall_strength_score=overall_score,
            evidence_uncertainty=uncertainty,
            evidence_distribution=dict(evidence_dist),
            strength_distribution=dict(strength_dist),
            total_sources_analyzed=len(sources)
        )
    
    def validate_evaluation_result(self, result: EvaluationResult) -> Tuple[bool, List[str]]:
        """
        Validate evaluation result.
        
        Args:
            result: Result to validate
            
        Returns:
            Tuple of (is_valid, error_list)
        """
        errors = []
        
        # Check minimum claims
        if len(result.claims) == 0:
            errors.append("At least one claim should be extracted")
        
        # Validate each claim
        for i, claim in enumerate(result.claims):
            is_valid, claim_errors = claim.validate()
            if not claim_errors:
                errors.extend([f"Claim {i+1}: {e}" for e in claim_errors])
        
        # Check scores
        if not 0 <= result.overall_strength_score <= 1:
            errors.append(f"overall_strength_score must be 0-1, got {result.overall_strength_score}")
        
        if not 0 <= result.evidence_uncertainty <= 1:
            errors.append(f"evidence_uncertainty must be 0-1, got {result.evidence_uncertainty}")
        
        return len(errors) == 0, errors


# Convenience function
def create_evaluator(llm_client=None, model: str = "gpt-4") -> EvidenceEvaluatorAgent:
    """Factory function to create an EvidenceEvaluatorAgent."""
    return EvidenceEvaluatorAgent(llm_client=llm_client, model=model)
