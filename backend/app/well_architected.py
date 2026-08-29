from collections import defaultdict
from typing import Any


# =========================================================
# Google Well-Architected Pillars
# =========================================================

PILLARS = {
    "operational_excellence": {
        "name": "Operational Excellence",
        "description": (
            "Ability to efficiently deploy, operate, monitor, "
            "and improve workloads."
        ),
    },

    "security": {
        "name": "Security",
        "description": (
            "Protection of systems, data, identities, "
            "and infrastructure."
        ),
    },

    "reliability": {
        "name": "Reliability",
        "description": (
            "Ability of a workload to perform its intended "
            "function consistently and recover from failures."
        ),
    },

    "cost_optimization": {
        "name": "Cost Optimization",
        "description": (
            "Ability to deliver business value while "
            "minimizing unnecessary resource cost."
        ),
    },

    "performance_optimization": {
        "name": "Performance Optimization",
        "description": (
            "Ability to use resources efficiently while "
            "meeting performance requirements."
        ),
    },

    "sustainability": {
        "name": "Sustainability",
        "description": (
            "Ability to minimize environmental impact "
            "through efficient resource utilization."
        ),
    },
}


# =========================================================
# Severity penalties
# =========================================================

SEVERITY_PENALTIES = {
    "critical": 30,
    "high": 20,
    "medium": 10,
    "low": 5,
    "info": 0,
}


# =========================================================
# Category -> Well-Architected Pillar mapping
# =========================================================

CATEGORY_TO_PILLARS = {

    # Reliability
    "reliability": [
        "reliability"
    ],

    "availability": [
        "reliability"
    ],

    "resilience": [
        "reliability"
    ],

    "fault tolerance": [
        "reliability"
    ],

    "single point of failure": [
        "reliability"
    ],

    # Security
    "security": [
        "security"
    ],

    "authentication": [
        "security"
    ],

    "authorization": [
        "security"
    ],

    "encryption": [
        "security"
    ],

    "secrets": [
        "security"
    ],

    # Performance
    "performance": [
        "performance_optimization"
    ],

    "scalability": [
        "performance_optimization",
        "reliability",
    ],

    "latency": [
        "performance_optimization"
    ],

    "database performance": [
        "performance_optimization"
    ],

    # Cost
    "cost": [
        "cost_optimization"
    ],

    "resource utilization": [
        "cost_optimization",
        "sustainability",
    ],

    # Operations
    "operations": [
        "operational_excellence"
    ],

    "observability": [
        "operational_excellence"
    ],

    "monitoring": [
        "operational_excellence"
    ],

    "deployment": [
        "operational_excellence"
    ],

    # Sustainability
    "sustainability": [
        "sustainability"
    ],
}


# =========================================================
# Finding text fallback mapping
# =========================================================

KEYWORD_RULES = {

    "security": [
        "authentication",
        "authorization",
        "secret",
        "credential",
        "encryption",
        "unencrypted",
        "public access",
        "rbac",
        "iam",
        "token",
    ],

    "reliability": [
        "single point of failure",
        "spof",
        "failure",
        "failover",
        "replica",
        "availability",
        "cascading",
        "dependency",
        "circuit breaker",
        "retry",
    ],

    "performance_optimization": [
        "latency",
        "bottleneck",
        "performance",
        "high fan-in",
        "throughput",
        "slow",
        "scalability",
        "traffic",
        "load",
    ],

    "cost_optimization": [
        "cost",
        "overprovision",
        "underutilized",
        "idle resource",
        "expensive",
    ],

    "operational_excellence": [
        "monitoring",
        "logging",
        "observability",
        "deployment",
        "alerting",
        "runbook",
    ],

    "sustainability": [
        "sustainability",
        "energy",
        "resource utilization",
        "unused resource",
    ],
}


# =========================================================
# Helpers
# =========================================================

def normalize_text(
    value: Any,
) -> str:

    if value is None:
        return ""

    return str(
        value
    ).strip().lower()


def normalize_severity(
    severity: Any,
) -> str:

    value = normalize_text(
        severity
    )

    aliases = {
        "crit": "critical",
        "severe": "critical",
        "warning": "medium",
        "moderate": "medium",
        "minor": "low",
    }

    value = aliases.get(
        value,
        value,
    )

    if value not in SEVERITY_PENALTIES:
        return "medium"

    return value


# =========================================================
# Extract useful text from a finding
# =========================================================

def finding_text(
    finding: dict[str, Any],
) -> str:

    fields = [
        finding.get("title"),
        finding.get("description"),
        finding.get("message"),
        finding.get("reason"),
        finding.get("recommendation"),
        finding.get("category"),
    ]

    return " ".join(
        normalize_text(
            field
        )
        for field in fields
        if field
    )


# =========================================================
# Determine affected pillars
# =========================================================

