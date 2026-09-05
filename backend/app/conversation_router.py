from enum import Enum
from typing import Optional


class EngineeringIntent(str, Enum):
    DESIGN = "design"
    REVIEW = "review"
    QUESTION = "question"
    MODIFY = "modify"
    SIMULATE = "simulate"
    REMEDIATE = "remediate"


def normalize_prompt(prompt: Optional[str]) -> str:
    """Normalize a user prompt for deterministic intent detection."""
    return (prompt or "").strip().lower()


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def detect_intent(prompt: Optional[str]) -> EngineeringIntent:
    """Determine the engineer's primary intent.

    Explicit action requests are intentionally prioritized over secondary
    requirements. For example, "Design an ecommerce platform ... traffic
    spike ... failure scenarios" is a DESIGN request, not a SIMULATE request.
    Simulation wins only when the prompt explicitly asks to simulate/what-if
    an existing or described system.
    """
    text = normalize_prompt(prompt)

    if not text:
        return EngineeringIntent.REVIEW

    remediation_keywords = [
        "remediate", "fix this", "fix these", "resolve these issues",
        "resolve this issue", "generate fix", "implement fix",
        "how do we fix", "how can we fix",
    ]
    modification_keywords = [
        "change architecture", "modify architecture", "update architecture",
        "redesign", "migrate", "replace", "move from", "switch from",
        "stakeholder wants", "new requirement", "new requirements",
        "change requirement",
    ]
    design_keywords = [
        "design a", "design an", "design system", "create architecture",
        "propose architecture", "suggest architecture", "build architecture",
        "architecture for", "what tech stack", "which tech stack",
        "technology stack", "which database", "what database", "which queue",
        "which cloud service",
    ]
    explicit_simulation_keywords = [
        "simulate", "what if", "blast radius", "what happens if",
        "what happens when",
    ]
    scenario_context_keywords = [
        "traffic spike", "10x traffic", "100x traffic", "database goes down",
        "database fails", "db goes down", "service fails", "service goes down",
        "dependency fails", "failure scenario",
    ]
    review_keywords = [
        "review architecture", "review this", "analyze architecture",
        "analyse architecture", "analyze this", "analyse this",
        "find bottleneck", "find bottlenecks", "security risk",
        "security risks", "single point of failure", "spof",
    ]

    # Strong, explicit action verbs define the primary request. This prevents
    # requirements such as "traffic spike" or "failure scenarios" from
    # hijacking a design prompt.
    if _contains_any(text, remediation_keywords):
        return EngineeringIntent.REMEDIATE

    if _contains_any(text, modification_keywords):
        return EngineeringIntent.MODIFY

    if _contains_any(text, design_keywords):
        return EngineeringIntent.DESIGN

    # Explicit simulation language is safe to route directly. Scenario-only
    # language also routes to SIMULATE when no stronger action intent exists.
    if _contains_any(text, explicit_simulation_keywords):
        return EngineeringIntent.SIMULATE

    if _contains_any(text, scenario_context_keywords):
        return EngineeringIntent.SIMULATE

    if _contains_any(text, review_keywords):
        return EngineeringIntent.REVIEW

    return EngineeringIntent.QUESTION


def route_request(
    prompt: Optional[str],
    has_architecture: bool = False,
    has_files: bool = False,
) -> dict:
    """Build the initial routing decision for the conversational orchestrator."""
    intent = detect_intent(prompt)

    return {
        "intent": intent.value,
        "prompt": prompt or "",
        "context": {
            "has_architecture": has_architecture,
            "has_files": has_files,
        },
        "recommended_pipeline": get_pipeline(
            intent=intent,
            has_architecture=has_architecture,
        ),
    }


def get_pipeline(intent: EngineeringIntent, has_architecture: bool) -> list[str]:
    """Determine which ArchGuard capabilities should handle the request."""
    if intent == EngineeringIntent.DESIGN:
        return [
            "requirements_analysis",
            "architecture_reasoning",
            "technology_selection",
            "risk_precheck",
        ]

    if intent == EngineeringIntent.REVIEW:
        pipeline = []
        if has_architecture:
            pipeline.extend(["digital_twin", "graph_engine"])
        pipeline.extend(["risk_engine", "well_architected_engine"])
        return pipeline

    if intent == EngineeringIntent.SIMULATE:
        return ["digital_twin", "graph_engine", "scenario_engine", "risk_engine"]

    if intent == EngineeringIntent.MODIFY:
        return [
            "requirements_analysis",
            "digital_twin",
            "impact_analysis",
            "architecture_reasoning",
            "risk_precheck",
        ]

    if intent == EngineeringIntent.REMEDIATE:
        return [
            "risk_engine",
            "remediation_engine",
            "human_approval",
            "sandbox_execution",
            "verification_engine",
        ]

    return ["architecture_qa"]
