import { useMemo, useState } from "react";
import ArchitectureGraph from "./components/ArchitectureGraph";
import FileDropZone from "./components/FileDropZone";
import "./App.css";
import "./EngineeringReport.css";

const API_BASE = "http://127.0.0.1:8000";
const SUGGESTIONS = [
  "Design an e-commerce platform for 10M users",
  "Review my architecture and find the biggest risks",
  "What happens if the database goes down?",
  "Stakeholders expect 20x traffic. What should change?",
];

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
  return value.replace(/\*\*(.*?)\*\*/g, "$1").replace(/\*(.*?)\*/g, "$1").replace(/`([^`]+)`/g, "$1").trim();
}

function parseEngineeringAnswer(text = "") {
  const lines = text.replace(/\r/g, "").split("\n");
  const sections = [];
  let current = { title: "Overview", lines: [], codeBlocks: [] };
  let inCode = false;
  let code = [];

  const pushCurrent = () => {
    const body = current.lines.join("\n").trim();
    if (body || current.codeBlocks.length) sections.push({ ...current, body });
  };

  lines.forEach((line) => {
    if (line.trim().startsWith("```")) {
      if (inCode) {
        current.codeBlocks.push(code.join("\n").trim());
        code = [];
        inCode = false;
      } else inCode = true;
      return;
    }
    if (inCode) {
      code.push(line);
      return;
    }
    const heading = line.match(/^#{2,4}\s+(.*)$/);
    if (heading) {
      pushCurrent();
      current = { title: stripMarkdown(heading[1]).replace(/^\d+\.\s*/, ""), lines: [], codeBlocks: [] };
      return;
    }
    if (!line.trim() && !current.lines.length) return;
    current.lines.push(line);
  });

  if (inCode && code.length) current.codeBlocks.push(code.join("\n").trim());
  pushCurrent();
  return { sections, allCodeBlocks: sections.flatMap((section) => section.codeBlocks || []) };
}

