"""
Examples demonstrating the Critical Reflection Agent

8 comprehensive examples showing:
1. Basic critical reflection
2. Detecting confirmation bias in research
3. Identifying missing perspectives
4. Detecting logical vulnerabilities
5. Counterfactual question generation
6. High-bias scenario detection
7. JSON export and analysis
8. Comprehensive critical analysis workflow
"""

from src.multi_agents.agents.critical_reflection_agent import (
    create_critical_reflection_agent,
    BiasType,
    VulnerabilityType,
)
import json

# Try importing from relative path if absolute fails
try:
    from src.multi_agents.agents.critical_reflection_agent import (
        create_critical_reflection_agent,
        BiasType,
        VulnerabilityType,
    )
except ImportError:
    from agents.critical_reflection_agent import (
        create_critical_reflection_agent,
        BiasType,
        VulnerabilityType,
    )


def example_1_basic_critical_reflection():
    """
    Example 1: Basic critical reflection on a simple claim.
    
    Scenario: We have evidence supporting a claim about climate change,
    and want to identify potential biases and logical flaws.
    """
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic Critical Reflection")
    print("="*70)

    agent = create_critical_reflection_agent(strict_mode=True)

    claims = [
        "Human activities are the primary cause of recent global warming",
        "This warming trend will continue accelerating",
    ]

    sources = [
        {
            "title": "IPCC Climate Assessment 2021",
            "summary": "Overwhelming evidence that human activities warm the climate",
            "domain_type": "academic",
            "credibility_score": 0.98,
            "publication_date": "2021",
            "authors": ["IPCC Panel"],
        },
        {
            "title": "Global Temperature Records",
            "summary": "Temperature increased 1.1°C since pre-industrial era",
            "domain_type": "government",
            "credibility_score": 0.95,
            "publication_date": "2023",
            "authors": ["NOAA", "NASA"],
        },
    ]

    result = agent.reflect(claims, sources)

    print("\n📊 REFLECTION ANALYSIS")
    print(f"Reflection Confidence: {result.reflection_confidence:.2%}")
    print(f"Bias Risk Level: {result.bias_risk_level:.2%}")
    print(f"Requires Additional Retrieval: {result.requires_additional_retrieval}")

    print("\n❌ Missing Perspectives:")
    for i, perspective in enumerate(result.missing_perspectives[:3], 1):
        print(f"  {i}. {perspective}")

    print("\n⚠️ Logical Vulnerabilities:")
    for vuln in result.logical_vulnerabilities[:2]:
        print(f"  - {vuln['type']}: {vuln['description'][:60]}...")
        print(f"    Severity: {vuln['severity']:.2f}")

    print("\n🔍 Counterfactual Questions:")
    for i, cq in enumerate(result.counterfactual_questions[:2], 1):
        print(f"  {i}. {cq['question']}")


def example_2_confirmation_bias_detection():
    """
    Example 2: Detecting confirmation bias in research selection.
    
    Scenario: Evidence selected appears to only show positive findings,
    potentially indicating confirmation bias.
    """
    print("\n" + "="*70)
    print("EXAMPLE 2: Confirmation Bias Detection")
    print("="*70)

    agent = create_critical_reflection_agent(strict_mode=True)

    claims = [
        "Social media usage improves mental health in teenagers",
    ]

    sources = [
        {
            "title": "Teen Social Connection Study",
            "summary": "Social media helps teens feel connected and supported",
            "domain_type": "academic",
            "credibility_score": 0.85,
        },
        {
            "title": "Mental Health Benefits Report",
            "summary": "Teens using social media show improved mood",
            "domain_type": "industry",
            "credibility_score": 0.7,
        },
        {
            "title": "Social Networks Success Story",
            "summary": "Platform users report positive outcomes",
            "domain_type": "industry",
            "credibility_score": 0.6,
        },
    ]

    result = agent.reflect(claims, sources)

    print(f"\n🎯 Bias Analysis")
    print(f"Overall Bias Risk: {result.bias_risk_level:.2%}")

    print("\n🔴 Detected Biases:")
    for bias in result.bias_detections:
        print(f"  Type: {bias['type']}")
        print(f"  Description: {bias['description']}")
        print(f"  Severity: {bias['severity']:.2f}")
        print()

    print("🚨 Critical Assessment:")
    print("  Evidence appears one-sided - all sources report positive findings")
    print("  Missing: critical perspectives, meta-analyses, contradictory evidence")

    if result.requires_additional_retrieval:
        print("\n✅ Additional retrieval NEEDED to balance perspective")
        print("Recommended search directions:")
        for i, direction in enumerate(result.additional_search_directions[:3], 1):
            print(f"  {i}. {direction}")


