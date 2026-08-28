import json
import re
from typing import Any

import yaml


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

TYPE_PRIORITY = {
    "unknown": 0,
    "service": 1,
    "microservice": 2,
    "queue": 2,
    "gateway": 3,
    "database": 3,
}


def normalize_name(name: str) -> str:
    """
    Normalize component names so artifacts such as:

    order-service
    Order Service
    order_service

    are more likely to become the same component.
    """

    name = name.strip()

    name = re.sub(
        r"[_\-]+",
        " ",
        name,
    )

    name = re.sub(
        r"\s+",
        " ",
        name,
    )

    return name.title()


def add_service(
    services: dict,
    name: str,
    service_type: str,
    evidence: dict | None = None,
):
    if not name:
        return

    normalized = normalize_name(name)

    existing = services.get(normalized)

    if existing is None:
        services[normalized] = {
            "name": normalized,
            "type": service_type,
            "evidence": [],
        }

    else:
        existing_type = existing.get(
            "type",
            "unknown",
        )

        if (
            TYPE_PRIORITY.get(
                service_type,
                0,
            )
            >
            TYPE_PRIORITY.get(
                existing_type,
                0,
            )
        ):
            existing["type"] = service_type

    if evidence:
        services[normalized][
            "evidence"
        ].append(evidence)


def add_connection(
    connections: set,
    source: str,
    destination: str,
):
    if not source or not destination:
        return

    source = normalize_name(source)
    destination = normalize_name(
        destination
    )

    if source == destination:
        return

    connections.add(
        (
            source,
            destination,
        )
    )


# ---------------------------------------------------------
# Canonical ArchGuard JSON
# ---------------------------------------------------------

def parse_archguard_json(
    content: str,
    filename: str,
):
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return None

    if not isinstance(data, dict):
        return None

    if (
        "services" not in data
        or "connections" not in data
    ):
        return None

    services = {}
    connections = set()

    for service in data.get(
        "services",
        [],
    ):
        if not isinstance(
            service,
            dict,
        ):
            continue

        name = service.get("name")

        service_type = service.get(
            "type",
            "unknown",
        )

        add_service(
            services,
            name,
            service_type,
            {
                "filename": filename,
                "reason":
                    "Explicit architecture definition",
            },
        )

    for connection in data.get(
        "connections",
        [],
    ):
        if (
            isinstance(connection, list)
            and len(connection) == 2
        ):
            add_connection(
                connections,
                connection[0],
                connection[1],
            )

    return services, connections


# ---------------------------------------------------------
# Kubernetes
# ---------------------------------------------------------

def parse_kubernetes_yaml(
    content: str,
    filename: str,
):
    services = {}
    connections = set()

    try:
        documents = list(
            yaml.safe_load_all(
                content
            )
        )
    except yaml.YAMLError:
        return services, connections

    kubernetes_kinds = {
        "Deployment",
        "StatefulSet",
        "DaemonSet",
        "Service",
        "Ingress",
        "Job",
        "CronJob",
    }

    detected_kubernetes = False

    for document in documents:

        if not isinstance(
            document,
            dict,
        ):
            continue

        kind = document.get("kind")

        if kind not in kubernetes_kinds:
            continue

        detected_kubernetes = True

        metadata = document.get(
            "metadata",
            {},
        )

        name = metadata.get("name")

        if not name:
            continue

        if kind == "Ingress":
            component_type = "gateway"

        elif kind == "StatefulSet":
            component_type = "service"

        else:
            component_type = "microservice"

        add_service(
            services,
            name,
            component_type,
            {
                "filename": filename,
                "reason":
                    f"Kubernetes {kind}",
            },
        )

        # Look for environment variables
        # that reference other services.

        spec = document.get(
            "spec",
            {},
        )

        template = spec.get(
            "template",
            {},
        )

        pod_spec = template.get(
            "spec",
            {},
        )

        containers = pod_spec.get(
            "containers",
            [],
        )

        for container in containers:

            env_variables = (
                container.get(
                    "env",
                    [],
                )
            )

            for env in env_variables:

                value = env.get(
                    "value"
                )

                if not isinstance(
                    value,
                    str,
                ):
                    continue

                discovered = (
                    extract_hosts_from_text(
                        value
                    )
                )

                for destination in discovered:

                    add_service(
                        services,
                        destination,
                        infer_type_from_name(
                            destination
                        ),
                        {
                            "filename":
                                filename,
                            "reason":
                                "Referenced by Kubernetes environment configuration",
                        },
                    )

                    add_connection(
                        connections,
                        name,
                        destination,
                    )

    if not detected_kubernetes:
        return {}, set()

    return services, connections


# ---------------------------------------------------------
# Terraform
# ---------------------------------------------------------

