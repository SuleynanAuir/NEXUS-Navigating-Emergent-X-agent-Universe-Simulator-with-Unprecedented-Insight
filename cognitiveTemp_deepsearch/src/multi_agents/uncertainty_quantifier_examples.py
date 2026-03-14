"""
Uncertainty Quantifier Agent Examples

Demonstrates various use cases:
1. Basic uncertainty quantification
2. High-confidence analysis
3. Low-confidence analysis requiring termination
4. Multi-domain evidence analysis
5. Conflicting evidence handling
6. Publication readiness assessment
7. Hallucination risk scenarios
8. Comprehensive workflow with all agents
"""

import json
from src.multi_agents.agents.uncertainty_quantifier_agent import (
    create_uncertainty_quantifier_agent,
)


def example_1_basic_uncertainty_quantification():
    """Example 1: Basic uncertainty quantification from mixed sources."""
    print("\n" + "="*60)
    print("Example 1: Basic Uncertainty Quantification")
    print("="*60)

    agent = create_uncertainty_quantifier_agent(llm_client=None)

    evidence_sources = [
        {
            "title": "Nature Article: AI Progress",
            "credibility_score": 0.95,
            "relevance_score": 0.90,
            "summary": "Recent AI developments show significant progress in language models",
            "publication_date": "2023-06-15",
            "domain_type": "academic",
        },
        {
            "title": "Tech Industry Report",
            "credibility_score": 0.80,
            "relevance_score": 0.85,
            "summary": "Commercial AI adoption accelerating across enterprises",
            "publication_date": "2023-07-01",
            "domain_type": "industry",
        },
        {
            "title": "Research Paper: LLM Capabilities",
            "credibility_score": 0.85,
            "relevance_score": 0.88,
            "summary": "Comprehensive evaluation shows LLMs achieving benchmark performance",
            "publication_date": "2023-05-20",
            "domain_type": "academic",
        },
    ]

    claims = [
        "AI language models have made significant progress",
        "Commercial adoption is accelerating",
        "Performance benchmarks are improving",
    ]

    result = agent.quantify(
        analysis_id="ai_progress_2023",
        evidence_sources=evidence_sources,
        claims=claims,
    )

    print(f"\nAnalysis ID: {result.analysis_id}")
    print(f"Aggregated Confidence: {result.aggregated_confidence:.2f}")
    print(f"Confidence Level: {result.confidence_level.value}")
    print(f"Variance Score: {result.variance_score:.2f}")
    print(f"Hallucination Risk: {result.hallucination_risk:.2f}")
    print(f"Global Uncertainty: {result.global_uncertainty:.2f}")
    print(f"Confidence Sufficient for Publication: {result.confidence_sufficient_for_publication}")
    print(f"\nRecommendations:")
    for rec in result.recommendations:
        print(f"  - {rec}")


def example_2_high_confidence_analysis():
    """Example 2: High-confidence analysis with consistent evidence."""
    print("\n" + "="*60)
    print("Example 2: High-Confidence Analysis")
    print("="*60)

    agent = create_uncertainty_quantifier_agent()

    evidence_sources = [
        {
            "title": "Meta-Analysis: COVID-19 Vaccines",
            "credibility_score": 0.98,
            "relevance_score": 0.95,
            "summary": "Multiple large-scale studies confirm vaccine efficacy across 90% effectiveness",
            "publication_date": "2023-01-15",
            "domain_type": "academic",
        },
        {
            "title": "WHO Official Report",
            "credibility_score": 0.96,
            "relevance_score": 0.93,
            "summary": "WHO confirms vaccine safety profile with extensive global monitoring",
            "publication_date": "2023-02-01",
            "domain_type": "government",
        },
        {
            "title": "CDC Safety Monitoring",
            "credibility_score": 0.97,
            "relevance_score": 0.94,
            "summary": "CDC reports minimal adverse effects after vaccinating billions",
            "publication_date": "2023-01-30",
            "domain_type": "government",
        },
        {
            "title": "Lancet Study: Long-term Effects",
            "credibility_score": 0.96,
            "relevance_score": 0.92,
            "summary": "Two-year follow-up study confirms sustained protection",
            "publication_date": "2023-03-10",
            "domain_type": "academic",
        },
    ]

    claims = [
        "COVID-19 vaccines are highly effective (>90%)",
        "COVID-19 vaccines have strong safety profile",
        "Vaccination benefits significantly outweigh risks",
    ]

    result = agent.quantify(
        analysis_id="vaccine_efficacy_2023",
        evidence_sources=evidence_sources,
        claims=claims,
    )

    print(f"\nAnalysis ID: {result.analysis_id}")
    print(f"Aggregated Confidence: {result.aggregated_confidence:.2f}")
    print(f"Confidence Level: {result.confidence_level.value}")
    print(f"Variance Score: {result.variance_score:.2f}")
    print(f"Hallucination Risk: {result.hallucination_risk:.2f}")
    print(f"Global Uncertainty: {result.global_uncertainty:.2f}")
    print(f"Ready for Publication: {result.confidence_sufficient_for_publication}")
    print(f"Recommend Termination: {result.recommend_termination}")