def example_3_missing_perspectives():
    """
    Example 3: Identifying missing critical perspectives.
    
    Scenario: Business decision based on limited stakeholder input.
    """
    print("\n" + "="*70)
    print("EXAMPLE 3: Missing Perspectives Analysis")
    print("="*70)

    agent = create_critical_reflection_agent()

    claims = [
        "Our new automation strategy will increase company efficiency",
        "Implementation will create competitive advantage",
    ]

    sources = [
        {
            "title": "Technology Analysis",
            "summary": "Automation tools offer 30% efficiency gains",
            "domain_type": "industry",
            "credibility_score": 0.85,
        },
        {
            "title": "Cost-Benefit Study",
            "summary": "ROI achieved within 2 years",
            "domain_type": "industry",
            "credibility_score": 0.8,
        },
    ]

    result = agent.reflect(claims, sources)

    print("\n🔍 Perspective Gap Analysis")
    print(f"Total missing perspectives identified: {len(result.missing_perspectives)}")

    print("\n📋 Missing Critical Perspectives:")
    for i, perspective in enumerate(result.missing_perspectives[:5], 1):
        print(f"  {i}. {perspective}")

    print("\n💡 Recommended Additional Perspectives:")
    for i, rec in enumerate(result.recommended_perspectives, 1):
        print(f"  {i}. {rec}")

    print("\n⚠️ Reasoning Gaps Identified:")
    for i, gap in enumerate(result.reasoning_gaps, 1):
        print(f"  {i}. {gap}")


def example_4_logical_vulnerabilities():
    """
    Example 4: Detecting multiple logical vulnerabilities.
    
    Scenario: Claims with various logical flaws.
    """
    print("\n" + "="*70)
    print("EXAMPLE 4: Logical Vulnerabilities Detection")
    print("="*70)

    agent = create_critical_reflection_agent(strict_mode=True)

    claims = [
        "All companies that adopted AI saw massive revenue growth, therefore AI guarantees success",
        "Since our competitors use this strategy, it clearly leads to profits",
        "One study proved this treatment works for everyone",
    ]

    sources = [
        {
            "title": "AI Success Story",
            "summary": "Fortune 500 company doubled revenue after AI adoption",
            "domain_type": "industry",
            "credibility_score": 0.8,
        },
    ]

    result = agent.reflect(claims, sources)

    print("\n🚨 Vulnerability Analysis")
    print(f"Total vulnerabilities detected: {len(result.logical_vulnerabilities)}")

    for i, vuln in enumerate(result.logical_vulnerabilities, 1):
        print(f"\n{i}. {vuln['type'].upper()}")
        print(f"   Description: {vuln['description']}")
        print(f"   Severity: {vuln['severity']:.2f}")
        print(f"   Affected claims: {len(vuln.get('affected_claims', []))}")
        print(f"   Remediation: {vuln['remediation']}")


