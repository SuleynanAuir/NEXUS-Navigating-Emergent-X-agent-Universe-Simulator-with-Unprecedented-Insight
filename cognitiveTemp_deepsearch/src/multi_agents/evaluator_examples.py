"""
Examples demonstrating Evidence Evaluator Agent usage.
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.multi_agents.agents.evaluator_agent import create_evaluator


def example_basic_evaluation():
    """Basic evidence evaluation example."""
    print("=" * 80)
    print("EXAMPLE 1: Basic Evidence Evaluation")
    print("=" * 80)
    
    evaluator = create_evaluator()
    
    sources = [
        {
            "title": "AI Research Report",
            "summary": "A comprehensive study of 10,000 participants shows that machine learning models achieve 95% accuracy in medical diagnosis.",
            "source": "Nature Medical"
        },
        {
            "title": "Industry Analysis",
            "summary": "Recent market data indicates AI adoption in healthcare has increased by 150% over the past two years.",
            "source": "McKinsey"
        }
    ]
    
    print(f"\n📝 Evaluating {len(sources)} sources\n")
    
    # Evaluate
    result = evaluator.evaluate(sources)
    
    # Validate
    is_valid, errors = evaluator.validate_evaluation_result(result)
    
    if is_valid:
        print("✅ Evaluation validated successfully!\n")
    else:
        print("❌ Validation errors:")
        for error in errors:
            print(f"  - {error}\n")
    
    # Display claims
    print(f"📋 Extracted {len(result.claims)} Claims:\n")
    for i, claim in enumerate(result.claims, 1):
        strength_emoji = "💪" if claim.strength == "strong" else "🟡" if claim.strength == "moderate" else "⚠️"
        print(f"{i}. {strength_emoji} {claim.statement}")
        print(f"   Type: {claim.evidence_type}")
        print(f"   Strength: {claim.strength}")
        print(f"   Rigor: {claim.methodological_rigor:.2f}")
        print()
    
    # Display contradictions
    if result.contradictions:
        print(f"\n⚡ Detected {len(result.contradictions)} Contradictions:\n")
        for i, contradiction in enumerate(result.contradictions, 1):
            print(f"{i}. Severity: {contradiction.severity:.2f}")
            print(f"   Claim 1: {contradiction.claim_1}")
            print(f"   Claim 2: {contradiction.claim_2}")
            print(f"   Type: {contradiction.contradiction_type}")
            print(f"   Explanation: {contradiction.explanation}\n")
    else:
        print("\n✅ No contradictions detected!\n")
    
    # Display overall scores
    print(f"📊 Overall Assessment:")
    print(f"  • Overall Strength Score: {result.overall_strength_score:.2f}/1.0")
    print(f"  • Evidence Uncertainty: {result.evidence_uncertainty:.2f}/1.0")
    print(f"  • Total Sources Analyzed: {result.total_sources_analyzed}")
    print(f"  • Evidence Distribution: {result.evidence_distribution}")
    print(f"  • Strength Distribution: {result.strength_distribution}")


def example_corroborated_evidence():
    """Example with corroborated evidence."""
    print("\n\n" + "=" * 80)
    print("EXAMPLE 2: Corroborated Evidence")
    print("=" * 80)
    
    evaluator = create_evaluator()
    
    sources = [
        {
            "title": "Climate Study 2024",
            "summary": "Global temperatures have increased by 1.1°C since pre-industrial times.",
            "source": "IPCC Report"
        },
        {
            "title": "Peer Review Analysis",
            "summary": "Multiple independent studies confirm global warming with temperature rise of approximately 1°C.",
            "source": "Nature Climate Change"
        },
        {
            "title": "Historical Data Analysis",
            "summary": "Temperature records from 150 years show consistent upward trend.",
            "source": "NASA"
        }
    ]
    
    print(f"\n📝 Analyzing {len(sources)} correlated sources\n")
    result = evaluator.evaluate(sources)
    
    # Find corroborated claims
    strong_claims = [c for c in result.claims if c.strength == "strong"]
    
    print(f"✅ Strong Claims ({len(strong_claims)}):")
    for claim in strong_claims:
        print(f"  • {claim.statement}")
        print(f"    Supporting sources: {len(claim.supporting_sources)}")
    
    print(f"\n📈 Corroboration Analysis:")
    avg_corroboration = sum(c.corroboration_level for c in result.claims) / len(result.claims) if result.claims else 0
    print(f"  • Average Corroboration Level: {avg_corroboration:.2f}")
    print(f"  • Overall Strength: {result.overall_strength_score:.2f}")


def example_contradictory_evidence():
    """Example with contradictory evidence."""
    print("\n\n" + "=" * 80)
    print("EXAMPLE 3: Contradictory Evidence Detection")
    print("=" * 80)
    
    evaluator = create_evaluator()
    
    sources = [
        {
            "title": "Study A",
            "summary": "Our research shows the treatment is highly effective with 80% success rate.",
            "source": "Research Lab A"
        },
        {
            "title": "Study B",
            "summary": "Contradicting findings indicate the treatment shows minimal effectiveness.",
            "source": "Research Lab B"
        },
        {
            "title": "Industry Report",
            "summary": "Market data does not support wide adoption due to effectiveness concerns.",
            "source": "Industry Analyst"
        }
    ]
    
    print(f"\n📝 Analyzing {len(sources)} sources for contradictions\n")
    result = evaluator.evaluate(sources)
    
    # Display contradictions
    print(f"⚡ Contradictions Detected: {len(result.contradictions)}\n")
    
    for i, contradiction in enumerate(result.contradictions, 1):
        print(f"Contradiction {i}:")
        print(f"  Type: {contradiction.contradiction_type}")
        print(f"  Severity: {contradiction.severity:.2f}/1.0")
        print(f"  Claim 1: {contradiction.claim_1[:50]}...")
        print(f"  Claim 2: {contradiction.claim_2[:50]}...")
        print(f"  Explanation: {contradiction.explanation}\n")
    
    print(f"⚠️  Overall Quality:")
    print(f"  • Strength Score: {result.overall_strength_score:.2f} (affected by contradictions)")
    print(f"  • Uncertainty: {result.evidence_uncertainty:.2f} (high due to conflicts)")


def example_evidence_type_analysis():
    """Analyze evidence types distribution."""
    print("\n\n" + "=" * 80)
    print("EXAMPLE 4: Evidence Type Analysis")
    print("=" * 80)
    
    evaluator = create_evaluator()
    
    sources = [
        {
            "title": "Statistical Analysis",
            "summary": "The data shows 73% improvement in performance metrics.",
            "source": "Data Research"
        },
        {
            "title": "Theoretical Framework",
            "summary": "The proposed model demonstrates fundamental principles.",
            "source": "Academic Theory"
        },
        {
            "title": "Expert Interview",
            "summary": "Dr. Jane Smith states the approach is groundbreaking.",
            "source": "Interview"
        },
        {
            "title": "Case Study",
            "summary": "Company X implemented the solution achieving results.",
            "source": "Business Case"
        }
    ]
    
    print(f"\n📝 Analyzing {len(sources)} diverse sources\n")
    result = evaluator.evaluate(sources)
    
    print(f"📊 Evidence Type Distribution:")
    for evidence_type, count in sorted(result.evidence_distribution.items()):
        print(f"  • {evidence_type}: {count}")
    
    print(f"\n💪 Strength Distribution:")
    for strength, count in sorted(result.strength_distribution.items()):
        print(f"  • {strength}: {count}")
    
    print(f"\n📋 Claims by Type:")
    for claim in result.claims:
        print(f"  • [{claim.evidence_type:15}] {claim.statement[:50]}...")


def example_methodological_rigor():
    """Analyze methodological rigor."""
    print("\n\n" + "=" * 80)
    print("EXAMPLE 5: Methodological Rigor Analysis")
    print("=" * 80)
    
    evaluator = create_evaluator()
    
    sources = [
        {
            "title": "Peer-Reviewed Study",
            "summary": "Double-blind randomized controlled trial with 5000 participants published in Nature.",
            "source": "Nature Journal"
        },
        {
            "title": "Blog Post",
            "summary": "I think this is probably true based on what I read somewhere.",
            "source": "Personal Blog"
        },
        {
            "title": "Industry Report",
            "summary": "Survey of 500 companies shows adoption patterns.",
            "source": "Analyst Report"
        }
    ]
    
    print(f"\n📝 Analyzing methodological quality\n")
    result = evaluator.evaluate(sources)
    
    print(f"🔬 Methodological Rigor Analysis:\n")
    
    # Sort by rigor
    sorted_claims = sorted(result.claims, key=lambda c: c.methodological_rigor, reverse=True)
    
    for i, claim in enumerate(sorted_claims, 1):
        rigor_pct = claim.methodological_rigor * 100
        rigor_level = "High" if rigor_pct >= 70 else "Medium" if rigor_pct >= 40 else "Low"
        
        print(f"{i}. Rigor: {rigor_pct:.0f}% ({rigor_level})")
        print(f"   Claim: {claim.statement[:60]}...")
        print(f"   Type: {claim.evidence_type}")
        print()


def example_strength_assessment():
    """Detailed strength assessment."""
    print("\n\n" + "=" * 80)
    print("EXAMPLE 6: Evidence Strength Assessment")
    print("=" * 80)
    
    evaluator = create_evaluator()
    
    sources = [
        {
            "title": "Robust Research",
            "summary": "Meta-analysis of 50 studies shows consistent results across populations.",
            "source": "Cochrane Review"
        },
        {
            "title": "Single Study",
            "summary": "A small pilot study suggests potential benefits.",
            "source": "Preliminary Study"
        },
        {
            "title": "Personal Account",
            "summary": "This worked for me, so everyone should try it.",
            "source": "Forum Post"
        }
    ]
    
    print(f"\n📝 Assessing evidence strength\n")
    result = evaluator.evaluate(sources)
    
    print(f"💪 Evidence Strength Breakdown:\n")
    
    strength_details = {
        "strong": {"emoji": "💪", "description": "High confidence", "threshold": 0.7},
        "moderate": {"emoji": "🟡", "description": "Medium confidence", "threshold": 0.4},
        "weak": {"emoji": "⚠️", "description": "Low confidence", "threshold": 0.0}
    }
    
    for strength_level in ["strong", "moderate", "weak"]:
        claims = [c for c in result.claims if c.strength == strength_level]
        details = strength_details[strength_level]
        
        print(f"{details['emoji']} {strength_level.upper()} ({details['description']})")
        print(f"   Count: {len(claims)}")
        
        for claim in claims:
            print(f"   • {claim.statement[:50]}...")
        print()


def example_json_export():
    """Export evaluation results as JSON."""
    print("\n\n" + "=" * 80)
    print("EXAMPLE 7: JSON Export")
    print("=" * 80)
    
    evaluator = create_evaluator()
    
    sources = [
        {
            "title": "Important Study",
            "summary": "Research demonstrates significant findings with 95% confidence.",
            "source": "Journal"
        }
    ]
    
    print(f"\n📝 Evaluating and exporting results\n")
    result = evaluator.evaluate(sources)
    
    # Export to JSON
    json_str = result.to_json()
    
    print("✅ Exported as JSON:\n")
    print(json_str[:600] + "\n...")
    
    # Save to file
    output_path = Path(__file__).parent / "evaluation_example.json"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(json_str)
    
    print(f"\n💾 Saved to: {output_path}")


def example_comprehensive_analysis():
    """Comprehensive evidence analysis."""
    print("\n\n" + "=" * 80)
    print("EXAMPLE 8: Comprehensive Analysis")
    print("=" * 80)
    
    evaluator = create_evaluator()
    
    sources = [
        {
            "title": "Clinical Trial Results",
            "summary": "Randomized trial of 3000 patients shows treatment reduces symptoms by 60%.",
            "source": "Medical Journal"
        },
        {
            "title": "Follow-up Study",
            "summary": "Two-year follow-up confirms sustained benefits in 85% of patients.",
            "source": "Medicine Today"
        },
        {
            "title": "Cost Analysis",
            "summary": "Economic analysis shows treatment is cost-effective at $5000 per patient.",
            "source": "Health Economics"
        },
        {
            "title": "Expert Commentary",
            "summary": "Leading researchers praise the study methodology as rigorous and unbiased.",
            "source": "Medical Commentary"
        },
        {
            "title": "Manufacturer Claim",
            "summary": "Company claims their product provides superior results.",
            "source": "Company Website"
        }
    ]
    
    print(f"\n📝 Comprehensive evaluation of {len(sources)} sources\n")
    result = evaluator.evaluate(sources)
    
    print(f"📊 COMPREHENSIVE ANALYSIS RESULTS:\n")
    
    print(f"Overview:")
    print(f"  • Total Claims Extracted: {len(result.claims)}")
    print(f"  • Contradictions Found: {len(result.contradictions)}")
    print(f"  • Overall Strength: {result.overall_strength_score:.2f}/1.0")
    print(f"  • Uncertainty Level: {result.evidence_uncertainty:.2f}/1.0")
    
    print(f"\nEvidence Quality:")
    strong_count = sum(1 for c in result.claims if c.strength == "strong")
    moderate_count = sum(1 for c in result.claims if c.strength == "moderate")
    weak_count = sum(1 for c in result.claims if c.strength == "weak")
    
    print(f"  • Strong Evidence: {strong_count} ({strong_count/len(result.claims)*100:.0f}%)")
    print(f"  • Moderate Evidence: {moderate_count} ({moderate_count/len(result.claims)*100:.0f}%)")
    print(f"  • Weak Evidence: {weak_count} ({weak_count/len(result.claims)*100:.0f}%)")
    
    print(f"\nEvidence Types:")
    for etype, count in sorted(result.evidence_distribution.items()):
        print(f"  • {etype}: {count}")
    
    # Quality assessment
    if result.overall_strength_score >= 0.8:
        quality = "🟢 Excellent"
    elif result.overall_strength_score >= 0.6:
        quality = "🟡 Good"
    elif result.overall_strength_score >= 0.4:
        quality = "🟠 Fair"
    else:
        quality = "🔴 Poor"
    
    print(f"\nQuality Assessment: {quality}")


if __name__ == "__main__":
    # Run all examples
    example_basic_evaluation()
    example_corroborated_evidence()
    example_contradictory_evidence()
    example_evidence_type_analysis()
    example_methodological_rigor()
    example_strength_assessment()
    example_json_export()
    example_comprehensive_analysis()
    
    print("\n" + "=" * 80)
    print("✅ All Evidence Evaluator Agent examples completed!")
    print("=" * 80)