def parse_terraform(
    content: str,
    filename: str,
):
    services = {}
    connections = set()

    resource_pattern = re.compile(
        r'resource\s+"([^"]+)"\s+"([^"]+)"\s*\{',
        re.MULTILINE,
    )

    matches = list(
        resource_pattern.finditer(
            content
        )
    )

    terraform_resources = []

    for match in matches:

        resource_type = match.group(1)
        resource_id = match.group(2)

        terraform_resources.append(
            (
                resource_type,
                resource_id,
            )
        )

        component_name = (
            terraform_component_name(
                resource_type,
                resource_id,
            )
        )

        component_type = (
            terraform_component_type(
                resource_type
            )
        )

        add_service(
            services,
            component_name,
            component_type,
            {
                "filename": filename,
                "reason":
                    f"Terraform resource {resource_type}.{resource_id}",
            },
        )

    # Detect Terraform references such as:
    #
    # google_sql_database_instance.orders_db.name

    for (
        source_resource_type,
        source_resource_id,
    ) in terraform_resources:

        source_name = (
            terraform_component_name(
                source_resource_type,
                source_resource_id,
            )
        )

        for (
            destination_resource_type,
            destination_resource_id,
        ) in terraform_resources:

            if (
                source_resource_type
                == destination_resource_type
                and source_resource_id
                == destination_resource_id
            ):
                continue

            reference = (
                f"{destination_resource_type}."
                f"{destination_resource_id}."
            )

            if reference in content:

                destination_name = (
                    terraform_component_name(
                        destination_resource_type,
                        destination_resource_id,
                    )
                )

                # This is intentionally
                # conservative.
                #
                # We will make Terraform
                # block-aware later rather
                # than claiming every textual
                # reference is a dependency.

                if (
                    source_name
                    != destination_name
                ):
                    pass

    return services, connections


def terraform_component_type(
    resource_type: str,
):
    lower = resource_type.lower()

    if any(
        token in lower
        for token in [
            "sql_database_instance",
            "spanner",
            "firestore",
            "bigtable",
            "database",
        ]
    ):
        return "database"

    if any(
        token in lower
        for token in [
            "pubsub_topic",
            "queue",
            "subscription",
        ]
    ):
        return "queue"

    if any(
        token in lower
        for token in [
            "load_balancer",
            "gateway",
            "forwarding_rule",
        ]
    ):
        return "gateway"

    if any(
        token in lower
        for token in [
            "cloud_run",
            "cloudfunctions",
            "function",
            "compute_instance",
        ]
    ):
        return "microservice"

    return "service"


def terraform_component_name(
    resource_type: str,
    resource_id: str,
):
    # Use the Terraform logical name
    # initially. Later evidence resolution
    # can reconcile this with configured
    # Google Cloud resource names.

    return normalize_name(
        resource_id
    )


# ---------------------------------------------------------
# Configuration / source / documentation
# ---------------------------------------------------------

def infer_type_from_name(
    name: str,
):
    lower = name.lower()

    if any(
        token in lower
        for token in [
            "postgres",
            "mysql",
            "database",
            "db",
            "sql",
        ]
    ):
        return "database"

    if any(
        token in lower
        for token in [
            "topic",
            "queue",
            "pubsub",
            "kafka",
        ]
    ):
        return "queue"

    if any(
        token in lower
        for token in [
            "gateway",
            "ingress",
            "proxy",
        ]
    ):
        return "gateway"

    return "microservice"


def extract_hosts_from_text(
    text: str,
):
    discovered = set()

    # HTTP service URLs
    #
    # http://payment-service:8080
    # https://order-api

    url_pattern = re.compile(
        r'https?://'
        r'([A-Za-z0-9._-]+)'
        r'(?::\d+)?'
    )

    for match in url_pattern.finditer(
        text
    ):
        host = match.group(1)

        if host not in {
            "localhost",
            "127.0.0.1",
        }:
            discovered.add(host)

    # JDBC
    #
    # jdbc:postgresql://orders-db:5432/orders

    jdbc_pattern = re.compile(
        r'jdbc:[A-Za-z0-9]+://'
        r'([A-Za-z0-9._-]+)'
        r'(?::\d+)?'
    )

    for match in jdbc_pattern.finditer(
        text
    ):
        discovered.add(
            match.group(1)
        )

    return discovered


def guess_source_component(
    filename: str,
    content: str,
):
    # Spring Boot
    match = re.search(
        r'spring\.application\.name'
        r'\s*=\s*'
        r'([A-Za-z0-9._-]+)',
        content,
    )

    if match:
        return match.group(1)

    # package.json-style name
    if filename.lower() == "package.json":
        try:
            data = json.loads(content)

            if isinstance(data, dict):
                name = data.get("name")

                if isinstance(
                    name,
                    str,
                ):
                    return name
        except json.JSONDecodeError:
            pass

    # Infer from source filename.
    stem = filename.rsplit(
        ".",
        1,
    )[0]

    lower_stem = stem.lower()

    generic_names = {
        "readme",
        "main",
        "application",
        "config",
        "settings",
        "deployment",
    }

    if (
        lower_stem
        not in generic_names
        and len(stem) > 2
    ):
        return stem

    return None


