from typing import Any, Optional

from .artifact_parser import (
    reconstruct_architecture,
)

from .ingestion import (
    create_artifact,
    decode_file_content,
    is_binary_file,
)

from .multimodal_parser import (
    convert_multimodal_to_architecture,
    extract_architecture_from_media,
)

from .evidence_engine import (
    enrich_architecture_with_evidence,
)

from .digital_twin import (
    build_architecture_digital_twin,
)


def merge_architectures(
    architectures: list[dict],
) -> dict:
    """
    Merge architecture fragments produced by
    deterministic and multimodal extraction.
    """

    services_by_name = {}
    connections = []
    connection_evidence = []
    assumptions = []

    for architecture in architectures:

        if not architecture:
            continue

        for service in architecture.get(
            "services",
            [],
        ):
            name = service.get("name")

            if not name:
                continue

            if name not in services_by_name:
                services_by_name[name] = service
            else:
                existing = services_by_name[name]

                existing_evidence = existing.get(
                    "evidence",
                    [],
                )

                new_evidence = service.get(
                    "evidence",
                    [],
                )

                existing["evidence"] = (
                    existing_evidence
                    + new_evidence
                )

        for connection in architecture.get(
            "connections",
            [],
        ):
            if connection not in connections:
                connections.append(connection)

        connection_evidence.extend(
            architecture.get(
                "connection_evidence",
                [],
            )
        )

        assumptions.extend(
            architecture.get(
                "assumptions",
                [],
            )
        )

    return {
        "services": list(
            services_by_name.values()
        ),
        "connections": connections,
        "connection_evidence":
            connection_evidence,
        "assumptions": assumptions,
    }


async def process_architecture_inputs(
    uploaded_files: Optional[list[Any]] = None,
    manual_input: Optional[str] = None,
) -> dict:
    """
    Shared ArchGuard ingestion pipeline.

    Used by both the traditional ingestion API
    and the conversational assistant.

    Processing strategy:

    Text artifacts
        -> deterministic parsers

    Images / PDFs
        -> Gemini multimodal extraction

    Results
        -> merged architecture
        -> evidence scoring
        -> architecture digital twin
    """

    uploaded_files = uploaded_files or []

    text_artifacts = []
    architecture_fragments = []

    processed_files = []
    multimodal_errors = []

    # ------------------------------------------
    # 1. Process uploaded files
    # ------------------------------------------

    for uploaded_file in uploaded_files:

        filename = (
            uploaded_file.filename
            or "unnamed"
        )

        content = await uploaded_file.read()

        # --------------------------------------
        # Binary / multimodal
        # --------------------------------------

        if is_binary_file(filename):

            mime_type = (
                uploaded_file.content_type
                or "application/octet-stream"
            )

            try:

                extraction = (
                    extract_architecture_from_media(
                        content=content,
                        mime_type=mime_type,
                        filename=filename,
                    )
                )

                architecture_fragment = (
                    convert_multimodal_to_architecture(
                        extraction,
                        filename=filename,
                    )
                )

                architecture_fragments.append(
                    architecture_fragment
                )

                processed_files.append({
                    "filename": filename,
                    "mode": "multimodal",
                    "success": True,
                })

            except Exception as exc:

                multimodal_errors.append({
                    "filename": filename,
                    "error": str(exc),
                })

                processed_files.append({
                    "filename": filename,
                    "mode": "multimodal",
                    "success": False,
                })

            continue

        # --------------------------------------
        # Text artifact
        # --------------------------------------

        try:

            text = decode_file_content(
                content
            )

            artifact = create_artifact(
                filename=filename,
                content=text,
                source="upload",
            )

            text_artifacts.append(
                artifact
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

    # ------------------------------------------
    # 2. Manual/pasted context
    # ------------------------------------------

    if manual_input and manual_input.strip():

        artifact = create_artifact(
            filename="manual_input.txt",
            content=manual_input.strip(),
            source="manual",
        )

        text_artifacts.append(
            artifact
        )

    # ------------------------------------------
    # 3. Deterministic reconstruction
    # ------------------------------------------

    if text_artifacts:

        deterministic_architecture = (
            reconstruct_architecture(
                text_artifacts
            )
        )

        if deterministic_architecture:
            architecture_fragments.append(
                deterministic_architecture
            )

    # ------------------------------------------
    # 4. Merge extracted architecture
    # ------------------------------------------

    architecture = merge_architectures(
        architecture_fragments
    )

    architecture_detected = bool(
        architecture.get("services")
    )

    # ------------------------------------------
    # 5. Evidence + Digital Twin
    # ------------------------------------------

    digital_twin = None

    if architecture_detected:

        architecture = (
            enrich_architecture_with_evidence(
                architecture
            )
        )

        digital_twin = (
            build_architecture_digital_twin(
                architecture
            )
        )

    # ------------------------------------------
    # 6. Shared result
    # ------------------------------------------

    return {
        "architecture_detected":
            architecture_detected,

        "architecture":
            architecture
            if architecture_detected
            else None,

        "digital_twin":
            digital_twin,

        "artifacts":
            text_artifacts,

        "processed_files":
            processed_files,

        "multimodal": {
            "attempted":
                sum(
                    1
                    for item
                    in processed_files
                    if item["mode"]
                    == "multimodal"
                ),

            "errors":
                multimodal_errors,
        },
    }