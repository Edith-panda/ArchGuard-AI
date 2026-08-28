from .models import Finding


SEVERITY_SCORES = {
    "HIGH": 80,
    "MEDIUM": 50,
    "LOW": 20,
}


CATEGORY_BONUS = {
    "Security": 10,
    "Reliability": 10,
    "Scalability": 5,
    "Performance": 5,
}


def calculate_risk_score(finding: Finding) -> int:
    severity_score = SEVERITY_SCORES.get(
        finding.severity.upper(),
        0
    )

    category_bonus = CATEGORY_BONUS.get(
        finding.category,
        0
    )

    score = severity_score + category_bonus

    return min(score, 100)


def assign_risk_scores(findings):
    scored_findings = []

    for finding in findings:
        finding.risk_score = calculate_risk_score(finding)
        scored_findings.append(finding)

    return scored_findings