from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def validate_yaml(
    path: Path,
) -> dict[str, Any]:

    try:

        content = path.read_text(
            encoding="utf-8"
        )

        yaml.safe_load(
            content
        )

        return {
            "valid":
                True,

            "validator":
                "yaml.safe_load",

            "message":
                "YAML syntax is valid.",
        }

    except Exception as error:

        return {
            "valid":
                False,

            "validator":
                "yaml.safe_load",

            "message":
                str(error),
        }


def validate_terraform(
    path: Path,
) -> dict[str, Any]:

    content = path.read_text(
        encoding="utf-8"
    )

    open_braces = (
        content.count("{")
    )

    close_braces = (
        content.count("}")
    )

    if (
        open_braces
        != close_braces
    ):

        return {
            "valid":
                False,

            "validator":
                "terraform_structural_check",

            "message":
                (
                    "Terraform braces "
                    "are not balanced."
                ),
        }

    return {
        "valid":
            True,

        "validator":
            "terraform_structural_check",

        "message":
            (
                "Basic Terraform structural "
                "validation passed."
            ),
    }


def validate_text(
    path: Path,
) -> dict[str, Any]:

    if (
        not path.exists()
        or path.stat().st_size == 0
    ):

        return {
            "valid":
                False,

            "validator":
                "file_check",

            "message":
                "Generated artifact is empty.",
        }

    return {
        "valid":
            True,

        "validator":
            "file_check",

        "message":
            "Generated artifact exists and is non-empty.",
    }


def validate_sandbox_artifact(
    artifact_path: str,
    file_format: str,
) -> dict[str, Any]:

    path = Path(
        artifact_path
    )

    if not path.exists():

        return {
            "valid":
                False,

            "validator":
                "existence_check",

            "message":
                "Sandbox artifact does not exist.",
        }

    normalized = (
        file_format
        .strip()
        .lower()
    )

    if normalized in {
        "yaml",
        "kubernetes",
        "policy",
    }:

        return validate_yaml(
            path
        )

    if (
        normalized
        ==
        "terraform"
    ):

        return validate_terraform(
            path
        )

    return validate_text(
        path
    )