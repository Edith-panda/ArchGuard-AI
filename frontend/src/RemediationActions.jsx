import { useMemo, useState } from "react";

const API_BASE = "http://127.0.0.1:8000";

async function requestJson(url, options) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof data.detail === "string" ? data.detail : "ArchGuard could not complete this action.";
    throw new Error(detail);
  }
  return data;
}

function proposalTitle(proposal) {
  return proposal?.finding?.issue || proposal?.finding?.category || proposal?.strategy || "Architecture remediation";
}

export default function RemediationActions({ result }) {
  const proposals = useMemo(() => result?.execution?.result?.remediation_plan?.proposals || [], [result]);
  const [selectedId, setSelectedId] = useState(proposals[0]?.proposal_id || "");
  const [preview, setPreview] = useState(null);
  const [state, setState] = useState(null);
  const [mcpResult, setMcpResult] = useState(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  if (!proposals.length) return null;

  const proposal = proposals.find((item) => item.proposal_id === selectedId) || proposals[0];
  const proposalId = proposal?.proposal_id;
  const approvalStatus = state?.approval_status || proposal?.approval_status || "pending";
  const approved = approvalStatus === "approved" || state?.approved === true;
  const rejected = approvalStatus === "rejected";
  const mcp = state?.mcp;
  const canCreatePr = approved && mcp?.configured && mcp?.write_enabled;
  const previewed = preview?.proposal_id === proposalId;

  async function loadState() {
    if (!proposalId) return;
    const data = await requestJson(`${API_BASE}/remediation/${proposalId}/state`);
    setState(data);
    return data;
  }

  async function showPreview() {
    setBusy("preview");
    setError("");
    try {
      const data = await requestJson(`${API_BASE}/remediation/${proposalId}/mcp-preview`);
      setPreview(data);
      await loadState();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  async function decide(action) {
    if (action === "approve" && !previewed) {
      setError("Preview the proposed change before approving it.");
      return;
    }
    setBusy(action);
    setError("");
    try {
      const data = await requestJson(`${API_BASE}/remediation/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ proposal_id: proposalId }),
      });
      setState((current) => ({ ...(current || {}), ...data }));
      setMcpResult(null);
      await loadState();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  async function createPullRequest() {
    setBusy("mcp");
    setError("");
    try {
      const data = await requestJson(`${API_BASE}/remediation/${proposalId}/mcp-create-pr`, { method: "POST" });
      setMcpResult(data);
      await loadState();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  function selectProposal(id) {
    setSelectedId(id);
    setPreview(null);
    setState(null);
    setMcpResult(null);
    setError("");
  }

  return (
    <section className="remediation-control" aria-label="Remediation approval and MCP execution">
      <div className="remediation-head">
        <div>
          <span className="kicker">SAFE REMEDIATION</span>
          <h3>Review, approve, then create a pull request</h3>
          <p>ArchGuard will not modify production. Approval only unlocks the review-only MCP action.</p>
        </div>
        <span className={`approval-pill approval-${approvalStatus}`}>{approvalStatus.replace("_", " ")}</span>
      </div>

      {proposals.length > 1 && (
        <div className="proposal-tabs">
          {proposals.map((item, index) => (
            <button key={item.proposal_id} className={item.proposal_id === proposalId ? "active" : ""} onClick={() => selectProposal(item.proposal_id)}>
              P{index} · {proposalTitle(item)}
            </button>
          ))}
        </div>
      )}

      <div className="proposal-summary">
        <div><span>Target</span><strong>{proposal?.change_scope || proposal?.finding?.component || "Architecture"}</strong></div>
        <div><span>Risk</span><strong>{proposal?.finding?.risk_score ?? "—"}</strong></div>
        <div><span>Severity</span><strong>{String(proposal?.finding?.severity || "unknown").toUpperCase()}</strong></div>
        <div><span>Production</span><strong>Not modified</strong></div>
      </div>

      <div className="proposal-copy">
        <h4>{proposalTitle(proposal)}</h4>
        <p>{proposal?.recommended_change || "Review the proposed architecture remediation."}</p>
      </div>

      <div className="remediation-actions">
        <button className="secondary-action" disabled={Boolean(busy)} onClick={showPreview}>
          {busy === "preview" ? "Preparing preview…" : previewed ? "Refresh preview" : "Preview proposed change"}
        </button>
        {!approved && !rejected && (
          <>
            <button className="reject-action" disabled={Boolean(busy)} onClick={() => decide("reject")}>Reject</button>
            <button className="approve-action" disabled={Boolean(busy) || !previewed} onClick={() => decide("approve")} title={!previewed ? "Preview the proposed change first" : "Approve this remediation"}>
              {busy === "approve" ? "Approving…" : "Approve change"}
            </button>
          </>
        )}
      </div>

      {!approved && !rejected && !previewed && <div className="approval-guidance">Preview is required before approval. No external action occurs during preview.</div>}

      {preview?.proposed_diff && (
        <div className="diff-preview">
          <div className="diff-preview-head"><div><span>PROPOSED ARTIFACT</span><strong>{preview.proposed_diff.filename}</strong></div><span>Preview only</span></div>
          <pre>{preview.proposed_diff.diff}</pre>
          <p>{preview.note || preview.proposed_diff.note}</p>
        </div>
      )}

      {approved && !mcpResult && (
        <div className="mcp-card">
          <div>
            <span className="kicker">MCP ACTION</span>
            <h4>Create a reviewable engineering change</h4>
            <p>Creates a feature branch and pull request only. It never merges or deploys the change.</p>
          </div>
          <div className="mcp-status-grid">
            <span><small>Repository</small><strong>{mcp?.repository || "Not configured"}</strong></span>
            <span><small>MCP configured</small><strong>{mcp?.configured ? "Yes" : "No"}</strong></span>
            <span><small>Write gate</small><strong>{mcp?.write_enabled ? "Enabled" : "Disabled"}</strong></span>
            <span><small>Production execution</small><strong>No</strong></span>
          </div>
          {!mcp?.configured || !mcp?.write_enabled ? <div className="mcp-warning">Approval succeeded, but GitHub MCP writes are still locked. Configure the demo repository and explicitly enable the write gate before creating a PR.</div> : null}
          <button className="mcp-action" disabled={Boolean(busy) || !canCreatePr} onClick={createPullRequest}>
            {busy === "mcp" ? "Creating pull request…" : "Create Pull Request via MCP →"}
          </button>
        </div>
      )}

      {rejected && <div className="decision-banner rejected">Proposal rejected. No external action can be performed for this proposal.</div>}

      {mcpResult && (
        <div className="mcp-success">
          <span>✓ MCP execution complete</span>
          <h4>Pull Request #{mcpResult.pull_request_number} created</h4>
          <p>{mcpResult.branch}</p>
          <div className="mcp-success-actions">
            {mcpResult.pull_request_url && <a href={mcpResult.pull_request_url} target="_blank" rel="noreferrer">View Pull Request ↗</a>}
            <button onClick={() => window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" })}>Continue to verification</button>
          </div>
          <small>Production modified: NO · Review and merge remain human-controlled.</small>
        </div>
      )}

      {error && <div className="remediation-error">{error}</div>}
    </section>
  );
}
