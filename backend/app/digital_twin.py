import re
from collections import defaultdict
from difflib import SequenceMatcher
from typing import Any


# ---------------------------------------------------------
# Generic names
# ---------------------------------------------------------

GENERIC_DATABASE_NAMES = {
    "postgres",
    "postgresql",
    "mysql",
    "mongodb",
    "mongo",
    "redis",
    "database",
    "db",
    "sql database",
}

GENERIC_QUEUE_NAMES = {
    "queue",
    "topic",
    "pubsub",
    "pub sub",
    "kafka",
    "rabbitmq",
}


# ---------------------------------------------------------
# Name normalization
# ---------------------------------------------------------

def normalize_entity_name(
    name: str,
) -> str:

    if not name:
        return ""

    value = name.strip().lower()

    value = re.sub(
        r"[_\-\.]+",
        " ",
        value,
    )

    value = re.sub(
        r"[^a-z0-9\s]",
        "",
        value,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


# ---------------------------------------------------------
# Stable entity ID
# ---------------------------------------------------------

def make_entity_id(
    name: str,
) -> str:

    normalized = (
        normalize_entity_name(
            name
        )
    )

    return re.sub(
        r"\s+",
        "-",
        normalized,
    )


# ---------------------------------------------------------
# Type normalization
# ---------------------------------------------------------

def normalize_type(
    component_type: str | None,
) -> str:

    if not component_type:
        return "unknown"

    value = (
        component_type
        .strip()
        .lower()
    )

    mapping = {
        "db": "database",
        "postgres": "database",
        "postgresql": "database",
        "mysql": "database",
        "sql": "database",

        "micro-service": "microservice",
        "micro service": "microservice",

        "api gateway": "gateway",

        "pubsub": "queue",
        "pub/sub": "queue",
        "topic": "queue",

        "client application": "client",
    }

    return mapping.get(
        value,
        value,
    )


# ---------------------------------------------------------
# Name similarity
# ---------------------------------------------------------

def name_similarity(
    first: str,
    second: str,
) -> float:

    first_normalized = (
        normalize_entity_name(
            first
        )
    )

    second_normalized = (
        normalize_entity_name(
            second
        )
    )

    if (
        not first_normalized
        or
        not second_normalized
    ):
        return 0.0

    if (
        first_normalized
        ==
        second_normalized
    ):
        return 1.0

    return SequenceMatcher(
        None,
        first_normalized,
        second_normalized,
    ).ratio()


# ---------------------------------------------------------
# Component type compatibility
# ---------------------------------------------------------

def types_compatible(
    first_type: str,
    second_type: str,
) -> bool:

    first = normalize_type(
        first_type
    )

    second = normalize_type(
        second_type
    )

    if first == second:
        return True

    if "unknown" in {
        first,
        second,
    }:
        return True

    service_family = {
        "service",
        "microservice",
    }

    if (
        first in service_family
        and
        second in service_family
    ):
        return True

    return False


# ---------------------------------------------------------
# Prefer better display names
# ---------------------------------------------------------

def choose_canonical_name(
    names: list[str],
) -> str:

    if not names:
        return "Unknown"

    def score(name: str):

        # Prefer readable names rather
        # than machine resource names.
        spaces = (
            1
            if " " in name
            else 0
        )

        uppercase_penalty = (
            1
            if name.isupper()
            else 0
        )

        machine_penalty = (
            name.count("_")
            +
            name.count("-")
        )

        return (
            spaces,
            -machine_penalty,
            -uppercase_penalty,
            len(name),
        )

    return max(
        names,
        key=score,
    )


# ---------------------------------------------------------
# Merge evidence
# ---------------------------------------------------------

def merge_evidence(
    first: list[dict[str, Any]],
    second: list[dict[str, Any]],
) -> list[dict[str, Any]]:

    combined = []

    seen = set()

    for item in (
        first + second
    ):

        key = (
            item.get(
                "filename"
            ),
            item.get(
                "reason"
            ),
            item.get(
                "source_type"
            ),
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        combined.append(
            item
        )

    return combined


# ---------------------------------------------------------
# Build initial entities
# ---------------------------------------------------------

def create_initial_entities(
    services: list[dict[str, Any]],
):

    entities = []

    for index, service in enumerate(
        services
    ):

        name = service.get(
            "name",
            f"Unknown {index}",
        )

        entity = {
            "entity_id":
                make_entity_id(
                    name
                )
                or f"entity-{index}",

            "canonical_name":
                name,

            "normalized_name":
                normalize_entity_name(
                    name
                ),

            "type":
                normalize_type(
                    service.get(
                        "type",
                        "unknown",
                    )
                ),

            "aliases": [
                name
            ],

            "confidence":
                service.get(
                    "confidence",
                    0.5,
                ),

            "evidence":
                service.get(
                    "evidence",
                    [],
                ),

            "evidence_count":
                service.get(
                    "evidence_count",
                    len(
                        service.get(
                            "evidence",
                            [],
                        )
                    ),
                ),
        }

        entities.append(
            entity
        )

    return entities


# ---------------------------------------------------------
# Should two entities merge?
# ---------------------------------------------------------

def should_merge(
    first: dict[str, Any],
    second: dict[str, Any],
) -> tuple[bool, str, float]:

    if not types_compatible(
        first["type"],
        second["type"],
    ):
        return (
            False,
            "incompatible component types",
            0.0,
        )

    first_name = (
        first[
            "normalized_name"
        ]
    )

    second_name = (
        second[
            "normalized_name"
        ]
    )

    # Exact normalized match:
    #
    # order-service
    # order_service
    # Order Service

    if first_name == second_name:

        return (
            True,
            "same normalized name",
            1.0,
        )

    similarity = (
        name_similarity(
            first_name,
            second_name,
        )
    )

    # Conservative fuzzy matching.
    #
    # This intentionally avoids merging
    # things such as:
    #
    # order-service
    # order-payment-service

    if similarity >= 0.93:

        return (
            True,
            "very high name similarity",
            round(
                similarity,
                3,
            ),
        )

    return (
        False,
        "insufficient evidence",
        round(
            similarity,
            3,
        ),
    )


# ---------------------------------------------------------
# Merge entity objects
# ---------------------------------------------------------

def merge_entities(
    first: dict[str, Any],
    second: dict[str, Any],
):

    aliases = list(
        dict.fromkeys(
            first.get(
                "aliases",
                [],
            )
            +
            second.get(
                "aliases",
                [],
            )
        )
    )

    canonical_name = (
        choose_canonical_name(
            aliases
        )
    )

    first_confidence = float(
        first.get(
            "confidence",
            0.0,
        )
    )

    second_confidence = float(
        second.get(
            "confidence",
            0.0,
        )
    )

    # Combined supporting evidence.
    combined_confidence = (
        1
        -
        (
            1 - first_confidence
        )
        *
        (
            1 - second_confidence
        )
    )

    evidence = (
        merge_evidence(
            first.get(
                "evidence",
                [],
            ),
            second.get(
                "evidence",
                [],
            ),
        )
    )

    return {
        "entity_id":
            make_entity_id(
                canonical_name
            ),

        "canonical_name":
            canonical_name,

        "normalized_name":
            normalize_entity_name(
                canonical_name
            ),

        "type":
            (
                first["type"]
                if first["type"]
                != "unknown"
                else second["type"]
            ),

        "aliases":
            aliases,

        "confidence":
            round(
                min(
                    combined_confidence,
                    1.0,
                ),
                3,
            ),

        "evidence":
            evidence,

        "evidence_count":
            len(
                evidence
            ),
    }


# ---------------------------------------------------------
# Resolve duplicate entities
# ---------------------------------------------------------

def resolve_entities(
    services: list[dict[str, Any]],
):

    candidates = (
        create_initial_entities(
            services
        )
    )

    resolved = []

    resolution_log = []

    for candidate in candidates:

        matched_index = None

        match_reason = None

        match_score = 0.0

        for index, existing in enumerate(
            resolved
        ):

            (
                merge,
                reason,
                score,
            ) = should_merge(
                existing,
                candidate,
            )

            if merge:

                matched_index = index
                match_reason = reason
                match_score = score

                break

        if matched_index is None:

            resolved.append(
                candidate
            )

            continue

        existing = resolved[
            matched_index
        ]

        before_aliases = list(
            existing[
                "aliases"
            ]
        )

        merged = merge_entities(
            existing,
            candidate,
        )

        resolved[
            matched_index
        ] = merged

        resolution_log.append(
            {
                "canonical_entity":
                    merged[
                        "canonical_name"
                    ],

                "merged_alias":
                    candidate[
                        "canonical_name"
                    ],

                "previous_aliases":
                    before_aliases,

                "reason":
                    match_reason,

                "similarity":
                    match_score,
            }
        )

    return (
        resolved,
        resolution_log,
    )


# ---------------------------------------------------------
# Alias lookup table
# ---------------------------------------------------------

def build_alias_lookup(
    entities: list[dict[str, Any]],
):

    lookup = {}

    for entity in entities:

        canonical_name = entity[
            "canonical_name"
        ]

        for alias in entity.get(
            "aliases",
            [],
        ):

            lookup[
                normalize_entity_name(
                    alias
                )
            ] = canonical_name

        lookup[
            normalize_entity_name(
                canonical_name
            )
        ] = canonical_name

    return lookup


# ---------------------------------------------------------
# Resolve edge names
# ---------------------------------------------------------

def resolve_connection_name(
    name: str,
    alias_lookup: dict[str, str],
) -> str:

    normalized = (
        normalize_entity_name(
            name
        )
    )

    return alias_lookup.get(
        normalized,
        name,
    )


# ---------------------------------------------------------
# Rebuild canonical connections
# ---------------------------------------------------------

def resolve_connections(
    connections: list[list[str]],
    alias_lookup: dict[str, str],
):

    resolved_connections = set()

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

        source = (
            resolve_connection_name(
                connection[0],
                alias_lookup,
            )
        )

        target = (
            resolve_connection_name(
                connection[1],
                alias_lookup,
            )
        )

        # Ignore accidental self-loops
        # created by alias collapsing.

        if source == target:
            continue

        resolved_connections.add(
            (
                source,
                target,
            )
        )

    return [
        [
            source,
            target,
        ]
        for (
            source,
            target
        )
        in sorted(
            resolved_connections
        )
    ]


# ---------------------------------------------------------
# Dependency metadata
# ---------------------------------------------------------

def build_dependency_metadata(
    entities: list[dict[str, Any]],
    connections: list[list[str]],
):

    outgoing = defaultdict(
        list
    )

    incoming = defaultdict(
        list
    )

    for (
        source,
        target
    ) in connections:

        outgoing[
            source
        ].append(
            target
        )

        incoming[
            target
        ].append(
            source
        )

    for entity in entities:

        name = entity[
            "canonical_name"
        ]

        entity[
            "dependencies"
        ] = sorted(
            set(
                outgoing.get(
                    name,
                    [],
                )
            )
        )

        entity[
            "dependents"
        ] = sorted(
            set(
                incoming.get(
                    name,
                    [],
                )
            )
        )

        entity[
            "out_degree"
        ] = len(
            entity[
                "dependencies"
            ]
        )

        entity[
            "in_degree"
        ] = len(
            entity[
                "dependents"
            ]
        )

    return entities


# ---------------------------------------------------------
# Generic DB reconciliation
# ---------------------------------------------------------

def reconcile_single_generic_database(
    entities: list[dict[str, Any]],
    connections: list[list[str]],
):

    databases = [
        entity
        for entity in entities
        if entity.get(
            "type"
        ) == "database"
    ]

    if len(
        databases
    ) != 2:
        return (
            entities,
            connections,
            [],
        )

    generic = None
    named = None

    for database in databases:

        normalized = (
            normalize_entity_name(
                database[
                    "canonical_name"
                ]
            )
        )

        if (
            normalized
            in GENERIC_DATABASE_NAMES
        ):
            generic = database

        else:
            named = database

    if (
        generic is None
        or
        named is None
    ):
        return (
            entities,
            connections,
            [],
        )

    # Conservative rule:
    #
    # If the reconstructed architecture
    # has exactly two DB entities and one
    # is merely a generic technology label
    # such as PostgreSQL, treat it as an
    # alias of the named database.
    #
    # Later we can replace this rule with
    # stronger semantic evidence.

    merged = merge_entities(
        named,
        generic,
    )

    merged[
        "canonical_name"
    ] = named[
        "canonical_name"
    ]

    merged[
        "entity_id"
    ] = make_entity_id(
        named[
            "canonical_name"
        ]
    )

    merged[
        "normalized_name"
    ] = normalize_entity_name(
        named[
            "canonical_name"
        ]
    )

    old_names = {
        generic[
            "canonical_name"
        ],
        named[
            "canonical_name"
        ],
    }

    new_entities = [
        entity
        for entity in entities
        if entity[
            "canonical_name"
        ]
        not in old_names
    ]

    new_entities.append(
        merged
    )

    new_connections = set()

    for (
        source,
        target
    ) in connections:

        if source in old_names:
            source = merged[
                "canonical_name"
            ]

        if target in old_names:
            target = merged[
                "canonical_name"
            ]

        if source != target:

            new_connections.add(
                (
                    source,
                    target,
                )
            )

    resolution_log = [
        {
            "canonical_entity":
                merged[
                    "canonical_name"
                ],

            "merged_alias":
                generic[
                    "canonical_name"
                ],

            "reason":
                (
                    "single generic database "
                    "technology label matched "
                    "to the only named database"
                ),

            "confidence":
                0.85,
        }
    ]

    return (
        new_entities,
        [
            [
                source,
                target,
            ]
            for (
                source,
                target
            )
            in sorted(
                new_connections
            )
        ],
        resolution_log,
    )


# ---------------------------------------------------------
# Build complete Architecture Digital Twin
# ---------------------------------------------------------

def build_architecture_digital_twin(
    architecture: dict[str, Any],
) -> dict[str, Any]:

    services = architecture.get(
        "services",
        [],
    )

    connections = architecture.get(
        "connections",
        [],
    )

    (
        entities,
        resolution_log,
    ) = resolve_entities(
        services
    )

    alias_lookup = (
        build_alias_lookup(
            entities
        )
    )

    resolved_connections = (
        resolve_connections(
            connections,
            alias_lookup,
        )
    )

    (
        entities,
        resolved_connections,
        database_log,
    ) = (
        reconcile_single_generic_database(
            entities,
            resolved_connections,
        )
    )

    resolution_log.extend(
        database_log
    )

    entities = (
        build_dependency_metadata(
            entities,
            resolved_connections,
        )
    )

    alias_lookup = (
        build_alias_lookup(
            entities
        )
    )

    return {
        "entities":
            entities,

        "connections":
            resolved_connections,

        "alias_lookup":
            alias_lookup,

        "resolution_log":
            resolution_log,

        "stats": {
            "entity_count":
                len(
                    entities
                ),

            "connection_count":
                len(
                    resolved_connections
                ),

            "aliases_resolved":
                len(
                    resolution_log
                ),
        },
    }