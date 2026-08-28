import yaml


def parse_kubernetes_yaml(content: str):
    documents = list(
        yaml.safe_load_all(content)
    )

    services = []
    connections = []

    deployments = {}
    k8s_services = {}

    for document in documents:
        if not document:
            continue

        kind = document.get("kind")
        metadata = document.get("metadata", {})
        spec = document.get("spec", {})

        name = metadata.get("name")

        if not kind or not name:
            continue

        # -----------------------------
        # Deployment
        # -----------------------------
        if kind == "Deployment":
            labels = (
                spec
                .get("template", {})
                .get("metadata", {})
                .get("labels", {})
            )

            deployments[name] = {
                "name": name,
                "labels": labels,
            }

            services.append(
                {
                    "name": name,
                    "type": "microservice",
                }
            )

        # -----------------------------
        # Kubernetes Service
        # -----------------------------
        elif kind == "Service":
            selector = spec.get(
                "selector",
                {}
            )

            k8s_services[name] = {
                "name": name,
                "selector": selector,
            }

            services.append(
                {
                    "name": name,
                    "type": "gateway",
                }
            )

    # ---------------------------------
    # Infer Service -> Deployment links
    # ---------------------------------

    for service_name, service_info in (
        k8s_services.items()
    ):
        selector = service_info[
            "selector"
        ]

        if not selector:
            continue

        for deployment_name, deployment_info in (
            deployments.items()
        ):
            labels = deployment_info[
                "labels"
            ]

            matches = all(
                labels.get(key) == value
                for key, value
                in selector.items()
            )

            if matches:
                connections.append(
                    [
                        service_name,
                        deployment_name,
                    ]
                )

    return {
        "services": services,
        "connections": connections,
    }