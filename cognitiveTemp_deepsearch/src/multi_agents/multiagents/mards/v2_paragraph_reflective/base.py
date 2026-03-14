"""
Base agent class and utilities for MARDS v2.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
import json
import uuid

from v2_paragraph_reflective.schema import AgentResponse, MARDSException

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all MARDS agents."""
    
    def __init__(self, agent_role: str, logger_name: str = __name__):
        """Initialize base agent.
        
        Args:
            agent_role: Role identifier for this agent
            logger_name: Logger name
        """
        self.agent_role = agent_role
        self.logger = logging.getLogger(logger_name)
        self.call_count = 0
        self.error_count = 0
    
    @abstractmethod
    async def execute(self, **kwargs) -> AgentResponse:
        """Execute agent task.
        
        Args:
            **kwargs: Task-specific parameters
            
        Returns:
            AgentResponse with task results
        """
        pass
    
    def _create_response(
        self,
        task_id: str,
        section: str,
        output: Dict[str, Any],
        confidence: float = 0.0,
        uncertainty: float = 0.0,
        needs_reflection: bool = False,
        reflection_count: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """Create standardized agent response.
        
        Args:
            task_id: Task identifier
            section: Section identifier
            output: Output data
            confidence: Confidence score (0-1)
            uncertainty: Uncertainty score (0-1)
            needs_reflection: Whether reflection is needed
            reflection_count: Number of reflection loops
            metadata: Additional metadata
            
        Returns:
            AgentResponse object
        """
        return AgentResponse(
            task_id=task_id,
            agent_role=self.agent_role,
            section=section,
            output=output,
            confidence=confidence,
            uncertainty=uncertainty,
            needs_reflection=needs_reflection,
            reflection_count=reflection_count,
            metadata=metadata or {}
        )
    
    def _validate_json(self, json_str: str) -> Dict[str, Any]:
        """Validate and parse JSON string.
        
        Args:
            json_str: JSON string to parse
            
        Returns:
            Parsed JSON object
            
        Raises:
            ValidationException: If JSON is invalid
        """
        try:
            # Try to extract JSON from response that may contain extra text
            import re
            json_match = re.search(r'\{.*\}', json_str, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON validation failed: {e}")
            raise MARDSException(f"Invalid JSON response: {e}")
    
    async def _retry_async(
        self,
        coro_func,
        max_retries: int = 3,
        delay: float = 1.0,
        backoff: float = 2.0
    ):
        """Retry async operation with exponential backoff.
        
        Args:
            coro_func: Async function to retry
            max_retries: Maximum number of retries
            delay: Initial delay between retries (seconds)
            backoff: Backoff multiplier
            
        Returns:
            Result from coro_func
            
        Raises:
            Exception: If all retries fail
        """
        current_delay = delay
        last_error = None
        
        for attempt in range(max_retries):
            try:
                return await coro_func()
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    self.logger.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed, "
                        f"retrying in {current_delay:.1f}s: {e}"
                    )
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
                else:
                    self.logger.error(f"All {max_retries} attempts failed: {e}")
        
        raise last_error or MARDSException("Retry failed")
    
    def log_execution(self, message: str, level: str = "info"):
        """Log execution message."""
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        log_method(f"[{self.agent_role}] {message}")
    
    async def sleep_with_jitter(self, base_delay: float = 0.5):
        """Sleep with random jitter to avoid API rate limiting.
        
        Args:
            base_delay: Base delay in seconds
        """
        import random
        jitter = random.uniform(0, base_delay * 0.5)
        await asyncio.sleep(base_delay + jitter)


class PromptManager:
    """Manage prompts for agents."""
    
    _prompts: Dict[str, str] = {}
    
    @classmethod
    def register_prompt(cls, agent_role: str, prompt: str):
        """Register prompt for an agent.
        
        Args:
            agent_role: Agent role identifier
            prompt: Prompt template
        """
        cls._prompts[agent_role] = prompt
    
    @classmethod
    def get_prompt(cls, agent_role: str) -> str:
        """Get prompt for an agent.
        
        Args:
            agent_role: Agent role identifier
            
        Returns:
            Prompt template
        """
        if agent_role not in cls._prompts:
            raise MARDSException(f"Prompt not found for agent: {agent_role}")
        return cls._prompts[agent_role]
    
    @classmethod
    def render_prompt(cls, agent_role: str, **variables) -> str:
        """Render prompt with variables.
        
        Args:
            agent_role: Agent role identifier
            **variables: Variables to substitute in prompt
            
        Returns:
            Rendered prompt
        """
        template = cls.get_prompt(agent_role)
        return template.format(**variables)


def load_prompts_from_files(prompts_dir: str):
    """Load all prompts from a directory.
    
    Args:
        prompts_dir: Directory containing prompt files
    """
    import os
    
    if not os.path.isdir(prompts_dir):
        logger.warning(f"Prompts directory not found: {prompts_dir}")
        return
    
    for filename in os.listdir(prompts_dir):
        if filename.endswith(".txt"):
            agent_role = filename[:-4]  # Remove .txt extension
            filepath = os.path.join(prompts_dir, filename)
            
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    prompt = f.read()
                PromptManager.register_prompt(agent_role, prompt)
                logger.debug(f"Loaded prompt for {agent_role}")
            except Exception as e:
                logger.error(f"Failed to load prompt from {filepath}: {e}")


# Default prompts (used if prompt files not found)
DEFAULT_PROMPTS = {
    "structure_planner": """You are a research structure planner. Based on the user query, generate a comprehensive report structure with at least 5 sections.

Query: {query}

Return ONLY valid JSON with this structure:
{{
  "title": "string",
  "objective": "string",
  "sections": [
    {{"section_id": "string", "section_title": "string", "objective": "string"}},
    ...
  ]
}}""",
    
    "section_summarizer": """You are a section summarizer. Create a structured summary based on the search results provided.

Query: {query}
Section: {section_title}
Section Objective: {section_objective}
Search Results:
{search_results}

Generate a comprehensive, well-structured summary that:
1. Synthesizes the search results
2. Highlights key findings
3. Identifies evidence strength
4. Notes any contradictions

Return only the summary text.""",
    
    "reflection": """You are a research reflection agent. Evaluate the current section summary for completeness and quality.

Query: {query}
Section: {section_title}
Current Summary:
{current_summary}

Evaluate and return ONLY valid JSON:
{{
  "missing_perspectives": ["perspective1", "perspective2"],
  "weak_evidence_areas": ["area1", "area2"],
  "bias_risks": ["risk1", "risk2"],
  "needs_deeper_search": true/false,
  "recommended_search_queries": ["query1", "query2"],
  "confidence": 0.0-1.0
}}""",
    
    "global_uncertainty": """You are a global uncertainty evaluator. Calculate overall uncertainty for the research.

Sections Analysis:
{sections_analysis}

Return ONLY valid JSON:
{{
  "global_uncertainty": 0.0-1.0,
  "section_uncertainties": {{"section1": 0.5}},
  "average_confidence": 0.0-1.0,
  "recommendation": "proceed|reflect|escalate",
  "reasoning": "string",
  "reflection_needed": true/false
}}""",
    
    "formatter": """You are a report formatter. Convert the collected sections into a final research report.

Title: {title}
Sections:
{sections}

Generate a comprehensive final report with all required sections."""
}

# Register default prompts
for role, prompt in DEFAULT_PROMPTS.items():
    PromptManager.register_prompt(role, prompt)