def example_3_low_confidence_termination():
    """Example 3: Analysis with insufficient confidence requiring termination."""
    print("\n" + "="*60)
    print("Example 3: Low-Confidence Analysis Requiring Termination")
    print("="*60)

    agent = create_uncertainty_quantifier_agent()

    evidence_sources = [
        {
            "title": "Unverified Blog Post",
            "credibility_score": 0.25,
            "relevance_score": 0.40,
            "summary": "Claims about new cancer treatment limited sample size",
            "publication_date": "2023-11-01",
            "domain_type": "unknown",
        },
        {
            "title": "Preliminary Report",
            "credibility_score": 0.35,
            "relevance_score": 0.50,
            "summary": "Early findings preliminary research not yet peer reviewed",
            "publication_date": "2023-10-15",
            "domain_type": "academic",
        },
    ]

    claims = [
        "New cancer treatment shows promise",
        "Treatment effective in early trials",
        "Ready for clinical deployment",
    ]

    result = agent.quantify(
        analysis_id="cancer_treatment_preliminary",
        evidence_sources=evidence_sources,
        claims=claims,
    )

    print(f"\nAnalysis ID: {result.analysis_id}")
    print(f"Aggregated Confidence: {result.aggregated_confidence:.2f}")
    print(f"Hallucination Risk: {result.hallucination_risk:.2f}")
    print(f"Global Uncertainty: {result.global_uncertainty:.2f}")
    print(f"Recommend Termination: {result.recommend_termination}")
    if result.recommend_termination:
        print(f"Reason: {result.termination_reason}")
    print(f"\nAdditional Evidence Needed:")
    for gap in result.additional_evidence_needed:
        print(f"  - {gap}")


def example_4_multi_domain_evidence():
    """Example 4: Multi-domain evidence integration."""
    print("\n" + "="*60)
    print("Example 4: Multi-Domain Evidence Analysis")
    print("="*60)

    agent = create_uncertainty_quantifier_agent()

    evidence_sources = [
        {
            "title": "Academic Research: Climate Science",
            "credibility_score": 0.92,
            "relevance_score": 0.88,
            "summary": "Global temperature increasing at 0.15°C per decade",
            "publication_date": "2023-04-15",
            "domain_type": "academic",
        },
        {
            "title": "Government Report: Environmental",
            "credibility_score": 0.88,
            "relevance_score": 0.85,
            "summary": "IPCC confirms anthropogenic climate change",
            "publication_date": "2023-03-20",
            "domain_type": "government",
        },
        {
            "title": "Industry Analysis: Energy Transition",
            "credibility_score": 0.75,
            "relevance_score": 0.82,
            "summary": "Renewable energy expansion accelerating globally",
            "publication_date": "2023-06-01",
            "domain_type": "industry",
        },
        {
            "title": "NGO Report: Environmental Impact",
            "credibility_score": 0.70,
            "relevance_score": 0.80,
            "summary": "Climate change driving ecosystem collapse",
            "publication_date": "2023-05-15",
            "domain_type": "government",
        },
    ]

    claims = [
        "Global temperatures are rising",
        "Climate change is anthropogenic",
        "Energy transition is necessary and feasible",
    ]

    result = agent.quantify(
        analysis_id="climate_consensus_2023",
        evidence_sources=evidence_sources,
        claims=claims,
    )

    print(f"\nAnalysis ID: {result.analysis_id}")
    print(f"Aggregated Confidence: {result.aggregated_confidence:.2f}")
    print(f"Domain Distribution in Analysis:")
    print(f"Variance Sources: {result.variance_sources}")
    print(f"\nConfidence Intervals:")
    for key, value in result.confidence_intervals.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")