def map_finding_to_pillars(
    finding: dict[str, Any],
) -> list[str]:

    pillars = set()

    category = normalize_text(
        finding.get(
            "category"
        )
    )

    # -----------------------------------------------------
    # Explicit category mapping
    # -----------------------------------------------------

    for (
        category_name,
        mapped_pillars,
    ) in CATEGORY_TO_PILLARS.items():

        if (
            category_name
            in category
        ):

            pillars.update(
                mapped_pillars
            )


    # -----------------------------------------------------
    # Text fallback
    # -----------------------------------------------------

    text = finding_text(
        finding
    )

    for (
        pillar,
        keywords,
    ) in KEYWORD_RULES.items():

        for keyword in keywords:

            if keyword in text:

                pillars.add(
                    pillar
                )

                break


    # -----------------------------------------------------
    # Safe fallback
    # -----------------------------------------------------

    if not pillars:

        pillars.add(
            "operational_excellence"
        )

    return sorted(
        pillars
    )


# =========================================================
# Confidence-aware penalty
# =========================================================

def calculate_penalty(
    finding: dict[str, Any],
) -> float:

    severity = (
        normalize_severity(
            finding.get(
                "severity"
            )
        )
    )

    base_penalty = (
        SEVERITY_PENALTIES[
            severity
        ]
    )

    confidence = finding.get(
        "confidence",
        1.0,
    )

    try:

        confidence = float(
            confidence
        )

    except (
        TypeError,
        ValueError,
    ):

        confidence = 1.0

    confidence = max(
        0.0,
        min(
            confidence,
            1.0,
        ),
    )

    return round(
        base_penalty
        * confidence,
        2,
    )


# =========================================================
# Score label
# =========================================================

def score_label(
    score: float,
) -> str:

    if score >= 90:
        return "Excellent"

    if score >= 75:
        return "Good"

    if score >= 60:
        return "Needs Attention"

    if score >= 40:
        return "High Risk"

    return "Critical"


# =========================================================
# Main scoring function
# =========================================================

def score_well_architected(
    findings: list[
        dict[str, Any]
    ],
) -> dict[str, Any]:

    pillar_penalties = defaultdict(
        float
    )

    pillar_findings = defaultdict(
        list
    )


    # -----------------------------------------------------
    # Process findings
    # -----------------------------------------------------

    enriched_findings = []

    for finding in findings:

        pillars = (
            map_finding_to_pillars(
                finding
            )
        )

        penalty = (
            calculate_penalty(
                finding
            )
        )

        # Divide the penalty across multiple pillars.
        #
        # Example:
        # Scalability issue affects both
        # performance and reliability.

        penalty_per_pillar = (
            penalty
            /
            max(
                len(pillars),
                1,
            )
        )


        for pillar in pillars:

            pillar_penalties[
                pillar
            ] += (
                penalty_per_pillar
            )

            pillar_findings[
                pillar
            ].append(
                finding
            )


        enriched = {
            **finding,

            "well_architected_pillars":
                pillars,

            "well_architected_penalty":
                penalty,
        }

        enriched_findings.append(
            enriched
        )


    # -----------------------------------------------------
    # Build pillar scores
    # -----------------------------------------------------

    pillar_scores = {}

    for (
        pillar_id,
        pillar_definition,
    ) in PILLARS.items():

        penalty = (
            pillar_penalties.get(
                pillar_id,
                0.0,
            )
        )

        score = max(
            0.0,
            100.0 - penalty,
        )

        score = round(
            score,
            1,
        )

        related_findings = (
            pillar_findings.get(
                pillar_id,
                []
            )
        )


        severity_counts = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0,
        }


        for finding in (
            related_findings
        ):

            severity = (
                normalize_severity(
                    finding.get(
                        "severity"
                    )
                )
            )

            severity_counts[
                severity
            ] += 1


        pillar_scores[
            pillar_id
        ] = {
            "name":
                pillar_definition[
                    "name"
                ],

            "description":
                pillar_definition[
                    "description"
                ],

            "score":
                score,

            "rating":
                score_label(
                    score
                ),

            "finding_count":
                len(
                    related_findings
                ),

            "severity_counts":
                severity_counts,
        }


    # -----------------------------------------------------
    # Overall score
    # -----------------------------------------------------

    scores = [
        pillar[
            "score"
        ]
        for pillar
        in pillar_scores.values()
    ]

    overall_score = (
        round(
            sum(scores)
            /
            len(scores),
            1,
        )
        if scores
        else 100.0
    )


    # -----------------------------------------------------
    # Lowest scoring pillars
    # -----------------------------------------------------

    weakest_pillars = sorted(
        [
            {
                "pillar":
                    pillar[
                        "name"
                    ],

                "score":
                    pillar[
                        "score"
                    ],
            }

            for pillar
            in pillar_scores.values()
        ],

        key=lambda item:
            item["score"],
    )[:3]


    # -----------------------------------------------------
    # Return report
    # -----------------------------------------------------

    return {
        "framework":
            "Google Cloud Well-Architected Framework",

        "overall_score":
            overall_score,

        "overall_rating":
            score_label(
                overall_score
            ),

        "pillar_scores":
            pillar_scores,

        "weakest_pillars":
            weakest_pillars,

        "findings":
            enriched_findings,

        "scoring_note": (
            "ArchGuard scores are heuristic "
            "architecture-health indicators, "
            "not official Google Cloud "
            "certification scores."
        ),
    }