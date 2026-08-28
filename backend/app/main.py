import json
from pathlib import Path

from analyzer import analyze_architecture
from gemini_analyzer import analyze_with_gemini
from aggregator import aggregate_findings
from risk_engine import assign_risk_scores
from deduplicator import deduplicate_findings
from graph_engine import (
    build_architecture_graph,
    get_graph_summary,
    get_dependencies,
    get_dependents,
    get_upstream_components,
)
from graph_risk_engine import (
    analyze_graph_risks,
    get_critical_components,
)
from scenario_engine import (
    simulate_component_failure,
    format_failure_scenario,
)


def load_architecture(file_path):
    with open(file_path, "r") as file:
        return json.load(file)


def main():
    architecture_path = (
        Path(__file__).parent.parent
        / "data"
        / "sample_architecture.json"
    )

    architecture = load_architecture(architecture_path)

    # Build architecture graph
    graph = build_architecture_graph(architecture)

    print("ArchGuard AI")
    print("============")
    print()

    # --------------------------------------------------
    # 1. Display architecture
    # --------------------------------------------------

    print("Services:")
    for service in architecture["services"]:
        print(f"- {service['name']} ({service['type']})")

    print()

    print("Connections:")
    for source, destination in architecture["connections"]:
        print(f"- {source} -> {destination}")

    # --------------------------------------------------
    # 2. Architecture graph
    # --------------------------------------------------

    print()
    print("Architecture Graph")
    print("==================")

    summary = get_graph_summary(graph)

    print(f"Nodes: {summary['nodes']}")
    print(f"Edges: {summary['edges']}")

    # --------------------------------------------------
    # 3. Dependency analysis
    # --------------------------------------------------

    print()
    print("Dependency Analysis")
    print("===================")

    for component in graph.nodes:
        dependencies = get_dependencies(
            graph,
            component
        )

        dependents = get_dependents(
            graph,
            component
        )

        print()
        print(f"Component: {component}")
        print(f"Depends on: {dependencies}")
        print(f"Used by: {dependents}")

    # --------------------------------------------------
    # 4. Failure reachability / blast radius preview
    # --------------------------------------------------

    print()
    print("Failure Reachability")
    print("====================")

    for component in graph.nodes:
        upstream = get_upstream_components(
            graph,
            component
        )

        print(
            f"If {component} fails, "
            f"potentially affected upstream components: {upstream}"
        )

    # --------------------------------------------------
    # 5. Deterministic analysis
    # --------------------------------------------------

    print()
    print("Architecture Analysis")
    print("=====================")

    findings = analyze_architecture(
        architecture
    )

    graph_findings = analyze_graph_risks(
    graph
)

    if not findings:
        print(
            "No deterministic risks detected."
        )

    # --------------------------------------------------
    # 6. Gemini analysis
    # --------------------------------------------------

    print()
    print("Gemini Architecture Analysis")
    print("============================")
    print()

    try:
        gemini_analysis = analyze_with_gemini(
            architecture
        )

        print(
            f"Gemini returned "
            f"{len(gemini_analysis.findings)} findings."
        )

        # Merge deterministic + Gemini findings
        all_findings = aggregate_findings(
            findings,
            gemini_analysis
        )
        all_findings.extend(
            graph_findings
        )

    except Exception as error:
        print(
            "Gemini analysis temporarily unavailable."
        )
        print(f"Reason: {error}")
        print(
            "Continuing with deterministic analysis only."
        )

        # Create an empty Gemini-like result
        class EmptyGeminiAnalysis:
            findings = []

        all_findings = aggregate_findings(
            findings,
            EmptyGeminiAnalysis()
        )

    # --------------------------------------------------
    # 7. Risk scoring
    # --------------------------------------------------

    scored_findings = assign_risk_scores(
        all_findings
    )

    # --------------------------------------------------
    # 8. Deduplication
    # --------------------------------------------------

    deduplicated_findings = (
        deduplicate_findings(
            scored_findings
        )
    )

    # --------------------------------------------------
    # 9. Sort by risk
    # --------------------------------------------------

    sorted_findings = sorted(
        deduplicated_findings,
        key=lambda finding: finding.risk_score,
        reverse=True
    )

    print()
    print("Critical Components")
    print("===================")

    critical_components = (
        get_critical_components(graph)
    )

    for item in critical_components:
        print(
            f"{item['component']}: "
            f"{item['criticality_score']}"
        )

    # --------------------------------------------------
    # 10. Final ranked findings
    # --------------------------------------------------

    print()
    print(
        "Final Ranked ArchGuard Findings"
    )
    print(
        "==============================="
    )

    if not sorted_findings:
        print(
            "No architecture risks detected."
        )

    for finding in sorted_findings:
        print()

        print(
            f"[{finding.severity}] "
            f"{finding.issue} "
            f"(Risk Score: "
            f"{finding.risk_score})"
        )

        print(
            f"Source: {finding.source}"
        )

        print(
            f"Category: {finding.category}"
        )

        print(
            f"Component: {finding.component}"
        )

        print(
            f"Explanation: "
            f"{finding.explanation}"
        )

        print(
            f"Recommendation: "
            f"{finding.recommendation}"
        )

    print()
    print("What-If Analysis")
    print("================")

    component_to_fail = input(
    "\nEnter a component to simulate failure: "
    ).strip()

    scenario = simulate_component_failure(
        graph,
        component_to_fail
    )

    print(
        format_failure_scenario(
            scenario
        )
    )


if __name__ == "__main__":
    main()