def example_5_conflicting_evidence():
    """Example 5: Handling conflicting evidence."""
    print("\n" + "="*60)
    print("Example 5: Conflicting Evidence Analysis")
    print("="*60)

    agent = create_uncertainty_quantifier_agent()

    evidence_sources = [
        {
            "title": "Study A: Medication Effectiveness",
            "credibility_score": 0.85,
            "relevance_score": 0.85,
            "summary": "Positive results medication shows 70% efficacy",
            "publication_date": "2023-02-15",
            "domain_type": "academic",
        },
        {
            "title": "Study B: Medication Analysis",
            "credibility_score": 0.88,
            "relevance_score": 0.80,
            "summary": "However, contradicts previous findings medication shows 35% efficacy",
            "publication_date": "2023-08-01",
            "domain_type": "academic",
        },
        {
            "title": "Meta-Analysis Attempt",
            "credibility_score": 0.82,
            "relevance_score": 0.87,
            "summary": "Conflicting results due to methodological differences",
            "publication_date": "2023-09-15",
            "domain_type": "academic",
        },
    ]

    claims = [
        "Medication is effective",
        "Efficacy rate is consistent",
        "Results are definitive",
    ]

    result = agent.quantify(
        analysis_id="conflicting_medication_study",
        evidence_sources=evidence_sources,
        claims=claims,
    )

    print(f"\nAnalysis ID: {result.analysis_id}")
    print(f"Aggregated Confidence: {result.aggregated_confidence:.2f}")
    print(f"Variance Score: {result.variance_score:.2f}")
    print(f"Hallucination Risk: {result.hallucination_risk:.2f}")
    print(f"\nVariance Sources:")
    for source in result.variance_sources:
        print(f"  - {source}")
    print(f"\nRecommendations:")
    for rec in result.recommendations:
        print(f"  - {rec}")


def example_6_publication_readiness():
    """Example 6: Assessing publication readiness."""
    print("\n" + "="*60)
    print("Example 6: Publication Readiness Assessment")
    print("="*60)

    agent = create_uncertainty_quantifier_agent()

    evidence_sources = [
        {
            "title": "Rigorous Study 1",
            "credibility_score": 0.90,
            "relevance_score": 0.92,
            "summary": "Finding X confirmed with rigorous methodology",
            "publication_date": "2023-03-15",
            "domain_type": "academic",
        },
        {
            "title": "Rigorous Study 2",
            "credibility_score": 0.88,
            "relevance_score": 0.90,
            "summary": "Finding X replicated independently",
            "publication_date": "2023-04-20",
            "domain_type": "academic",
        },
        {
            "title": "Peer Review Synthesis",
            "credibility_score": 0.92,
            "relevance_score": 0.91,
            "summary": "Consensus formed finding X is significant",
            "publication_date": "2023-05-30",
            "domain_type": "academic",
        },
    ]

    claims = [
        "Finding X is well-established",
        "Finding X is reproducible",
        "Finding X ready for publication",
    ]

    result = agent.quantify(
        analysis_id="publication_ready_research",
        evidence_sources=evidence_sources,
        claims=claims,
    )

    print(f"\nAnalysis ID: {result.analysis_id}")
    print(f"Aggregated Confidence: {result.aggregated_confidence:.2f}")
    print(f"Confidence Level: {result.confidence_level.value}")
    print(f"Global Uncertainty: {result.global_uncertainty:.2f}")
    print(f"Confidence Sufficient for Publication: {result.confidence_sufficient_for_publication}")
    print(f"Recommend Termination: {result.recommend_termination}")


def example_7_hallucination_risk_scenarios():
    """Example 7: Hallucination risk in various scenarios."""
    print("\n" + "="*60)
    print("Example 7: Hallucination Risk Scenarios")
    print("="*60)

    agent = create_uncertainty_quantifier_agent()

    # Scenario A: Publication bias risk
    biased_sources = [
        {
            "title": "Positive Result 1",
            "credibility_score": 0.70,
            "relevance_score": 0.75,
            "summary": "Positive successful outcome achieved",
            "publication_date": "2023-01-15",
            "domain_type": "academic",
        },
        {
            "title": "Positive Result 2",
            "credibility_score": 0.72,
            "relevance_score": 0.76,
            "summary": "Positive successful finding confirmed",
            "publication_date": "2023-02-20",
            "domain_type": "academic",
        },
    ]

    result_bias = agent.quantify(
        analysis_id="publication_bias_risk",
        evidence_sources=biased_sources,
        claims=["Method works", "Success is assured"],
    )

    print("\nScenario A: Publication Bias Risk")
    print(f"Hallucination Risk: {result_bias.hallucination_risk:.2f}")
    print(f"Risk Factors Identified: {len(result_bias.hallucination_risk_factors)}")
    for factor in result_bias.hallucination_risk_factors[:2]:
        print(f"  - {factor.get('type', 'unknown')}: {factor.get('severity', 0):.2f}")

    # Scenario B: Small sample risk
    small_sources = [
        {
            "title": "Single Case Study",
            "credibility_score": 0.50,
            "relevance_score": 0.60,
            "summary": "Single patient positive outcome",
            "publication_date": "2023-10-01",
            "domain_type": "academic",
        },
    ]

    result_small = agent.quantify(
        analysis_id="small_sample_risk",
        evidence_sources=small_sources,
        claims=["Treatment works"],
    )

    print("\nScenario B: Small Sample Risk")
    print(f"Hallucination Risk: {result_small.hallucination_risk:.2f}")
    print(f"Number of Sources: {len(small_sources)}")


