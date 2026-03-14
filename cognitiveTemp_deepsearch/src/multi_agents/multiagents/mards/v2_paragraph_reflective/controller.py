"""
Main Controller for MARDS v2 - orchestrates all agents.
"""

import asyncio
import json
import logging
import uuid
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from v2_paragraph_reflective.agents import (
    StructurePlannerAgent,
    SectionRetrieverAgent,
    SectionSummarizerAgent,
    ReflectionAgent,
    SectionUpdaterAgent,
    GlobalUncertaintyAgent,
    FinalFormatterAgent
)
from v2_paragraph_reflective.clients import DeepSeekClient, TavilyClient
from v2_paragraph_reflective.schema import Section, MARDSException

logger = logging.getLogger(__name__)


class MARDSController:
    """Main orchestrator for MARDS v2."""
    
    def __init__(
        self,
        deepseek_key: str,
        tavily_key: str,
        results_dir: Optional[str] = None,
        max_reflection_loops: int = 2,  # Reduced to 2 following DeepSearch
        uncertainty_threshold: float = 0.2,
        deterministic: bool = False
    ):
        """Initialize MARDS controller (DeepSearch mode: fewer searches).
        
        Args:
            deepseek_key: DeepSeek API key
            tavily_key: Tavily API key
            results_dir: Directory to save results
            max_reflection_loops: Maximum reflection loops per section (default 2)
            uncertainty_threshold: Threshold for proceeding without reflection
            deterministic: Enable deterministic mode
        """
        self.deepseek_key = deepseek_key
        self.tavily_key = tavily_key
        self.results_dir = Path(results_dir) if results_dir else Path("runs")
        self.max_reflection_loops = max_reflection_loops
        self.uncertainty_threshold = uncertainty_threshold
        self.deterministic = deterministic
        
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.task_id = str(uuid.uuid4())
        
        logger.info(f"MARDS Controller initialized (Task ID: {self.task_id})")
    
    async def run(
        self,
        query: str,
        enable_reflection: bool = True,
        save_intermediate: bool = True
    ) -> Dict[str, Any]:
        """Execute the full MARDS workflow.
        
        Args:
            query: User research query
            enable_reflection: Enable reflection loops
            save_intermediate: Save intermediate results
            
        Returns:
            Final report and metadata
        """
        logger.info(f"Starting MARDS workflow for query: {query}")
        
        try:
            async with DeepSeekClient(self.deepseek_key) as deepseek_client:
                async with TavilyClient(self.tavily_key) as tavily_client:
                    # Step 1: Plan report structure
                    logger.info("Step 1: Planning report structure...")
                    structure_agent = StructurePlannerAgent(deepseek_client)
                    structure_response = await structure_agent.execute(
                        task_id=self.task_id,
                        query=query
                    )
                    
                    structure_data = structure_response.output["structure"]
                    sections = [
                        Section(
                            section_id=sec["section_id"],
                            section_title=sec["section_title"],
                            objective=sec["objective"]
                        )
                        for sec in structure_data["sections"]
                    ]
                    
                    if save_intermediate:
                        self._save_result("01_structure", structure_response.to_dict())
                    
                    # Step 2-5: Process sections in parallel with reflection loops (fast mode)
                    logger.info(f"Step 2-5: Processing {len(sections)} sections in parallel...")
                    retriever_agent = SectionRetrieverAgent(tavily_client)
                    summarizer_agent = SectionSummarizerAgent(deepseek_client)
                    reflection_agent = ReflectionAgent(deepseek_client)
                    updater_agent = SectionUpdaterAgent(deepseek_client)
                    
                    # Process all sections in parallel
                    tasks = [
                        self._process_section(
                            section=section,
                            query=query,
                            retriever_agent=retriever_agent,
                            summarizer_agent=summarizer_agent,
                            reflection_agent=reflection_agent,
                            updater_agent=updater_agent,
                            tavily_client=tavily_client,
                            enable_reflection=enable_reflection,
                            save_intermediate=save_intermediate
                        )
                        for section in sections
                    ]
                    
                    await asyncio.gather(*tasks, return_exceptions=False)
                    
                    async def _process_section(
                        
                        section.sources = retrieval_response.output.get("sources", [])
                        section.confidence = retrieval_response.confidence
                        section.uncertainty = retrieval_response.uncertainty
                        
                        if save_intermediate:
                            self._save_result(
                                f"02_retrieval_{section.section_id}",
                                retrieval_response.to_dict()
                            )
                        
                        # Initial summarization
                        logger.info(f"  - Generating initial summary...")
                        summary_response = await summarizer_agent.execute(
                            task_id=self.task_id,
                            section=section,
                            query=query,
                            sources=section.sources
                        )
                        
                        section.initial_summary = summary_response.output.get("summary", "")
                        
                        if save_intermediate:
                            self._save_result(
                                f"03_summary_{section.section_id}",
                                summary_response.to_dict()
                            )
                        
                        # Reflection loops (max 2, DeepSearch mode)
                        if enable_reflection:
                            for reflection_loop in range(min(self.max_reflection_loops, 2)):  # Max 2 loops
                                logger.info(f"  - Reflection loop {reflection_loop + 1}/2")
                                
                                current_summary = section.final_summary or section.initial_summary
                                
                                # Reflection generates 1 query (DeepSearch mode)
                                reflection_response = await reflection_agent.execute(
                                    task_id=self.task_id,
                                    section=section,
                                    query=query,
                                    current_summary=current_summary
                                )
                                
                                search_query = reflection_response.output.get("search_query", "")
                                needs_search = reflection_response.output.get("needs_deeper_search", False)
                                
                                section.reflection_count += 1
                                
                                if save_intermediate:
                                    self._save_result(
                                        f"04_reflection_{section.section_id}_loop{reflection_loop}",
                                        reflection_response.to_dict()
                                    )
                                
                                if not needs_search or not search_query:
                                    logger.info(f"  - Reflection complete, no deeper search needed")
                                    break
                                
                                # Additional search (1 query, 3 results - DeepSearch mode)
                                logger.info(f"  - Performing reflection search: {search_query[:50]}...")
                                additional_results = await tavily_client.search(
                                    query=search_query,
                                    max_results=3  # Reduced to 3, DeepSearch mode
                                )
                                
                                additional_sources = [
                                    {
                                        "title": r.title,
                                        "url": r.url,
                                        "content": r.content[:500],
                                        "domain": r.domain,
                                        "score": r.score
                                    }
                                    for r in additional_results
                                ]
                                
                                # Update summary
                                logger.info(f"  - Updating summary with {len(additional_sources)} new sources...")
                                update_response = await updater_agent.execute(
                                    task_id=self.task_id,
                                    section=section,
                                    current_summary=current_summary,
                                    new_sources=additional_sources
                                )
                                
                                section.final_summary = update_response.output.get("updated_summary", "")
                                
                                if save_intermediate:
                                    self._save_result(
                                        f"05_update_{section.section_id}_loop{reflection_loop}",
                                        update_response.to_dict()
                                    )
                        
                        # Finalize section summary
                        if not section.final_summary:
                            section.final_summary = section.initial_summary
                    
                    # Step 6: Global uncertainty evaluation
                    logger.info("Step 6: Calculating global uncertainty...")
                    uncertainty_agent = GlobalUncertaintyAgent(deepseek_client)
                    uncertainty_response = await uncertainty_agent.execute(
                        task_id=self.task_id,
                        sections=sections
                    )
                    
                    global_uncertainty = uncertainty_response.output.get("global_uncertainty", 0.5)
                    
                    if save_intermediate:
                        self._save_result(
                            "06_uncertainty",
                            uncertainty_response.to_dict()
                        )
                    
                    # Step 7: Final formatting
                    logger.info("Step 7: Formatting final report...")
                    formatter_agent = FinalFormatterAgent(deepseek_client)
                    format_response = await formatter_agent.execute(
                        task_id=self.task_id,
                        title=structure_data.get("title", query),
                        sections=sections,
                        global_uncertainty=global_uncertainty
                    )
                    
                    if save_intermediate:
                        self._save_result(
                            "07_final_report",
                            format_response.to_dict()
                        )
                    
                    # Prepare final output
                    final_result = {
                        "task_id": self.task_id,
                        "query": query,
                        "timestamp": datetime.now().isoformat(),
                        "title": structure_data.get("title", query),
                        "report_markdown": format_response.output.get("report_markdown", ""),
                        "global_uncertainty": global_uncertainty,
                        "sections_count": len(sections),
                        "total_sources": sum(len(s.sources) for s in sections),
                        "total_reflections": sum(s.reflection_count for s in sections),
                        "status": "completed"
                    }
                    
                    # Save final result
                    final_path = self.results_dir / f"{self.task_id}_final.json"
                    with open(final_path, "w", encoding="utf-8") as f:
                        json.dump(final_result, f, ensure_ascii=False, indent=2)
                    
                    logger.info(f"MARDS workflow completed successfully")
                    logger.info(f"Results saved to: {final_path}")
                    
                    return final_result
        
        except Exception as e:
            logger.error(f"MARDS workflow error: {e}", exc_info=True)
            error_result = {
                "task_id": self.task_id,
                "query": query,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
            # Save error result
            error_path = self.results_dir / f"{self.task_id}_error.json"
            with open(error_path, "w", encoding="utf-8") as f:
                json.dump(error_result, f, ensure_ascii=False, indent=2)
            
            raise
    
    def _save_result(self, step_name: str, data: Dict[str, Any]):
        """Save intermediate result.
        
        Args:
            step_name: Step identifier
            data: Data to save
        """
        try:
            filepath = self.results_dir / f"{self.task_id}_{step_name}.json"
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save result for {step_name}: {e}")


async def main_workflow():
    """Example workflow execution."""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="MARDS v2: Paragraph-level Reflective Deep Search")
    parser.add_argument("--deepseek_key", required=True, help="DeepSeek API key")
    parser.add_argument("--tavily_key", required=True, help="Tavily API key")
    parser.add_argument("--query", required=True, help="Research query")
    parser.add_argument("--results_dir", default="runs", help="Results directory")
    parser.add_argument("--max_reflection_loops", type=int, default=3, help="Max reflection loops")
    parser.add_argument("--uncertainty_threshold", type=float, default=0.2, help="Uncertainty threshold")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run MARDS
    controller = MARDSController(
        deepseek_key=args.deepseek_key,
        tavily_key=args.tavily_key,
        results_dir=args.results_dir,
        max_reflection_loops=args.max_reflection_loops,
        uncertainty_threshold=args.uncertainty_threshold
    )
    
    result = await controller.run(
        query=args.query,
        enable_reflection=True,
        save_intermediate=True
    )
    
    print("\n" + "="*80)
    print("MARDS WORKFLOW COMPLETED")
    print("="*80)
    print(f"\nReport:\n{result['report_markdown']}")
    print(f"\n\nGlobal Uncertainty: {result['global_uncertainty']:.2%}")
    print(f"Task ID: {result['task_id']}")


if __name__ == "__main__":
    asyncio.run(main_workflow())
