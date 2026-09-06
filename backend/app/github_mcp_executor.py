from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from .approval_engine import get_proposal
from .diff_engine import generate_proposed_diff


class GitHubMCPError(RuntimeError):
    pass


@dataclass(frozen=True)
class GitHubConfig:
    token: str
    repository: str
    base_branch: str = "main"

    @classmethod
    def from_env(cls) -> "GitHubConfig":
        token = os.getenv("GITHUB_TOKEN", "").strip()
        repository = os.getenv("GITHUB_REPOSITORY", "").strip()
        base_branch = os.getenv("GITHUB_BASE_BRANCH", "main").strip() or "main"
        if not token:
            raise GitHubMCPError("GITHUB_TOKEN is not configured.")
        if not repository or "/" not in repository:
            raise GitHubMCPError("GITHUB_REPOSITORY must be configured as owner/repo.")
        return cls(token=token, repository=repository, base_branch=base_branch)


def github_mcp_status() -> dict[str, Any]:
    repository = os.getenv("GITHUB_REPOSITORY", "").strip()
    token_present = bool(os.getenv("GITHUB_TOKEN", "").strip())
    write_enabled = os.getenv("ARCHGUARD_GITHUB_WRITE_ENABLED", "false").lower() == "true"
    return {
        "provider": "github",
        "protocol": "mcp",
        "configured": bool(repository and token_present),
        "repository": repository or None,
        "write_enabled": write_enabled,
        "safety_mode": "pull_request_only",
        "production_execution": False,
        "human_approval_required": True,
    }


def _api(config: GitHubConfig, method: str, path: str, payload: dict | None = None) -> Any:
    url = f"https://api.github.com/repos/{config.repository}{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Authorization", f"Bearer {config.token}")
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")
    request.add_header("User-Agent", "ArchGuard-AI-MCP")
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise GitHubMCPError(f"GitHub API {exc.code}: {body[:500]}") from exc
    except urllib.error.URLError as exc:
        raise GitHubMCPError(f"GitHub API unavailable: {exc.reason}") from exc


def _safe_slug(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip("-.")
    return value[:60] or "change"


def _proposal_or_error(proposal_id: str) -> dict[str, Any]:
    proposal = get_proposal(proposal_id)
    if not proposal:
        raise GitHubMCPError("Remediation proposal not found.")
    return proposal


def preview_github_remediation(proposal_id: str) -> dict[str, Any]:
    proposal = _proposal_or_error(proposal_id)
    proposed_diff = generate_proposed_diff(proposal)
    filename = _safe_slug(proposed_diff.get("filename") or "proposed-change.txt")
    artifact_path = f"archguard/remediations/{_safe_slug(proposal_id)}/{filename}"
    return {
        "proposal_id": proposal_id,
        "approval_status": proposal.get("approval_status", "pending"),
        "requires_human_approval": True,
        "execution_target": "github_pull_request",
        "artifact_path": artifact_path,
        "proposed_diff": proposed_diff,
        "will_modify_default_branch": False,
        "will_open_pull_request": True,
        "note": "Preview only. No GitHub write has occurred.",
    }


def create_github_remediation_pr(proposal_id: str, title: str | None = None) -> dict[str, Any]:
    proposal = _proposal_or_error(proposal_id)
    if proposal.get("approval_status") != "approved" or not proposal.get("approved"):
        raise GitHubMCPError("Human approval is required before the GitHub MCP tool can create a PR.")
    if os.getenv("ARCHGUARD_GITHUB_WRITE_ENABLED", "false").lower() != "true":
        raise GitHubMCPError(
            "GitHub writes are disabled. Set ARCHGUARD_GITHUB_WRITE_ENABLED=true only for an explicitly approved demo repository."
        )

    config = GitHubConfig.from_env()
    preview = preview_github_remediation(proposal_id)
    proposed = preview["proposed_diff"]

    base_ref = _api(config, "GET", f"/git/ref/heads/{config.base_branch}")
    base_sha = base_ref["object"]["sha"]
    branch = f"archguard/{_safe_slug(proposal_id)}"

    try:
        _api(config, "POST", "/git/refs", {"ref": f"refs/heads/{branch}", "sha": base_sha})
    except GitHubMCPError as exc:
        if "Reference already exists" not in str(exc):
            raise

    content = (
        "# ArchGuard approved remediation proposal\n\n"
        f"Proposal: {proposal_id}\n"
        f"Strategy: {proposal.get('strategy', 'architecture_improvement')}\n"
        f"Scope: {proposal.get('change_scope', 'architecture')}\n\n"
        "## Proposed change\n\n"
        f"```{proposed.get('format', '')}\n{proposed.get('diff', '')}\n```\n\n"
        "## Validation checks\n"
        + "\n".join(f"- {check}" for check in proposal.get("validation_checks", []))
        + "\n\nThis PR was created only after explicit human approval. ArchGuard did not deploy or apply infrastructure.\n"
    )
    encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
    _api(
        config,
        "PUT",
        f"/contents/{preview['artifact_path']}",
        {
            "message": f"chore: add approved ArchGuard remediation {proposal_id}",
            "content": encoded,
            "branch": branch,
        },
    )

    pr_title = title or f"ArchGuard: remediate {proposal.get('change_scope', 'architecture risk')}"
    pr = _api(
        config,
        "POST",
        "/pulls",
        {
            "title": pr_title[:240],
            "head": branch,
            "base": config.base_branch,
            "body": (
                "Generated by ArchGuard's approval-gated MCP workflow.\n\n"
                f"Proposal: `{proposal_id}`\n\n"
                "Safety: this PR contains a reviewable remediation artifact only. "
                "No production deployment or infrastructure apply was performed."
            ),
        },
    )

    proposal["mcp_execution"] = {
        "provider": "github",
        "action": "create_pull_request",
        "branch": branch,
        "pull_request_number": pr.get("number"),
        "pull_request_url": pr.get("html_url"),
        "production_modified": False,
        "completed": True,
    }

    return {
        "status": "success",
        "provider": "github",
        "protocol": "mcp",
        "proposal_id": proposal_id,
        "branch": branch,
        "pull_request_number": pr.get("number"),
        "pull_request_url": pr.get("html_url"),
        "production_modified": False,
        "next_step": "Review the pull request, merge it manually if acceptable, then re-ingest the changed architecture for verification.",
    }
