from .models import Finding
from .analyzer import analyze_architecture


SEVERITY_SCORES = {
    "CRITICAL": 95,
    "HIGH": 80,
    "MEDIUM": 50,
    "LOW": 20,
    "INFO": 0,
}

CATEGORY_BONUS = {
    "Security": 10,
    "Reliability": 10,
    "Scalability": 5,
    "Performance": 5,
}


def calculate_risk_score(finding) -> int:
    if isinstance(finding, dict):
        severity = str(finding.get("severity", "")).upper()
        category = finding.get("category", "")
    else:
        severity = str(finding.severity).upper()
        category = finding.category

    score = SEVERITY_SCORES.get(severity, 0) + CATEGORY_BONUS.get(category, 0)
    return min(score, 100)


def assign_risk_scores(findings):
    scored_findings = []

    for finding in findings:
        score = calculate_risk_score(finding)
        if isinstance(finding, dict):
            finding = dict(finding)
            finding["risk_score"] = score
        else:
            finding.risk_score = score
        scored_findings.append(finding)

    return scored_findings


def analyze_risks(architecture, graph=None):
    """Run deterministic architecture rules and attach risk scores.

    ``graph`` is accepted for the conversational executor API. The current
    deterministic rule set operates on the canonical architecture itself;
    graph-specific findings remain handled by graph_risk_engine.
    """
    return assign_risk_scores(analyze_architecture(architecture))
