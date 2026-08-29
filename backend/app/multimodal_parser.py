import json
import os
from typing import Any

from google import genai
from google.genai import types
from pydantic import (
    BaseModel,
    Field,
)


MODEL_NAME = "gemini-3.6-flash"


# ---------------------------------------------------------
# Component schema
# ---------------------------------------------------------

class ExtractedComponent(
    BaseModel
):

    name: str

    type: str

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    evidence: str


# ---------------------------------------------------------
# Connection schema
# ---------------------------------------------------------

class ExtractedConnection(
    BaseModel
):

    source: str

    target: str

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    evidence: str


# ---------------------------------------------------------
# Complete extraction schema
# ---------------------------------------------------------

class ArchitectureExtraction(
    BaseModel
):

    components:list[
            ExtractedComponent
        ]

    connections:list[
            ExtractedConnection
        ]

    assumptions:list[str]


# ---------------------------------------------------------
# Extraction prompt
# ---------------------------------------------------------

ARCHITECTURE_EXTRACTION_PROMPT = """
You are ArchGuard AI's architecture evidence extractor.

Analyze the supplied software architecture artifact.

Extract only architecture information that is reasonably
supported by the supplied artifact.

Identify:

1. software services
2. microservices
3. API gateways
4. databases
5. queues/topics/event buses
6. caches
7. external systems
8. clients
9. infrastructure components
10. directed dependencies

For every component:

- provide a concise canonical name
- assign a component type
- provide confidence from 0.0 to 1.0
- explain the evidence supporting it

Preferred component types:

gateway
microservice
service
database
queue
cache
external
client
infrastructure
unknown

For every connection:

- provide source
- provide target
- provide confidence from 0.0 to 1.0
- explain the evidence supporting the relationship

Rules:

- Do not invent components.
- Do not invent dependencies.
- Treat visible labels as strong evidence.
- Treat clear directed arrows as strong evidence.
- If arrow direction is ambiguous, lower confidence
  or omit the connection.
- Keep assumptions separate.
- Do not perform architecture risk analysis here.
- Your job is extraction only.
- Follow the structured schema exactly.
"""


# ---------------------------------------------------------
# Gemini client
# ---------------------------------------------------------

def get_gemini_client():

    api_key = os.getenv(
        "GEMINI_API_KEY"
    )

    if not api_key:

        raise RuntimeError(
            "GEMINI_API_KEY "
            "is not configured."
        )

    return genai.Client(
        api_key=api_key
    )


# ---------------------------------------------------------
# Gemini multimodal extraction
# ---------------------------------------------------------

def extract_architecture_from_media(
    content: bytes,
    mime_type: str,
    filename: str,
) -> dict[str, Any]:

    client = (
        get_gemini_client()
    )

    try:

        response = (
            client.models.generate_content(
                model=MODEL_NAME,

                contents=[
                    ARCHITECTURE_EXTRACTION_PROMPT,

                    types.Part.from_bytes(
                        data=content,
                        mime_type=mime_type,
                    ),
                ],

                config=(
                    types.GenerateContentConfig(
                        response_mime_type=(
                            "application/json"
                        ),

                        response_schema=(
                            ArchitectureExtraction
                        ),
                    )
                ),
            )
        )

    except Exception as error:

        raise RuntimeError(
            f"Gemini multimodal request failed "
            f"for {filename}: {error}"
        ) from error

    if not response.text:

        raise RuntimeError(
            "Gemini returned an empty "
            f"response for {filename}."
        )

    try:

        parsed = json.loads(
            response.text
        )

    except json.JSONDecodeError as error:

        raise RuntimeError(
            "Gemini returned invalid "
            "structured JSON."
        ) from error

    return parsed


# ---------------------------------------------------------
# Convert Gemini extraction to ArchGuard format
# ---------------------------------------------------------

def convert_multimodal_to_architecture(
    extraction: dict[str, Any],
    filename: str,
):

    services = []

    connections = []

    connection_evidence = []


    # -----------------------------------------------------
    # Components
    # -----------------------------------------------------

    for component in extraction.get(
        "components",
        [],
    ):

        name = component.get(
            "name"
        )

        if not name:
            continue

        services.append(
            {
                "name":
                    name,

                "type":
                    component.get(
                        "type",
                        "unknown",
                    ),

                "confidence":
                    component.get(
                        "confidence",
                        0.0,
                    ),

                "evidence": [
                                {
                    "filename": filename,

                    "reason": component.get(
                        "evidence",
                        "Detected by Gemini multimodal analysis",
                    ),

                    "source_type":
                        "multimodal",

                    "confidence":
                        component.get(
                            "confidence",
                            0.80,
                        ),
                }
                ],
            }
        )


    # -----------------------------------------------------
    # Connections
    # -----------------------------------------------------

    for connection in extraction.get(
        "connections",
        [],
    ):

        source = connection.get(
            "source"
        )

        target = connection.get(
            "target"
        )

        if (
            not source
            or
            not target
        ):
            continue

        connections.append(
            [
                source,
                target,
            ]
        )

        connection_evidence.append(
                {
            "filename": filename,

            "reason": component.get(
                "evidence",
                "Detected by Gemini multimodal analysis",
            ),

            "source_type":
                "multimodal",

            "confidence":
                component.get(
                    "confidence",
                    0.80,
                ),
        }
        )


    return {
        "services":
            services,

        "connections":
            connections,

        "connection_evidence":
            connection_evidence,

        "assumptions":
            extraction.get(
                "assumptions",
                [],
            ),
    }