def example_5_counterfactual_reasoning():
    """
    Example 5: Generating counterfactual questions for assumption testing.
    
    Scenario: Healthcare policy decision that may be based on assumptions.
    """
    print("\n" + "="*70)
    print("EXAMPLE 5: Counterfactual Reasoning")
    print("="*70)

    agent = create_critical_reflection_agent()

    claims = [
        "Universal healthcare reduces overall healthcare costs",
        "Countries with public healthcare have better health outcomes",
    ]

    sources = [
        {
            "title": "Comparative Healthcare Analysis",
            "summary": "Nations with universal healthcare spend less per capita",
            "domain_type": "academic",
            "credibility_score": 0.9,
        },
        {
            "title": "WHO Health Outcomes Study",
            "summary": "Universal healthcare countries rank higher on health metrics",
            "domain_type": "government",
            "credibility_score": 0.95,
        },
    ]

    result = agent.reflect(claims, sources)

    print("\n🤔 Counterfactual Questions Generated")
    print(f"Total questions: {len(result.counterfactual_questions)}")

    for i, cq in enumerate(result.counterfactual_questions, 1):
        print(f"\n{i}. [Priority {cq['priority']}] {cq['question']}")
        print(f"   Related assumption: {cq['related_assumption']}")
        print(f"   Expected impact: {cq['expected_impact']}")


def example_6_high_bias_scenario():
    """
    Example 6: Analyzing a high-bias scenario.
    
    Scenario: Investment decision based on potentially biased information.
    """
    print("\n" + "="*70)
    print("EXAMPLE 6: High-Bias Scenario Detection")
    print("="*70)

    agent = create_critical_reflection_agent(strict_mode=True)

    claims = [
        "This startup is the next unicorn",
        "It will definitely disrupt the industry",
    ]

    sources = [
        {
            "title": "Success Story",
            "summary": "Startup showing rapid growth",
            "domain_type": "industry",
            "credibility_score": 0.6,
            "publication_date": "2025",
        },
    ]

    result = agent.reflect(claims, sources)

    print(f"\n⚠️ HIGH BIAS ALERT")
    print(f"Bias Risk Level: {result.bias_risk_level:.2%}")
    print(f"Reflection Confidence: {result.reflection_confidence:.2%}")
    print(f"Requires Additional Retrieval: {result.requires_additional_retrieval}")

    print("\n🔴 Detected Issues:")
    print(f"  - {len(result.missing_perspectives)} missing perspectives")
    print(f"  - {len(result.logical_vulnerabilities)} logical vulnerabilities")
    print(f"  - {len(result.bias_detections)} potential biases")

    if result.requires_additional_retrieval:
        print("\n🔍 Additional Search Needed:")
        for direction in result.additional_search_directions:
            print(f"  → {direction}")


def example_7_json_export():
    """
    Example 7: Exporting reflection results to JSON.
    
    Scenario: Generating structured output for downstream analysis.
    """
    print("\n" + "="*70)
    print("EXAMPLE 7: JSON Export")
    print("="*70)

    agent = create_critical_reflection_agent()

    claims = ["Finding: X improves Y by 50%"]
    sources = [
        {
            "title": "Study",
            "summary": "X improves Y",
            "domain_type": "academic",
            "credibility_score": 0.85,
        }
    ]

    result = agent.reflect(claims, sources)

    print("\n📋 JSON Output:")
    print(result.to_json(indent=2))

    print("\n✅ JSON is valid and contains all required fields")

    # Validate
    is_valid, errors = agent.validate_reflection_result(result)
    print(f"\nValidation: {'✅ PASSED' if is_valid else '❌ FAILED'}")
    if errors:
        for error in errors:
            print(f"  - {error}")


