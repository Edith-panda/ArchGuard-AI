import { useEffect, useState } from "react";
import RemediationActions from "./RemediationActions";

const EVENT_NAME = "archguard:assistant-response";

export function installAssistantResponseBridge() {
  if (window.__archguardResponseBridgeInstalled) return;
  window.__archguardResponseBridgeInstalled = true;
  const originalFetch = window.fetch.bind(window);
  window.fetch = async (...args) => {
    const response = await originalFetch(...args);
    const url = typeof args[0] === "string" ? args[0] : args[0]?.url || "";
    if (url.includes("/assistant/input")) {
      response.clone().json().then((data) => {
        if (data?.execution?.result?.remediation_plan?.proposals?.length) {
          window.dispatchEvent(new CustomEvent(EVENT_NAME, { detail: data }));
        }
      }).catch(() => {});
    }
    return response;
  };
}

export default function RemediationDock() {
  const [result, setResult] = useState(null);
  const [open, setOpen] = useState(true);

  useEffect(() => {
    const handler = (event) => {
      setResult(event.detail);
      setOpen(true);
      requestAnimationFrame(() => window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" }));
    };
    window.addEventListener(EVENT_NAME, handler);
    return () => window.removeEventListener(EVENT_NAME, handler);
  }, []);

  if (!result) return null;
  const proposalKey = result?.execution?.result?.remediation_plan?.proposals?.[0]?.proposal_id || "remediation";

  return (
    <aside className={`remediation-dock ${open ? "open" : "collapsed"}`}>
      <button className="remediation-dock-toggle" onClick={() => setOpen((value) => !value)}>
        <span>SAFE REMEDIATION</span>
        <b>{open ? "Hide" : "Review approval"}</b>
      </button>
      {open && <div className="remediation-dock-body"><RemediationActions key={proposalKey} result={result} /></div>}
    </aside>
  );
}
