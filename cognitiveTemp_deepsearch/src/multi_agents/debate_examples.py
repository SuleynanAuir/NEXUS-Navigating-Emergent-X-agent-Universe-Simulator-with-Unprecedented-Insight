"""
Examples demonstrating the Debate Agent

8 comprehensive examples showing:
1. Basic structured debate
2. Detecting unresolved tensions
3. Evaluating epistemic balance
4. Identifying publishable insights
5. Debate on technology adoption
6. Environmental policy debate
7. JSON export and analysis
8. Comprehensive debate workflow
"""

try:
    from src.multi_agents.agents.debate_agent import (
        create_debate_agent,
        ArgumentStrength,
        TensionType,
    )
except ImportError:
    from agents.debate_agent import (
        create_debate_agent,
        ArgumentStrength,
        TensionType,
    )

import json


def example_1_basic_structured_debate():
    """
    Example 1: Basic structured debate on a scientific claim.

    Scenario: Debate whether remote work increases productivity.
    """
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic Structured Debate")
    print("="*70)

    agent = create_debate_agent(debate_style="rigorous")

    topic = "Remote work increases overall productivity"

    sources = [
        {
            "title": "Stanford Remote Work Study 2020",
            "summary": "13% productivity increase observed in remote workers",
            "credibility_score": 0.95,
            "domain_type": "academic",
        },
        {
            "title": "Microsoft Workplace Survey",
            "summary": "Remote work correlated with mental health benefits",
            "credibility_score": 0.85,
            "domain_type": "industry",
        },
        {
            "title": "Remote Work Challenges Report",
            "summary": "Collaboration and communication barriers in remote teams",
            "credibility_score": 0.75,
            "domain_type": "industry",
        },
    ]

    result = agent.debate(topic, sources)

    print("\n📚 DEBATE TOPIC")
    print(f"  {result.debate_topic}")

    print("\n✅ PRO ARGUMENT")
    print(f"  Thesis: {result.pro_argument.get('thesis', 'N/A')[:80]}...")
    print(f"  Confidence: {result.pro_argument.get('confidence', 0):.2%}")
    print(f"  Strength: {result.pro_argument.get('strength', 'N/A')}")

    print("\n❌ CON ARGUMENT")
    print(f"  Thesis: {result.con_argument.get('thesis', 'N/A')[:80]}...")
    print(f"  Confidence: {result.con_argument.get('confidence', 0):.2%}")
    print(f"  Strength: {result.con_argument.get('strength', 'N/A')}")

    print("\n📊 DEBATE ASSESSMENT")
    print(f"  Epistemic Balance: {result.epistemic_balance_score:.2%}")
    print(f"  Debate Quality: {result.debate_quality_score:.2%}")
    print(f"  Winning Argument: {result.winning_argument or 'Balanced'}")


def example_2_unresolved_tensions():
    """
    Example 2: Analyzing unresolved tensions.

    Scenario: Tensions in AI development impact debate.
    """
    print("\n" + "="*70)
    print("EXAMPLE 2: Unresolved Tensions")
    print("="*70)

    agent = create_debate_agent()

    topic = "AI development poses existential risks"

    sources = [
        {
            "title": "AI Safety Research",
            "summary": "Long-term AI risks require serious attention",
            "credibility_score": 0.9,
        },
        {
            "title": "AI Benefits Study",
            "summary": "AI delivers significant near-term benefits",
            "credibility_score": 0.85,
        },
        {
            "title": "Risk Assessment Report",
            "summary": "Risk quantification remains highly uncertain",
            "credibility_score": 0.8,
        },
    ]

    result = agent.debate(topic, sources)

    print(f"\n🎯 Total Tensions Identified: {len(result.unresolved_issues)}")

    for i, tension in enumerate(result.unresolved_issues[:3], 1):
        print(f"\n{i}. {tension.get('type', 'Unknown').upper()}")
        print(f"   Description: {tension.get('description', 'N/A')}")
        print(f"   Severity: {tension.get('severity', 0):.2f}")
        print(f"   Pro says: {tension.get('pro_position', 'N/A')[:50]}...")
        print(f"   Con says: {tension.get('con_position', 'N/A')[:50]}...")

        if tension.get("possible_resolutions"):
            print(f"   Resolution directions:")
            for direction in tension["possible_resolutions"][:2]:
                print(f"     → {direction}")


