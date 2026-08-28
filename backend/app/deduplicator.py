def normalize_text(value):
    return (
        value.lower()
        .replace("-", " ")
        .replace("_", " ")
        .strip()
    )


def are_similar(finding_a, finding_b):
    same_component = (
        normalize_text(finding_a.component)
        == normalize_text(finding_b.component)
    )

    same_category = (
        normalize_text(finding_a.category)
        == normalize_text(finding_b.category)
    )

    if not same_component:
        return False

    issue_a = set(
        normalize_text(finding_a.issue).split()
    )

    issue_b = set(
        normalize_text(finding_b.issue).split()
    )

    if not issue_a or not issue_b:
        return False

    overlap = issue_a.intersection(issue_b)

    similarity = len(overlap) / min(
        len(issue_a),
        len(issue_b)
    )

    return same_category and similarity >= 0.5


def deduplicate_findings(findings):
    unique_findings = []

    for finding in findings:
        duplicate = False

        for existing in unique_findings:
            if are_similar(finding, existing):
                duplicate = True

                # Keep the higher-risk finding
                if finding.risk_score > existing.risk_score:
                    unique_findings.remove(existing)
                    unique_findings.append(finding)

                break

        if not duplicate:
            unique_findings.append(finding)

    return unique_findings