"""
Strategic Research Decomposition Agent (Planner Agent)

Decompose complex research queries into structured, multi-dimensional sub-questions.
"""

import json
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class DifficultyLevel(Enum):
    """Difficulty levels for sub-questions."""
    TRIVIAL = 1
    EASY = 2
    MEDIUM = 3
    HARD = 4
    VERY_HARD = 5


@dataclass
class SubQuestion:
    """Represents a sub-question in the decomposition."""
    question: str
    difficulty: int  # 1-5
    expected_evidence_type: str
    dimension: str = ""  # theoretical, empirical, methodological, applications
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ResearchDecomposition:
    """Complete decomposition of a research query."""
    main_question: str
    assumptions_detected: List[str]
    dimensions: Dict[str, List[str]]
    sub_questions: List[SubQuestion]
    iteration_strategy: str
    estimated_total_rounds: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "main_question": self.main_question,
            "assumptions_detected": self.assumptions_detected,
            "dimensions": self.dimensions,
            "sub_questions": [sq.to_dict() for sq in self.sub_questions],
            "iteration_strategy": self.iteration_strategy,
            "estimated_total_rounds": self.estimated_total_rounds,
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class PlannerAgent:
    """
    Strategic Research Decomposition Agent.
    
    Analyzes complex research queries and decomposes them into:
    - Conceptual/Theoretical questions
    - Empirical/Factual questions
    - Methodological questions
    - Application/Comparative questions
    """
    
    SYSTEM_PROMPT = """You are a Strategic Research Decomposition Agent in a multi-agent deep search system.

Your task is to decompose complex research queries into structured, multi-dimensional sub-questions that enable efficient collaborative research.

Requirements:
1. Identify conceptual, empirical, methodological, and comparative aspects
2. Detect hidden assumptions in the research query
3. Estimate complexity per sub-question (1-5 scale)
4. Design an iterative research strategy
5. Ensure minimum 4 sub-questions with good coverage diversity
6. Avoid redundancy across sub-questions

Output MUST be valid JSON following this exact schema:
{
  "main_question": "The original research question",
  "assumptions_detected": ["assumption1", "assumption2", ...],
  "dimensions": {
    "theoretical": ["theoretical aspect 1", "theoretical aspect 2", ...],
    "empirical": ["empirical aspect 1", "empirical aspect 2", ...],
    "methodological": ["methodological aspect 1", "methodological aspect 2", ...],
    "applications": ["application 1", "application 2", ...]
  },
  "sub_questions": [
    {
      "question": "specific sub-question",
      "difficulty": 1-5,
      "expected_evidence_type": "type of evidence expected (e.g., academic papers, statistics, case studies, expert interviews)"
    },
    ...
  ],
  "iteration_strategy": "description of how to iteratively search and combine results",
  "estimated_total_rounds": 1-5
}

Key principles:
- Be thorough but avoid redundancy
- Ensure sub-questions are specific and answerable
- Consider dependencies between sub-questions
- Design strategy for meaningful answer synthesis"""
    
    def __init__(self, llm_client=None, model: str = "gpt-4"):
        """
        Initialize Planner Agent.
        
        Args:
            llm_client: Optional LLM client (e.g., OpenAI client)
            model: Model name to use (default: gpt-4)
        """
        self.llm_client = llm_client
        self.model = model
    
    def decompose(self, query: str) -> ResearchDecomposition:
        """
        Decompose a research query into structured sub-questions.
        
        Args:
            query: The research query to decompose
            
        Returns:
            ResearchDecomposition object with structured analysis
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        
        # If no LLM client provided, use local decomposition
        if self.llm_client is None:
            logger.warning("No LLM client provided. Using local decomposition strategy.")
            return self._local_decompose(query)
        
        # Use LLM for decomposition
        return self._llm_decompose(query)
    
    def _llm_decompose(self, query: str) -> ResearchDecomposition:
        """
        Use LLM to decompose the query.
        
        Args:
            query: The research query
            
        Returns:
            ResearchDecomposition object
        """
        try:
            # Prepare the user message
            user_message = f"""Decompose this research query:

Query: {query}

