import networkx as nx


def build_architecture_graph(architecture):
    graph = nx.DiGraph()

    services = architecture.get("services", [])
    connections = architecture.get("connections", [])

    for service in services:
        name = service.get("name")
        if not name:
            continue
        graph.add_node(
            name,
            type=service.get("type", "unknown"),
        )

    for connection in connections:
        if isinstance(connection, (list, tuple)) and len(connection) >= 2:
            graph.add_edge(connection[0], connection[1])

    return graph


# Conversational-agent compatibility alias.
def build_graph(architecture):
    return build_architecture_graph(architecture)


def get_graph_summary(graph):
    return {
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
    }


def get_dependencies(graph, component):
    return list(graph.successors(component))


def get_dependents(graph, component):
    return list(graph.predecessors(component))


def get_downstream_components(graph, component):
    return list(nx.descendants(graph, component))


def get_upstream_components(graph, component):
    return list(nx.ancestors(graph, component))
