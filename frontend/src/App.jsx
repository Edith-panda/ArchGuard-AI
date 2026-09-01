import { useState } from "react";
import ArchitectureGraph from "./components/ArchitectureGraph";
import FileDropZone from "./components/FileDropZone";
import "./App.css";

const API_BASE = "http://127.0.0.1:8000";

const SUGGESTIONS = [
  "Design an e-commerce platform for 10M users",
  "Review my architecture and find the biggest risks",
  "What happens if the database goes down?",
  "Stakeholders expect 20x traffic. What should change?",
];

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
    if (!question) {
      setError("Ask ArchGuard a question or describe what you want to build.");
      return;
    }

    setLoading(true);
    setError("");
    setMessages((current) => [...current, { role: "user", text: question }]);

    try {
      const formData = new FormData();
      formData.append("prompt", question);
      files.forEach((file) => formData.append("files", file));
      if (manualInput.trim()) formData.append("manual_input", manualInput.trim());

      const response = await fetch(`${API_BASE}/assistant/input`, {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(typeof data.detail === "string" ? data.detail : "ArchGuard could not process the request.");
      }

      setResult(data);
      setMessages((current) => [
        ...current,
        { role: "assistant", text: data.answer || "Analysis completed. Explore the architecture and evidence panel." },
      ]);
      setPrompt("");
    } catch (err) {
      setError(err.message || "Something went wrong while contacting ArchGuard.");
    } finally {
      setLoading(false);
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
  }

  return (
    <div className="app-shell">
      <nav className="topbar">
        <button className="brand" onClick={resetWorkspace}>
          <span className="brand-mark">A</span>
          <span><strong>ArchGuard</strong><small>AI Architecture Engineer</small></span>
        </button>
        <div className="top-actions">
          <span className="status"><i /> System ready</span>
          <button className="ghost" onClick={resetWorkspace}>New session</button>
        </div>
      </nav>

      <main className={messages.length ? "workspace has-chat" : "workspace"}>
        {!messages.length && (
          <section className="welcome">
            <div className="glow glow-one" />
            <div className="glow glow-two" />
            <span className="kicker">DESIGN · REVIEW · SIMULATE · EVOLVE</span>
            <h1>Build systems that are ready<br />for the <span>real world.</span></h1>
            <p>Describe an idea, attach architecture artifacts, or ask a what-if question. ArchGuard turns engineering context into evidence-backed architecture guidance.</p>

            <form className="composer hero-composer" onSubmit={askArchGuard}>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    askArchGuard(e);
                  }
                }}
                placeholder="Ask ArchGuard anything about your system..."
                rows={3}
              />
              <div className="composer-footer">
                <button type="button" className="attach" onClick={() => setShowArtifacts((v) => !v)}>
                  ＋ Attach context {files.length > 0 && <b>{files.length}</b>}
                </button>
                <span className="hint">Enter to send · Shift + Enter for new line</span>
                <button className="send" disabled={loading || !prompt.trim()}>{loading ? "Thinking…" : "Ask ArchGuard →"}</button>
              </div>
            </form>

            <div className="suggestions">
              {SUGGESTIONS.map((item) => (
                <button key={item} onClick={() => setPrompt(item)}>{item}<span>↗</span></button>
              ))}
            </div>
          </section>
        )}

        {showArtifacts && (
          <section className="artifact-drawer">
            <div className="drawer-head"><div><span className="kicker">OPTIONAL CONTEXT</span><h2>Give ArchGuard more evidence</h2></div><button className="close" onClick={() => setShowArtifacts(false)}>×</button></div>
            <FileDropZone files={files} setFiles={setFiles} />
            <label className="manual-label">Or paste architecture, requirements, logs, or notes</label>
            <textarea className="manual-area" value={manualInput} onChange={(e) => setManualInput(e.target.value)} placeholder="Paste JSON, YAML, architecture notes, stakeholder requirements..." />
          </section>
        )}

        {messages.length > 0 && (
          <div className="product-grid">
            <section className="conversation-panel">
              <div className="panel-title"><div><span className="kicker">ARCHITECTURE COPILOT</span><h2>Engineering conversation</h2></div><span className={`intent intent-${intent}`}>{intent}</span></div>
              <div className="messages">
                {messages.map((message, index) => (
                  <article className={`message ${message.role}`} key={`${message.role}-${index}`}>
                    <div className="avatar">{message.role === "user" ? "Y" : "A"}</div>
                    <div><strong>{message.role === "user" ? "You" : "ArchGuard"}</strong><div className="message-text">{message.text}</div></div>
                  </article>
                ))}
                {loading && <article className="message assistant"><div className="avatar">A</div><div><strong>ArchGuard</strong><div className="thinking"><i /><i /><i /> Analyzing architecture and evidence…</div></div></article>}
              </div>

              {error && <div className="error-box">{error}</div>}

              <form className="composer compact" onSubmit={askArchGuard}>
                <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} placeholder="Ask a follow-up, change a requirement, or run a scenario..." rows={2} />
                <div className="composer-footer">
                  <button type="button" className="attach" onClick={() => setShowArtifacts((v) => !v)}>＋ Context {files.length > 0 && <b>{files.length}</b>}</button>
                  <button className="send" disabled={loading || !prompt.trim()}>Send →</button>
                </div>
              </form>
            </section>

            <section className="insight-panel">
              <div className="tabs">
                <button className={activeTab === "architecture" ? "active" : ""} onClick={() => setActiveTab("architecture")}>Architecture</button>
                <button className={activeTab === "risks" ? "active" : ""} onClick={() => setActiveTab("risks")}>Risks <b>{findings.length || ""}</b></button>
                <button className={activeTab === "evidence" ? "active" : ""} onClick={() => setActiveTab("evidence")}>Evidence</button>
              </div>

              {activeTab === "architecture" && (
                <div className="tab-body">
                  <div className="insight-heading"><div><span className="kicker">DIGITAL TWIN</span><h2>System topology</h2></div><span className="metric">{digitalTwin?.entities?.length || 0} components</span></div>
                  {digitalTwin?.entities?.length ? <ArchitectureGraph digitalTwin={digitalTwin} /> : <div className="empty-state"><span>◇</span><h3>No architecture yet</h3><p>Attach artifacts or ask ArchGuard to review an existing system. Design-mode structured graph generation is a follow-up capability.</p></div>}
                </div>
              )}

              {activeTab === "risks" && (
                <div className="tab-body">
                  <div className="insight-heading"><div><span className="kicker">RISK INTELLIGENCE</span><h2>Detected findings</h2></div>{waf?.overall_score != null && <span className="score">{Math.round(waf.overall_score)}<small>/100</small></span>}</div>
                  <div className="risk-list">
                    {findings.length ? findings.map((finding, index) => (
                      <article className="risk-card" key={finding.id || index}>
                        <div className="risk-top"><span className={`severity ${String(finding.severity || "info").toLowerCase()}`}>{finding.severity || "INFO"}</span>{finding.risk_score != null && <span>Risk {finding.risk_score}</span>}</div>
                        <h3>{finding.title || finding.category || "Architecture finding"}</h3>
                        <p>{finding.description || finding.message}</p>
                        {finding.recommendation && <div className="recommendation">↳ {finding.recommendation}</div>}
                      </article>
                    )) : <div className="empty-state"><span>✓</span><h3>No structured risks returned</h3><p>Run a REVIEW request with architecture context to populate deterministic findings.</p></div>}
                  </div>
                </div>
              )}

              {activeTab === "evidence" && (
                <div className="tab-body">
                  <div className="insight-heading"><div><span className="kicker">TRACEABILITY</span><h2>Input & reasoning context</h2></div></div>
                  <div className="evidence-grid">
                    <div><span>Intent</span><strong>{intent}</strong></div>
                    <div><span>Architecture detected</span><strong>{result?.context?.architecture_detected ? "Yes" : "No"}</strong></div>
                    <div><span>Files processed</span><strong>{result?.context?.processed_files?.length || files.length}</strong></div>
                    <div><span>Gemini synthesis</span><strong>{result?.synthesis?.status || "—"}</strong></div>
                  </div>
                  <pre className="raw-context">{JSON.stringify(execution, null, 2)}</pre>
                </div>
              )}
            </section>
          </div>
        )}
      </main>

      <footer><span>ArchGuard AI</span><span>Evidence-backed architecture engineering · Human approval before execution</span></footer>
    </div>
  );
}

export default App;
