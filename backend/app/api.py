from asyncio import graph
from platform import architecture
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
from pathlib import Path
from .ingestion import (
    MAX_FILES,
    MAX_FILE_SIZE,
    create_artifact,
    decode_file_content,
    is_binary_file,
    is_supported,
)
from .multimodal_parser import (
    convert_multimodal_to_architecture,
    extract_architecture_from_media,
)

from fastapi import (
    File,
    Form,
    HTTPException,
    UploadFile,
)
from .scenario_lab import (
    run_scenario,
)
from .scenario_engine import simulate_component_failure


from .artifact_parser import (
    reconstruct_architecture,
)
from .evidence_engine import (
    enrich_architecture_with_evidence,
)
from .digital_twin import (
    build_architecture_digital_twin,
)
from pathlib import Path
from typing import List, Optional

from fastapi import (
    File,
    Form,
    HTTPException,
    UploadFile,
)

from .well_architected import (
    score_well_architected,
)
from .orchestrator import (
    build_execution_plan,
    summarize_plan,
)
from .remediation_engine import (
    build_remediation_plan,
)
from .approval_engine import (
    approve_proposal,
    get_proposal,
    register_proposals,
    reject_proposal,
)

from .diff_engine import (
    generate_proposed_diff,
)
from .tool_layer import (
    execute_approved_proposal,
)
from .approval_engine import (
    approve_proposal,
    get_proposal,
    register_proposals,
    reject_proposal,
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

class ScenarioRequest(BaseModel):
    architecture: ArchitectureInput
    scenario_type: str
    target: Optional[str] = None
    traffic_multiplier: float = 1.0

class OrchestratorRequest(BaseModel):
    artifacts: list[dict]

class EmptyGeminiAnalysis:
    findings = []

class ParseRequest(BaseModel):
    content: str
    file_type: str

class RemediationRequest(BaseModel):
    findings: list[dict]


def architecture_to_dict(
    architecture: ArchitectureInput,
):
    return architecture.model_dump()

class ApprovalRequest(BaseModel):
    proposal_id: str

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
    files: Optional[
        List[UploadFile]
    ] = File(
        default=None
    ),

    manual_input:
        Optional[str] = Form(
            default=None
        ),
):

    uploaded_files = (
        files or []
    )

    has_manual_input = bool(
        manual_input
        and
        manual_input.strip()
    )


    # -----------------------------------------------------
    # 1. Validate request
    # -----------------------------------------------------

    if (
        not uploaded_files
        and
        not has_manual_input
    ):

        raise HTTPException(
            status_code=400,

            detail=(
                "Upload at least one file "
                "or provide manual input."
            ),
        )


    if (
        len(uploaded_files)
        > MAX_FILES
    ):

        raise HTTPException(
            status_code=400,

            detail=(
                f"A maximum of "
                f"{MAX_FILES} files "
                f"can be analyzed at once."
            ),
        )


    artifacts = []

    unsupported_files = []


    # -----------------------------------------------------
    # 2. Process uploaded files
    # -----------------------------------------------------

    for uploaded_file in uploaded_files:

        filename = (
            uploaded_file.filename
            or
            "unnamed"
        )


        # -------------------------------------------------
        # Unsupported extension
        # -------------------------------------------------

        if not is_supported(
            filename
        ):

            unsupported_files.append(
                filename
            )

            continue


        # -------------------------------------------------
        # Read uploaded bytes
        # -------------------------------------------------

        raw_content = (
            await uploaded_file.read()
        )


        # -------------------------------------------------
        # File-size protection
        # -------------------------------------------------

        if (
            len(raw_content)
            > MAX_FILE_SIZE
        ):

            raise HTTPException(
                status_code=400,

                detail=(
                    f"{filename} exceeds "
                    "the 5 MB limit."
                ),
            )


        # -------------------------------------------------
        # Binary files
        #
        # PNG
        # JPG
        # JPEG
        # WEBP
        # PDF
        # -------------------------------------------------

        if is_binary_file(
            filename
        ):

            artifact = (
                create_artifact(
                    filename=filename,

                    content=(
                        raw_content
                    ),
                )
            )


        # -------------------------------------------------
        # Text files
        # -------------------------------------------------

        else:

            try:

                text = (
                    decode_file_content(
                        raw_content,
                        filename,
                    )
                )

            except ValueError as error:

                raise HTTPException(
                    status_code=400,
                    detail=str(
                        error
                    ),
                )


            artifact = (
                create_artifact(
                    filename=filename,

                    content=text,
                )
            )


        artifacts.append(
            artifact
        )


    # -----------------------------------------------------
    # 3. Optional manual input
    # -----------------------------------------------------

    if has_manual_input:

        manual_text = (
            manual_input.strip()
        )

        manual_artifact = (
            create_artifact(
                filename=(
                    "manual-input.txt"
                ),

                content=(
                    manual_text
                ),

                source="manual",
            )
        )

        artifacts.append(
            manual_artifact
        )


    # -----------------------------------------------------
    # 4. Ensure at least one supported artifact exists
    # -----------------------------------------------------

    if not artifacts:

        raise HTTPException(
            status_code=400,

            detail=(
                "None of the provided "
                "files are currently "
                "supported."
            ),
        )


    # -----------------------------------------------------
    # 5. Separate deterministic and multimodal artifact
    # -----------------------------------------------------

    text_artifacts = [
        artifact

        for artifact
        in artifacts

        if artifact[
            "file_type"
        ]
        not in {
            "image",
            "pdf",
        }
    ]


    media_artifacts = [
        artifact

        for artifact
        in artifacts

        if artifact[
            "file_type"
        ]
        in {
            "image",
            "pdf",
        }
    ]


    # -----------------------------------------------------
    # 6. Deterministic architecture reconstruction
    # -----------------------------------------------------

    if text_artifacts:

        architecture = (
            reconstruct_architecture(
                text_artifacts
            )
        )

    else:

        architecture = {
            "services": [],
            "connections": [],
        }


    # -----------------------------------------------------
    # 7. Gemini multimodal extraction
    # -----------------------------------------------------

    multimodal_architectures = []

    multimodal_errors = []


    mime_types = {
        ".png":
            "image/png",

        ".jpg":
            "image/jpeg",

        ".jpeg":
            "image/jpeg",

        ".webp":
            "image/webp",

        ".pdf":
            "application/pdf",
    }


    for artifact in media_artifacts:

        filename = artifact[
            "filename"
        ]

        extension = (
            Path(
                filename
            )
            .suffix
            .lower()
        )


        mime_type = (
            mime_types.get(
                extension
            )
        )


        if not mime_type:

            continue


        try:

            extraction = (
                extract_architecture_from_media(
                    content=(
                        artifact[
                            "content"
                        ]
                    ),

                    mime_type=(
                        mime_type
                    ),

                    filename=(
                        filename
                    ),
                )
            )


            multimodal_architecture = (
                convert_multimodal_to_architecture(
                    extraction=(
                        extraction
                    ),

                    filename=(
                        filename
                    ),
                )
            )


            multimodal_architectures.append(
                multimodal_architecture
            )


        except Exception as error:

            # We intentionally record the error
            # instead of crashing the entire
            # multi-file analysis.

            multimodal_errors.append(
                {
                    "filename":
                        filename,

                    "error":
                        str(
                            error
                        ),
                }
            )


    # -----------------------------------------------------
    # 8. Merge deterministic + multimodal architectures
    # -----------------------------------------------------

    service_map = {}


    for service in architecture.get(
        "services",
        [],
    ):

        name = service.get(
            "name"
        )

        if name:

            service_map[
                name
            ] = service


    connection_set = set()


    for connection in architecture.get(
        "connections",
        [],
    ):

        if (
            isinstance(
                connection,
                list,
            )
            and
            len(
                connection
            ) == 2
        ):

            connection_set.add(
                (
                    connection[0],
                    connection[1],
                )
            )


    connection_evidence = []


    multimodal_assumptions = []


    for multimodal_architecture in (
        multimodal_architectures
    ):


        # -------------------------------------------------
        # Merge services
        # -------------------------------------------------

        for service in (
            multimodal_architecture.get(
                "services",
                [],
            )
        ):

            name = service.get(
                "name"
            )

            if not name:
                continue


            if (
                name
                not in service_map
            ):

                service_map[
                    name
                ] = service


            else:

                existing = (
                    service_map[
                        name
                    ]
                )


                existing.setdefault(
                    "evidence",
                    [],
                )


                existing[
                    "evidence"
                ].extend(
                    service.get(
                        "evidence",
                        [],
                    )
                )


                incoming_confidence = (
                    service.get(
                        "confidence",
                        0.0,
                    )
                )


                existing_confidence = (
                    existing.get(
                        "confidence",
                        0.0,
                    )
                )


                if (
                    incoming_confidence
                    >
                    existing_confidence
                ):

                    existing[
                        "confidence"
                    ] = (
                        incoming_confidence
                    )


        # -------------------------------------------------
        # Merge connections
        # -------------------------------------------------

        for connection in (
            multimodal_architecture.get(
                "connections",
                [],
            )
        ):

            if (
                isinstance(
                    connection,
                    list,
                )
                and
                len(
                    connection
                ) == 2
            ):

                connection_set.add(
                    (
                        connection[0],
                        connection[1],
                    )
                )


        # -------------------------------------------------
        # Preserve connection evidence
        # -------------------------------------------------

        connection_evidence.extend(
            multimodal_architecture.get(
                "connection_evidence",
                [],
            )
        )


        # -------------------------------------------------
        # Preserve Gemini assumptions
        # -------------------------------------------------

        multimodal_assumptions.extend(
            multimodal_architecture.get(
                "assumptions",
                [],
            )
        )


    # -----------------------------------------------------
    # 9. Final canonical architecture
    # -----------------------------------------------------

    architecture[
        "services"
    ] = list(
        service_map.values()
    )


    architecture[
        "connections"
    ] = [
        [
            source,
            target,
        ]

        for (
            source,
            target
        )
        in sorted(
            connection_set
        )
    ]


    architecture[
        "connection_evidence"
    ] = (
        connection_evidence
    )


    architecture[
        "assumptions"
    ] = (
        multimodal_assumptions
    )
    architecture = (
    enrich_architecture_with_evidence(
        architecture
    )
)
    digital_twin = (
        build_architecture_digital_twin(
            architecture
        )
    )


    # -----------------------------------------------------
    # 10. Was architecture actually detected?
    # -----------------------------------------------------

    architecture_detected = bool(
        architecture.get(
            "services"
        )
        or
        architecture.get(
            "connections"
        )
    )


    # -----------------------------------------------------
    # 11. Response metadata
    # -----------------------------------------------------

    artifact_metadata = [
        {
            "filename":
                artifact[
                    "filename"
                ],

            "file_type":
                artifact[
                    "file_type"
                ],

            "source":
                artifact[
                    "source"
                ],

            "size":
                artifact[
                    "size"
                ],
        }

        for artifact
        in artifacts
    ]

    # Build AI Agent execution plan
    execution_plan = summarize_plan(
        build_execution_plan(artifact_metadata)
    )


    # -----------------------------------------------------
    # 12. Return ingestion response
    # -----------------------------------------------------

    return {
        "status":
            "success",

        "artifact_count":
            len(
                artifacts
            ),

        "artifacts":
            artifact_metadata,

        "unsupported_files":
            unsupported_files,

        "architecture":
            architecture,

        "digital_twin":
            digital_twin,

        "architecture_detected":
            architecture_detected,

        "multimodal_enabled":
            True,

        "multimodal_files_received":
            len(
                media_artifacts
            ),

        "multimodal_files_analyzed":
            len(
                multimodal_architectures
            ),

        "multimodal_errors":
            multimodal_errors,

        "execution_plan": execution_plan,

        "message":
            (
                "Artifacts ingested and "
                "architecture reconstruction "
                "completed."
                "Digital Twin created."
            ),
    }

