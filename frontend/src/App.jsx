import { useState } from "react";
import ArchitectureGraph from "./components/ArchitectureGraph";
import FileDropZone from "./components/FileDropZone";
import AnalysisProgress from "./AnalysisProgress";
import "./App.css";
import "./EngineeringReport.css";

const API_BASE = "http://127.0.0.1:8000";

const SUGGESTIONS = [
  { mode: "DESIGN", text: "Design a payment platform for 10M users" },
  { mode: "REVIEW", text: "Review my architecture and identify production risks" },
  { mode: "SIMULATE", text: "What happens if PostgreSQL goes down?" },
  { mode: "EVOLVE", text: "We now expect 20x traffic. What should change?" },
];

const FOLLOW_UPS = {
  design: ["Why did you choose this database?", "Simulate a database outage", "Make this multi-region", "Reduce infrastructure cost"],
  review: ["Show the highest-risk dependency", "Simulate the biggest SPOF", "How should I fix the top risk?", "What changes for 10x traffic?"],
  simulate: ["How do we reduce this blast radius?", "Which service fails first?", "Create a remediation plan", "Compare before and after"],
  modify: ["Compare the old and new architecture", "What new risks does this introduce?", "Create a migration plan", "Simulate the target architecture"],
  remediate: ["Show the proposed change", "What will this fix?", "How will we verify it?", "Show remaining risks"],
  question: ["Review the full architecture", "What is the biggest risk?", "Simulate a failure", "Recommend improvements"],
};

function entityName(entity) {
  return entity?.name || entity?.canonical_name || entity?.id || "Unnamed component";
}

function entityType(entity) {
  return entity?.type || entity?.component_type || "component";
}

function connectionParts(connection) {
  if (Array.isArray(connection)) return { source: connection[0], target: connection[1], label: connection[2] };
  return {
    source: connection?.source || connection?.from,
    target: connection?.target || connection?.to,
    label: connection?.type || connection?.protocol || connection?.label,
  };
}

function stripMarkdown(value = "") {
  return value
    .replace(/\*\*(.*?)\*\*/g, "$1")
    .replace(/\*(.*?)\*/g, "$1")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/&nbsp;|&#x20;/g, " ")
    .trim();
}

function cleanResponseText(value = "") {
  return value
    .split("\n")
    .filter((line) => !/^\s*\\?-{3,}\s*$/.test(line))
    .join("\n")
    .trim();
}

function normalizeTableLine(line = "") {
  return line.replace(/\\\|/g, "|").trim();
}

function splitTableRow(line = "") {
  return normalizeTableLine(line)
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => stripMarkdown(cell.trim()));
}

function isTableSeparator(line = "") {
  const normalized = normalizeTableLine(line);
  if (!normalized.includes("|")) return false;
  const cells = splitTableRow(normalized);
  return cells.length > 1 && cells.every((cell) => /^:?-{3,}:?$/.test(cell.replace(/\s/g, "")));
}

function extractTables(body = "") {
  const lines = cleanResponseText(body).split("\n");
  const tables = [];
  const remaining = [];
  let i = 0;

  while (i < lines.length) {
    const header = normalizeTableLine(lines[i]);
    const separator = i + 1 < lines.length ? normalizeTableLine(lines[i + 1]) : "";
    if (header.includes("|") && splitTableRow(header).length > 1 && isTableSeparator(separator)) {
      const headers = splitTableRow(header);
      const rows = [];
      i += 2;
      while (i < lines.length) {
        const candidate = normalizeTableLine(lines[i]);
        if (!candidate || !candidate.includes("|")) break;
        const cells = splitTableRow(candidate);
        if (cells.length < 2) break;
        while (cells.length < headers.length) cells.push("");
        rows.push(cells.slice(0, headers.length));
        i += 1;
      }
      tables.push({ headers, rows });
      continue;
    }
    remaining.push(lines[i]);
    i += 1;
  }

  return { tables, text: remaining.join("\n").trim() };
}

