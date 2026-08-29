from typing import Any, Dict, List


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def calculate_risk_summary(findings: List[Dict]) -> Dict:
    if not findings:
        return {
            "finding_count": 0,
            "total_risk": 0,
            "average_risk": 0,
            "maximum_risk": 0,
            "high_or_critical": 0,
        }

    scores = [
        _number(finding.get("risk_score", 0))
        for finding in findings
    ]

    severe = sum(
        1
        for finding in findings
        if str(
            finding.get("severity", "")
        ).lower()
        in {"high", "critical"}
    )

    return {
        "finding_count": len(findings),
        "total_risk": round(sum(scores), 2),
        "average_risk": round(
            sum(scores) / len(scores),
            2,
        ),
        "maximum_risk": round(max(scores), 2),
        "high_or_critical": severe,
    }


def compare_well_architected(
    before: Dict,
    after: Dict,
) -> Dict:

    before_score = _number(
        before.get("overall_score", 0)
    )

    after_score = _number(
        after.get("overall_score", 0)
    )

    return {
        "before": before_score,
        "after": after_score,
        "change": round(
            after_score - before_score,
            2,
        ),
    }


def verify_remediation(
    before_findings: List[Dict],
    after_findings: List[Dict],
    before_well_architected: Dict = None,
    after_well_architected: Dict = None,
) -> Dict:

    before_summary = calculate_risk_summary(
        before_findings
    )

    after_summary = calculate_risk_summary(
        after_findings
    )

    risk_reduction = round(
        before_summary["total_risk"]
        - after_summary["total_risk"],
        2,
    )

    severe_reduction = (
        before_summary["high_or_critical"]
        - after_summary["high_or_critical"]
    )

    wa_comparison = compare_well_architected(
        before_well_architected or {},
        after_well_architected or {},
    )

    improved = (
        risk_reduction > 0
        or severe_reduction > 0
        or wa_comparison["change"] > 0
    )

    if improved:
        status = "improved"
    elif (
        risk_reduction == 0
        and severe_reduction == 0
        and wa_comparison["change"] == 0
    ):
        status = "unchanged"
    else:
        status = "regressed"

    return {
        "status": status,
        "improved": improved,

        "before": before_summary,
        "after": after_summary,

        "risk_reduction": risk_reduction,
        "high_or_critical_reduction":
            severe_reduction,

        "well_architected":
            wa_comparison,

        "verification_message": (
            "The proposed remediation improved "
            "the architecture."
            if status == "improved"
            else
            "The proposed remediation did not "
            "demonstrate a measurable improvement."
            if status == "unchanged"
            else
            "The proposed remediation appears "
            "to have increased architecture risk."
        ),
    }