def parse_text_artifact(
    content: str,
    filename: str,
):
    services = {}
    connections = set()

    source_component = (
        guess_source_component(
            filename,
            content,
        )
    )

    discovered_hosts = (
        extract_hosts_from_text(
            content
        )
    )

    if source_component:

        add_service(
            services,
            source_component,
            infer_type_from_name(
                source_component
            ),
            {
                "filename": filename,
                "reason":
                    "Component inferred from artifact metadata",
            },
        )

    for destination in discovered_hosts:

        add_service(
            services,
            destination,
            infer_type_from_name(
                destination
            ),
            {
                "filename": filename,
                "reason":
                    "Dependency endpoint discovered in artifact",
            },
        )

        if source_component:
            add_connection(
                connections,
                source_component,
                destination,
            )

    return services, connections


# ---------------------------------------------------------
# Unified Artifact Parser
# ---------------------------------------------------------

def parse_artifact(
    artifact: dict[str, Any],
):
    filename = artifact[
        "filename"
    ]

    content = artifact[
        "content"
    ]

    file_type = artifact[
        "file_type"
    ]

    # ---------------------------------
    # ArchGuard canonical JSON
    # ---------------------------------

    canonical = (
        parse_archguard_json(
            content,
            filename,
        )
    )

    if canonical:
        return canonical

    # ---------------------------------
    # ArchGuard canonical YAML
    # ---------------------------------

    if file_type == "yaml":

        canonical_yaml = (
            parse_archguard_yaml(
                content,
                filename,
            )
        )

        if canonical_yaml:
            return canonical_yaml

    # ---------------------------------
    # Kubernetes YAML
    # ---------------------------------

    if file_type == "yaml":

        kubernetes_result = (
            parse_kubernetes_yaml(
                content,
                filename,
            )
        )

        if (
            kubernetes_result[0]
            or kubernetes_result[1]
        ):
            return kubernetes_result

    # ---------------------------------
    # Terraform
    # ---------------------------------

    if file_type == "terraform":

        return parse_terraform(
            content,
            filename,
        )

    # ---------------------------------
    # Generic source / config / docs
    # ---------------------------------

    return parse_text_artifact(
        content,
        filename,
    )
   

   
def parse_archguard_yaml(
    content: str,
    filename: str,
):
    try:
        data = yaml.safe_load(
            content
        )

    except yaml.YAMLError:
        return None

    if not isinstance(
        data,
        dict,
    ):
        return None

    if (
        "services" not in data
        or "connections" not in data
    ):
        return None

    services = {}
    connections = set()

    for service in data.get(
        "services",
        [],
    ):
        if not isinstance(
            service,
            dict,
        ):
            continue

        name = service.get(
            "name"
        )

        service_type = service.get(
            "type",
            "unknown",
        )

        add_service(
            services,
            name,
            service_type,
            {
                "filename": filename,
                "reason":
                    "Explicit architecture YAML definition",
            },
        )

    for connection in data.get(
        "connections",
        [],
    ):
        if (
            isinstance(
                connection,
                list,
            )
            and len(
                connection
            ) == 2
        ):
            add_connection(
                connections,
                connection[0],
                connection[1],
            )

    return (
        services,
        connections,
    )

# ---------------------------------------------------------
# Multi-artifact reconstruction
# ---------------------------------------------------------

def reconstruct_architecture(
    artifacts: list[
        dict[str, Any]
    ],
):
    combined_services = {}
    combined_connections = set()

    for artifact in artifacts:

        services, connections = (
            parse_artifact(
                artifact
            )
        )

        for (
            name,
            service,
        ) in services.items():

            add_service(
                combined_services,
                name,
                service.get(
                    "type",
                    "unknown",
                ),
            )

            for evidence in service.get(
                "evidence",
                [],
            ):
                combined_services[
                    normalize_name(name)
                ]["evidence"].append(
                    evidence
                )

        combined_connections.update(
            connections
        )

    # If a connection points to a
    # component not otherwise discovered,
    # create it so the graph remains valid.

    for (
        source,
        destination,
    ) in combined_connections:

        if source not in combined_services:
            add_service(
                combined_services,
                source,
                infer_type_from_name(
                    source
                ),
            )

        if (
            destination
            not in combined_services
        ):
            add_service(
                combined_services,
                destination,
                infer_type_from_name(
                    destination
                ),
            )

    return {
        "services": [
            {
                "name":
                    service["name"],

                "type":
                    service["type"],

                "evidence":
                    service[
                        "evidence"
                    ],
            }
            for service
            in combined_services.values()
        ],

        "connections": [
            [source, destination]
            for source, destination
            in sorted(
                combined_connections
            )
        ],
    }