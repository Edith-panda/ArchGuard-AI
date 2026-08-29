from typing import Any


def database_diff(
    component: str,
) -> dict[str, Any]:

    return {
        "format":
            "terraform",

        "filename":
            "proposed-database-change.tf",

        "component":
            component,

        "diff":
"""
resource "google_sql_database_instance" "primary" {
  name = "archguard-primary"

+ availability_type = "REGIONAL"

+ backup_configuration {
+   enabled = true
+ }

+ deletion_protection = true
}
""".strip(),

        "note":
            (
                "Illustrative proposed Terraform "
                "change. ArchGuard has not applied "
                "this configuration."
            ),
    }


def dependency_diff(
    component: str,
) -> dict[str, Any]:

    return {
        "format":
            "yaml",

        "filename":
            "proposed-resilience-policy.yaml",

        "component":
            component,

        "diff":
"""
resilience:
  target: payment-service

+ timeout: 3s
+ retries:
+   maxAttempts: 3
+   backoff: exponential
+ circuitBreaker:
+   enabled: true
+ fallback:
+   enabled: true
""".strip(),

        "note":
            (
                "Illustrative resilience configuration. "
                "No service configuration has been modified."
            ),
    }


def scalability_diff(
    component: str,
) -> dict[str, Any]:

    return {
        "format":
            "kubernetes",

        "filename":
            "proposed-autoscaling.yaml",

        "component":
            component,

        "diff":
"""
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: proposed-autoscaler

spec:
  minReplicas: 2

+ maxReplicas: 10

+ metrics:
+   - type: Resource
+     resource:
+       name: cpu
+       target:
+         type: Utilization
+         averageUtilization: 70
""".strip(),

        "note":
            (
                "Illustrative Kubernetes autoscaling "
                "proposal. It has not been deployed."
            ),
    }


def security_diff(
    component: str,
) -> dict[str, Any]:

    return {
        "format":
            "policy",

        "filename":
            "proposed-security-policy.yaml",

        "component":
            component,

        "diff":
"""
security:
  component: service

+ authentication:
+   required: true

+ authorization:
+   leastPrivilege: true

+ secrets:
+   externalSecretManager: true
""".strip(),

        "note":
            (
                "Illustrative security policy proposal. "
                "No IAM or secret configuration has changed."
            ),
    }


def generic_diff(
    component: str,
) -> dict[str, Any]:

    return {
        "format":
            "architecture",

        "filename":
            "proposed-architecture-change.txt",

        "component":
            component,

        "diff":
            (
                f"- Current architecture for {component}\n"
                f"+ Apply recommended architecture improvement\n"
                f"+ Re-run analysis after change"
            ),

        "note":
            (
                "Generic architecture proposal only. "
                "No source code or infrastructure was modified."
            ),
    }


def generate_proposed_diff(
    proposal: dict[str, Any],
) -> dict[str, Any]:

    strategy = proposal.get(
        "strategy",
        ""
    )

    component = (
        proposal.get(
            "change_scope"
        )
        or proposal
        .get(
            "finding",
            {}
        )
        .get(
            "component",
            "architecture",
        )
    )

    if (
        strategy
        ==
        "increase_database_resilience"
    ):
        return database_diff(
            component
        )

    if (
        strategy
        ==
        "isolate_service_dependency"
    ):
        return dependency_diff(
            component
        )

    if (
        strategy
        ==
        "improve_scalability"
    ):
        return scalability_diff(
            component
        )

    if (
        strategy
        ==
        "strengthen_security_controls"
    ):
        return security_diff(
            component
        )

    return generic_diff(
        component
    )