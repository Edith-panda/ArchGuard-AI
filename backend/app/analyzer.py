def analyze_architecture(architecture):
    findings = []

    services = architecture.get("services", [])
    connections = architecture.get("connections", [])

    service_types = {
        service["name"]: service["type"]
        for service in services
    }

    # RULE 1:
    # Detect databases shared by multiple services.
    for service in services:
        if service["type"] != "database":
            continue

        database_name = service["name"]

        dependent_services = [
            source
            for source, destination in connections
            if destination == database_name
        ]

        if len(dependent_services) > 1:
            findings.append(
                {
                    "severity": "HIGH",
                    "category": "Reliability",
                    "component": database_name,
                    "issue": "Shared database dependency",
                    "reason": (
                        f"{database_name} is directly used by "
                        f"{len(dependent_services)} services: "
                        f"{dependent_services}."
                    ),
                    "recommendation": (
                        "Evaluate high availability, replication, "
                        "failover, connection limits, and data "
                        "ownership boundaries."
                    ),
                }
            )

    # RULE 2:
    # Detect direct microservice-to-microservice dependencies.
    for source, destination in connections:
        source_type = service_types.get(source)
        destination_type = service_types.get(destination)

        if (
            source_type == "microservice"
            and destination_type == "microservice"
        ):
            findings.append(
                {
                    "severity": "MEDIUM",
                    "category": "Reliability",
                    "component": source,
                    "issue": "Service dependency",
                    "reason": (
                        f"{source} directly depends on {destination}. "
                        f"A failure or slowdown in {destination} "
                        f"may affect {source}."
                    ),
                    "recommendation": (
                        "Consider timeouts, retries with exponential "
                        "backoff, circuit breakers, graceful degradation, "
                        "or asynchronous communication where appropriate."
                    ),
                }
            )

    # RULE 3:
    # Detect components with multiple incoming dependencies.
    dependency_count = {}

    for _, destination in connections:
        dependency_count[destination] = (
            dependency_count.get(destination, 0) + 1
        )

    for component, count in dependency_count.items():
        if count >= 2:
            findings.append(
                {
                    "severity": "MEDIUM",
                    "category": "Scalability",
                    "component": component,
                    "issue": "High fan-in component",
                    "reason": (
                        f"{component} receives direct dependencies "
                        f"from {count} components."
                    ),
                    "recommendation": (
                        "Review capacity limits, autoscaling, connection "
                        "limits, caching, queueing, and horizontal scaling."
                    ),
                }
            )

    # RULE 4:
    # Detect architectures with only one database component.
    databases = [
        service["name"]
        for service in services
        if service["type"] == "database"
    ]

    if len(databases) == 1:
        database_name = databases[0]

        findings.append(
            {
                "severity": "HIGH",
                "category": "Reliability",
                "component": database_name,
                "issue": "Potential database single point of failure",
                "reason": (
                    f"The architecture contains only one database "
                    f"component: {database_name}."
                ),
                "recommendation": (
                    "Verify whether the database has high availability, "
                    "replication, automated failover, backups, and "
                    "disaster recovery."
                ),
            }
        )

    return findings