import io

import hcl2


RESOURCE_TYPE_MAP = {
    "google_cloud_run_v2_service": "microservice",
    "google_cloud_run_service": "microservice",
    "google_sql_database_instance": "database",
    "google_pubsub_topic": "queue",
    "google_pubsub_subscription": "queue",
    "google_storage_bucket": "storage",
    "google_compute_instance": "compute",
    "google_compute_backend_service": "gateway",
    "google_compute_url_map": "gateway",
}


def get_component_type(
    terraform_resource_type,
):
    return RESOURCE_TYPE_MAP.get(
        terraform_resource_type,
        "infrastructure",
    )


def get_display_name(
    resource_config,
    fallback_name,
):
    name = resource_config.get("name")

    if isinstance(name, str):
        return name

    return fallback_name


def parse_terraform_data(terraform):
    services = []
    connections = []

    resources = terraform.get(
        "resource",
        [],
    )

    for resource_block in resources:
        for (
            resource_type,
            resource_instances,
        ) in resource_block.items():

            for (
                resource_name,
                resource_config,
            ) in resource_instances.items():

                component_name = get_display_name(
                    resource_config,
                    resource_name,
                )

                component_type = get_component_type(
                    resource_type
                )

                services.append(
                    {
                        "name": component_name,
                        "type": component_type,
                        "metadata": {
                            "terraform_type": resource_type,
                            "terraform_name": resource_name,
                        },
                    }
                )

    return {
        "services": services,
        "connections": connections,
    }


def parse_terraform_file(file_path):
    with open(
        file_path,
        "r",
        encoding="utf-8",
    ) as file:
        terraform = hcl2.load(file)

    return parse_terraform_data(
        terraform
    )


def parse_terraform_text(content: str):
    terraform = hcl2.load(
        io.StringIO(content)
    )

    return parse_terraform_data(
        terraform
    )