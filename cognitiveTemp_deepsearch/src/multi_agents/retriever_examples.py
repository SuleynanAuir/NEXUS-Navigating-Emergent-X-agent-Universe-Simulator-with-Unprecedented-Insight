"""
Examples demonstrating Retriever Agent usage.
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.multi_agents.agents.retriever_agent import create_retriever
from src.multi_agents.utils.json_parser import format_decomposition_output


def example_basic_retrieval():
    """Basic retrieval example."""
    print("=" * 80)
    print("EXAMPLE 1: Basic Retrieval")
    print("=" * 80)
    
    retriever = create_retriever()
    
    query = "Latest developments in artificial intelligence"
    print(f"\n📝 Query: {query}\n")
    
    # Retrieve sources
    result = retriever.retrieve(query)
    
    # Validate
    is_valid, errors = retriever.validate_retrieval_result(result)
    
    if not is_valid:
        print("❌ Validation errors:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("✅ Retrieval validated successfully!")
    
    # Display results
    print(f"\n📊 Retrieved {len(result.results)} sources")
    print(f"🎯 Diversity Score: {result.diversity_score}")
    print(f"📈 Retrieval Confidence: {result.retrieval_confidence}")
    print(f"\n📋 Domain Distribution:")
    for domain, count in result.domain_distribution.items():
        print(f"  • {domain}: {count}")
    
    # Display sources
    print(f"\n📚 Retrieved Sources:")
    for i, source in enumerate(result.results, 1):
        print(f"\n  {i}. {source.title}")
        print(f"     Source: {source.source}")
        print(f"     Domain: {source.domain_type}")
        print(f"     Credibility: {source.credibility_score}/1.0")
        print(f"     Relevance: {source.relevance_score}/1.0")
        if source.uncertainty_marked:
            print(f"     ⚠️  [UNCERTAIN]")
        print(f"     Summary: {source.summary[:60]}...")


def example_diversity_comparison():
    """Compare diversity across different queries."""
    print("\n\n" + "=" * 80)
    print("EXAMPLE 2: Diversity Comparison Across Queries")
    print("=" * 80)
    
    retriever = create_retriever()
    
    queries = [
        "machine learning algorithms",
        "blockchain and cryptocurrency",
        "climate change solutions",
    ]
    
    results_data = []
    
    for query in queries:
        print(f"\n--- {query} ---")
        result = retriever.retrieve(query)
        results_data.append(result)
        
        domains = set(s.domain_type for s in result.results)
        print(f"✅ Sources: {len(result.results)}")
        print(f"🎯 Diversity: {result.diversity_score}")
        print(f"📈 Confidence: {result.retrieval_confidence}")
        print(f"📊 Domains: {', '.join(sorted(domains))}")
    
    # Comparison summary
    print(f"\n{'=' * 80}")
    print("DIVERSITY SUMMARY:")
    print(f"{'Query':<35} {'Diversity':<12} {'Confidence':<12}")
    print("-" * 80)
    for result in results_data:
        print(f"{result.query_used[:34]:<35} {result.diversity_score:<12} {result.retrieval_confidence:<12}")


def example_domain_analysis():
    """Detailed domain analysis."""
    print("\n\n" + "=" * 80)
    print("EXAMPLE 3: Domain Analysis")
    print("=" * 80)
    
    retriever = create_retriever()
    
    query = "artificial intelligence safety and ethics"
    print(f"\n📝 Query: {query}\n")
    
    result = retriever.retrieve(query)
    
    # Analyze sources by domain
    sources_by_domain = {}
    for source in result.results:
        if source.domain_type not in sources_by_domain:
            sources_by_domain[source.domain_type] = []
        sources_by_domain[source.domain_type].append(source)
    
    print("📊 SOURCES BY DOMAIN:\n")
    for domain, sources in sorted(sources_by_domain.items()):
        print(f"{domain.upper()} ({len(sources)} sources):")
        
        avg_credibility = sum(s.credibility_score for s in sources) / len(sources)
        avg_relevance = sum(s.relevance_score for s in sources) / len(sources)
        
        print(f"  Average Credibility: {avg_credibility:.2f}")
        print(f"  Average Relevance: {avg_relevance:.2f}")
        
        for source in sources:
            print(f"  • {source.title}")
            print(f"    By: {source.source}")
        print()


def example_credibility_analysis():
    """Analyze credibility of retrieved sources."""
    print("\n\n" + "=" * 80)
    print("EXAMPLE 4: Credibility Analysis")
    print("=" * 80)
    
    retriever = create_retriever()
    
    query = "research on deep learning"
    print(f"\n📝 Query: {query}\n")
    
    result = retriever.retrieve(query)
    
    # Sort by credibility
    sorted_sources = sorted(result.results, key=lambda s: s.credibility_score, reverse=True)
    
    print("📈 SOURCES BY CREDIBILITY:\n")
    
    for i, source in enumerate(sorted_sources, 1):
        # Credibility level indicator
        if source.credibility_score >= 0.9:
            level = "⭐⭐⭐ Very High"
        elif source.credibility_score >= 0.8:
            level = "⭐⭐ High"
        elif source.credibility_score >= 0.7:
            level = "⭐ Medium-High"
        else:
            level = "Medium"
        
        print(f"{i}. {source.title}")
        print(f"   Credibility: {source.credibility_score:.2f} - {level}")
        print(f"   Domain: {source.domain_type}")
        print(f"   By: {source.source}")
        print()


def example_relevance_ranking():
    """Rank sources by relevance."""
    print("\n\n" + "=" * 80)
    print("EXAMPLE 5: Relevance Ranking")
    print("=" * 80)
    
    retriever = create_retriever()
    
    query = "natural language processing applications"
    print(f"\n📝 Query: {query}\n")
    
    result = retriever.retrieve(query)
    
    # Sort by relevance
    sorted_sources = sorted(result.results, key=lambda s: s.relevance_score, reverse=True)
    
    print("🎯 SOURCES BY RELEVANCE:\n")
    
    for i, source in enumerate(sorted_sources, 1):
        # Relevance level
        if source.relevance_score >= 0.8:
            level = "🔥 Highly Relevant"
        elif source.relevance_score >= 0.6:
            level = "✅ Relevant"
        elif source.relevance_score >= 0.4:
            level = "⚠️  Moderately Relevant"
        else:
            level = "❓ Weakly Relevant"
        
        print(f"{i}. {source.title}")
        print(f"   Relevance: {source.relevance_score:.2f} - {level}")
        print(f"   Summary: {source.summary}")
        print()


def example_json_export():
    """Export retrieval result as JSON."""
    print("\n\n" + "=" * 80)
    print("EXAMPLE 6: JSON Export")
    print("=" * 80)
    
    retriever = create_retriever()
    
    query = "quantum computing breakthrough"
    print(f"\n📝 Query: {query}\n")
    
    result = retriever.retrieve(query)
    
    # Export to JSON
    json_str = result.to_json()
    
    print("✅ Export as JSON:")
    print(json_str[:800] + "\n...")
    
    # Save to file
    output_path = Path(__file__).parent / "retrieval_example.json"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(json_str)
    
    print(f"\n💾 Saved to: {output_path}")


def example_quality_metrics():
    """Display quality metrics for retrieval."""
    print("\n\n" + "=" * 80)
    print("EXAMPLE 7: Quality Metrics")
    print("=" * 80)
    
    retriever = create_retriever()
    
    query = "COVID-19 pandemic response strategies"
    print(f"\n📝 Query: {query}\n")
    
    result = retriever.retrieve(query)
    
    # Calculate metrics
    avg_credibility = sum(s.credibility_score for s in result.results) / len(result.results)
    avg_relevance = sum(s.relevance_score for s in result.results) / len(result.results)
    has_academic = any(s.domain_type == "academic" for s in result.results)
    distinct_domains = len(set(s.domain_type for s in result.results))
    uncertain_count = sum(1 for s in result.results if s.uncertainty_marked)
    
    print("📊 RETRIEVAL QUALITY METRICS:\n")
    print(f"Overall Metrics:")
    print(f"  • Total Sources: {len(result.results)}")
    print(f"  • Distinct Domains: {distinct_domains}")
    print(f"  • Has Academic Source: {'✅ Yes' if has_academic else '❌ No'}")
    print(f"  • Uncertain Sources: {uncertain_count}")
    
    print(f"\nScore Metrics:")
    print(f"  • Average Credibility: {avg_credibility:.2f}/1.0")
    print(f"  • Average Relevance: {avg_relevance:.2f}/1.0")
    print(f"  • Diversity Score: {result.diversity_score:.2f}")
    print(f"  • Retrieval Confidence: {result.retrieval_confidence:.2f}")
    
    print(f"\nQuality Assessment:")
    
    if result.retrieval_confidence >= 0.8:
        quality = "🟢 Excellent"
    elif result.retrieval_confidence >= 0.6:
        quality = "🟡 Good"
    elif result.retrieval_confidence >= 0.4:
        quality = "🟠 Fair"
    else:
        quality = "🔴 Poor"
    
    print(f"  • Overall Quality: {quality}")


if __name__ == "__main__":
    # Run all examples
    example_basic_retrieval()
    example_diversity_comparison()
    example_domain_analysis()
    example_credibility_analysis()
    example_relevance_ranking()
    example_json_export()
    example_quality_metrics()
    
    print("\n" + "=" * 80)
    print("✅ All Retriever Agent examples completed!")
    print("=" * 80)
