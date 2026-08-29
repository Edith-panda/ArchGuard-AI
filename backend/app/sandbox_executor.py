from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any


ALLOWED_FORMATS = {
    "terraform",
    "yaml",
    "kubernetes",
    "policy",
    "architecture",
}


def _safe_filename(
    filename: str,
) -> str:

    name = Path(
        filename
    ).name

    if not name:
        return "proposed-change.txt"

    return name


def create_execution_sandbox(
    proposal_id: str,
) -> Path:

    root = Path(
        tempfile.gettempdir()
    ) / "archguard-sandbox"

    root.mkdir(
        parents=True,
        exist_ok=True,
    )

    sandbox = (
        root /
        proposal_id
    )

    sandbox.mkdir(
        parents=True,
        exist_ok=True,
    )

    return sandbox


def write_proposed_change(
    proposal_id: str,
    proposed_diff: dict[str, Any],
) -> dict[str, Any]:

    file_format = (
        proposed_diff.get(
            "format",
            ""
        )
        .strip()
        .lower()
    )

    if (
        file_format
        not in ALLOWED_FORMATS
    ):
        raise ValueError(
            f"Unsupported sandbox format: "
            f"{file_format}"
        )

    filename = _safe_filename(
        proposed_diff.get(
            "filename",
            "proposed-change.txt",
        )
    )

    content = (
        proposed_diff.get(
            "diff",
            ""
        )
    )

    if not content:
        raise ValueError(
            "Proposed diff is empty."
        )

    sandbox = (
        create_execution_sandbox(
            proposal_id
        )
    )

    target = (
        sandbox /
        filename
    )

    target.write_text(
        content,
        encoding="utf-8",
    )

    return {
        "success":
            True,

        "sandbox_path":
            str(
                sandbox
            ),

        "artifact_path":
            str(
                target
            ),

        "filename":
            filename,

        "format":
            file_format,

        "bytes_written":
            target.stat().st_size,

        "execution_scope":
            "local_sandbox_only",
    }