def example_8_comprehensive_workflow():
    """
    Example 8: Comprehensive critical analysis workflow.
    
    Scenario: Full analysis of a complex research conclusion.
    """
    print("\n" + "="*70)
    print("EXAMPLE 8: Comprehensive Critical Analysis Workflow")
    print("="*70)

    agent = create_critical_reflection_agent(strict_mode=True)

    initial_conclusion = """
    Recent studies show that working from home increases productivity by 15-20%.
    This trend is especially pronounced in tech companies where remote work is
    the norm. Therefore, companies should transition to full remote work policies.
    """

    claims = [
        "Working from home increases productivity",
        "Remote work is especially effective in tech",
        "Companies should adopt full remote policies",
    ]

    sources = [
        {
            "title": "Stanford Remote Work Study 2020",
            "summary": "Remote workers show 13% productivity increase in customer service",
            "domain_type": "academic",
            "credibility_score": 0.92,
            "publication_date": "2020",
            "authors": ["Stanford Economics"],
        },
        {
            "title": "Tech Company Survey",
            "summary": "65% of tech workers report higher productivity at home",
            "domain_type": "industry",
            "credibility_score": 0.75,
            "publication_date": "2022",
            "authors": ["TechPulse Research"],
        },
        {
            "title": "Microsoft Remote Work Report",
            "summary": "Productivity metrics improved during pandemic lockdowns",
            "domain_type": "industry",
            "credibility_score": 0.8,
            "publication_date": "2021",
            "authors": ["Microsoft Work Lab"],
        },
    ]

    print("\n📋 ANALYZING CONCLUSION:")
    print(initial_conclusion)

    result = agent.reflect(claims, sources, initial_conclusion)

    # Section 1: Overall Assessment
    print("\n" + "="*70)
    print("🎯 OVERALL ASSESSMENT")
    print("="*70)
    print(f"Reflection Confidence: {result.reflection_confidence:.2%}")
    print(f"Bias Risk Level: {result.bias_risk_level:.2%}")
    print(f"Additional Retrieval Needed: {result.requires_additional_retrieval}")

    # Section 2: Identified Gaps
    print("\n" + "="*70)
    print("❌ PERSPECTIVE GAPS")
    print("="*70)
    for i, perspective in enumerate(result.missing_perspectives[:3], 1):
        print(f"{i}. {perspective}")

    # Section 3: Logical Issues
    print("\n" + "="*70)
    print("⚠️ LOGICAL VULNERABILITIES")
    print("="*70)
    for vuln in result.logical_vulnerabilities[:2]:
        print(f"• {vuln['type']}")
        print(f"  {vuln['description']}")
        print(f"  Remediation: {vuln['remediation']}\n")

    # Section 4: Biases
    print("\n" + "="*70)
    print("🔴 DETECTED BIASES")
    print("="*70)
    for bias in result.bias_detections[:2]:
        print(f"• {bias['type']}")
        print(f"  {bias['description']}")
        print(f"  Severity: {bias['severity']:.2f}\n")

    # Section 5: Challenge Questions
    print("\n" + "="*70)
    print("❓ CHALLENGING QUESTIONS")
    print("="*70)
    for i, cq in enumerate(result.counterfactual_questions[:3], 1):
        print(f"{i}. {cq['question']}")

    # Section 6: Recommendations
    print("\n" + "="*70)
    print("💡 RECOMMENDED NEXT STEPS")
    print("="*70)
    for i, direction in enumerate(result.additional_search_directions, 1):
        print(f"{i}. {direction}")

    print("\n" + "="*70)
    print("✅ ANALYSIS COMPLETE")
    print("="*70)


def main():
    """Run all examples."""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*10 + "CRITICAL REFLECTION AGENT - 8 EXAMPLES" + " "*20 + "║")
    print("╚" + "="*68 + "╝")

    example_1_basic_critical_reflection()
    example_2_confirmation_bias_detection()
    example_3_missing_perspectives()
    example_4_logical_vulnerabilities()
    example_5_counterfactual_reasoning()
    example_6_high_bias_scenario()
    example_7_json_export()
    example_8_comprehensive_workflow()

    print("\n" + "="*70)
    print("✅ ALL EXAMPLES COMPLETED")
    print("="*70)


if __name__ == "__main__":
    main()
