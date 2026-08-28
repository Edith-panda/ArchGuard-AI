from .graph_engine import (
    get_dependents,
    get_upstream_components,
)



def simulate_component_failure(
    graph,
    component
):
    if component not in graph:
        return {
            "success": False,
            "component": component,
            "message": (
                f"Component '{component}' "
                f"does not exist in the architecture."
            ),
        }

    direct_dependents = get_dependents(
        graph,
        component
    )

    affected_components = (
        get_upstream_components(
            graph,
            component
        )
    )

    total_nodes = graph.number_of_nodes()

    affected_count = len(
        affected_components
    )

    if total_nodes > 1:
        impact_percentage = round(
            (
                affected_count
                / (total_nodes - 1)
            )
            * 100,
            2,
        )
    else:
        impact_percentage = 0

    if impact_percentage >= 75:
        impact_level = "CRITICAL"

    elif impact_percentage >= 40:
        impact_level = "HIGH"

    elif impact_percentage > 0:
        impact_level = "MEDIUM"

    else:
        impact_level = "LOW"

    return {
        "success": True,
        "failed_component": component,
        "direct_dependents": direct_dependents,
        "affected_components": (
            affected_components
        ),
        "affected_count": affected_count,
        "impact_percentage": (
            impact_percentage
        ),
        "impact_level": impact_level,
    }

def format_failure_scenario(
    scenario
):
    if not scenario["success"]:
        return scenario["message"]

    failed_component = scenario[
        "failed_component"
    ]

    direct_dependents = scenario[
        "direct_dependents"
    ]

    affected_components = scenario[
        "affected_components"
    ]

    impact_percentage = scenario[
        "impact_percentage"
    ]

    impact_level = scenario[
        "impact_level"
    ]

    lines = []

    lines.append(
        f"Scenario: {failed_component} fails"
    )

    lines.append(
        f"Impact Level: {impact_level}"
    )

    lines.append(
        f"Architecture Impact: "
        f"{impact_percentage}%"
    )

    lines.append(
        f"Direct Dependents: "
        f"{direct_dependents}"
    )

    lines.append(
        f"Potentially Affected Components: "
        f"{affected_components}"
    )

    return "\n".join(lines)