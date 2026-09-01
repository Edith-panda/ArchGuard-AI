from typing import List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .aggregator import aggregate_findings
from .analyzer import analyze_architecture
from .approval_engine import approve_proposal, get_proposal, register_proposals, reject_proposal
from .artifact_parser import reconstruct_architecture
from .assistant_engine import generate_assistant_response
from .assistant_executor import AssistantExecutionError, execute_assistant_intent
from .assistant_synthesis import synthesize_assistant_response
from .conversation_router import EngineeringIntent, route_request
from .deduplicator import deduplicate_findings
from .diff_engine import generate_proposed_diff
from .gemini_analyzer import analyze_with_gemini
from .graph_engine import build_architecture_graph
from .graph_risk_engine import analyze_graph_risks, get_critical_components
from .ingestion_service import process_architecture_inputs
from .input_parser import parse_architecture_text
from .multimodal_parser import get_gemini_client
from .normalizer import normalize_architecture
from .orchestrator import build_execution_plan, summarize_plan
from .remediation_engine import build_remediation_plan
from .retrieval_engine import retrieve_for_architecture
from .risk_engine import assign_risk_scores
from .scenario_engine import simulate_component_failure
from .scenario_lab import run_scenario
from .tool_layer import execute_approved_proposal
from .verification_engine import verify_remediation
from .well_architected import score_well_architected