def example_3_epistemic_balance():
    """
    Example 3: Evaluating epistemic balance.

    Scenario: Compare balance in debates with different evidence profiles.
    """
    print("\n" + "="*70)
    print("EXAMPLE 3: Epistemic Balance Analysis")
    print("="*70)

    agent = create_debate_agent()

    # Scenario A: One-sided evidence
    one_sided_topic = "This intervention definitely works"
    one_sided_sources = [
        {
            "title": "Success Story 1",
            "summary": "Positive outcomes observed",
            "credibility_score": 0.85,
        },
        {
            "title": "Success Story 2",
            "summary": "More positive outcomes",
            "credibility_score": 0.8,
        },
    ]

    result_one_sided = agent.debate(one_sided_topic, one_sided_sources)

    # Scenario B: Balanced evidence
    balanced_topic = "This intervention has mixed effects"
    balanced_sources = [
        {
            "title": "Positive Study",
            "summary": "Some benefits observed",
            "credibility_score": 0.9,
        },
        {
            "title": "Negative Study",
            "summary": "Some harms also observed",
            "credibility_score": 0.9,
        },
        {
            "title": "Neutral Analysis",
            "summary": "Context-dependent effectiveness",
            "credibility_score": 0.85,
        },
    ]

    result_balanced = agent.debate(balanced_topic, balanced_sources)

    print("\n⚖️ EPISTEMIC BALANCE COMPARISON")
    print(f"\nOne-sided evidence:")
    print(f"  Balance score: {result_one_sided.epistemic_balance_score:.2%}")
    print(f"  Quality score: {result_one_sided.debate_quality_score:.2%}")

    print(f"\nBalanced evidence:")
    print(f"  Balance score: {result_balanced.epistemic_balance_score:.2%}")
    print(f"  Quality score: {result_balanced.debate_quality_score:.2%}")

    print(f"\nInterpretation:")
    if result_balanced.epistemic_balance_score > result_one_sided.epistemic_balance_score:
        print("  ✓ Balanced evidence creates more balanced debate")
    else:
        print("  - Both achieve similar balance (topic-dependent)")


def example_4_publishable_insights():
    """
    Example 4: Extracting publishable research insights.

    Scenario: Finding research frontier insights from structured debate.
    """
    print("\n" + "="*70)
    print("EXAMPLE 4: Publishable Research Insights")
    print("="*70)

    agent = create_debate_agent(debate_style="rigorous")

    topic = "Blockchain technology will revolutionize supply chains"

    sources = [
        {
            "title": "Blockchain Benefits Study",
            "summary": "Blockchain enables transparent and efficient tracking",
            "credibility_score": 0.9,
        },
        {
            "title": "Implementation Challenges",
            "summary": "Significant barriers to enterprise adoption",
            "credibility_score": 0.85,
        },
        {
            "title": "Scalability Concerns",
            "summary": "Technical limitations prevent large-scale deployment",
            "credibility_score": 0.8,
        },
    ]

    context = "Post-2023 enterprise blockchain initiatives"

    result = agent.debate(topic, sources, context)

    print(f"\n🔬 RESEARCH FRONTIER INSIGHTS")
    print(f"(Publishable contributions from structured debate)\n")

    for i, insight in enumerate(result.research_frontier_insights, 1):
        print(f"{i}. {insight}\n")

    print(f"💡 DISAGREEMENT DIMENSIONS")
    for i, dimension in enumerate(result.dominant_disagreement_dimensions, 1):
        print(f"{i}. {dimension}")


def example_5_technology_adoption_debate():
    """
    Example 5: Debate on technology adoption strategy.

    Scenario: Should organizations rapidly adopt generative AI?
    """
    print("\n" + "="*70)
    print("EXAMPLE 5: Technology Adoption Debate")
    print("="*70)

    agent = create_debate_agent(debate_style="exploratory")

    topic = "Organizations should rapidly adopt generative AI"

    sources = [
        {
            "title": "AI Productivity Study",
            "summary": "Early adopters see 30% productivity gains",
            "credibility_score": 0.9,
            "domain_type": "industry",
        },
        {
            "title": "AI Risk Assessment",
            "summary": "Significant risks from rapid deployment without governance",
            "credibility_score": 0.85,
            "domain_type": "academic",
        },
        {
            "title": "First-Mover Advantage Analysis",
            "summary": "Late adoption risks losing competitive position",
            "credibility_score": 0.8,
            "domain_type": "industry",
        },
        {
            "title": "Technology Integration Study",
            "summary": "Successful adoption requires careful change management",
            "credibility_score": 0.75,
            "domain_type": "academic",
        },
    ]

    result = agent.debate(topic, sources)

    print(f"\n🏢 DEBATE: {result.debate_topic}")

    print(f"\n✅ RAPID ADOPTION ARGUMENT")
    print(f"  Key points:")
    for i, point in enumerate(result.pro_argument.get("supporting_points", [])[:2], 1):
        print(f"    {i}. {point}")

    print(f"\n🛑 CAUTIOUS APPROACH ARGUMENT")
    print(f"  Key concerns:")
    for i, point in enumerate(result.con_argument.get("supporting_points", [])[:2], 1):
        print(f"    {i}. {point}")

    print(f"\n📈 RECOMMENDED EMPIRICAL TESTS")
    for i, test in enumerate(result.recommended_empirical_tests[:3], 1):
        print(f"  {i}. {test}")


