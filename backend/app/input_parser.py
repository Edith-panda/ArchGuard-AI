import json

import yaml
from .normalizer import normalize_architecture
from .kubernetes_parser import (
    parse_kubernetes_yaml,
)
from .terraform_parser import (
    parse_terraform_text,
)

def parse_architecture_text(
    content: str,
    file_type: str,
):
    normalized_type = (
        file_type
        .lower()
        .strip()
    )

    if normalized_type == "json":
        architecture = json.loads(
            content
        )

    elif normalized_type in (
        "yaml",
        "yml",
    ):
        architecture = yaml.safe_load(
            content
        )

    elif normalized_type in (
        "kubernetes",
        "k8s",
    ):
        architecture = (
            parse_kubernetes_yaml(
                content
            )
        )
    elif normalized_type in (
        "terraform",
        "tf",
        "hcl",
    ):
        architecture = (
            parse_terraform_text(
                content
            )
        )

    else:
        raise ValueError(
            f"Unsupported file type: "
            f"{file_type}"
        )

    validated_architecture = (
        validate_architecture(
            architecture
        )
    )

    return normalize_architecture(
        validated_architecture
    )
    normalized_type = file_type.lower().strip()

    if normalized_type == "json":
        architecture = json.loads(content)

    elif normalized_type in ("yaml", "yml"):
        architecture = yaml.safe_load(content)

    else:
        raise ValueError(
            f"Unsupported file type: {file_type}"
        )

    validated_architecture = (
    validate_architecture(
        architecture
    )
    )

    return normalize_architecture(
        validated_architecture
    )


def validate_architecture(
    architecture: dict,
):
    if not isinstance(architecture, dict):
        raise ValueError(
            "Architecture input must be an object."
        )

    if "services" not in architecture:
        raise ValueError(
            "Architecture must contain 'services'."
        )

    if "connections" not in architecture:
        raise ValueError(
            "Architecture must contain 'connections'."
        )

    if not isinstance(
        architecture["services"],
        list,
    ):
        raise ValueError(
            "'services' must be a list."
        )

    if not isinstance(
        architecture["connections"],
        list,
    ):
        raise ValueError(
            "'connections' must be a list."
        )

    return architecture