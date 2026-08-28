from .models import Finding
from .graph_engine import get_upstream_components


def calculate_blast_radius(graph, component):
    affected_components = get_upstream_components(
        graph,
        component
    )

    return {
        "component": component,
        "affected_components": affected_components,
        "blast_radius": len(affected_components),
    }


def calculate_component_criticality(
    graph,
    component
):
    direct_dependents = list(
        graph.predecessors(component)
    )

    affected_components = (
        get_upstream_components(
            graph,
            component
        )
    )

    direct_score = len(
        direct_dependents
    ) * 10

    blast_score = len(
        affected_components
    ) * 20

    criticality_score = (
        direct_score
        + blast_score
    )

    return min(
        criticality_score,
        100
    )


def get_critical_components(graph):
    components = []

    for component in graph.nodes:
        score = calculate_component_criticality(
            graph,
            component
        )

        components.append(
            {
                "component": component,
                "criticality_score": score,
            }
        )

    return sorted(
        components,
        key=lambda item: item[
            "criticality_score"
        ],
        reverse=True
    )


def analyze_graph_risks(graph):
    findings = []

    total_nodes = graph.number_of_nodes()

    if total_nodes <= 1:
        return findings

    for component in graph.nodes:
        result = calculate_blast_radius(
            graph,
            component
        )

        blast_radius = result[
            "blast_radius"
        ]

        affected_components = result[
            "affected_components"
        ]

        if blast_radius == 0:
            continue

        blast_ratio = (
            blast_radius
            / (total_nodes - 1)
        )

        if blast_ratio >= 0.75:
            severity = "HIGH"

        elif blast_ratio >= 0.40:
            severity = "MEDIUM"

        else:
            severity = "LOW"

        findings.append(
            Finding(
                source="GRAPH_ENGINE",
                severity=severity,
                category="Reliability",
                component=component,
                issue="Large failure blast radius",
                explanation=(
                    f"If {component} fails, "
                    f"{blast_radius} other component(s) "
                    f"may be affected: "
                    f"{affected_components}."
                ),
                recommendation=(
                    "Review redundancy, failover, "
                    "timeouts, circuit breakers, "
                    "graceful degradation, and "
                    "dependency isolation."
                ),
            )
        )

    return findings