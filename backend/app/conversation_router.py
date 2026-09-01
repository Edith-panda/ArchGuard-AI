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
    """
    Normalize a user prompt for deterministic
    intent detection.
    """
    return (prompt or "").strip().lower()


def detect_intent(prompt: Optional[str]) -> EngineeringIntent:
    """
    Determine what the engineer is trying to do.

    This first implementation is intentionally
    deterministic and local.

    Gemini reasoning will be added later for
    ambiguous requests.
    """

    text = normalize_prompt(prompt)

    if not text:
        return EngineeringIntent.REVIEW

    # -----------------------------------------
    # SIMULATION / WHAT-IF
    # -----------------------------------------

    simulation_keywords = [
        "what if",
        "traffic spike",
        "10x traffic",
        "100x traffic",
        "database goes down",
        "database fails",
        "db goes down",
        "service fails",
        "service goes down",
        "dependency fails",
        "blast radius",
        "failure scenario",
        "simulate",
    ]

    if any(
        keyword in text
        for keyword in simulation_keywords
    ):
        return EngineeringIntent.SIMULATE

    # -----------------------------------------
    # REMEDIATION
    # -----------------------------------------

    remediation_keywords = [
        "remediate",
        "fix this",
        "fix these",
        "resolve these issues",
        "resolve this issue",
        "generate fix",
        "implement fix",
        "how do we fix",
        "how can we fix",
    ]

    if any(
        keyword in text
        for keyword in remediation_keywords
    ):
        return EngineeringIntent.REMEDIATE

    # -----------------------------------------
    # MODIFY / EVOLVE
    # -----------------------------------------

    modification_keywords = [
        "change architecture",
        "modify architecture",
        "update architecture",
        "redesign",
        "migrate",
        "replace",
        "move from",
        "switch from",
        "stakeholder wants",
        "new requirement",
        "new requirements",
        "change requirement",
    ]

    if any(
        keyword in text
        for keyword in modification_keywords
    ):
        return EngineeringIntent.MODIFY

    # -----------------------------------------
    # DESIGN
    # -----------------------------------------

    design_keywords = [
        "design a",
        "design an",
        "design system",
        "create architecture",
        "propose architecture",
        "suggest architecture",
        "build architecture",
        "architecture for",
        "what tech stack",
        "which tech stack",
        "technology stack",
        "which database",
        "what database",
        "which queue",
        "which cloud service",
    ]

    if any(
        keyword in text
        for keyword in design_keywords
    ):
        return EngineeringIntent.DESIGN

    # -----------------------------------------
    # REVIEW
    # -----------------------------------------

    review_keywords = [
        "review architecture",
        "review this",
        "analyze architecture",
        "analyse architecture",
        "analyze this",
        "analyse this",
        "find bottleneck",
        "find bottlenecks",
        "security risk",
        "security risks",
        "single point of failure",
        "spof",
    ]

    if any(
        keyword in text
        for keyword in review_keywords
    ):
        return EngineeringIntent.REVIEW

    # Everything else is treated as a general
    # architecture / engineering question.

    return EngineeringIntent.QUESTION


def route_request(
    prompt: Optional[str],
    has_architecture: bool = False,
    has_files: bool = False,
) -> dict:
    """
    Build the initial routing decision used by
    the ArchGuard conversational orchestrator.
    """

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


def get_pipeline(
    intent: EngineeringIntent,
    has_architecture: bool,
) -> list[str]:
    """
    Determine which ArchGuard capabilities
    should handle the request.

    This only creates a plan. It does not execute
    external tools or modify infrastructure.
    """

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
            pipeline.extend([
                "digital_twin",
                "graph_engine",
            ])

        pipeline.extend([
            "risk_engine",
            "well_architected_engine",
        ])

        return pipeline

    if intent == EngineeringIntent.SIMULATE:
        return [
            "digital_twin",
            "graph_engine",
            "scenario_engine",
            "risk_engine",
        ]

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

    return [
        "architecture_qa",
    ]