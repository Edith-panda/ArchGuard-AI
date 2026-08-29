from dataclasses import dataclass, field
from typing import Any


# =========================================================
# Tool execution object
# =========================================================

@dataclass
class ToolExecution:
    tool: str
    reason: str
    status: str = "pending"
    metadata: dict[str, Any] = field(default_factory=dict)


# =========================================================
# Available tools
# =========================================================

TOOL_NAMES = {
    "terraform_parser",
    "yaml_parser",
    "json_parser",
    "code_parser",
    "documentation_parser",
    "multimodal_parser",
    "entity_resolution",
    "graph_engine",
    "risk_engine",
    "well_architected_engine",
    "scenario_engine",
    "rag_engine",
    "gemini_reasoning",
}


# =========================================================
# Decide tools based on uploaded artifacts
# =========================================================

def build_execution_plan(
    artifacts: list[dict[str, Any]]
) -> list[ToolExecution]:

    plan: list[ToolExecution] = []

    file_types = {
        artifact["file_type"]
        for artifact in artifacts
    }

    # ---------- Parsers ----------
    if "terraform" in file_types:
        plan.append(
            ToolExecution(
                tool="terraform_parser",
                reason="Terraform (.tf) files detected."
            )
        )

    if "yaml" in file_types:
        plan.append(
            ToolExecution(
                tool="yaml_parser",
                reason="YAML / Kubernetes configuration detected."
            )
        )

    if "json" in file_types:
        plan.append(
            ToolExecution(
                tool="json_parser",
                reason="JSON architecture detected."
            )
        )

    if "source_code" in file_types:
        plan.append(
            ToolExecution(
                tool="code_parser",
                reason="Source code uploaded."
            )
        )

    if "documentation" in file_types:
        plan.append(
            ToolExecution(
                tool="documentation_parser",
                reason="Documentation uploaded."
            )
        )

    if (
        "image" in file_types
        or "pdf" in file_types
    ):
        plan.append(
            ToolExecution(
                tool="multimodal_parser",
                reason="Architecture diagram or PDF uploaded."
            )
        )

    # ---------- Always execute ----------
    plan.extend([
        ToolExecution(
            tool="entity_resolution",
            reason="Merge aliases into Digital Twin."
        ),
        ToolExecution(
            tool="graph_engine",
            reason="Construct dependency graph."
        ),
        ToolExecution(
            tool="risk_engine",
            reason="Run deterministic and graph analysis."
        ),
        ToolExecution(
            tool="well_architected_engine",
            reason="Compute Google Well-Architected scores."
        ),
        ToolExecution(
            tool="scenario_engine",
            reason="Enable failure and traffic simulations."
        ),
    ])

    # ---------- Optional RAG ----------
    if (
        "documentation" in file_types
        or "source_code" in file_types
    ):
        plan.append(
            ToolExecution(
                tool="rag_engine",
                reason="Retrieve contextual knowledge."
            )
        )

    # ---------- Gemini reasoning ----------
    if (
        "image" in file_types
        or "pdf" in file_types
        or "documentation" in file_types
    ):
        plan.append(
            ToolExecution(
                tool="gemini_reasoning",
                reason="LLM reasoning adds architectural insights."
            )
        )

    return plan


# =========================================================
# Summarize execution plan
# =========================================================

def summarize_plan(plan):

    return {
        "total_tools": len(plan),
        "tools": [step.tool for step in plan],
        "execution_order": [
            {
                "step": index + 1,
                "tool": step.tool,
                "reason": step.reason,
            }
            for index, step in enumerate(plan)
        ],
    }