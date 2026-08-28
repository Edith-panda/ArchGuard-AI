from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .analyzer import analyze_architecture
from .aggregator import aggregate_findings
from .deduplicator import deduplicate_findings
from .gemini_analyzer import analyze_with_gemini
from .graph_engine import build_architecture_graph
from .graph_risk_engine import (
    analyze_graph_risks,
    get_critical_components,
)
from .risk_engine import assign_risk_scores
from .scenario_engine import simulate_component_failure
from .input_parser import parse_architecture_text
from .normalizer import normalize_architecture
from .retrieval_engine import (
    retrieve_for_architecture,
)

from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional

from fastapi import (
    File,
    Form,
    HTTPException,
    UploadFile,
)
from .ingestion import (
    MAX_FILES,
    create_artifact,
    decode_file_content,
    is_supported,
    merge_canonical_architectures,
    parse_canonical_json,
)

from .artifact_parser import (
    reconstruct_architecture,
)



app = FastAPI(
    title="ArchGuard AI",
    description="AI-powered software architecture risk analysis",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
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


class FailureRequest(BaseModel):
    architecture: ArchitectureInput
    component: str


class EmptyGeminiAnalysis:
    findings = []

class ParseRequest(BaseModel):
    content: str
    file_type: str


def architecture_to_dict(
    architecture: ArchitectureInput,
):
    return architecture.model_dump()


@app.get("/")
def root():
    return {
        "name": "ArchGuard AI",
        "status": "running",
        "version": "0.1.0",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }

@app.post("/ingest")
async def ingest_architecture(
    files: Optional[List[UploadFile]] = File(default=None),
    manual_input: Optional[str] = Form(default=None),
):
    uploaded_files = files or []

    has_manual_input = bool(
        manual_input and manual_input.strip()
    )

    # ---------------------------------------
    # 1. Validate input
    # ---------------------------------------

    if not uploaded_files and not has_manual_input:
        raise HTTPException(
            status_code=400,
            detail=(
                "Upload at least one file "
                "or provide manual input."
            ),
        )

    if len(uploaded_files) > MAX_FILES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"A maximum of {MAX_FILES} "
                f"files can be analyzed at once."
            ),
        )

    artifacts = []
    unsupported_files = []

    # ---------------------------------------
    # 2. Process uploaded files
    # ---------------------------------------

    for uploaded_file in uploaded_files:

        filename = (
            uploaded_file.filename
            or "unnamed"
        )

        if not is_supported(filename):
            unsupported_files.append(filename)
            continue

        raw_content = await uploaded_file.read()

        try:
            text = decode_file_content(
                raw_content,
                filename,
            )

        except ValueError as error:
            raise HTTPException(
                status_code=400,
                detail=str(error),
            )

        artifact = create_artifact(
            filename=filename,
            text=text,
        )

        artifacts.append(artifact)

    # ---------------------------------------
    # 3. Process optional manual input
    # ---------------------------------------

    if has_manual_input:

        manual_text = manual_input.strip()

        manual_artifact = create_artifact(
            filename="manual-input.txt",
            text=manual_text,
            source="manual",
        )

        artifacts.append(
            manual_artifact
        )

    # ---------------------------------------
    # 4. Make sure something was accepted
    # ---------------------------------------

    if not artifacts:
        raise HTTPException(
            status_code=400,
            detail=(
                "None of the provided files "
                "are currently supported."
            ),
        )

    # ---------------------------------------
    # 5. Reconstruct architecture
    # ---------------------------------------

    architecture = reconstruct_architecture(
        artifacts
    )

    # ---------------------------------------
    # 6. Determine whether anything useful
    #    was reconstructed
    # ---------------------------------------

    architecture_detected = bool(
        architecture.get("services")
        or architecture.get("connections")
    )

    # ---------------------------------------
    # 7. Return ingestion result
    # ---------------------------------------

    return {
        "status": "success",

        "artifact_count": len(
            artifacts
        ),

        "artifacts": [
            {
                "filename": artifact["filename"],
                "file_type": artifact["file_type"],
                "source": artifact["source"],
                "size": artifact["size"],
            }
            for artifact in artifacts
        ],

        "unsupported_files": unsupported_files,

        "architecture": architecture,

        "architecture_detected":
            architecture_detected,

        "message": (
            "Artifacts ingested and "
            "architecture reconstruction "
            "completed successfully."
        ),
    }
@app.post("/analyze")
def analyze(
    architecture: ArchitectureInput,
):
    architecture_dict = architecture_to_dict(
        architecture
    )

    graph = build_architecture_graph(
        architecture_dict
    )

    # Deterministic rules
    rule_findings = analyze_architecture(
        architecture_dict
    )

    # Graph analysis
    graph_findings = analyze_graph_risks(
        graph
    )

    # Gemini is useful, but ArchGuard must still work
    # when the model is temporarily unavailable.
    gemini_available = True

    try:
        gemini_analysis = analyze_with_gemini(
            architecture_dict
        )

    except Exception as error:
        gemini_available = False

        print(
            f"Gemini temporarily unavailable: {error}"
        )

        gemini_analysis = EmptyGeminiAnalysis()

    # Normalize rule + Gemini findings
    all_findings = aggregate_findings(
        rule_findings,
        gemini_analysis,
    )
    retrieved_knowledge = (
        retrieve_for_architecture(
            architecture_dict,
            limit=4,
        )
    )

    # Graph findings already use our Finding model.
    all_findings.extend(
        graph_findings
    )

    # Score
    scored_findings = assign_risk_scores(
        all_findings
    )

    # Deduplicate
    unique_findings = deduplicate_findings(
        scored_findings
    )

    # Highest risk first
    ranked_findings = sorted(
        unique_findings,
        key=lambda finding: finding.risk_score,
        reverse=True,
    )

    critical_components = (
        get_critical_components(graph)
    )

    return {
        "status": "success",
        "gemini_available": gemini_available,
        "architecture": {
            "component_count": graph.number_of_nodes(),
            "connection_count": graph.number_of_edges(),
        },
        "critical_components": critical_components,
        "knowledge_sources": retrieved_knowledge,
        "findings": [
            finding.model_dump()
            for finding in ranked_findings
        ],
    }


@app.post("/simulate-failure")
def simulate_failure(
    request: FailureRequest,
):
    architecture_dict = (
    architecture_to_dict(
        request.architecture
    )
)

    architecture_dict = normalize_architecture(
        architecture_dict
    )

    graph = build_architecture_graph(
        architecture_dict
    )

    scenario = simulate_component_failure(
        graph,
        request.component,
    )

    if not scenario["success"]:
        raise HTTPException(
            status_code=404,
            detail=scenario["message"],
        )

    return scenario

@app.post("/parse")
def parse_architecture(
    request: ParseRequest,
):
    try:
        architecture = parse_architecture_text(
            request.content,
            request.file_type,
        )

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    return {
        "status": "success",
        "architecture": architecture,
    }