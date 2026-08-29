from __future__ import annotations

from typing import Any

from .diff_engine import (
    generate_proposed_diff,
)

from .sandbox_executor import (
    write_proposed_change,
)

from .sandbox_validator import (
    validate_sandbox_artifact,
)


def execute_approved_proposal(
    proposal: dict[str, Any],
) -> dict[str, Any]:

    if (
        proposal.get(
            "approval_status"
        )
        !=
        "approved"
    ):

        return {
            "success":
                False,

            "stage":
                "authorization",

            "message":
                (
                    "Proposal has not "
                    "been approved."
                ),
        }

    proposed_diff = (
        generate_proposed_diff(
            proposal
        )
    )

    execution = (
        write_proposed_change(
            proposal_id=(
                proposal[
                    "proposal_id"
                ]
            ),

            proposed_diff=(
                proposed_diff
            ),
        )
    )

    validation = (
        validate_sandbox_artifact(
            artifact_path=(
                execution[
                    "artifact_path"
                ]
            ),

            file_format=(
                execution[
                    "format"
                ]
            ),
        )
    )

    return {
        "success":
            validation[
                "valid"
            ],

        "stage":
            "sandbox_execution",

        "proposal_id":
            proposal[
                "proposal_id"
            ],

        "execution":
            execution,

        "validation":
            validation,

        "external_system_modified":
            False,

        "production_modified":
            False,

        "safety":
            (
                "Executed only inside "
                "the ArchGuard local sandbox."
            ),
    }