import json
from pathlib import Path
from typing import Any


MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB per file
MAX_FILES = 20


SUPPORTED_EXTENSIONS = {
    ".json",
    ".yaml",
    ".yml",
    ".tf",
    ".hcl",
    ".md",
    ".txt",
    ".properties",
    ".toml",
    ".xml",
    ".proto",
    ".py",
    ".java",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".go",
}


def get_file_type(filename: str) -> str:
    lower_name = filename.lower()

    if lower_name == "dockerfile":
        return "dockerfile"

    extension = Path(lower_name).suffix

    mapping = {
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".tf": "terraform",
        ".hcl": "terraform",
        ".md": "documentation",
        ".txt": "documentation",
        ".properties": "configuration",
        ".toml": "configuration",
        ".xml": "configuration",
        ".proto": "protobuf",
        ".py": "source_code",
        ".java": "source_code",
        ".js": "source_code",
        ".jsx": "source_code",
        ".ts": "source_code",
        ".tsx": "source_code",
        ".go": "source_code",
    }

    return mapping.get(
        extension,
        "unsupported",
    )


def is_supported(filename: str) -> bool:
    lower_name = filename.lower()

    if lower_name == "dockerfile":
        return True

    return (
        Path(lower_name).suffix
        in SUPPORTED_EXTENSIONS
    )


def decode_file_content(
    content: bytes,
    filename: str,
) -> str:
    if len(content) > MAX_FILE_SIZE:
        raise ValueError(
            f"{filename} exceeds the "
            f"5 MB file-size limit."
        )

    try:
        return content.decode("utf-8")

    except UnicodeDecodeError:
        raise ValueError(
            f"{filename} is not valid "
            f"UTF-8 text."
        )


def parse_canonical_json(
    text: str,
) -> dict[str, Any] | None:
    """
    Detect our existing canonical
    ArchGuard JSON format.

    {
        "services": [...],
        "connections": [...]
    }
    """

    try:
        data = json.loads(text)

    except json.JSONDecodeError:
        return None

    if not isinstance(data, dict):
        return None

    services = data.get("services")
    connections = data.get("connections")

    if (
        isinstance(services, list)
        and isinstance(connections, list)
    ):
        return data

    return None


def create_artifact(
    filename: str,
    text: str,
    source: str = "upload",
) -> dict[str, Any]:

    return {
        "filename": filename,
        "file_type": get_file_type(
            filename
        ),
        "source": source,
        "content": text,
        "size": len(
            text.encode("utf-8")
        ),
    }


def merge_canonical_architectures(
    architectures: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Merge multiple canonical architecture
    JSON documents while removing duplicate
    services and connections.
    """

    service_map = {}
    connection_set = set()

    for architecture in architectures:

        for service in architecture.get(
            "services",
            [],
        ):
            name = service.get("name")

            if name:
                service_map[name] = service

        for connection in architecture.get(
            "connections",
            [],
        ):
            if (
                isinstance(connection, list)
                and len(connection) == 2
            ):
                connection_set.add(
                    (
                        connection[0],
                        connection[1],
                    )
                )

    return {
        "services": list(
            service_map.values()
        ),
        "connections": [
            [source, destination]
            for source, destination
            in sorted(connection_set)
        ],
    }