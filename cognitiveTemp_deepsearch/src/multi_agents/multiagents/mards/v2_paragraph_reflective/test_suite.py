"""
Test suite for MARDS v2.
"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

import asyncio
import json
import logging
from typing import Dict, Any

from schema import (
    AgentResponse, Section, ReportStructure, SearchResult,
    ReflectionEvaluation, GlobalUncertaintyResult
)
from base import BaseAgent, PromptManager
from clients import MetricsCalculator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestSuite:
    """Test suite for MARDS v2."""
    
    def __init__(self):
        self.test_results = []
        self.passed = 0
        self.failed = 0
    
    def test_agent_response_creation(self):
        """Test AgentResponse creation and serialization."""
        try:
            response = AgentResponse(
                task_id="test_123",
                agent_role="TestAgent",
                section="sec_1",
                output={"test": "data"},
                confidence=0.9,
                uncertainty=0.1,
                needs_reflection=False
            )
            
            # Test serialization
            response_dict = response.to_dict()
            assert response_dict["task_id"] == "test_123"
            assert response_dict["agent_role"] == "TestAgent"
            assert response_dict["confidence"] == 0.9
            
            # Test JSON
            response_json = response.to_json()
            assert isinstance(response_json, str)
            
            # Test deserialization
            response_restored = AgentResponse.from_dict(response_dict)
            assert response_restored.task_id == "test_123"
            
            self.passed += 1
            logger.info("✓ test_agent_response_creation passed")
        except Exception as e:
            self.failed += 1
            logger.error(f"✗ test_agent_response_creation failed: {e}")
    
    def test_section_creation(self):
        """Test Section creation and serialization."""
        try:
            section = Section(
                section_id="sec_1",
                section_title="Test Section",
                objective="Test objective",
                confidence=0.85,
                uncertainty=0.15
            )
            
            assert section.section_id == "sec_1"
            assert section.confidence == 0.85
            assert len(section.reflection_history) == 0
            
            self.passed += 1
            logger.info("✓ test_section_creation passed")
        except Exception as e:
            self.failed += 1
            logger.error(f"✗ test_section_creation failed: {e}")
    
    def test_report_structure_creation(self):
        """Test ReportStructure creation."""
        try:
            sections = [
                Section(f"sec_{i}", f"Section {i}", f"Objective {i}")
                for i in range(5)
            ]
            
            structure = ReportStructure(
                title="Test Report",
                query="test query",
                sections=sections,
                objective="Test objective"
            )
            
            assert len(structure.sections) == 5
            assert structure.title == "Test Report"
            
            # Test to_dict
            structure_dict = structure.to_dict()
            assert structure_dict["title"] == "Test Report"
            assert len(structure_dict["sections"]) == 5
            
            self.passed += 1
            logger.info("✓ test_report_structure_creation passed")
        except Exception as e:
            self.failed += 1
            logger.error(f"✗ test_report_structure_creation failed: {e}")
    
    def test_search_result_creation(self):
        """Test SearchResult creation."""
        try:
            result = SearchResult(
                title="Test Article",
                url="https://example.com/article",
                content="Test content",
                domain="example.com",
                score=0.95,
                relevance=0.87
            )
            
            assert result.title == "Test Article"
            assert result.domain == "example.com"
            assert result.score == 0.95
            
            self.passed += 1
            logger.info("✓ test_search_result_creation passed")
        except Exception as e:
            self.failed += 1
            logger.error(f"✗ test_search_result_creation failed: {e}")
    
    def test_reflection_evaluation_creation(self):
        """Test ReflectionEvaluation creation."""
        try:
            evaluation = ReflectionEvaluation(
                missing_perspectives=["perspective1", "perspective2"],
                weak_evidence_areas=["area1"],
                bias_risks=["risk1", "risk2"],
                needs_deeper_search=True,
                recommended_search_queries=["query1", "query2"],
                confidence=0.75
            )
            
            assert len(evaluation.missing_perspectives) == 2
            assert evaluation.needs_deeper_search
            assert len(evaluation.recommended_search_queries) == 2
            
            self.passed += 1
            logger.info("✓ test_reflection_evaluation_creation passed")
        except Exception as e:
            self.failed += 1
            logger.error(f"✗ test_reflection_evaluation_creation failed: {e}")
    
    def test_global_uncertainty_result(self):
        """Test GlobalUncertaintyResult creation."""
        try:
            result = GlobalUncertaintyResult(
                global_uncertainty=0.25,
                section_uncertainties={"sec_1": 0.2, "sec_2": 0.3},
                average_confidence=0.75,
                recommendation="reflect",
                reasoning="Some sections need refinement",
                reflection_needed=True
            )
            
            assert result.global_uncertainty == 0.25
            assert result.recommendation == "reflect"
            assert len(result.section_uncertainties) == 2
            
            self.passed += 1
            logger.info("✓ test_global_uncertainty_result passed")
        except Exception as e:
            self.failed += 1
            logger.error(f"✗ test_global_uncertainty_result failed: {e}")
    
    def test_metrics_ndcg(self):
        """Test NDCG calculation."""
        try:
            results = [
                SearchResult("Title 1", "url1", "content", score=0.9),
                SearchResult("Title 2", "url2", "content", score=0.7),
                SearchResult("Title 3", "url3", "content", score=0.5),
            ]
            
            ndcg = MetricsCalculator.calculate_ndcg(results)
            assert 0 <= ndcg <= 1
            assert ndcg > 0
            
            self.passed += 1
            logger.info(f"✓ test_metrics_ndcg passed (NDCG={ndcg:.3f})")
        except Exception as e:
            self.failed += 1
            logger.error(f"✗ test_metrics_ndcg failed: {e}")
    
    def test_metrics_mrr(self):
        """Test MRR calculation."""
        try:
            results = [
                SearchResult("Title 1", "url1", "content", score=0.3),
                SearchResult("Title 2", "url2", "content", score=0.8),
                SearchResult("Title 3", "url3", "content", score=0.6),
            ]
            
            mrr = MetricsCalculator.calculate_mrr(results, threshold=0.5)
            assert 0 <= mrr <= 1
            assert mrr == 0.5  # Second result exceeds threshold
            
            self.passed += 1
            logger.info(f"✓ test_metrics_mrr passed (MRR={mrr:.3f})")
        except Exception as e:
            self.failed += 1
            logger.error(f"✗ test_metrics_mrr failed: {e}")
    
    def test_metrics_source_diversity(self):
        """Test source diversity calculation."""
        try:
            results = [
                SearchResult("Title 1", "url1", "content", domain="domain1.com"),
                SearchResult("Title 2", "url2", "content", domain="domain2.com"),
                SearchResult("Title 3", "url3", "content", domain="domain1.com"),
            ]
            
            diversity = MetricsCalculator.calculate_source_diversity(results)
            assert 0 <= diversity <= 1
            assert diversity == 2/3  # 2 unique domains out of 3 results
            
            self.passed += 1
            logger.info(f"✓ test_metrics_source_diversity passed (diversity={diversity:.3f})")
        except Exception as e:
            self.failed += 1
            logger.error(f"✗ test_metrics_source_diversity failed: {e}")
    
    def test_metrics_reflection_depth(self):
        """Test reflection depth calculation."""
        try:
            depth1 = MetricsCalculator.calculate_reflection_depth(1, 3)
            depth2 = MetricsCalculator.calculate_reflection_depth(2, 3)
            depth3 = MetricsCalculator.calculate_reflection_depth(3, 3)
            depth4 = MetricsCalculator.calculate_reflection_depth(4, 3)  # Capped at 1.0
            
            assert depth1 < depth2 < depth3
            assert depth4 == 1.0
            
            self.passed += 1
            logger.info(f"✓ test_metrics_reflection_depth passed")
        except Exception as e:
            self.failed += 1
            logger.error(f"✗ test_metrics_reflection_depth failed: {e}")
    
    def test_prompt_manager_registration(self):
        """Test PromptManager registration and retrieval."""
        try:
            test_prompt = "This is a test prompt with {variable}"
            PromptManager.register_prompt("test_agent", test_prompt)
            
            retrieved_prompt = PromptManager.get_prompt("test_agent")
            assert retrieved_prompt == test_prompt
            
            rendered_prompt = PromptManager.render_prompt("test_agent", variable="value")
            assert "value" in rendered_prompt
            
            self.passed += 1
            logger.info("✓ test_prompt_manager_registration passed")
        except Exception as e:
            self.failed += 1
            logger.error(f"✗ test_prompt_manager_registration failed: {e}")
    
    def test_base_agent_response_creation(self):
        """Test BaseAgent response creation utility."""
        try:
            agent = BaseAgent("TestAgent", __name__)
            response = agent._create_response(
                task_id="test_123",
                section="sec_1",
                output={"key": "value"},
                confidence=0.9,
                uncertainty=0.1
            )
            
            assert response.agent_role == "TestAgent"
            assert response.output == {"key": "value"}
            
            self.passed += 1
            logger.info("✓ test_base_agent_response_creation passed")
        except Exception as e:
            self.failed += 1
            logger.error(f"✗ test_base_agent_response_creation failed: {e}")
    
    def test_json_validation(self):
        """Test JSON validation."""
        try:
            agent = BaseAgent("TestAgent", __name__)
            
            # Valid JSON
            valid_json = '{"key": "value"}'
            result = agent._validate_json(valid_json)
            assert result["key"] == "value"
            
            # JSON with extra text (should extract JSON)
            json_with_text = 'Some text before {"key": "value"} some text after'
            result = agent._validate_json(json_with_text)
            assert result["key"] == "value"
            
            self.passed += 1
            logger.info("✓ test_json_validation passed")
        except Exception as e:
            self.failed += 1
            logger.error(f"✗ test_json_validation failed: {e}")
    
    def run_all_tests(self):
        """Run all tests."""
        logger.info("Starting MARDS v2 Test Suite")
        logger.info("=" * 60)
        
        # Run tests
        self.test_agent_response_creation()
        self.test_section_creation()
        self.test_report_structure_creation()
        self.test_search_result_creation()
        self.test_reflection_evaluation_creation()
        self.test_global_uncertainty_result()
        self.test_metrics_ndcg()
        self.test_metrics_mrr()
        self.test_metrics_source_diversity()
        self.test_metrics_reflection_depth()
        self.test_prompt_manager_registration()
        self.test_base_agent_response_creation()
        self.test_json_validation()
        
        # Print summary
        logger.info("=" * 60)
        total = self.passed + self.failed
        logger.info(f"Tests Completed: {total}")
        logger.info(f"Passed: {self.passed}")
        logger.info(f"Failed: {self.failed}")
        
        if self.failed == 0:
            logger.info("✓ All tests passed!")
            return 0
        else:
            logger.error(f"✗ {self.failed} test(s) failed")
            return 1


def main():
    """Run test suite."""
    suite = TestSuite()
    return suite.run_all_tests()


if __name__ == "__main__":
    sys.exit(main())
