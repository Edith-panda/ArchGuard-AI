SERVICE_TYPE_ALIASES = {
    "service": "microservice",
    "micro-service": "microservice",
    "micro_service": "microservice",
    "app": "microservice",
    "application": "microservice",

    "db": "database",
    "postgres": "database",
    "postgresql": "database",
    "mysql": "database",
    "sql": "database",

    "api-gateway": "gateway",
    "api_gateway": "gateway",

    "redis": "cache",
    "memcached": "cache",

    "kafka": "queue",
    "pubsub": "queue",
    "pub/sub": "queue",
    "message-queue": "queue",
}


def normalize_service_type(service_type):
    if not service_type:
        return "unknown"

    normalized = (
        service_type
        .strip()
        .lower()
    )

    return SERVICE_TYPE_ALIASES.get(
        normalized,
        normalized
    )


def normalize_service(service):
    name = service.get("name")

    if not name:
        raise ValueError(
            "Every service must have a name."
        )

    name = name.strip()

    if not name:
        raise ValueError(
            "Service name cannot be empty."
        )

    service_type = normalize_service_type(
        service.get("type")
    )

    normalized_service = {
    "name": name,
    "type": service_type,
}

    if "metadata" in service:
        normalized_service["metadata"] = (
            service["metadata"]
        )

    return normalized_service


def normalize_architecture(architecture):
    raw_services = architecture.get(
        "services",
        []
    )

    raw_connections = architecture.get(
        "connections",
        []
    )

    services_by_name = {}

    for service in raw_services:
        normalized_service = normalize_service(
            service
        )

        services_by_name[
            normalized_service["name"]
        ] = normalized_service

    services = list(
        services_by_name.values()
    )

    known_services = set(
        services_by_name.keys()
    )

    normalized_connections = []
    seen_connections = set()

    for connection in raw_connections:
        if (
            not isinstance(connection, list)
            or len(connection) != 2
        ):
            raise ValueError(
                "Every connection must contain "
                "exactly two component names."
            )

        source = str(
            connection[0]
        ).strip()

        destination = str(
            connection[1]
        ).strip()

        if (
            source not in known_services
            or destination not in known_services
        ):
            raise ValueError(
                f"Invalid connection: "
                f"{source} -> {destination}. "
                f"Both components must exist "
                f"in services."
            )

        connection_tuple = (
            source,
            destination
        )

        if connection_tuple in seen_connections:
            continue

        seen_connections.add(
            connection_tuple
        )

        normalized_connections.append(
            [source, destination]
        )

    return {
        "services": services,
        "connections": normalized_connections,
    }