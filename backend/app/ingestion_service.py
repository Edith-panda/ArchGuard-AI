from pathlib import Path
from typing import Any, Optional

from .artifact_parser import reconstruct_architecture
from .ingestion import (
    MAX_FILES,
    MAX_FILE_SIZE,
    create_artifact,
    decode_file_content,
    is_binary_file,
    is_supported,
)
from .multimodal_parser import (
    convert_multimodal_to_architecture,
    extract_architecture_from_media,
)
from .evidence_engine import enrich_architecture_with_evidence
from .digital_twin import build_architecture_digital_twin


MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
}


def merge_architectures(architectures: list[dict]) -> dict:
    services_by_name = {}
    connections = []
    connection_evidence = []
    assumptions = []

    for architecture in architectures:
        if not architecture:
            continue

        for service in architecture.get("services", []):
            name = service.get("name")
            if not name:
                continue
            if name not in services_by_name:
                services_by_name[name] = service
            else:
                existing = services_by_name[name]
                existing["evidence"] = (
                    existing.get("evidence", []) + service.get("evidence", [])
                )
                if service.get("confidence", 0) > existing.get("confidence", 0):
                    existing["confidence"] = service.get("confidence")

        for connection in architecture.get("connections", []):
            if connection not in connections:
                connections.append(connection)

        connection_evidence.extend(architecture.get("connection_evidence", []))
        assumptions.extend(architecture.get("assumptions", []))

    return {
        "services": list(services_by_name.values()),
        "connections": connections,
        "connection_evidence": connection_evidence,
        "assumptions": assumptions,
    }


async def process_architecture_inputs(
    uploaded_files: Optional[list[Any]] = None,
    manual_input: Optional[str] = None,
) -> dict:
    """Shared ingestion path for classic analysis and conversational requests."""
    uploaded_files = uploaded_files or []
    if len(uploaded_files) > MAX_FILES:
        raise ValueError(f"A maximum of {MAX_FILES} files can be analyzed at once.")

    text_artifacts = []
    architecture_fragments = []
    processed_files = []
    multimodal_errors = []

    for uploaded_file in uploaded_files:
        filename = uploaded_file.filename or "unnamed"

        if not is_supported(filename):
            processed_files.append({
                "filename": filename,
                "mode": "unsupported",
                "success": False,
                "error": "Unsupported file type",
            })
            continue

        content = await uploaded_file.read()
        if len(content) > MAX_FILE_SIZE:
            raise ValueError(f"{filename} exceeds the 5 MB file-size limit.")

        if is_binary_file(filename):
            mime_type = MIME_TYPES.get(Path(filename).suffix.lower())
            if not mime_type:
                continue
            try:
                extraction = extract_architecture_from_media(
                    content=content,
                    mime_type=mime_type,
                    filename=filename,
                )
                architecture_fragments.append(
                    convert_multimodal_to_architecture(
                        extraction=extraction,
                        filename=filename,
                    )
                )
                processed_files.append({
                    "filename": filename,
                    "mode": "multimodal",
                    "success": True,
                })
            except Exception as exc:
                multimodal_errors.append({"filename": filename, "error": str(exc)})
                processed_files.append({
                    "filename": filename,
                    "mode": "multimodal",
                    "success": False,
                    "error": str(exc),
                })
            continue

        try:
            text = decode_file_content(content, filename)
            text_artifacts.append(
                create_artifact(filename=filename, content=text, source="upload")
            )
            processed_files.append({
                "filename": filename,
                "mode": "deterministic",
                "success": True,
            })
        except Exception as exc:
            processed_files.append({
                "filename": filename,
                "mode": "deterministic",
                "success": False,
                "error": str(exc),
            })

    if manual_input and manual_input.strip():
        text_artifacts.append(
            create_artifact(
                filename="manual-input.txt",
                content=manual_input.strip(),
                source="manual",
            )
        )

    if text_artifacts:
        deterministic_architecture = reconstruct_architecture(text_artifacts)
        if deterministic_architecture:
            architecture_fragments.append(deterministic_architecture)

    architecture = merge_architectures(architecture_fragments)
    architecture_detected = bool(architecture.get("services"))
    digital_twin = None

    if architecture_detected:
        architecture = enrich_architecture_with_evidence(architecture)
        digital_twin = build_architecture_digital_twin(architecture)

    return {
        "architecture_detected": architecture_detected,
        "architecture": architecture if architecture_detected else None,
        "digital_twin": digital_twin,
        "artifacts": text_artifacts,
        "processed_files": processed_files,
        "multimodal": {
            "attempted": sum(
                1 for item in processed_files if item["mode"] == "multimodal"
            ),
            "errors": multimodal_errors,
        },
    }
