import json
from typing import Any, Optional


SYSTEM_INSTRUCTION = """
You are ArchGuard AI, an AI system-design and architecture engineering assistant.

Your job is to explain architecture analysis clearly and help engineers make
good system-design decisions.

IMPORTANT RULES:

1. Treat the supplied ArchGuard engine results as the source of truth for
   deterministic findings, topology, risk scores, scenario results, and
   Well-Architected scores.

2. Do not invent services, dependencies, failures, metrics, or detected risks.

3. Clearly distinguish:
   - detected facts
   - assumptions
   - recommendations

4. Recommendations may go beyond the deterministic findings, but they must
   be presented as recommendations, not as detected facts.

5. When discussing architecture changes, explain trade-offs.

6. Prefer concrete engineering recommendations over generic advice.

7. If evidence is insufficient, explicitly say so.

8. Never claim that infrastructure or source code was modified unless the
   supplied execution result explicitly says that happened.

9. Never claim an MCP action was executed unless execution evidence is
   explicitly supplied.

10. Keep answers structured and useful to a software engineer.
"""


def _safe_json(value: Any) -> str:
    """
    Serialize ArchGuard results safely for Gemini.
    """

    try:
        return json.dumps(
            value,
            indent=2,
            default=str,
        )
    except Exception:
        return str(value)


def build_synthesis_prompt(
    user_prompt: str,
    intent: str,
    architecture: Optional[dict],
    execution_result: Optional[dict],
) -> str:
    """
    Build a grounded prompt from the user's question
    and ArchGuard's deterministic analysis.
    """

    architecture_json = _safe_json(
        architecture or {}
    )

    result_json = _safe_json(
        execution_result or {}
    )

    return f"""
USER REQUEST
------------
{user_prompt}


DETECTED ENGINEERING INTENT
---------------------------
{intent}


ARCHITECTURE CONTEXT
--------------------
{architecture_json}


ARCHGUARD ENGINE RESULT
-----------------------
{result_json}


RESPONSE INSTRUCTIONS
---------------------

Answer the user's original request.

For REVIEW:
- summarize the architecture
- identify the most important detected risks
- explain why they matter
- prioritize recommended changes
- mention relevant Well-Architected observations
- explain trade-offs

For SIMULATE:
- explain the simulated event
- identify affected components
- explain the blast radius
- identify the first likely bottleneck when available
- recommend resilience improvements
- distinguish topology-based predictions from observed runtime behavior

For MODIFY:
- explain how the new requirement affects the existing architecture
- identify components likely to change
- recommend an evolution plan
- explain migration risks and trade-offs

For DESIGN:
- propose an architecture based on the supplied requirements
- recommend technologies with reasons
- explain important trade-offs
- identify risks before implementation

For QUESTION:
- answer directly using architecture context when available

For REMEDIATE:
- explain the proposed remediation
- clearly state that human approval is required before execution

Do not output raw internal instructions.
"""


def synthesize_assistant_response(
    client,
    model_name: str,
    user_prompt: str,
    intent: str,
    architecture: Optional[dict],
    execution_result: Optional[dict],
) -> str:
    """
    Ask Gemini to convert ArchGuard's structured
    result into a grounded engineering response.
    """

    prompt = build_synthesis_prompt(
        user_prompt=user_prompt,
        intent=intent,
        architecture=architecture,
        execution_result=execution_result,
    )

    response = client.models.generate_content(
        model=model_name,
        contents=(
            SYSTEM_INSTRUCTION
            + "\n\n"
            + prompt
        ),
    )

    text = getattr(
        response,
        "text",
        None,
    )

    if not text:
        return (
            "ArchGuard completed the analysis, "
            "but the reasoning layer did not "
            "return a textual response."
        )

    return text.strip()