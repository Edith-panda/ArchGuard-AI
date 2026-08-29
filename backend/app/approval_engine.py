from __future__ import annotations

from typing import Any


_APPROVAL_STORE: dict[str, dict[str, Any]] = {}


def register_proposal(
    proposal: dict[str, Any],
) -> dict[str, Any]:

    proposal_id = proposal.get(
        "proposal_id"
    )

    if not proposal_id:
        raise ValueError(
            "Proposal must contain proposal_id."
        )

    stored = {
        **proposal,
        "approval_status":
            "pending",
        "approved":
            False,
        "execution_allowed":
            False,
    }

    _APPROVAL_STORE[
        proposal_id
    ] = stored

    return stored


def register_proposals(
    proposals: list[
        dict[str, Any]
    ],
) -> None:

    for proposal in proposals:
        register_proposal(
            proposal
        )


def get_proposal(
    proposal_id: str,
) -> dict[str, Any] | None:

    return _APPROVAL_STORE.get(
        proposal_id
    )


def approve_proposal(
    proposal_id: str,
) -> dict[str, Any]:

    proposal = get_proposal(
        proposal_id
    )

    if not proposal:
        raise ValueError(
            "Proposal not found."
        )

    proposal[
        "approval_status"
    ] = "approved"

    proposal[
        "approved"
    ] = True

    # IMPORTANT:
    # approval is not execution.
    proposal[
        "execution_allowed"
    ] = False

    return proposal


def reject_proposal(
    proposal_id: str,
) -> dict[str, Any]:

    proposal = get_proposal(
        proposal_id
    )

    if not proposal:
        raise ValueError(
            "Proposal not found."
        )

    proposal[
        "approval_status"
    ] = "rejected"

    proposal[
        "approved"
    ] = False

    proposal[
        "execution_allowed"
    ] = False

    return proposal