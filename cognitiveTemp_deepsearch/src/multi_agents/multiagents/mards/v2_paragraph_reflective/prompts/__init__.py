"""
MARDS v2: Paragraph-level Iterative Reflective Deep Search Framework

A comprehensive multi-agent research system with structured section-wise processing,
deep reflection loops, and uncertainty quantification.

Quick Start:
    from controller import MARDSController
    import asyncio
    
    async def main():
        controller = MARDSController(
            deepseek_key="your-key",
            tavily_key="your-key"
        )
        result = await controller.run("Your research query")
        print(result['report_markdown'])
    
    asyncio.run(main())

Module Structure:
    types.py       - Core data types and communication protocol
    clients.py     - API clients for DeepSeek and Tavily
    base.py        - Base agent class and utilities
    agents.py      - All agent implementations (8 agents)
    controller.py  - Main workflow orchestrator
    main.py        - CLI entry point

Features:
    - 8 specialized agents for different research tasks
    - Paragraph-level reflection with up to 3 iterations per section
    - Source diversity enforcement
    - Uncertainty quantification (0-1 scale)
    - Evaluation metrics (NDCG, MRR, diversity, depth)
    - Intermediate result saving
    - Full async architecture with retry logic
    - Comprehensive structured reports

Documentation:
    See README.md for complete documentation
"""

__version__ = "2.0.0"
__author__ = "DeepSearch Project"
__license__ = "Proprietary"

from .types import (
    AgentResponse,
    Section,
    ReportStructure,
    SearchResult,
    ReflectionEvaluation,
    GlobalUncertaintyResult,
    FinalReport,
    MARDSException,
    APIException,
    ValidationException
)

from .controller import MARDSController

__all__ = [
    "MARDSController",
    "AgentResponse",
    "Section",
    "ReportStructure",
    "SearchResult",
    "ReflectionEvaluation",
    "GlobalUncertaintyResult",
    "FinalReport",
    "MARDSException",
    "APIException",
    "ValidationException",
]
