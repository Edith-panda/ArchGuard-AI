import json
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel
from .retrieval_engine import (
    retrieve_for_architecture,
)


load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError(
        "GEMINI_API_KEY was not found. "
        "Make sure it exists in your .env file."
    )


client = genai.Client(api_key=api_key)


class GeminiFinding(BaseModel):
    severity: str
    category: str
    component: str
    issue: str
    explanation: str
    recommendation: str


class GeminiAnalysis(BaseModel):
    findings: list[GeminiFinding]


def analyze_with_gemini(architecture):
    architecture_json = json.dumps(
        architecture,
        indent=2
    )
    retrieved_documents = (
        retrieve_for_architecture(
            architecture,
            limit=4,
        )
    )

    knowledge_context = "\n\n".join(
        [
            (
                f"TITLE: {document['title']}\n"
                f"CATEGORY: {document['category']}\n"
                f"GUIDANCE: {document['content']}"
            )
            for document in retrieved_documents
        ]
    )

    prompt = f"""
    You are ArchGuard AI, an expert software architecture reviewer.

    Analyze the architecture below.

    ARCHITECTURE:
    {architecture_json}

    RETRIEVED ENGINEERING KNOWLEDGE:
    {knowledge_context}

    Use the retrieved engineering knowledge as supporting guidance.

    Identify the most important:

    - reliability risks
    - scalability bottlenecks
    - performance risks
    - security concerns
    - single points of failure
    - cascading failure scenarios

    Important rules:

    1. Do not invent architecture components.
    2. Base architecture facts only on the supplied architecture.
    3. Use retrieved knowledge as guidance, not as proof that a condition exists.
    4. If architecture information is missing, clearly state the assumption.
    5. Use severity HIGH, MEDIUM, or LOW.
    6. Keep findings technically specific.
    7. Avoid duplicate findings.
    """

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=GeminiAnalysis,
        ),
    )

    return GeminiAnalysis.model_validate_json(response.text)