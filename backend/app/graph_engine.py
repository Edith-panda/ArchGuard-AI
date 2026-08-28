import networkx as nx


def build_architecture_graph(architecture):
    graph = nx.DiGraph()

    services = architecture.get("services", [])
    connections = architecture.get("connections", [])

    # Add architecture components as graph nodes.
    for service in services:
        graph.add_node(
            service["name"],
            type=service["type"]
        )

    # Add dependency relationships as directed edges.
    for source, destination in connections:
        graph.add_edge(source, destination)

    return graph


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