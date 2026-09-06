const STAGES = {
  design: ["Understanding requirements", "Designing system boundaries", "Selecting technologies", "Evaluating scalability", "Checking failure scenarios", "Preparing recommendations"],
  review: ["Reading architecture context", "Resolving components", "Building the digital twin", "Running risk analysis", "Evaluating architecture quality", "Preparing recommendations"],
  simulate: ["Loading architecture context", "Identifying failure target", "Tracing dependencies", "Calculating blast radius", "Evaluating cascading effects", "Preparing mitigations"],
  modify: ["Loading current architecture", "Understanding the new requirement", "Calculating impacted components", "Designing the target state", "Evaluating migration risks", "Preparing the change plan"],
  remediate: ["Loading prioritized risks", "Explaining root causes", "Designing remediation options", "Preparing safe changes", "Checking approval boundaries", "Preparing verification steps"],
  question: ["Loading architecture context", "Understanding the question", "Grounding the answer", "Preparing engineering guidance"],
};

function inferIntent(prompt = "") {
  const text = prompt.toLowerCase();
  if (/(remediat|fix the|fix this|highest-risk|highest risk)/.test(text)) return "remediate";
  if (/(modify|change|new requirement|stakeholders now|evolve|multi-region)/.test(text)) return "modify";
  if (/(simulate|what if|what happens|blast radius|outage|goes down|failed)/.test(text)) return "simulate";
  if (/(review|analy[sz]e|bottleneck|risk|spof)/.test(text)) return "review";
  if (/(design|architecture for|tech stack|technology stack)/.test(text)) return "design";
  return "question";
}

export default function AnalysisProgress({ prompt }) {
  const intent = inferIntent(prompt);
  const stages = STAGES[intent] || STAGES.question;
  return (
    <section className="analysis-progress" aria-live="polite">
      <div className="analysis-progress-head">
        <div>
          <span className="kicker">ARCHGUARD ANALYSIS</span>
          <h3>{intent === "simulate" ? "Tracing system impact" : intent === "modify" ? "Evolving the architecture" : intent === "remediate" ? "Preparing a safe remediation plan" : "Analyzing your system"}</h3>
          <p>ArchGuard is working through the engineering pipeline. Result panels stay hidden until grounded data is available.</p>
        </div>
        <span className={`intent intent-${intent}`}>{intent}</span>
      </div>
      <div className="analysis-stage-list">
        {stages.map((stage, index) => (
          <div className={`analysis-stage ${index === 0 ? "active" : "waiting"}`} key={stage}>
            <span className="analysis-stage-icon">{index === 0 ? "●" : "○"}</span>
            <div><strong>{stage}</strong><small>{index === 0 ? "In progress" : "Queued"}</small></div>
          </div>
        ))}
      </div>
    </section>
  );
}