app = FastAPI(
    title="ArchGuard AI",
    description="AI-powered software architecture design, review and remediation",
    version="0.2.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Service(BaseModel):
    name: str
    type: str


class ArchitectureInput(BaseModel):
    services: list[Service]
    connections: list[list[str]]


class VerificationRequest(BaseModel):
    before_findings: list[dict]
    after_findings: list[dict]
    before_well_architected: dict = Field(default_factory=dict)
    after_well_architected: dict = Field(default_factory=dict)


class FailureRequest(BaseModel):
    architecture: ArchitectureInput
    component: str


class ScenarioRequest(BaseModel):
    architecture: ArchitectureInput
    scenario_type: str
    target: Optional[str] = None
    traffic_multiplier: float = 1.0


class OrchestratorRequest(BaseModel):
    artifacts: list[dict]


class ParseRequest(BaseModel):
    content: str
    file_type: str


class RemediationRequest(BaseModel):
    findings: list[dict]


class AssistantRequest(BaseModel):
    prompt: str
    architecture: dict | None = None
    has_files: bool = False


class ApprovalRequest(BaseModel):
    proposal_id: str


class EmptyGeminiAnalysis:
    findings = []


def architecture_to_dict(architecture: ArchitectureInput) -> dict:
    return architecture.model_dump()


@app.get("/")
def root():
    return {"name": "ArchGuard AI", "status": "running", "version": "0.2.0"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/ingest")
async def ingest_architecture(
    files: Optional[List[UploadFile]] = File(default=None),
    manual_input: Optional[str] = Form(default=None),
):
    if not files and not (manual_input and manual_input.strip()):
        raise HTTPException(400, "Upload at least one file or provide manual input.")

    try:
        result = await process_architecture_inputs(files or [], manual_input)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, f"Artifact ingestion failed: {exc}") from exc

    artifacts = [
        {
            "filename": item.get("filename"),
            "mode": item.get("mode"),
            "success": item.get("success"),
            "error": item.get("error"),
        }
        for item in result.get("processed_files", [])
    ]

    plan = summarize_plan(build_execution_plan(artifacts)) if artifacts else []
    multimodal = result.get("multimodal", {})

    return {
        "status": "success",
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "architecture": result.get("architecture"),
        "digital_twin": result.get("digital_twin"),
        "architecture_detected": result.get("architecture_detected", False),
        "multimodal_enabled": True,
        "multimodal_files_received": multimodal.get("attempted", 0),
        "multimodal_errors": multimodal.get("errors", []),
        "execution_plan": plan,
        "message": "Artifacts ingested and architecture digital twin reconstructed.",
    }


@app.post("/orchestrate")
def orchestrate(request: OrchestratorRequest):
    return {
        "status": "success",
        "agent": "ArchGuard Orchestrator",
        "execution_plan": summarize_plan(build_execution_plan(request.artifacts)),
    }


@app.post("/analyze")
def analyze(architecture: ArchitectureInput):
    architecture_dict = architecture_to_dict(architecture)
    graph = build_architecture_graph(architecture_dict)
    rule_findings = analyze_architecture(architecture_dict)
    graph_findings = analyze_graph_risks(graph)

    gemini_available = True
    try:
        gemini_analysis = analyze_with_gemini(architecture_dict)
    except Exception:
        gemini_available = False
        gemini_analysis = EmptyGeminiAnalysis()

    all_findings = aggregate_findings(rule_findings, gemini_analysis)
    all_findings.extend(graph_findings)
    scored = assign_risk_scores(all_findings)
    unique = deduplicate_findings(scored)
    ranked = sorted(unique, key=lambda item: item.risk_score, reverse=True)
    finding_dicts = [item.model_dump() for item in ranked]

    return {
        "status": "success",
        "gemini_available": gemini_available,
        "architecture": {
            "component_count": graph.number_of_nodes(),
            "connection_count": graph.number_of_edges(),
        },
        "critical_components": get_critical_components(graph),
        "knowledge_sources": retrieve_for_architecture(architecture_dict, limit=4),
        "well_architected": score_well_architected(finding_dicts),
        "findings": finding_dicts,
    }


@app.post("/remediation-plan")
def remediation_plan(request: RemediationRequest):
    if not request.findings:
        raise HTTPException(400, "At least one finding is required.")
    plan = build_remediation_plan(request.findings)
    register_proposals(plan["proposals"])
    return plan


@app.get("/remediation/{proposal_id}/diff")
def remediation_diff(proposal_id: str):
    proposal = get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(404, "Remediation proposal not found.")
    return {
        "status": "success",
        "proposal_id": proposal_id,
        "approval_status": proposal.get("approval_status"),
        "execution_allowed": False,
        "proposed_diff": generate_proposed_diff(proposal),
        "safety": "Preview only. Nothing has been executed.",
    }


@app.post("/remediation/approve")
def approve_remediation(request: ApprovalRequest):
    try:
        proposal = approve_proposal(request.proposal_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {
        "status": "success",
        "proposal_id": request.proposal_id,
        "approval_status": proposal["approval_status"],
        "approved": proposal["approved"],
        "execution_allowed": False,
        "message": "Proposal approved. Production execution remains disabled.",
    }


@app.post("/remediation/reject")
def reject_remediation(request: ApprovalRequest):
    try:
        proposal = reject_proposal(request.proposal_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {
        "status": "success",
        "proposal_id": request.proposal_id,
        "approval_status": proposal["approval_status"],
        "approved": False,
        "execution_allowed": False,
        "message": "Proposal rejected.",
    }


@app.post("/remediation/{proposal_id}/execute-sandbox")
def execute_remediation_sandbox(proposal_id: str):
    proposal = get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(404, "Remediation proposal not found.")
    if proposal.get("approval_status") != "approved":
        raise HTTPException(403, "Human approval is required before sandbox execution.")
    result = execute_approved_proposal(proposal)
    if not result.get("success"):
        raise HTTPException(400, detail=result)
    return result


@app.post("/simulate-failure")
def simulate_failure(request: FailureRequest):
    architecture_dict = normalize_architecture(architecture_to_dict(request.architecture))
    graph = build_architecture_graph(architecture_dict)
    scenario = simulate_component_failure(graph, request.component)
    if not scenario.get("success"):
        raise HTTPException(404, scenario.get("message", "Simulation failed"))
    return scenario


@app.post("/scenario")
def run_architecture_scenario(request: ScenarioRequest):
    architecture_dict = normalize_architecture(architecture_to_dict(request.architecture))
    graph = build_architecture_graph(architecture_dict)
    result = run_scenario(
        graph=graph,
        scenario_type=request.scenario_type,
        target=request.target,
        traffic_multiplier=request.traffic_multiplier,
    )
    if not result.get("success"):
        raise HTTPException(400, detail=result)
    return result


@app.post("/parse")
def parse_architecture(request: ParseRequest):
    try:
        architecture = parse_architecture_text(request.content, request.file_type)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"status": "success", "architecture": architecture}


@app.post("/verify-remediation")
def verify_remediation_endpoint(request: VerificationRequest):
    return {
        "status": "success",
        "verification": verify_remediation(
            before_findings=request.before_findings,
            after_findings=request.after_findings,
            before_well_architected=request.before_well_architected,
            after_well_architected=request.after_well_architected,
        ),
    }


@app.post("/assistant")
def architecture_assistant(request: AssistantRequest):
    prompt = request.prompt.strip()
    if not prompt:
        raise HTTPException(400, "Prompt cannot be empty.")

    routing = route_request(
        prompt=prompt,
        has_architecture=bool(request.architecture),
        has_files=request.has_files,
    )
    intent = EngineeringIntent(routing["intent"])

    # DESIGN and general QUESTION can start before an architecture exists.
    if intent in {EngineeringIntent.DESIGN, EngineeringIntent.QUESTION}:
        try:
            result = generate_assistant_response(
                client=get_gemini_client(),
                model_name="gemini-3.6-flash",
                prompt=prompt,
                intent=intent,
                architecture=request.architecture,
            )
            return {
                "status": "success",
                "mode": "conversation",
                "routing": routing,
                "execution": {"started": True, "engine": "gemini_architecture_reasoning"},
                "assistant": result,
            }
        except Exception as exc:
            raise HTTPException(503, f"ArchGuard reasoning is temporarily unavailable: {exc}") from exc

    try:
        result = execute_assistant_intent(intent, prompt, request.architecture)
    except AssistantExecutionError as exc:
        raise HTTPException(400, str(exc)) from exc

    return {
        "status": "success",
        "mode": "conversation",
        "routing": routing,
        "execution": {"started": True, "result": result},
    }


@app.post("/assistant/input")
async def assistant_input(
    prompt: str = Form(...),
    files: Optional[List[UploadFile]] = File(default=None),
    manual_input: Optional[str] = Form(default=None),
):
    prompt = prompt.strip()
    if not prompt:
        raise HTTPException(400, "Prompt cannot be empty.")

    try:
        ingestion = await process_architecture_inputs(files or [], manual_input)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, f"ArchGuard could not process supplied artifacts: {exc}") from exc

    architecture = ingestion.get("architecture")
    routing = route_request(
        prompt=prompt,
        has_architecture=bool(architecture),
        has_files=bool(files),
    )
    intent = EngineeringIntent(routing["intent"])

    try:
        execution_result = execute_assistant_intent(intent, prompt, architecture)
    except AssistantExecutionError as exc:
        execution_result = {"status": "blocked", "error": str(exc)}
    except Exception as exc:
        execution_result = {"status": "error", "error": str(exc)}

    synthesis_status = "skipped"
    synthesis_error = None
    answer = None

    # DESIGN/QUESTION need model reasoning even without a pre-existing architecture.
    if intent in {EngineeringIntent.DESIGN, EngineeringIntent.QUESTION}:
        try:
            generated = generate_assistant_response(
                client=get_gemini_client(),
                model_name="gemini-3.6-flash",
                prompt=prompt,
                intent=intent,
                architecture=architecture,
            )
            answer = generated.get("response", "")
            synthesis_status = "success"
        except Exception as exc:
            synthesis_status = "error"
            synthesis_error = str(exc)
            answer = "The AI design/reasoning layer is temporarily unavailable."

    elif execution_result.get("status") not in {"blocked", "error"}:
        try:
            answer = synthesize_assistant_response(
                client=get_gemini_client(),
                model_name="gemini-3.6-flash",
                user_prompt=prompt,
                intent=intent.value,
                architecture=architecture,
                execution_result=execution_result,
            )
            synthesis_status = "success"
        except Exception as exc:
            synthesis_status = "error"
            synthesis_error = str(exc)
            answer = (
                "ArchGuard completed local analysis, but the AI explanation layer "
                "is temporarily unavailable. Structured results are still included."
            )
    else:
        answer = (
            "ArchGuard could not run the requested architecture analysis with the "
            "supplied context. See the execution result for details."
        )

    context = {
        "prompt": prompt,
        "architecture_detected": ingestion.get("architecture_detected", False),
        "architecture": architecture,
        "digital_twin": ingestion.get("digital_twin"),
        "processed_files": ingestion.get("processed_files", []),
        "multimodal": ingestion.get("multimodal", {}),
        "manual_input_provided": bool(manual_input and manual_input.strip()),
    }

    return {
        "status": "success",
        "mode": "conversational_architecture",
        "answer": answer,
        "routing": routing,
        "context": context,
        "execution": {"started": True, "result": execution_result},
        "synthesis": {
            "status": synthesis_status,
            "model": "gemini-3.6-flash" if synthesis_status == "success" else None,
            "error": synthesis_error,
        },
    }