def example_6_environmental_policy_debate():
    """
    Example 6: Debate on environmental policy.

    Scenario: Should governments implement carbon taxes?
    """
    print("\n" + "="*70)
    print("EXAMPLE 6: Environmental Policy Debate")
    print("="*70)

    agent = create_debate_agent(debate_style="critical")

    topic = "Carbon taxes are an effective climate policy tool"

    sources = [
        {
            "title": "Economic Analysis of Carbon Tax",
            "summary": "Carbon taxes effectively reduce emissions at lower cost",
            "credibility_score": 0.95,
            "domain_type": "academic",
        },
        {
            "title": "Social Impact Study",
            "summary": "Carbon taxes disproportionately harm low-income households",
            "credibility_score": 0.85,
            "domain_type": "academic",
        },
        {
            "title": "International Policy Review",
            "summary": "Carbon tax effectiveness varies significantly by implementation",
            "credibility_score": 0.9,
            "domain_type": "government",
        },
        {
            "title": "Climate Modeling",
            "summary": "Carbon pricing insufficient alone to meet climate targets",
            "credibility_score": 0.88,
            "domain_type": "academic",
        },
    ]

    result = agent.debate(topic, sources)

    print(f"\n🌍 DEBATE: {result.debate_topic}")

    print(f"\n💰 ECONOMIC EFFICIENCY ARGUMENT (Pro)")
    print(f"  Confidence: {result.pro_argument.get('confidence', 0):.2%}")
    print(f"  Summary: {result.pro_argument.get('evidence_summary', 'N/A')}")

    print(f"\n👥 SOCIAL EQUITY ARGUMENT (Con)")
    print(f"  Confidence: {result.con_argument.get('confidence', 0):.2%}")
    print(f"  Summary: {result.con_argument.get('evidence_summary', 'N/A')}")

    print(f"\n⚖️ DEBATE METRICS")
    print(f"  Epistemic Balance: {result.epistemic_balance_score:.2%}")
    print(f"  Debate Quality: {result.debate_quality_score:.2%}")

    if result.winning_argument:
        print(f"  Stronger argument: {result.winning_argument.upper()}")
    else:
        print(f"  Assessment: Neither argument clearly dominates")


def example_7_json_export():
    """
    Example 7: Exporting debate results to JSON.

    Scenario: Generating structured output for analysis.
    """
    print("\n" + "="*70)
    print("EXAMPLE 7: JSON Export")
    print("="*70)

    agent = create_debate_agent()

    topic = "Remote work is permanently changing workplace structure"

    sources = [
        {
            "title": "Workplace Trends Study",
            "summary": "Hybrid and remote work becoming mainstream",
            "credibility_score": 0.9,
        },
        {
            "title": "Office Return Movement",
            "summary": "Some companies requiring return-to-office",
            "credibility_score": 0.8,
        },
    ]

    result = agent.debate(topic, sources)

    print("\n📋 JSON OUTPUT (excerpt):")
    json_dict = result.to_dict()

    # Print key sections
    print(f"\nDebate Topic: {json_dict['debate_topic']}")
    print(f"\nPro Argument Strength: {json_dict['pro_argument'].get('strength', 'N/A')}")
    print(f"Con Argument Strength: {json_dict['con_argument'].get('strength', 'N/A')}")

    print(f"\nEpistemic Balance Score: {json_dict['epistemic_balance_score']}")
    print(f"Debate Quality Score: {json_dict['debate_quality_score']}")

    print(f"\nUnresolved Tensions: {len(json_dict['unresolved_issues'])}")
    print(f"Research Insights: {len(json_dict['research_frontier_insights'])}")

    print("\n✅ Full JSON is valid and machine-readable")

    # Validate
    is_valid, errors = agent.validate_debate_result(result)
    print(f"Validation: {'✅ PASSED' if is_valid else '❌ FAILED'}")
    if errors:
        for error in errors:
            print(f"  - {error}")


