import json
from pathlib import Path
from typing import Any


# ---------------------------------------------------------
# Limits
# ---------------------------------------------------------

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB per file
MAX_FILES = 20


# ---------------------------------------------------------
# Supported file extensions
# ---------------------------------------------------------

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

    # Multimodal
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".pdf",
}


BINARY_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".pdf",
}


# ---------------------------------------------------------
# File type detection
# ---------------------------------------------------------

def get_file_type(filename: str) -> str:

    lower_name = filename.lower()

    if lower_name == "dockerfile":
        return "dockerfile"

    extension = Path(
        lower_name
    ).suffix

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

        # Multimodal
        ".png": "image",
        ".jpg": "image",
        ".jpeg": "image",
        ".webp": "image",

        ".pdf": "pdf",
    }

    return mapping.get(
        extension,
        "unsupported",
    )


# ---------------------------------------------------------
# Supported file check
# ---------------------------------------------------------

def is_supported(
    filename: str,
) -> bool:

    lower_name = filename.lower()

    if lower_name == "dockerfile":
        return True

    extension = Path(
        lower_name
    ).suffix

    return (
        extension
        in SUPPORTED_EXTENSIONS
    )


# ---------------------------------------------------------
# Binary file detection
# ---------------------------------------------------------

def is_binary_file(
    filename: str,
) -> bool:

    extension = Path(
        filename.lower()
    ).suffix

    return (
        extension
        in BINARY_EXTENSIONS
    )


# ---------------------------------------------------------
# Text decoding
# ---------------------------------------------------------

def decode_file_content(
    content: bytes,
    filename: str,
) -> str:

    if len(content) > MAX_FILE_SIZE:

        raise ValueError(
            f"{filename} exceeds "
            f"the 5 MB file-size limit."
        )

    try:

        return content.decode(
            "utf-8"
        )

    except UnicodeDecodeError:

        raise ValueError(
            f"{filename} is not valid "
            f"UTF-8 text."
        )


# ---------------------------------------------------------
# Generic artifact object
# ---------------------------------------------------------

def create_artifact(
    filename: str,
    content,
    source: str = "upload",
) -> dict[str, Any]:

    if isinstance(
        content,
        bytes,
    ):

        size = len(
            content
        )

    else:

        size = len(
            content.encode(
                "utf-8"
            )
        )

    return {
        "filename": filename,

        "file_type":
            get_file_type(
                filename
            ),

        "source": source,

        "content": content,

        "size": size,
    }


# ---------------------------------------------------------
# Detect canonical ArchGuard JSON
# ---------------------------------------------------------

def parse_canonical_json(
    text: str,
) -> dict[str, Any] | None:

    try:

        data = json.loads(
            text
        )

    except json.JSONDecodeError:

        return None

    if not isinstance(
        data,
        dict,
    ):
        return None

    services = data.get(
        "services"
    )

    connections = data.get(
        "connections"
    )

    if (
        isinstance(
            services,
            list,
        )
        and
        isinstance(
            connections,
            list,
        )
    ):

        return data

    return None


# ---------------------------------------------------------
# Merge canonical architectures
# ---------------------------------------------------------

def merge_canonical_architectures(
    architectures:
        list[dict[str, Any]],
) -> dict[str, Any]:

    service_map = {}

    connection_set = set()

    for architecture in architectures:

        for service in architecture.get(
            "services",
            [],
        ):

            name = service.get(
                "name"
            )

            if name:

                service_map[
                    name
                ] = service

        for connection in architecture.get(
            "connections",
            [],
        ):

            if (
                isinstance(
                    connection,
                    list,
                )
                and
                len(
                    connection
                ) == 2
            ):

                connection_set.add(
                    (
                        connection[0],
                        connection[1],
                    )
                )

    return {
        "services":
            list(
                service_map.values()
            ),

        "connections": [
            [
                source,
                destination,
            ]
            for (
                source,
                destination
            )
            in sorted(
                connection_set
            )
        ],
    }