from typing import Any


SOURCE_WEIGHTS = {
    "terraform": 0.95,
    "kubernetes": 0.95,
    "json": 0.98,
    "yaml": 0.95,
    "configuration": 0.85,
    "source_code": 0.85,
    "documentation": 0.65,
    "multimodal": 0.80,
    "unknown": 0.50,
}


def clamp(value: float) -> float:
    return max(
        0.0,
        min(
            1.0,
            value,
        ),
    )


def infer_source_kind(
    filename: str,
) -> str:

    lower = filename.lower()

    if lower.endswith(".tf"):
        return "terraform"

    if lower.endswith(
        (".yaml", ".yml")
    ):
        return "yaml"

    if lower.endswith(".json"):
        return "json"

    if lower.endswith(
        (
            ".properties",
            ".toml",
            ".xml",
        )
    ):
        return "configuration"

    if lower.endswith(
        (
            ".py",
            ".java",
            ".js",
            ".jsx",
            ".ts",
            ".tsx",
            ".go",
        )
    ):
        return "source_code"

    if lower.endswith(
        (
            ".md",
            ".txt",
        )
    ):
        return "documentation"

    if lower.endswith(
        (
            ".png",
            ".jpg",
            ".jpeg",
            ".webp",
            ".pdf",
        )
    ):
        return "multimodal"

    return "unknown"


def normalize_evidence_item(
    evidence: dict[str, Any],
) -> dict[str, Any]:

    filename = evidence.get(
        "filename",
        "unknown",
    )

    source_type = evidence.get(
        "source_type"
    )

    if not source_type:
        source_type = (
            infer_source_kind(
                filename
            )
        )

    confidence = evidence.get(
        "confidence"
    )

    if confidence is None:
        confidence = (
            SOURCE_WEIGHTS.get(
                source_type,
                0.50,
            )
        )

    return {
        "filename": filename,
        "source_type": source_type,
        "reason": evidence.get(
            "reason",
            "Evidence detected",
        ),
        "confidence": clamp(
            float(confidence)
        ),
    }


def combine_confidences(
    confidences: list[float],
) -> float:
    """
    Combine independent evidence using:

    1 - Π(1 - confidence_i)

    This means multiple independent
    evidence sources increase confidence
    without simply adding probabilities.
    """

    if not confidences:
        return 0.0

    remaining_uncertainty = 1.0

    for confidence in confidences:
        remaining_uncertainty *= (
            1.0 - clamp(
                confidence
            )
        )

    combined = (
        1.0
        - remaining_uncertainty
    )

    return round(
        clamp(combined),
        3,
    )


def score_component_evidence(
    service: dict[str, Any],
) -> dict[str, Any]:

    evidence_items = []

    for evidence in service.get(
        "evidence",
        [],
    ):
        evidence_items.append(
            normalize_evidence_item(
                evidence
            )
        )

    explicit_confidence = (
        service.get(
            "confidence"
        )
    )

    confidences = [
        item["confidence"]
        for item
        in evidence_items
    ]

    if explicit_confidence is not None:
        confidences.append(
            clamp(
                float(
                    explicit_confidence
                )
            )
        )

    overall_confidence = (
        combine_confidences(
            confidences
        )
    )

    return {
        **service,
        "evidence":
            evidence_items,
        "confidence":
            overall_confidence,
        "evidence_count":
            len(
                evidence_items
            ),
    }


def score_connection_evidence(
    connections: list[list[str]],
    evidence_items: list[
        dict[str, Any]
    ],
):
    evidence_by_connection = {}

    for evidence in evidence_items:

        source = evidence.get(
            "source"
        )

        target = evidence.get(
            "target"
        )

        if not source or not target:
            continue

        key = (
            source,
            target,
        )

        normalized = (
            normalize_evidence_item(
                evidence
            )
        )

        evidence_by_connection.setdefault(
            key,
            [],
        ).append(
            normalized
        )

    scored_connections = []

    for connection in connections:

        if (
            not isinstance(
                connection,
                list,
            )
            or len(
                connection
            ) != 2
        ):
            continue

        source = connection[0]
        target = connection[1]

        key = (
            source,
            target,
        )

        items = (
            evidence_by_connection.get(
                key,
                [],
            )
        )

        confidences = [
            item["confidence"]
            for item in items
        ]

        # If the graph connection exists
        # but we don't yet have explicit
        # connection evidence, give it
        # a conservative deterministic
        # baseline.
        if not confidences:
            confidences = [
                0.70
            ]

        scored_connections.append(
            {
                "source": source,
                "target": target,
                "confidence":
                    combine_confidences(
                        confidences
                    ),
                "evidence": items,
                "evidence_count":
                    len(items),
            }
        )

    return scored_connections


def enrich_architecture_with_evidence(
    architecture: dict[str, Any],
) -> dict[str, Any]:

    services = [
        score_component_evidence(
            service
        )
        for service
        in architecture.get(
            "services",
            [],
        )
    ]

    scored_connections = (
        score_connection_evidence(
            architecture.get(
                "connections",
                [],
            ),
            architecture.get(
                "connection_evidence",
                [],
            ),
        )
    )

    architecture[
        "services"
    ] = services

    architecture[
        "scored_connections"
    ] = scored_connections

    return architecture