def example_8_comprehensive_workflow():
    """
    Example 8: Comprehensive debate workflow.

    Scenario: Full analysis of a complex policy question.
    """
    print("\n" + "="*70)
    print("EXAMPLE 8: Comprehensive Debate Workflow")
    print("="*70)

    agent = create_debate_agent(debate_style="rigorous")

    topic = "Universal basic income (UBI) effectively reduces poverty"

    sources = [
        {
            "title": "UBI Pilot Study Finland 2017-2018",
            "summary": "UBI improved wellbeing without reducing employment",
            "credibility_score": 0.95,
            "domain_type": "academic",
        },
        {
            "title": "Cost-Benefit Analysis",
            "summary": "UBI fiscally unsustainable at meaningful levels",
            "credibility_score": 0.9,
            "domain_type": "academic",
        },
        {
            "title": "Economic Displacement Study",
            "summary": "Wage effects depend on implementation details",
            "credibility_score": 0.85,
            "domain_type": "academic",
        },
        {
            "title": "Social Integration Research",
            "summary": "UBI shows promise for social cohesion",
            "credibility_score": 0.8,
            "domain_type": "academic",
        },
    ]

    context = "Post-2020 pandemic interest in UBI policies"

    print(f"\n📚 ANALYZING: {topic}")
    print(f"Context: {context}")

    result = agent.debate(topic, sources)

    # Section 1: Main Arguments
    print("\n" + "="*70)
    print("POSITION ARGUMENTS")
    print("="*70)

    print(f"\n✅ PRO ARGUMENT (For UBI)")
    print(f"Thesis: {result.pro_argument.get('thesis', 'N/A')}")
    print(f"\nKey Supporting Points:")
    for i, point in enumerate(result.pro_argument.get("supporting_points", [])[:3], 1):
        print(f"  {i}. {point}")
    print(f"\nEvidence: {result.pro_argument.get('evidence_summary', 'N/A')}")
    print(f"Confidence: {result.pro_argument.get('confidence', 0):.2%}")

    print(f"\n❌ CON ARGUMENT (Against universal UBI)")
    print(f"Thesis: {result.con_argument.get('thesis', 'N/A')}")
    print(f"\nKey Concerns:")
    for i, point in enumerate(result.con_argument.get("supporting_points", [])[:3], 1):
        print(f"  {i}. {point}")
    print(f"\nEvidence: {result.con_argument.get('evidence_summary', 'N/A')}")
    print(f"Confidence: {result.con_argument.get('confidence', 0):.2%}")

    # Section 2: Tensions
    print("\n" + "="*70)
    print("UNRESOLVED TENSIONS")
    print("="*70)

    for i, tension in enumerate(result.unresolved_issues[:3], 1):
        print(f"\n{i}. {tension.get('description', 'N/A')}")
        print(f"   Severity: {tension.get('severity', 0):.2f}")
        print(f"   Pro: {tension.get('pro_position', 'N/A')[:60]}...")
        print(f"   Con: {tension.get('con_position', 'N/A')[:60]}...")

    # Section 3: Metrics
    print("\n" + "="*70)
    print("DEBATE ASSESSMENT")
    print("="*70)

    print(f"\nEpistemic Balance: {result.epistemic_balance_score:.2%}")
    print(f"  (0.5 = perfectly balanced, higher = Pro favored)")
    print(f"\nDebate Quality: {result.debate_quality_score:.2%}")
    print(f"  (How comprehensive and rigorous is the debate)")
    print(f"\nWinning Argument: {result.winning_argument or 'Neither dominates (balanced)'}")

    # Section 4: Research Insights
    print("\n" + "="*70)
    print("RESEARCH FRONTIER INSIGHTS")
    print("="*70)

    for i, insight in enumerate(result.research_frontier_insights, 1):
        print(f"\n{i}. {insight}")

    # Section 5: Research Directions
    print("\n" + "="*70)
    print("RECOMMENDED EMPIRICAL TESTS")
    print("="*70)

    for i, test in enumerate(result.recommended_empirical_tests[:5], 1):
        print(f"{i}. {test}")

    print("\n" + "="*70)
    print("✅ DEBATE ANALYSIS COMPLETE")
    print("="*70)


def main():
    """Run all examples."""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*15 + "DEBATE AGENT - 8 EXAMPLES" + " "*29 + "║")
    print("╚" + "="*68 + "╝")

    example_1_basic_structured_debate()
    example_2_unresolved_tensions()
    example_3_epistemic_balance()
    example_4_publishable_insights()
    example_5_technology_adoption_debate()
    example_6_environmental_policy_debate()
    example_7_json_export()
    example_8_comprehensive_workflow()

    print("\n" + "="*70)
    print("✅ ALL EXAMPLES COMPLETED")
    print("="*70)


if __name__ == "__main__":
    main()
