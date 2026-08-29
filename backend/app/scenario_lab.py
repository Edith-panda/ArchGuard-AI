from typing import Any

import networkx as nx


SUPPORTED_SCENARIOS = {
    "component_failure",
    "traffic_spike",
    "database_failure",
    "dependency_failure",
}


def normalize_component_name(
    graph: nx.DiGraph,
    requested_name: str,
) -> str | None:
    """
    Resolve component names case-insensitively.
    """

    if not requested_name:
        return None

    requested = requested_name.strip().lower()

    for node in graph.nodes:

        if str(node).strip().lower() == requested:
            return node

    return None


def get_downstream_nodes(
    graph: nx.DiGraph,
    component: str,
) -> list[str]:

    if component not in graph:
        return []

    return sorted(
        nx.descendants(
            graph,
            component,
        )
    )


def get_upstream_nodes(
    graph: nx.DiGraph,
    component: str,
) -> list[str]:

    if component not in graph:
        return []

    return sorted(
        nx.ancestors(
            graph,
            component,
        )
    )


def calculate_blast_radius(
    graph: nx.DiGraph,
    component: str,
) -> dict[str, Any]:

    downstream = get_downstream_nodes(
        graph,
        component,
    )

    upstream = get_upstream_nodes(
        graph,
        component,
    )

    total_components = (
        graph.number_of_nodes()
    )

    affected_count = (
        1 + len(downstream)
    )

    percentage = (
        round(
            (
                affected_count
                / total_components
            )
            * 100,
            1,
        )
        if total_components
        else 0.0
    )

    return {
        "failed_component":
            component,

        "direct_dependents":
            sorted(
                list(
                    graph.predecessors(
                        component
                    )
                )
            ),

        "direct_dependencies":
            sorted(
                list(
                    graph.successors(
                        component
                    )
                )
            ),

        "downstream_components":
            downstream,

        "upstream_components":
            upstream,

        "affected_component_count":
            affected_count,

        "total_component_count":
            total_components,

        "blast_radius_percent":
            percentage,
    }


def classify_blast_radius(
    percentage: float,
) -> str:

    if percentage >= 75:
        return "critical"

    if percentage >= 50:
        return "high"

    if percentage >= 25:
        return "medium"

    return "low"


def find_high_fan_in_components(
    graph: nx.DiGraph,
) -> list[dict[str, Any]]:

    results = []

    for node in graph.nodes:

        fan_in = graph.in_degree(
            node
        )

        if fan_in >= 2:

            results.append(
                {
                    "component":
                        node,

                    "fan_in":
                        fan_in,

                    "risk":
                        (
                            "Multiple components "
                            "depend on this node."
                        ),
                }
            )

    return sorted(
        results,
        key=lambda item:
            item["fan_in"],
        reverse=True,
    )


def find_high_fan_out_components(
    graph: nx.DiGraph,
) -> list[dict[str, Any]]:

    results = []

    for node in graph.nodes:

        fan_out = graph.out_degree(
            node
        )

        if fan_out >= 2:

            results.append(
                {
                    "component":
                        node,

                    "fan_out":
                        fan_out,

                    "risk":
                        (
                            "This component depends "
                            "on multiple downstream "
                            "components."
                        ),
                }
            )

    return sorted(
        results,
        key=lambda item:
            item["fan_out"],
        reverse=True,
    )


def bottleneck_score(
    graph: nx.DiGraph,
    node: str,
) -> float:

    fan_in = graph.in_degree(
        node
    )

    fan_out = graph.out_degree(
        node
    )

    try:

        centrality = (
            nx.betweenness_centrality(
                graph
            ).get(
                node,
                0.0,
            )
        )

    except Exception:

        centrality = 0.0

    score = (
        fan_in * 2
        +
        fan_out
        +
        centrality * 10
    )

    return round(
        score,
        2,
    )


def rank_bottlenecks(
    graph: nx.DiGraph,
) -> list[dict[str, Any]]:

    results = []

    for node in graph.nodes:

        results.append(
            {
                "component":
                    node,

                "score":
                    bottleneck_score(
                        graph,
                        node,
                    ),

                "fan_in":
                    graph.in_degree(
                        node
                    ),

                "fan_out":
                    graph.out_degree(
                        node
                    ),
            }
        )

    return sorted(
        results,
        key=lambda item:
            item["score"],
        reverse=True,
    )


def simulate_component_failure(
    graph: nx.DiGraph,
    component: str,
) -> dict[str, Any]:

    resolved = (
        normalize_component_name(
            graph,
            component,
        )
    )

    if not resolved:

        return {
            "success": False,
            "scenario":
                "component_failure",
            "message":
                (
                    f"Component '{component}' "
                    "was not found."
                ),
        }

    blast_radius = (
        calculate_blast_radius(
            graph,
            resolved,
        )
    )

    severity = (
        classify_blast_radius(
            blast_radius[
                "blast_radius_percent"
            ]
        )
    )

    return {
        "success": True,

        "scenario":
            "component_failure",

        "target":
            resolved,

        "severity":
            severity,

        "blast_radius":
            blast_radius,

        "likely_effects": [
            (
                f"{resolved} becomes "
                "unavailable."
            ),
            (
                f"{blast_radius['affected_component_count']} "
                "components may be affected "
                "directly or indirectly."
            ),
        ],

        "recommendations": [
            "Add redundancy where appropriate.",
            "Introduce health checks and failover.",
            "Reduce synchronous dependency chains.",
            "Add circuit breakers and timeout policies.",
        ],
    }