Provide a comprehensive decomposition in the required JSON format."""
            
            # Call LLM
            response = self.llm_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            # Extract and parse response
            response_text = response.choices[0].message.content
            decomposition_data = json.loads(response_text)
            
            return self._parse_decomposition(decomposition_data)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            raise ValueError(f"Invalid JSON response from LLM: {e}")
        except Exception as e:
            logger.error(f"LLM decomposition failed: {e}")
            raise
    
    def _local_decompose(self, query: str) -> ResearchDecomposition:
        """
        Local decomposition strategy without LLM (fallback).
        
        Args:
            query: The research query
            
        Returns:
            ResearchDecomposition object
        """
        # Analyze query for key concepts
        query_lower = query.lower()
        
        # Detect assumptions
        assumptions = self._detect_assumptions(query)
        
        # Extract dimensions
        dimensions = self._extract_dimensions(query)
        
        # Generate sub-questions
        sub_questions = self._generate_sub_questions(query, assumptions, dimensions)
        
        # Determine iteration strategy
        iteration_strategy = self._determine_iteration_strategy(sub_questions, query)
        
        # Estimate rounds
        estimated_rounds = min(5, max(2, len(sub_questions) // 2))
        
        return ResearchDecomposition(
            main_question=query,
            assumptions_detected=assumptions,
            dimensions=dimensions,
            sub_questions=sub_questions,
            iteration_strategy=iteration_strategy,
            estimated_total_rounds=estimated_rounds
        )
    
    def _detect_assumptions(self, query: str) -> List[str]:
        """
        Detect hidden assumptions in the query.
        
        Args:
            query: The research query
            
        Returns:
            List of detected assumptions
        """
        assumptions = []
        
        # Common assumption patterns
        assumption_keywords = {
            "是否": "Assumes there are alternatives or uncertainty",
            "怎样": "Assumes the phenomenon exists or is relevant",
            "为什么": "Assumes causality and relevant contributing factors",
            "如何": "Assumes the goal is achievable",
            "影响": "Assumes causal relationships exist",
            "效果": "Assumes interventions have measurable outcomes",
            "趋势": "Assumes historical patterns will continue or be meaningful",
            "比较": "Assumes measurable differences exist between entities",
        }
        
        for keyword, assumption in assumption_keywords.items():
            if keyword in query:
                assumptions.append(assumption)
        
        # If no keyword-based assumptions found, add general ones
        if not assumptions:
            assumptions = [
                "The query assumes the topic is relevant and has meaningful data available",
                "The query assumes existing research or information on this topic",
            ]
        
        return assumptions[:4]  # Return top 4 assumptions
    
    def _extract_dimensions(self, query: str) -> Dict[str, List[str]]:
        """
        Extract research dimensions from query.
        
        Args:
            query: The research query
            
        Returns:
            Dictionary of dimensions
        """
        return {
            "theoretical": [
                "Conceptual frameworks and definitions",
                "Underlying principles and theories",
                "Related academic domains"
            ],
            "empirical": [
                "Current state and statistics",
                "Real-world evidence and examples",
                "Data and measurements"
            ],
            "methodological": [
                "Research approaches and methods",
                "Data collection techniques",
                "Analysis and validation approaches"
            ],
            "applications": [
                "Practical implications and use cases",
                "Comparative analysis with related topics",
                "Future directions and extensions"
            ]
        }
    
    def _generate_sub_questions(
        self, 
        query: str, 
        assumptions: List[str],
        dimensions: Dict[str, List[str]]
    ) -> List[SubQuestion]:
        """
        Generate diverse sub-questions covering multiple dimensions.
        
        Args:
            query: The main research query
            assumptions: Detected assumptions
            dimensions: Research dimensions
            
        Returns:
            List of SubQuestion objects
        """
        sub_questions = []
        
        # Theoretical question
        sub_questions.append(SubQuestion(
            question=f"What are the key theoretical frameworks and definitions relevant to '{query}'?",
            difficulty=2,
            expected_evidence_type="academic papers, theoretical reviews, expert definitions",
            dimension="theoretical"
        ))
        
        # Empirical question - current state
        sub_questions.append(SubQuestion(
            question=f"What is the current empirical state and evidence regarding '{query}'?",
            difficulty=3,
            expected_evidence_type="statistics, research data, case studies, real-world examples",
            dimension="empirical"
        ))
        
        # Methodological question
        sub_questions.append(SubQuestion(
            question=f"What methodological approaches and research techniques are most effective for studying '{query}'?",
            difficulty=3,
            expected_evidence_type="research methodologies, best practices, technical approaches",
            dimension="methodological"
        ))
        
        # Application/impact question
        sub_questions.append(SubQuestion(
            question=f"What are the practical applications, implications, and future directions of '{query}'?",
            difficulty=3,
            expected_evidence_type="case studies, implementation examples, expert opinions, predictions",
            dimension="applications"
        ))
        
        # Comparative question (if not already covered)
        sub_questions.append(SubQuestion(
            question=f"How does '{query}' compare to related or alternative approaches/concepts?",
            difficulty=2,
            expected_evidence_type="comparative analysis, benchmarking data, expert comparisons",
            dimension="applications"
        ))
        
        # Challenge/limitation question
        sub_questions.append(SubQuestion(
            question=f"What are the key challenges, limitations, and open questions in '{query}'?",
            difficulty=4,
            expected_evidence_type="research gaps, expert opinions, critical analyses",
            dimension="methodological"
        ))
        
        return sub_questions
    
    def _determine_iteration_strategy(
        self, 
        sub_questions: List[SubQuestion],
        query: str
    ) -> str:
        """
        Determine the research iteration strategy.
        
        Args:
            sub_questions: Generated sub-questions
            query: The main query
            
        Returns:
            Description of iteration strategy
        """
        strategy = (
            f"1. FOUNDATION PHASE (Round 1): Address theoretical (difficulty 2) and empirical (difficulty 3) "
            f"sub-questions in parallel to establish baseline knowledge about '{query}'.\n"
            f"2. DEPTH PHASE (Round 2-3): Investigate methodological approaches and gather specific evidence. "
            f"Use findings from Phase 1 to guide targeted searches.\n"
            f"3. APPLICATION PHASE (Round 4): Explore practical applications and comparative analysis. "
            f"Synthesize findings to identify patterns and insights.\n"
            f"4. SYNTHESIS PHASE (Final): Consolidate all findings, identify gaps, and highlight "
            f"key insights and recommendations for '{query}'."
        )
        return strategy
    
    def _parse_decomposition(self, data: Dict[str, Any]) -> ResearchDecomposition:
        """
        Parse LLM response into ResearchDecomposition object.
        
        Args:
            data: Dictionary from LLM response
            
        Returns:
            ResearchDecomposition object
        """
        # Extract and validate main fields
        main_question = data.get("main_question", "")
        assumptions = data.get("assumptions_detected", [])
        dimensions = data.get("dimensions", {})
        iteration_strategy = data.get("iteration_strategy", "")
        estimated_rounds = data.get("estimated_total_rounds", 3)
        
        # Parse sub-questions
        sub_questions_data = data.get("sub_questions", [])
        sub_questions = [
            SubQuestion(
                question=sq.get("question", ""),
                difficulty=min(5, max(1, int(sq.get("difficulty", 3)))),
                expected_evidence_type=sq.get("expected_evidence_type", "")
            )
            for sq in sub_questions_data
        ]
        
        # Validate minimum sub-questions
        if len(sub_questions) < 4:
            logger.warning(f"Only {len(sub_questions)} sub-questions found, minimum is 4")
        
        return ResearchDecomposition(
            main_question=main_question,
            assumptions_detected=assumptions,
            dimensions=dimensions,
            sub_questions=sub_questions,
            iteration_strategy=iteration_strategy,
            estimated_total_rounds=min(5, max(1, estimated_rounds))
        )
    
    def validate_decomposition(self, decomposition: ResearchDecomposition) -> tuple[bool, List[str]]:
        """
        Validate the decomposition output.
        
        Args:
            decomposition: The decomposition to validate
            
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        # Check minimum sub-questions
        if len(decomposition.sub_questions) < 4:
            errors.append(f"Minimum 4 sub-questions required, got {len(decomposition.sub_questions)}")
        
        # Check difficulty range
        for i, sq in enumerate(decomposition.sub_questions):
            if not 1 <= sq.difficulty <= 5:
                errors.append(f"Sub-question {i+1}: difficulty must be 1-5, got {sq.difficulty}")
        
        # Check for empty questions
        for i, sq in enumerate(decomposition.sub_questions):
            if not sq.question or not sq.question.strip():
                errors.append(f"Sub-question {i+1}: question cannot be empty")
        
        # Check for required fields
        if not decomposition.main_question:
            errors.append("Main question cannot be empty")
        
        if decomposition.estimated_total_rounds < 1 or decomposition.estimated_total_rounds > 5:
            errors.append(f"Estimated rounds must be 1-5, got {decomposition.estimated_total_rounds}")
        
        return len(errors) == 0, errors


# Convenience functions
def create_planner(llm_client=None, model: str = "gpt-4") -> PlannerAgent:
    """Factory function to create a PlannerAgent."""
    return PlannerAgent(llm_client=llm_client, model=model)
