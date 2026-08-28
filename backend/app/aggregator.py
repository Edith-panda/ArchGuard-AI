from .models import Finding


def aggregate_findings(rule_findings, gemini_analysis):
    findings = []

    for finding in rule_findings:
        findings.append(
            Finding(
                source="RULE_ENGINE",
                severity=finding["severity"],
                category=finding["category"],
                component=finding["component"],
                issue=finding["issue"],
                explanation=finding["reason"],
                recommendation=finding["recommendation"],
            )
        )

    for finding in gemini_analysis.findings:
        findings.append(
            Finding(
                source="GEMINI",
                severity=finding.severity,
                category=finding.category,
                component=finding.component,
                issue=finding.issue,
                explanation=finding.explanation,
                recommendation=finding.recommendation,
            )
        )

    return findings