def simulate_database_failure(
    graph: nx.DiGraph,
    component: str,
) -> dict[str, Any]:

    result = (
        simulate_component_failure(
            graph,
            component,
        )
    )

    if not result[
        "success"
    ]:

        return result

    result[
        "scenario"
    ] = "database_failure"

    result[
        "likely_effects"
    ].extend(
        [
            (
                "Dependent services may "
                "lose read/write capability."
            ),
            (
                "Requests may queue, retry, "
                "or fail depending on client "
                "behavior."
            ),
        ]
    )

    result[
        "recommendations"
    ].extend(
        [
            "Use database replication.",
            "Define failover strategy.",
            "Use connection-pool limits.",
            "Protect the database from retry storms.",
        ]
    )

    return result


def simulate_dependency_failure(
    graph: nx.DiGraph,
    component: str,
) -> dict[str, Any]:

    result = (
        simulate_component_failure(
            graph,
            component,
        )
    )

    if result[
        "success"
    ]:

        result[
            "scenario"
        ] = "dependency_failure"

        result[
            "recommendations"
        ].extend(
            [
                "Add timeout boundaries.",
                "Use fallback behavior where possible.",
                "Consider asynchronous communication.",
            ]
        )

    return result


def simulate_traffic_spike(
    graph: nx.DiGraph,
    traffic_multiplier: float,
) -> dict[str, Any]:

    if traffic_multiplier <= 1:

        return {
            "success": False,
            "scenario":
                "traffic_spike",
            "message":
                (
                    "traffic_multiplier "
                    "must be greater than 1."
                ),
        }

    bottlenecks = (
        rank_bottlenecks(
            graph
        )
    )

    first_bottleneck = (
        bottlenecks[0]
        if bottlenecks
        else None
    )

    if traffic_multiplier >= 100:

        severity = "critical"

    elif traffic_multiplier >= 50:

        severity = "high"

    elif traffic_multiplier >= 10:

        severity = "medium"

    else:

        severity = "low"

    likely_effects = [
        (
            f"Traffic increases by "
            f"{traffic_multiplier}×."
        ),
        (
            "Highly shared dependencies "
            "are likely to saturate first."
        ),
    ]

    if first_bottleneck:

        likely_effects.append(
            (
                f"{first_bottleneck['component']} "
                "is currently the highest "
                "structural bottleneck candidate."
            )
        )

    return {
        "success": True,

        "scenario":
            "traffic_spike",

        "traffic_multiplier":
            traffic_multiplier,

        "severity":
            severity,

        "first_likely_bottleneck":
            first_bottleneck,

        "bottleneck_ranking":
            bottlenecks[:5],

        "high_fan_in_components":
            find_high_fan_in_components(
                graph
            ),

        "high_fan_out_components":
            find_high_fan_out_components(
                graph
            ),

        "likely_effects":
            likely_effects,

        "recommendations": [
            "Add horizontal scaling.",
            "Introduce caching where appropriate.",
            "Protect databases with connection limits.",
            "Use queues to absorb burst traffic.",
            "Load-test the highest-centrality components first.",
        ],

        "analysis_note":
            (
                "This is a structural simulation "
                "based on architecture topology. "
                "It does not yet use runtime CPU, "
                "memory, latency, or throughput telemetry."
            ),
    }


def run_scenario(
    graph: nx.DiGraph,
    scenario_type: str,
    target: str | None = None,
    traffic_multiplier: float = 1.0,
) -> dict[str, Any]:

    scenario_type = (
        scenario_type
        .strip()
        .lower()
    )

    if (
        scenario_type
        not in SUPPORTED_SCENARIOS
    ):

        return {
            "success": False,

            "message": (
                f"Unsupported scenario: "
                f"{scenario_type}"
            ),

            "supported_scenarios":
                sorted(
                    SUPPORTED_SCENARIOS
                ),
        }

    if (
        scenario_type
        ==
        "traffic_spike"
    ):

        return (
            simulate_traffic_spike(
                graph,
                traffic_multiplier,
            )
        )

    if not target:

        return {
            "success": False,

            "message":
                (
                    f"Scenario "
                    f"'{scenario_type}' "
                    "requires a target component."
                ),
        }

    if (
        scenario_type
        ==
        "component_failure"
    ):

        return (
            simulate_component_failure(
                graph,
                target,
            )
        )

    if (
        scenario_type
        ==
        "database_failure"
    ):

        return (
            simulate_database_failure(
                graph,
                target,
            )
        )

    return (
        simulate_dependency_failure(
            graph,
            target,
        )
    )