function splitSectionItems(body = "") {
  const lines = body.split("\n").map((line) => line.trim()).filter(Boolean);
  const intro = [];
  const items = [];
  let current = null;

  lines.forEach((line) => {
    const numbered = line.match(/^\d+[.)]\s+(.*)$/);
    const bullet = line.match(/^[-*]\s+(.*)$/);
    if (numbered) {
      if (current) items.push(current);
      current = { title: stripMarkdown(numbered[1]), details: [] };
      return;
    }
    if (bullet) {
      const value = stripMarkdown(bullet[1]);
      const labelMatch = value.match(/^([^:]{2,45}):\s*(.*)$/);
      if (labelMatch) items.push({ title: labelMatch[1], details: [labelMatch[2]] });
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
  if (value.includes("risk") || value.includes("bottleneck")) return "danger";
  if (value.includes("mitigation") || value.includes("recommend") || value.includes("improve")) return "success";
  if (value.includes("question") || value.includes("assumption")) return "warning";
  if (value.includes("component") || value.includes("technology")) return "info";
  return "neutral";
}

function EngineeringSection({ section, index }) {
  const { intro, items } = splitSectionItems(section.body);
  const tone = sectionTone(section.title);
  return (
    <section className={`report-section report-${tone}`}>
      <div className="report-section-head">
        <span className="report-index">{String(index + 1).padStart(2, "0")}</span>
        <div><h4>{section.title}</h4><small>{tone === "danger" ? "Risks that deserve attention" : tone === "success" ? "Recommended engineering actions" : tone === "warning" ? "Assumptions and information gaps" : "Architecture detail"}</small></div>
      </div>
      {intro.length > 0 && <div className="report-intro">{intro.map((paragraph, i) => <p key={i}>{paragraph}</p>)}</div>}
      {items.length > 0 && <div className="report-item-grid">{items.map((item, itemIndex) => <article className="report-item" key={`${item.title}-${itemIndex}`}><div className="report-item-number">{itemIndex + 1}</div><div><h5>{item.title}</h5>{item.details.map((detail, detailIndex) => <p key={detailIndex}>{detail}</p>)}</div></article>)}</div>}
      {section.codeBlocks?.map((block, blockIndex) => <div className="inline-blueprint" key={blockIndex}><div className="blueprint-label">Architecture blueprint</div><pre>{block}</pre></div>)}
    </section>
  );
}

function StructuredAnswer({ result }) {
  if (!result) return null;
  const twin = result?.context?.digital_twin || {};
  const architecture = result?.context?.architecture || {};
  const execution = result?.execution?.result || {};
  const entities = twin?.entities?.length ? twin.entities : (architecture?.services || []);
  const rawConnections = twin?.connections?.length ? twin.connections : (architecture?.connections || []);
  const connections = rawConnections.map(connectionParts).filter((item) => item.source && item.target);
  const findings = execution?.findings || [];
  const waf = execution?.well_architected || {};
  const intent = result?.routing?.intent || "analysis";
  const parsed = parseEngineeringAnswer(result?.answer || "Analysis completed.");

  return (
    <div className="structured-answer">
      <div className="answer-hero"><div><span className="kicker">ARCHGUARD {String(intent).toUpperCase()}</span><h3>Engineering assessment</h3><p>Structured architecture guidance generated from your request and available evidence.</p></div><div className="answer-stats"><span><b>{entities.length}</b> components</span><span><b>{connections.length}</b> connections</span><span><b>{findings.length}</b> findings</span></div></div>
      {entities.length > 0 && <section className="answer-section compact-section"><div className="section-label"><span>SYS</span><div><b>Detected system components</b><small>Current architecture evidence</small></div></div><div className="component-grid">{entities.map((entity, index) => <article className="component-card" key={entity?.id || entityName(entity) || index}><div className="component-icon">{String(entityType(entity)).toLowerCase().includes("database") ? "DB" : "◇"}</div><div><h4>{entityName(entity)}</h4><span>{entityType(entity)}</span>{entity?.confidence != null && <small>{Math.round(Number(entity.confidence) * 100)}% evidence confidence</small>}</div></article>)}</div></section>}
      {connections.length > 0 && <section className="answer-section compact-section"><div className="section-label"><span>FLOW</span><div><b>Connection flow</b><small>How components communicate</small></div></div><div className="connection-list">{connections.map((connection, index) => <div className="connection-row" key={`${connection.source}-${connection.target}-${index}`}><strong>{connection.source}</strong><span className="connection-arrow"><i />→<i /></span><strong>{connection.target}</strong>{connection.label && <em>{connection.label}</em>}</div>)}</div></section>}
      <div className="report-stack">{parsed.sections.map((section, index) => <EngineeringSection key={`${section.title}-${index}`} section={section} index={index} />)}</div>
      {findings.length > 0 && <section className="answer-section"><div className="section-label"><span>RISK</span><div><b>Evidence-backed risk register</b><small>Deterministic findings from ArchGuard engines</small></div></div><div className="answer-risk-grid">{findings.slice(0, 8).map((finding, index) => <article className="answer-risk" key={finding.id || index}><div className="risk-top"><span className={`severity ${String(finding.severity || "info").toLowerCase()}`}>{finding.severity || "INFO"}</span>{finding.risk_score != null && <span>Risk {finding.risk_score}</span>}</div><h4>{finding.title || finding.category || "Architecture finding"}</h4><p>{finding.description || finding.message || "Review this architecture finding."}</p>{finding.recommendation && <div className="action-box"><b>Recommended action</b><span>{finding.recommendation}</span></div>}</article>)}</div></section>}
      {waf?.overall_score != null && <section className="answer-section score-strip"><div><span className="kicker">GOOGLE WELL-ARCHITECTED</span><b>{Math.round(waf.overall_score)}<small>/100</small></b></div><p>Heuristic architecture score from ArchGuard's deterministic review. It is guidance, not an official Google certification.</p></section>}
    </div>
  );
}

function BlueprintPanel({ result, digitalTwin }) {
  const parsed = useMemo(() => parseEngineeringAnswer(result?.answer || ""), [result?.answer]);
  const architecture = result?.context?.architecture || {};
  const detectedServices = digitalTwin?.entities?.length ? digitalTwin.entities : (architecture?.services || []);
  const diagram = parsed.allCodeBlocks.find((block) => /\[|→|↓|│|gateway|database|service|cluster/i.test(block));
  const proposedSection = parsed.sections.find((section) => /component|proposed architecture|technology/i.test(section.title));
  const proposedItems = proposedSection ? splitSectionItems(proposedSection.body).items : [];
  if (digitalTwin?.entities?.length) return <ArchitectureGraph digitalTwin={digitalTwin} />;
  if (!diagram && !proposedItems.length && !detectedServices.length) return <div className="empty-state"><span>◇</span><h3>No architecture blueprint yet</h3><p>Ask ArchGuard for a system design or attach architecture evidence. A generated blueprint will appear here when the answer contains architecture structure.</p></div>;

  return <div className="blueprint-panel">{diagram && <div className="blueprint-canvas"><div className="blueprint-toolbar"><span>GENERATED ARCHITECTURE</span><small>Conceptual design</small></div><pre>{diagram}</pre></div>}{(proposedItems.length > 0 || detectedServices.length > 0) && <div className="blueprint-components"><div className="blueprint-subhead"><span>COMPONENT INVENTORY</span><b>{proposedItems.length || detectedServices.length}</b></div>{(proposedItems.length ? proposedItems : detectedServices.map((item) => ({ title: entityName(item), details: [entityType(item)] }))).slice(0, 12).map((item, index) => <article key={`${item.title}-${index}`}><span className="node-dot" /><div><strong>{item.title}</strong>{item.details?.[0] && <small>{item.details[0]}</small>}</div></article>)}</div>}</div>;
}

function App() {
  const [prompt, setPrompt] = useState("");
  const [files, setFiles] = useState([]);
  const [manualInput, setManualInput] = useState("");
  const [showArtifacts, setShowArtifacts] = useState(false);
  const [messages, setMessages] = useState([]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState("architecture");

  const digitalTwin = result?.context?.digital_twin;
  const execution = result?.execution?.result || {};
  const findings = execution?.findings || [];
  const waf = execution?.well_architected || {};
  const intent = result?.routing?.intent || "ready";

  async function askArchGuard(event) {
    event?.preventDefault();
    const question = prompt.trim();
    if (!question) { setError("Enter a question or requirement before asking ArchGuard."); return; }
    setLoading(true); setError(""); setMessages((current) => [...current, { role: "user", text: question }]);
    try {
      const formData = new FormData();
      formData.append("prompt", question);
      files.forEach((file) => formData.append("files", file));
      if (manualInput.trim()) formData.append("manual_input", manualInput.trim());
      const response = await fetch(`${API_BASE}/assistant/input`, { method: "POST", body: formData });
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "ArchGuard could not process the request.");
      setResult(data); setMessages((current) => [...current, { role: "assistant", result: data }]); setPrompt("");
    } catch (err) { setError(err.message || "Something went wrong while contacting ArchGuard."); }
    finally { setLoading(false); }
  }

  function resetWorkspace() { setPrompt(""); setFiles([]); setManualInput(""); setMessages([]); setResult(null); setError(""); setShowArtifacts(false); }

  return <div className="app-shell">
    <nav className="topbar"><button className="brand" onClick={resetWorkspace}><span className="brand-mark">A</span><span><strong>ArchGuard</strong><small>AI Architecture Engineer</small></span></button><div className="top-actions"><span className="status"><i /> System ready</span><button className="ghost" onClick={resetWorkspace}>New session</button></div></nav>
    <main className={messages.length ? "workspace has-chat" : "workspace"}>
      {!messages.length && <section className="welcome"><div className="glow glow-one" /><div className="glow glow-two" /><span className="kicker">DESIGN · REVIEW · SIMULATE · EVOLVE</span><h1>Build systems that are ready<br />for the <span>real world.</span></h1><p>Describe an idea, attach architecture artifacts or diagrams, or ask a what-if question. ArchGuard turns engineering context into structured, evidence-backed guidance.</p><form className="composer hero-composer" onSubmit={askArchGuard}><textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); askArchGuard(e); } }} placeholder="Ask ArchGuard anything about your system..." rows={3} /><div className="composer-footer"><button type="button" className="attach" onClick={() => setShowArtifacts((v) => !v)}>＋ Attach files / image {files.length > 0 && <b>{files.length}</b>}</button><span className="hint">Prompt is required · files / image are optional</span><button className="send" disabled={loading || !prompt.trim()}>{loading ? "Thinking…" : "Ask ArchGuard →"}</button></div></form><div className="suggestions">{SUGGESTIONS.map((item) => <button key={item} onClick={() => setPrompt(item)}>{item}<span>↗</span></button>)}</div></section>}
      {showArtifacts && <section className="artifact-drawer"><div className="drawer-head"><div><span className="kicker">OPTIONAL CONTEXT</span><h2>Add files, diagrams or engineering evidence</h2></div><button className="close" onClick={() => setShowArtifacts(false)}>×</button></div><FileDropZone files={files} setFiles={setFiles} /><label className="manual-label">Or paste architecture, stakeholder requirements, logs, or notes</label><textarea className="manual-area" value={manualInput} onChange={(e) => setManualInput(e.target.value)} placeholder="Paste JSON, YAML, architecture notes, stakeholder requirements..." /></section>}
      {messages.length > 0 && <div className="product-grid rich-grid">
        <section className="conversation-panel wide-conversation"><div className="panel-title"><div><span className="kicker">ARCHITECTURE COPILOT</span><h2>Engineering conversation</h2></div><span className={`intent intent-${intent}`}>{intent}</span></div><div className="messages rich-messages">{messages.map((message, index) => <article className={`message ${message.role} ${message.result ? "structured-message" : ""}`} key={`${message.role}-${index}`}><div className="avatar">{message.role === "user" ? "Y" : "A"}</div><div className="message-content"><strong>{message.role === "user" ? "You" : "ArchGuard"}</strong>{message.result ? <StructuredAnswer result={message.result} /> : <div className="message-text">{message.text}</div>}</div></article>)}{loading && <article className="message assistant"><div className="avatar">A</div><div><strong>ArchGuard</strong><div className="thinking"><i /><i /><i /> Reconstructing topology, checking risks and preparing recommendations…</div></div></article>}</div>{error && <div className="error-box">{error}</div>}<form className="composer compact" onSubmit={askArchGuard}><textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} placeholder="Ask a follow-up, change a stakeholder requirement, or run a scenario..." rows={2} /><div className="composer-footer"><button type="button" className="attach" onClick={() => setShowArtifacts((v) => !v)}>＋ Files / image {files.length > 0 && <b>{files.length}</b>}</button><span className="hint">Prompt required</span><button className="send" disabled={loading || !prompt.trim()}>Ask ArchGuard →</button></div></form></section>
        <section className="insight-panel sticky-insights"><div className="tabs"><button className={activeTab === "architecture" ? "active" : ""} onClick={() => setActiveTab("architecture")}>Blueprint</button><button className={activeTab === "risks" ? "active" : ""} onClick={() => setActiveTab("risks")}>Risks <b>{findings.length || ""}</b></button><button className={activeTab === "evidence" ? "active" : ""} onClick={() => setActiveTab("evidence")}>Evidence</button></div>{activeTab === "architecture" && <div className="tab-body"><div className="insight-heading"><div><span className="kicker">ARCHITECTURE VIEW</span><h2>{digitalTwin?.entities?.length ? "Interactive Digital Twin" : "Generated system blueprint"}</h2></div><span className="metric">{digitalTwin?.entities?.length || result?.context?.architecture?.services?.length || 0} detected</span></div><BlueprintPanel result={result} digitalTwin={digitalTwin} /></div>}{activeTab === "risks" && <div className="tab-body"><div className="insight-heading"><div><span className="kicker">RISK INTELLIGENCE</span><h2>Detected findings</h2></div>{waf?.overall_score != null && <span className="score">{Math.round(waf.overall_score)}<small>/100</small></span>}</div><div className="risk-list">{findings.length ? findings.map((finding, index) => <article className="risk-card" key={finding.id || index}><div className="risk-top"><span className={`severity ${String(finding.severity || "info").toLowerCase()}`}>{finding.severity || "INFO"}</span>{finding.risk_score != null && <span>Risk {finding.risk_score}</span>}</div><h3>{finding.title || finding.category || "Architecture finding"}</h3><p>{finding.description || finding.message}</p>{finding.recommendation && <div className="recommendation">↳ {finding.recommendation}</div>}</article>) : <div className="empty-state"><span>✓</span><h3>No deterministic risks returned</h3><p>Design guidance may still contain projected risks. Upload or provide an existing architecture to run deterministic REVIEW findings.</p></div>}</div></div>}{activeTab === "evidence" && <div className="tab-body"><div className="insight-heading"><div><span className="kicker">TRACEABILITY</span><h2>Input & reasoning context</h2></div></div><div className="evidence-grid"><div><span>Intent</span><strong>{intent}</strong></div><div><span>Architecture detected</span><strong>{result?.context?.architecture_detected ? "Yes" : "No"}</strong></div><div><span>Files processed</span><strong>{result?.context?.processed_files?.length || files.length}</strong></div><div><span>Gemini synthesis</span><strong>{result?.synthesis?.status || "—"}</strong></div></div><pre className="raw-context">{JSON.stringify(execution, null, 2)}</pre></div>}</section>
      </div>}
    </main>
    <footer><span>ArchGuard AI</span><span>Evidence-backed architecture engineering · Human approval before execution</span></footer>
  </div>;
}

export default App;