function parseEngineeringAnswer(text = "") {
  const lines = cleanResponseText(text).replace(/\r/g, "").split("\n");
  const sections = [];
  let current = { title: "Overview", lines: [] };
  let inCode = false;

  const push = () => {
    const body = cleanResponseText(current.lines.join("\n"));
    if (body && !/^\*\*?\d+\*\*?$/.test(body)) sections.push({ ...current, body });
  };

  lines.forEach((line) => {
    if (line.trim().startsWith("```")) {
      inCode = !inCode;
      return;
    }
    if (inCode) return;
    const heading = line.match(/^#{2,4}\s+(.*)$/);
    if (heading) {
      push();
      current = {
        title: stripMarkdown(heading[1]).replace(/^\d+[.)]?\s*/, "") || "Architecture detail",
        lines: [],
      };
      return;
    }
    if (/^\s*\*\*\d+\*\*\s*$/.test(line)) return;
    if (!line.trim() && !current.lines.length) return;
    current.lines.push(line);
  });
  push();
  return sections;
}

function splitSectionItems(body = "") {
  const lines = cleanResponseText(body).split("\n").map((line) => line.trim()).filter(Boolean);
  const intro = [];
  const items = [];
  let current = null;

  lines.forEach((line) => {
    const numbered = line.match(/^\d+[.)]\s+(.*)$/);
    const bullet = line.match(/^[-*]\s+(.*)$/);
    const subheading = line.match(/^#{1,5}\s+(.*)$/);

    if (subheading || numbered) {
      if (current) items.push(current);
      current = { title: stripMarkdown((subheading || numbered)[1]), details: [] };
      return;
    }

    if (bullet) {
      const value = stripMarkdown(bullet[1]);
      const label = value.match(/^([^:]{2,45}):\s*(.*)$/);
      if (label) items.push({ title: label[1], details: [label[2]] });
      else if (current) current.details.push(value);
      else items.push({ title: value, details: [] });
      return;
    }

    if (current) current.details.push(stripMarkdown(line));
    else intro.push(stripMarkdown(line));
  });

  if (current) items.push(current);
  return { intro, items };
}

function sectionTone(title = "") {
  const value = title.toLowerCase();
  if (value.includes("risk") || value.includes("bottleneck") || value.includes("failure")) return "danger";
  if (value.includes("mitigation") || value.includes("recommend") || value.includes("improve") || value.includes("migration")) return "success";
  if (value.includes("question") || value.includes("assumption")) return "warning";
  if (value.includes("component") || value.includes("technology") || value.includes("architecture")) return "info";
  return "neutral";
}

