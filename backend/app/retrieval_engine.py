import json
import re
from pathlib import Path


KNOWLEDGE_PATH = (
    Path(__file__).parent.parent
    / "knowledge"
    / "architecture_best_practices.json"
)


def load_knowledge_base():
    with open(
        KNOWLEDGE_PATH,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def tokenize(text):
    return set(
        re.findall(
            r"[a-zA-Z0-9]+",
            text.lower(),
        )
    )


def calculate_relevance(
    query,
    document,
):
    query_tokens = tokenize(query)

    searchable_text = " ".join(
        [
            document.get("title", ""),
            document.get("category", ""),
            " ".join(
                document.get(
                    "keywords",
                    [],
                )
            ),
            document.get("content", ""),
        ]
    )

    document_tokens = tokenize(
        searchable_text
    )

    overlap = query_tokens.intersection(
        document_tokens
    )

    return len(overlap)


def retrieve_knowledge(
    query,
    limit=3,
):
    documents = load_knowledge_base()

    scored_documents = []

    for document in documents:
        score = calculate_relevance(
            query,
            document,
        )

        if score > 0:
            scored_documents.append(
                (
                    score,
                    document,
                )
            )

    scored_documents.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    return [
        document
        for _, document
        in scored_documents[:limit]
    ]

def build_architecture_query(
    architecture,
):
    parts = []

    for service in architecture.get(
        "services",
        [],
    ):
        parts.append(
            service.get(
                "name",
                "",
            )
        )

        parts.append(
            service.get(
                "type",
                "",
            )
        )

    connection_count = len(
        architecture.get(
            "connections",
            [],
        )
    )

    parts.extend(
        [
            "architecture",
            "reliability",
            "scalability",
            "security",
            "failure",
            "dependency",
            f"{connection_count} connections",
        ]
    )

    return " ".join(parts)


def retrieve_for_architecture(
    architecture,
    limit=4,
):
    query = build_architecture_query(
        architecture
    )

    return retrieve_knowledge(
        query,
        limit=limit,
    )