# GitHub MCP Integration

ArchGuard now exposes a real Model Context Protocol server using the Python MCP SDK.

## What the MCP server can do

Tools exposed by `backend.app.mcp_server`:

- `archguard_mcp_status` — read-only integration/safety status
- `inspect_remediation` — read-only proposal and approval state
- `preview_remediation_pull_request` — exact PR preview; no write
- `create_approved_remediation_pull_request` — approval-gated GitHub PR creation
- `compare_architecture_versions` — V1/V2 component/dependency delta
- `verify_before_after` — before/after finding and architecture-health verification

## Run locally

```bash
source .venv/bin/activate
pip install -r requirements.txt
python3 -m backend.app.mcp_server
```

The default MCP transport is provided by the MCP SDK and is suitable for connecting an MCP-capable local client.

## GitHub configuration

Copy `.env.example` values into your local `.env` (never commit the real token):

```text
GITHUB_TOKEN=<dedicated demo token>
GITHUB_REPOSITORY=owner/repository
GITHUB_BASE_BRANCH=main
ARCHGUARD_GITHUB_WRITE_ENABLED=false
```

Use a dedicated demo repository or a narrowly scoped token. The token should have only the repository permissions needed to create a branch, file commit and pull request.

## Safety sequence

1. ArchGuard detects a risk.
2. ArchGuard creates a remediation proposal.
3. User previews the proposed diff.
4. User explicitly approves the proposal.
5. Operator deliberately sets `ARCHGUARD_GITHUB_WRITE_ENABLED=true` for the demo repository.
6. MCP creates a feature branch and PR containing the approved remediation artifact.
7. A human reviews/merges the PR.
8. ArchGuard re-ingests the resulting architecture and runs verification.

The MCP tool does **not** merge the PR, modify the default branch directly, deploy infrastructure, or execute Terraform/Kubernetes commands.

## Competition/demo narrative

A concise end-to-end demonstration is:

1. Review architecture and identify database SPOF.
2. Simulate database outage and show blast radius.
3. Ask ArchGuard to remediate the top reliability risk.
4. Preview remediation and show that execution is blocked.
5. Approve the proposal.
6. Invoke `create_approved_remediation_pull_request` through MCP.
7. Open the generated GitHub PR to prove an external engineering action occurred.
8. Re-ingest the changed architecture and show before/after verification.

This demonstrates that ArchGuard is not only generating advice: it can use a constrained external engineering tool while preserving human control and an auditable review boundary.