function EngineeringTable({ table, tone }) {
  return (
    <div className="engineering-table-wrap">
      <table className={`engineering-table engineering-table-${tone}`}>
        <thead><tr>{table.headers.map((header, index) => <th key={index}>{header}</th>)}</tr></thead>
        <tbody>
          {table.rows.map((row, rowIndex) => (
            <tr key={rowIndex}>{row.map((cell, columnIndex) => <td key={columnIndex} data-label={table.headers[columnIndex] || "Value"}>{cell}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function EngineeringSection({ section, index }) {
  const tone = sectionTone(section.title);
  const parsed = extractTables(section.body);
  const { intro, items } = splitSectionItems(parsed.text);
  if (!intro.length && !items.length && !parsed.tables.length) return null;

  return (
    <section className={`report-section report-${tone}`}>
      <div className="report-section-head">
        <span className="report-index">{String(index + 1).padStart(2, "0")}</span>
        <div>
          <h4>{section.title}</h4>
          <small>{tone === "danger" ? "Risks that deserve attention" : tone === "success" ? "Recommended engineering actions" : tone === "warning" ? "Assumptions and information gaps" : "Architecture detail"}</small>
        </div>
      </div>
      {intro.length > 0 && <div className="report-intro">{intro.map((paragraph, i) => <p key={i}>{paragraph}</p>)}</div>}
      {parsed.tables.map((table, i) => <EngineeringTable key={i} table={table} tone={tone} />)}
      {items.length > 0 && (
        <div className="report-item-grid">
          {items.map((item, i) => (
            <article className="report-item" key={`${item.title}-${i}`}>
              <div className="report-item-number">{i + 1}</div>
              <div><h5>{item.title}</h5>{item.details.map((detail, j) => <p key={j}>{detail}</p>)}</div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function WorkspaceSummary({ result }) {
  if (!result) return null;
  const twin = result?.context?.digital_twin || {};
  const architecture = result?.context?.architecture || result?.execution?.result?.architecture || {};
  const entities = twin?.entities?.length ? twin.entities : (architecture?.services || []);
  const connections = (twin?.connections?.length ? twin.connections : (architecture?.connections || [])).map(connectionParts).filter((item) => item.source && item.target);
  const findings = result?.execution?.result?.findings || [];
  const waf = result?.execution?.result?.well_architected || {};
  const intent = result?.routing?.intent || "analysis";

  return (
    <section className="workspace-summary">
      <div>
        <span className="kicker">ARCHITECTURE WORKSPACE</span>
        <h1>{intent === "simulate" ? "Scenario analysis complete" : intent === "modify" ? "Architecture evolution proposed" : intent === "remediate" ? "Remediation plan prepared" : "Architecture analysis complete"}</h1>
        <p>Continue asking questions without losing the current system context.</p>
      </div>
      <div className="workspace-metrics">
        {entities.length > 0 && <span><b>{entities.length}</b>Components</span>}
        {connections.length > 0 && <span><b>{connections.length}</b>Connections</span>}
        {findings.length > 0 && <span><b>{findings.length}</b>Risks</span>}
        {waf?.overall_score != null && <span><b>{Math.round(waf.overall_score)}</b>Health score</span>}
      </div>
    </section>
  );
}

function StructuredAnswer({ result }) {
  if (!result) return null;
  const twin = result?.context?.digital_twin || {};
  const architecture = result?.context?.architecture || result?.execution?.result?.architecture || {};
  const execution = result?.execution?.result || {};
  const entities = twin?.entities?.length ? twin.entities : (architecture?.services || []);
  const connections = (twin?.connections?.length ? twin.connections : (architecture?.connections || [])).map(connectionParts).filter((item) => item.source && item.target);
  const findings = execution?.findings || [];
  const waf = execution?.well_architected || {};
  const intent = result?.routing?.intent || "analysis";
  const sections = parseEngineeringAnswer(result?.answer || "Analysis completed.");

  return (
    <div className="structured-answer">
      <div className="answer-hero">
        <div>
          <span className="kicker">ARCHGUARD {String(intent).toUpperCase()}</span>
          <h3>Engineering assessment</h3>
          <p>Grounded architecture guidance generated from the current system context and available evidence.</p>
        </div>
      </div>

      {entities.length > 0 && (
        <section className="answer-section compact-section">
          <div className="section-label"><span>SYS</span><div><b>System components</b><small>Current architecture context</small></div></div>
          <div className="component-grid">
            {entities.map((entity, i) => (
              <article className="component-card" key={entity?.id || entityName(entity) || i}>
                <div className="component-icon">{String(entityType(entity)).toLowerCase().includes("database") ? "DB" : "◇"}</div>
                <div><h4>{entityName(entity)}</h4><span>{entityType(entity)}</span>{entity?.confidence != null && <small>{Math.round(Number(entity.confidence) * 100)}% evidence confidence</small>}</div>
              </article>
            ))}
          </div>
        </section>
      )}

      {connections.length > 0 && (
        <section className="answer-section compact-section">
          <div className="section-label"><span>FLOW</span><div><b>Connection flow</b><small>How components communicate</small></div></div>
          <div className="connection-list">
            {connections.map((connection, i) => (
              <div className="connection-row" key={i}><strong>{connection.source}</strong><span className="connection-arrow"><i />→<i /></span><strong>{connection.target}</strong>{connection.label && <em>{connection.label}</em>}</div>
            ))}
          </div>
        </section>
      )}

      <div className="report-stack">{sections.map((section, i) => <EngineeringSection key={`${section.title}-${i}`} section={section} index={i} />)}</div>

      {findings.length > 0 && (
        <section className="answer-section">
          <div className="section-label"><span>RISK</span><div><b>Evidence-backed risk register</b><small>Prioritized architecture findings</small></div></div>
          <div className="answer-risk-grid">
            {findings.slice(0, 8).map((finding, i) => (
              <article className="answer-risk" key={finding.id || i}>
                <div className="risk-top"><span className={`severity ${String(finding.severity || "info").toLowerCase()}`}>{finding.severity || "INFO"}</span>{finding.risk_score != null && <span>Risk {finding.risk_score}</span>}</div>
                <h4>{finding.title || finding.category || "Architecture finding"}</h4>
                <p>{finding.description || finding.message || "Review this architecture finding."}</p>
                {finding.recommendation && <div className="action-box"><b>Recommended action</b><span>{finding.recommendation}</span></div>}
              </article>
            ))}
          </div>
        </section>
      )}

      {waf?.overall_score != null && (
        <section className="answer-section score-strip">
          <div><span className="kicker">ARCHITECTURE HEALTH</span><b>{Math.round(waf.overall_score)}<small>/100</small></b></div>
          <p>Heuristic architecture-quality score from ArchGuard's deterministic review. Use it as engineering guidance rather than a certification.</p>
        </section>
      )}
    </div>
  );
}

export default function App() {
  const [prompt, setPrompt] = useState("");
  const [files, setFiles] = useState([]);
  const [manualInput, setManualInput] = useState("");
  const [showArtifacts, setShowArtifacts] = useState(false);
  const [messages, setMessages] = useState([]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activePrompt, setActivePrompt] = useState("");
  const [error, setError] = useState("");
  const [activeDetail, setActiveDetail] = useState("risks");

  const digitalTwin = result?.context?.digital_twin;
  const architecture = result?.context?.architecture || result?.execution?.result?.architecture;
  const execution = result?.execution?.result || {};
  const findings = execution?.findings || [];
  const waf = execution?.well_architected || {};
  const intent = result?.routing?.intent || "ready";
  const hasArchitecture = Boolean(digitalTwin?.entities?.length || architecture?.services?.length);
  const hasEvidence = Boolean(result?.context?.processed_files?.length || result?.context?.manual_input_provided || result?.context?.architecture_detected);
  const hasDetails = findings.length > 0 || waf?.overall_score != null || hasEvidence;
  const followUps = FOLLOW_UPS[intent] || FOLLOW_UPS.question;

  async function askArchGuard(event, suggestedPrompt) {
    event?.preventDefault?.();
    const question = (suggestedPrompt ?? prompt).trim();
    if (!question) {
      setError("Enter a question or requirement before asking ArchGuard.");
      return;
    }

    setLoading(true);
    setActivePrompt(question);
    setError("");
    setMessages((current) => [...current, { role: "user", text: question }]);

    try {
      const formData = new FormData();
      formData.append("prompt", question);
      files.forEach((file) => formData.append("files", file));
      if (manualInput.trim()) formData.append("manual_input", manualInput.trim());

      const response = await fetch(`${API_BASE}/assistant/input`, { method: "POST", body: formData });
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "ArchGuard could not process the request.");

      setResult(data);
      setMessages((current) => [...current, { role: "assistant", result: data }]);
      setPrompt("");
    } catch (err) {
      setError(err.message || "Something went wrong while contacting ArchGuard.");
    } finally {
      setLoading(false);
      setActivePrompt("");
    }
  }

  function resetWorkspace() {
    setPrompt("");
    setFiles([]);
    setManualInput("");
    setMessages([]);
    setResult(null);
    setError("");
    setShowArtifacts(false);
    setActivePrompt("");
  }

  return (
    <div className="app-shell">
      <nav className="topbar">
        <button className="brand" onClick={resetWorkspace}><span className="brand-mark">A</span><span><strong>ArchGuard</strong><small>AI Architecture Engineer</small></span></button>
        <div className="top-actions"><span className="status"><i /> System ready</span><button className="ghost" onClick={resetWorkspace}>New session</button></div>
      </nav>

      <main className={messages.length ? "workspace has-chat" : "workspace"}>
        {!messages.length && (
          <section className="welcome">
            <div className="glow glow-one" /><div className="glow glow-two" />
            <span className="kicker">DESIGN · REVIEW · SIMULATE · EVOLVE</span>
            <h1>Build systems that are ready<br />for the <span>real world.</span></h1>
            <p>Describe an idea, attach architecture artifacts or diagrams, or ask a what-if question. ArchGuard turns engineering context into structured, evidence-backed guidance.</p>
            <form className="composer hero-composer" onSubmit={askArchGuard}>
              <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); askArchGuard(event); } }} placeholder="Ask ArchGuard anything about your system..." rows={3} />
              <div className="composer-footer"><button type="button" className="attach" onClick={() => setShowArtifacts((value) => !value)}>＋ Attach files / image {files.length > 0 && <b>{files.length}</b>}</button><span className="hint">Prompt required · files / image optional</span><button className="send" disabled={loading || !prompt.trim()}>{loading ? "Analyzing…" : "Ask ArchGuard →"}</button></div>
            </form>
            <div className="suggestions">{SUGGESTIONS.map((item) => <button key={item.text} onClick={() => setPrompt(item.text)}><span><em>{item.mode}</em>{item.text}</span><b>↗</b></button>)}</div>
          </section>
        )}

        {showArtifacts && (
          <section className="artifact-drawer">
            <div className="drawer-head"><div><span className="kicker">OPTIONAL CONTEXT</span><h2>Add files, diagrams or engineering evidence</h2></div><button className="close" onClick={() => setShowArtifacts(false)}>×</button></div>
            <FileDropZone files={files} setFiles={setFiles} />
            <label className="manual-label">Or paste architecture, stakeholder requirements, logs, or notes</label>
            <textarea className="manual-area" value={manualInput} onChange={(event) => setManualInput(event.target.value)} placeholder="Paste JSON, YAML, architecture notes, stakeholder requirements..." />
          </section>
        )}

        {messages.length > 0 && (
          <div className="stacked-workspace">
            {loading ? (
              <AnalysisProgress prompt={activePrompt} />
            ) : (
              <WorkspaceSummary result={result} />
            )}

            {!loading && hasArchitecture && digitalTwin?.entities?.length > 0 && (
              <section className="architecture-stage">
                <div className="stage-heading"><div><span className="kicker">ARCHITECTURE VIEW</span><h2>Interactive Digital Twin</h2><p>Explore the current system model, dependencies, critical paths and architecture evidence without leaving the workspace.</p></div><span className="metric">{digitalTwin.entities.length} components</span></div>
                <div className="architecture-canvas-shell"><ArchitectureGraph digitalTwin={digitalTwin} /></div>
              </section>
            )}

            {!loading && result && (
              <section className="result-navigation">
                <div className="result-nav-copy"><span className="kicker">ANALYSIS WORKSPACE</span><h2>Explore the result</h2><p>Start with the summary, then drill into risk, evidence and follow-up scenarios only when needed.</p></div>
                <div className="result-nav-pills"><span className="active">Overview</span>{findings.length > 0 && <span>Risks · {findings.length}</span>}{hasArchitecture && <span>Architecture</span>}{hasEvidence && <span>Evidence</span>}<span>Ask follow-up</span></div>
              </section>
            )}

            <section className="conversation-panel full-conversation">
              <div className="panel-title"><div><span className="kicker">ARCHITECTURE COPILOT</span><h2>Engineering conversation</h2></div><span className={`intent intent-${intent}`}>{intent}</span></div>
              <div className="messages rich-messages">
                {messages.map((message, index) => (
                  <article className={`message ${message.role} ${message.result ? "structured-message" : ""}`} key={`${message.role}-${index}`}>
                    <div className="avatar">{message.role === "user" ? "Y" : "A"}</div>
                    <div className="message-content"><strong>{message.role === "user" ? "You" : "ArchGuard"}</strong>{message.result ? <StructuredAnswer result={message.result} /> : <div className="message-text">{message.text}</div>}</div>
                  </article>
                ))}
              </div>

              {!loading && result && <div className="follow-up-row">{followUps.map((item) => <button key={item} onClick={(event) => askArchGuard(event, item)}>{item}<span>↗</span></button>)}</div>}
              {error && <div className="error-box">{error}</div>}
              <form className="composer compact sticky-composer" onSubmit={askArchGuard}>
                <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="Ask about this architecture, change a requirement, or run a scenario..." rows={2} />
                <div className="composer-footer"><button type="button" className="attach" onClick={() => setShowArtifacts((value) => !value)}>＋ Files / image {files.length > 0 && <b>{files.length}</b>}</button><span className="hint">Current architecture context is preserved</span><button className="send" disabled={loading || !prompt.trim()}>{loading ? "Analyzing…" : "Ask ArchGuard →"}</button></div>
              </form>
            </section>

            {!loading && hasDetails && (
              <section className="detail-stage">
                <div className="tabs detail-tabs">
                  {(findings.length > 0 || waf?.overall_score != null) && <button className={activeDetail === "risks" ? "active" : ""} onClick={() => setActiveDetail("risks")}>Risk intelligence {findings.length > 0 && <b>{findings.length}</b>}</button>}
                  {hasEvidence && <button className={activeDetail === "evidence" ? "active" : ""} onClick={() => setActiveDetail("evidence")}>Evidence</button>}
                </div>
                <div className="detail-body">
                  {activeDetail === "risks" && (findings.length > 0 || waf?.overall_score != null) ? (
                    <div><div className="insight-heading"><div><span className="kicker">RISK INTELLIGENCE</span><h2>Prioritized architecture risks</h2></div>{waf?.overall_score != null && <span className="score">{Math.round(waf.overall_score)}<small>/100 health</small></span>}</div><div className="risk-list detail-risk-grid">{findings.map((finding, index) => <article className="risk-card" key={finding.id || index}><div className="risk-top"><span className={`severity ${String(finding.severity || "info").toLowerCase()}`}>{finding.severity || "INFO"}</span>{finding.risk_score != null && <span>Risk {finding.risk_score}</span>}</div><h3>{finding.title || finding.category || "Architecture finding"}</h3><p>{finding.description || finding.message || "Review this architecture finding."}</p>{finding.recommendation && <div className="recommendation">{finding.recommendation}</div>}</article>)}</div></div>
                  ) : hasEvidence ? (
                    <div><div className="insight-heading"><div><span className="kicker">EVIDENCE</span><h2>What ArchGuard used</h2></div></div><div className="evidence-grid"><div><span>Architecture</span><strong>{result?.context?.architecture_detected ? "detected" : "contextual"}</strong></div><div><span>Files processed</span><strong>{result?.context?.processed_files?.length || 0}</strong></div><div><span>Manual context</span><strong>{result?.context?.manual_input_provided ? "included" : "none"}</strong></div><div><span>Reasoning</span><strong>{result?.synthesis?.status || "local"}</strong></div></div></div>
                  ) : null}
                </div>
              </section>
            )}
          </div>
        )}
      </main>

      <footer><span>ArchGuard AI</span><span>Evidence-backed architecture engineering · Human approval before execution</span></footer>
    </div>
  );
}
