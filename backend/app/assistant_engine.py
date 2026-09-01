from typing import Optional

from google import genai

from .conversation_router import EngineeringIntent


SYSTEM_PROMPT = """
You are ArchGuard AI, an AI system design and architecture engineer.

You help software engineers during pre-development and architecture evolution.

Your responsibilities include:
- understanding functional and non-functional requirements
- suggesting software architecture
- recommending technology stacks
- identifying bottlenecks and trade-offs
- identifying scalability, reliability and security risks
- explaining architectural decisions
- evaluating stakeholder requirements
- suggesting alternatives

Do not claim that infrastructure, source code, cloud resources,
or external systems were modified unless an authorized tool actually
performed the change.

When recommending architecture:
1. State important assumptions.
2. Propose components.
3. Recommend technologies.
4. Explain why each major technology was chosen.
5. Identify bottlenecks and risks.
6. Suggest mitigations.
7. Mention important open questions.

Keep the answer technical but understandable.
"""


def build_architecture_context(
    architecture: Optional[dict],
) -> str:
    if not architecture:
        return "No existing architecture was provided."

    services = architecture.get("services", [])
    connections = architecture.get("connections", [])

    return f"""
Existing architecture:

Services:
{services}

Connections:
{connections}
"""


def build_user_message(
    prompt: str,
    intent: EngineeringIntent,
    architecture: Optional[dict] = None,
) -> str:

    architecture_context = build_architecture_context(
        architecture
    )

    return f"""
Engineering intent: {intent.value}

User request:
{prompt}

{architecture_context}

Respond as ArchGuard AI.
"""


def generate_assistant_response(
    client: genai.Client,
    model_name: str,
    prompt: str,
    intent: EngineeringIntent,
    architecture: Optional[dict] = None,
) -> dict:

    user_message = build_user_message(
        prompt=prompt,
        intent=intent,
        architecture=architecture,
    )

    response = client.models.generate_content(
        model=model_name,
        contents=[
            SYSTEM_PROMPT,
            user_message,
        ],
    )

    text = response.text or ""

    return {
        "intent": intent.value,
        "response": text.strip(),
        "model": model_name,
        "architecture_context_used": bool(
            architecture
        ),
    }