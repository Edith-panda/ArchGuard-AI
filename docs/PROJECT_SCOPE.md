# ArchGuard Product Scope and Definition of Done

## Product statement

ArchGuard is an AI architecture engineering workspace that turns requirements and architecture evidence into a structured system model, evaluates risks and failure behavior, proposes safer target architectures, and converts approved recommendations into reviewable engineering changes.

## Core lifecycle

**Design → Understand → Review → Simulate → Evolve → Remediate → Verify**

This lifecycle is the product. New work should strengthen one of these stages rather than add unrelated platform features.

## In scope for the finished competition/demo build

1. Natural-language system design from requirements.
2. Architecture artifact ingestion: code/config/IaC/docs/diagrams.
3. Canonical architecture model and Digital Twin.
4. Interactive architecture visualization.
5. Deterministic risk, bottleneck, SPOF and dependency analysis.
6. Failure and traffic scenario simulation with blast radius.
7. Architecture-aware follow-up conversation.
8. Architecture evolution when stakeholder requirements change.
9. V1 → V2 architecture comparison.
10. Evidence-backed recommendations and confidence where evidence exists.
11. Prioritized remediation proposals.
12. Explicit human approval before any external write.
13. Real MCP integration with GitHub that creates a reviewable pull request only.
14. Re-ingestion and before/after verification after a change.
15. A clear final outcome showing whether risk and architecture health improved.

## Explicitly out of scope

- unrestricted autonomous production changes
- direct `terraform apply`, cluster mutation, database schema mutation, or shell execution
- dozens of MCP integrations
- full observability/APM replacement
- full CI/CD replacement
- cloud provisioning platform
- enterprise IAM platform
- generic code-generation IDE
- complete cost-management platform

These may be future integrations, but they are not required to prove the ArchGuard product.

## Safety contract

Every external change follows:

**Detect → Explain → Recommend → Preview → Human Approval → Execute via constrained tool → Validate → Verify**

For the GitHub MCP workflow:

- no write is allowed before proposal approval
- repository writes are additionally gated by `ARCHGUARD_GITHUB_WRITE_ENABLED=true`
- the MCP tool creates a feature branch and pull request
- it does not push to the default branch
- it does not merge the pull request
- it does not deploy infrastructure
- it does not run `terraform apply`

## Definition of Done

ArchGuard is considered feature-complete when the following single demo can run reliably from start to finish:

1. User describes or uploads an architecture.
2. ArchGuard builds/uses the Digital Twin and identifies grounded risks.
3. User asks for a database/service/traffic failure simulation.
4. ArchGuard shows the blast radius using the same architecture context.
5. User adds a stakeholder requirement such as multi-region availability.
6. ArchGuard proposes V2 and shows a V1 → V2 delta.
7. User requests remediation of the highest-risk issue.
8. ArchGuard generates a proposal and preview; nothing external changes yet.
9. User explicitly approves the proposal.
10. The GitHub MCP tool creates a reviewable PR in an approved repository.
11. After the changed architecture is re-ingested, ArchGuard compares before/after findings.
12. The final screen reports whether the architecture improved, what risks remain, and what still requires human review.

## Final demo success metrics

The end state should be visually obvious:

- architecture version: V1 → V2
- critical/high risks: before → after
- architecture health: before → after
- original finding: resolved / still present
- scenario blast radius: before → after when applicable
- MCP action: PR created / not created
- production modified: **No**

## Stop-building rule

Once the Definition of Done flow works reliably and is visually polished, stop adding major capabilities. Remaining work should be limited to testing, UX polish, demo data, reliability, security hardening, documentation, and deployment readiness.
