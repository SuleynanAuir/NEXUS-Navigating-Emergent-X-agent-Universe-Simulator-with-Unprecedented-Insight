#!/usr/bin/env python3
"""
Simple test runner for MARDS v2.
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from v2_paragraph_reflective.schema import (
    AgentResponse, Section, ReportStructure, SearchResult,
    ReflectionEvaluation, GlobalUncertaintyResult
)
from v2_paragraph_reflective.base import BaseAgent, PromptManager
from v2_paragraph_reflective.clients import MetricsCalculator


def test_basic_types():
    """Test basic type creation."""
    # Test AgentResponse
    response = AgentResponse(
        task_id="test_123",
        agent_role="TestAgent",
        section="sec_1",
        output={"test": "data"},
        confidence=0.9,
        uncertainty=0.1
    )
    assert response.task_id == "test_123"
    print("✓ AgentResponse creation test passed")
    
    # Test Section
    section = Section(
        section_id="sec_1",
        section_title="Test Section",
        objective="Test objective"
    )
    assert section.section_id == "sec_1"
    print("✓ Section creation test passed")
    
    # Test SearchResult
    result = SearchResult(
        title="Test Article",
        url="https://example.com/article",
        content="Test content",
        domain="example.com",
        score=0.95
    )
    assert result.domain == "example.com"
    print("✓ SearchResult creation test passed")


def test_metrics():
    """Test metrics calculation."""
    results = [
        SearchResult("Title 1", "url1", "content", score=0.9),
        SearchResult("Title 2", "url2", "content", score=0.7),
        SearchResult("Title 3", "url3", "content", score=0.5),
    ]
    
    ndcg = MetricsCalculator.calculate_ndcg(results)
    assert 0 <= ndcg <= 1
    print(f"✓ NDCG calculation test passed (NDCG={ndcg:.3f})")
    
    mrr = MetricsCalculator.calculate_mrr(results, threshold=0.5)
    assert 0 <= mrr <= 1
    print(f"✓ MRR calculation test passed (MRR={mrr:.3f})")
    
    # Test diversity
    results_div = [
        SearchResult("Title 1", "url1", "content", domain="domain1.com"),
        SearchResult("Title 2", "url2", "content", domain="domain2.com"),
        SearchResult("Title 3", "url3", "content", domain="domain1.com"),
    ]
    diversity = MetricsCalculator.calculate_source_diversity(results_div)
    assert diversity == 2/3
    print(f"✓ Source diversity test passed (diversity={diversity:.3f})")


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("MARDS v2 Quick Tests")
    print("="*60 + "\n")
    
    try:
        test_basic_types()
        print()
        test_metrics()
        
        print("\n" + "="*60)
        print("✓ All tests passed!")
        print("="*60 + "\n")
        return 0
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