@app.post("/orchestrate")
def orchestrate(request: OrchestratorRequest):

    plan = build_execution_plan(request.artifacts)

    return {
        "status": "success",
        "agent": "ArchGuard Orchestrator",
        "execution_plan": summarize_plan(plan)
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

    # Google Well-Architected scoring
    well_architected = score_well_architected(
        [
            finding.model_dump()
            for finding in unique_findings
        ]
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
        "well_architected": well_architected,
        "findings": [
            finding.model_dump()
            for finding in ranked_findings
        ],
    }

@app.post("/remediation-plan")
def remediation_plan(
    request: RemediationRequest,
):

    if not request.findings:

        raise HTTPException(
            status_code=400,
            detail=(
                "At least one finding "
                "is required."
            ),
        )

    plan = (
        build_remediation_plan(
            request.findings
        )
    )

    register_proposals(
        plan["proposals"]
)

    return plan

@app.get(
    "/remediation/{proposal_id}/diff"
)
def remediation_diff(
    proposal_id: str,
):

    proposal = get_proposal(
        proposal_id
    )

    if not proposal:

        raise HTTPException(
            status_code=404,
            detail=(
                "Remediation proposal "
                "not found."
            ),
        )

    proposed_diff = (
        generate_proposed_diff(
            proposal
        )
    )

    return {
        "status":
            "success",

        "proposal_id":
            proposal_id,

        "approval_status":
            proposal.get(
                "approval_status"
            ),

        "execution_allowed":
            False,

        "proposed_diff":
            proposed_diff,

        "safety":
            (
                "Preview only. "
                "Nothing has been executed."
            ),
    }

    @app.post(
    "/remediation/approve"
)
    def approve_remediation(
        request: ApprovalRequest,
    ):

        try:

            proposal = (
                approve_proposal(
                    request.proposal_id
                )
            )

        except ValueError as error:

            raise HTTPException(
                status_code=404,
                detail=str(error),
            )

        return {
            "status":
                "success",

            "proposal_id":
                request.proposal_id,

            "approval_status":
                proposal[
                    "approval_status"
                ],

            "approved":
                proposal[
                    "approved"
                ],

            "execution_allowed":
                False,

            "message":
                (
                    "Proposal approved for review workflow. "
                    "Execution remains disabled."
                ),
        }
        @app.post(
        "/remediation/reject"
    )
        def reject_remediation(
            request: ApprovalRequest,
        ):

            try:

                proposal = (
                    reject_proposal(
                        request.proposal_id
                    )
                )

            except ValueError as error:

                raise HTTPException(
                    status_code=404,
                    detail=str(error),
                )

            return {
                "status":
                    "success",

                "proposal_id":
                    request.proposal_id,

                "approval_status":
                    proposal[
                        "approval_status"
                    ],

                "approved":
                    False,

                "execution_allowed":
                    False,

                "message":
                    "Proposal rejected.",
            }

@app.post(
    "/remediation/{proposal_id}/execute-sandbox"
)
def execute_remediation_sandbox(
    proposal_id: str,
):

    proposal = get_proposal(
        proposal_id
    )

    if not proposal:

        raise HTTPException(
            status_code=404,
            detail=(
                "Remediation proposal "
                "not found."
            ),
        )

    if (
        proposal.get(
            "approval_status"
        )
        !=
        "approved"
    ):

        raise HTTPException(
            status_code=403,
            detail=(
                "Human approval is required "
                "before sandbox execution."
            ),
        )

    result = (
        execute_approved_proposal(
            proposal
        )
    )

    if not result[
        "success"
    ]:

        raise HTTPException(
            status_code=400,
            detail=result,
        )

    return result

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

@app.post("/scenario")
def run_architecture_scenario(
    request: ScenarioRequest,
):

    architecture_dict = (
        architecture_to_dict(
            request.architecture
        )
    )

    architecture_dict = (
        normalize_architecture(
            architecture_dict
        )
    )

    graph = (
        build_architecture_graph(
            architecture_dict
        )
    )

    result = run_scenario(
        graph=graph,
        scenario_type=(
            request.scenario_type
        ),
        target=(
            request.target
        ),
        traffic_multiplier=(
            request.traffic_multiplier
        ),
    )

    if not result.get(
        "success"
    ):

        raise HTTPException(
            status_code=400,
            detail=result,
        )

    return result

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