def example_8_comprehensive_workflow():
    """Example 8: Comprehensive workflow with full details."""
    print("\n" + "="*60)
    print("Example 8: Comprehensive Uncertainty Quantification Workflow")
    print("="*60)

    agent = create_uncertainty_quantifier_agent()

    # Comprehensive analysis
    evidence_sources = [
        {
            "title": "Major Study",
            "credibility_score": 0.90,
            "relevance_score": 0.88,
            "summary": "Comprehensive empirical research methodology",
            "publication_date": "2023-05-15",
            "domain_type": "academic",
        },
        {
            "title": "Follow-up Study",
            "credibility_score": 0.85,
            "relevance_score": 0.85,
            "summary": "Replication study confirms findings",
            "publication_date": "2023-07-20",
            "domain_type": "academic",
        },
        {
            "title": "Industry Application",
            "credibility_score": 0.78,
            "relevance_score": 0.82,
            "summary": "Practical application in industry settings",
            "publication_date": "2023-08-01",
            "domain_type": "industry",
        },
    ]

    claims = [
        "Finding A is statistically significant",
        "Finding B has practical implications",
        "Results are reproducible",
    ]

    custom_confidence = [0.85, 0.80, 0.82]

    result = agent.quantify(
        analysis_id="comprehensive_analysis_2023",
        evidence_sources=evidence_sources,
        claims=claims,
        confidence_scores=custom_confidence,
    )

    print(f"\nAnalysis ID: {result.analysis_id}")
    print(f"\n📊 Confidence Metrics:")
    print(f"  Aggregated Confidence: {result.aggregated_confidence:.2f}")
    print(f"  Confidence Level: {result.confidence_level.value}")
    print(f"  Lower Bound: {result.confidence_intervals.get('lower_bound', 'N/A'):.2f}")
    print(f"  Upper Bound: {result.confidence_intervals.get('upper_bound', 'N/A'):.2f}")

    print(f"\n📈 Uncertainty Metrics:")
    print(f"  Variance Score: {result.variance_score:.2f}")
    print(f"  Hallucination Risk: {result.hallucination_risk:.2f}")
    print(f"  Global Uncertainty: {result.global_uncertainty:.2f}")

    print(f"\n🎯 Decisions:")
    print(f"  Recommend Termination: {result.recommend_termination}")
    print(f"  Publication Ready: {result.confidence_sufficient_for_publication}")

    print(f"\n📋 Uncertainty Sources ({len(result.uncertainty_sources)}):")
    for src in result.uncertainty_sources:
        print(f"  - {src}")

    print(f"\n💡 Recommendations ({len(result.recommendations)}):")
    for rec in result.recommendations:
        print(f"  - {rec}")

    print(f"\n🔍 Additional Evidence Needed ({len(result.additional_evidence_needed)}):")
    for gap in result.additional_evidence_needed:
        print(f"  - {gap}")

    # Validation
    is_valid, errors = agent.validate_quantification(result)
    print(f"\n✓ Validation: {'PASSED' if is_valid else 'FAILED'}")
    if not is_valid:
        for error in errors:
            print(f"  Error: {error}")

    # JSON output
    print(f"\n📄 JSON Output (truncated):")
    json_output = result.to_json()
    json_obj = json.loads(json_output)
    print(f"  Analysis ID: {json_obj['analysis_id']}")
    print(f"  Confidence: {json_obj['aggregated_confidence']}")
    print(f"  Variance: {json_obj['variance_score']}")
    print(f"  Hallucination Risk: {json_obj['hallucination_risk']}")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Uncertainty Quantifier Agent - Working Examples")
    print("="*60)

    example_1_basic_uncertainty_quantification()
    example_2_high_confidence_analysis()
    example_3_low_confidence_termination()
    example_4_multi_domain_evidence()
    example_5_conflicting_evidence()
    example_6_publication_readiness()
    example_7_hallucination_risk_scenarios()
    example_8_comprehensive_workflow()

    print("\n" + "="*60)
    print("All examples completed successfully!")
    print("="*60)
