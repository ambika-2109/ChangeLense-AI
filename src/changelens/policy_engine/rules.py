"""Explainable first-pass Terraform risk rules; no LLM-generated assertions."""

from __future__ import annotations

from hashlib import sha256

from changelens.schemas.report import Evidence, Finding, ResourceChange, Severity

_PUBLIC_VALUES = {"0.0.0.0/0", "::/0", "true"}


def _finding(
    change: ResourceChange,
    *,
    suffix: str,
    severity: Severity,
    risk_type: str,
    title: str,
    reasoning: str,
    test: str,
    uncertainty: str | None = None,
) -> Finding:
    attributes = ", ".join(change.changed_attributes) or "resource action"
    evidence = Evidence(
        evidence_id=f"{change.address}:{suffix}",
        source=change.evidence_ref,
        detail=(
            f"Terraform planned operation: {change.operation}; "
            f"attributes: {attributes}."
        ),
    )
    stable_id = sha256(f"{change.address}:{suffix}".encode()).hexdigest()[:10].upper()
    return Finding(
        finding_id=f"CL-{stable_id}",
        change_id=change.address,
        severity=severity,
        risk_type=risk_type,
        title=title,
        affected_resources=[change.address],
        evidence_refs=[change.evidence_ref],
        evidence=[evidence],
        reasoning=reasoning,
        uncertainties=[uncertainty] if uncertainty else [],
        recommended_test=test,
    )


def evaluate_policies(changes: list[ResourceChange]) -> list[Finding]:
    """Evaluate deterministic policy checks over normalized Terraform changes."""
    findings: list[Finding] = []
    for change in changes:
        if change.operation == "delete":
            findings.append(
                _finding(
                    change,
                    suffix="delete",
                    severity=Severity.CRITICAL,
                    risk_type="availability",
                    title="Resource deletion is planned",
                    reasoning=(
                        f"Terraform plans to delete {change.address}; "
                        "consumers may lose this dependency."
                    ),
                    test=(
                        "Confirm ownership and dependents, then exercise the affected "
                        "service in an isolated environment."
                    ),
                    uncertainty="Runtime consumers cannot be confirmed from the plan alone.",
                )
            )
        elif change.operation == "replace":
            findings.append(
                _finding(
                    change,
                    suffix="replace",
                    severity=Severity.HIGH,
                    risk_type="availability",
                    title="Resource replacement is planned",
                    reasoning=(
                        f"Terraform will destroy and recreate {change.address}, "
                        "which can cause interruption or data loss."
                    ),
                    test=(
                        "Run the replacement in a disposable environment and verify "
                        "service health and data continuity."
                    ),
                    uncertainty=(
                        "The plan does not establish whether the provider can replace "
                        "this resource without downtime."
                    ),
                )
            )

        for attribute, values in change.changed_attributes.items():
            old, new = values.get("before"), values.get("after")
            lowered = attribute.lower()
            if any(token in lowered for token in ("public", "public_access", "cidr", "ingress")):
                disables_public_block = (
                    "block_public" in lowered and str(new).lower() == "false"
                )
                explicitly_public = (
                    "block_public" not in lowered and str(new).lower() in _PUBLIC_VALUES
                )
                if disables_public_block or explicitly_public:
                    findings.append(
                        _finding(
                            change,
                            suffix="public-exposure",
                            severity=Severity.HIGH,
                            risk_type="security",
                            title="Potentially public network or storage access",
                            reasoning=(
                                f"The changed attribute {attribute} is set to {new}, "
                                "a value commonly associated with public exposure."
                            ),
                            test=(
                                "Inspect effective cloud policy and verify access from "
                                "an external network in a controlled environment."
                            ),
                            uncertainty=(
                                "Provider-specific semantics and surrounding security "
                                "controls are not evaluated by this rule."
                            ),
                        )
                    )
            if "encrypt" in lowered and new is False:
                findings.append(
                    _finding(
                        change,
                        suffix="encryption-disabled",
                        severity=Severity.HIGH,
                        risk_type="security",
                        title="Encryption appears to be disabled",
                        reasoning=(
                            f"The changed attribute {attribute} is false in the planned state."
                        ),
                        test=(
                            "Verify deployed encryption configuration and applicable "
                            "organizational policy."
                        ),
                        uncertainty=(
                            "The rule checks an explicitly false attribute and does not "
                            "infer provider defaults."
                        ),
                    )
                )
            connection_tokens = ("connection_limit", "max_connections", "connectionlimit")
            if any(token in lowered for token in connection_tokens):
                try:
                    decreased = float(new) < float(old)
                except (TypeError, ValueError):
                    decreased = False
                if decreased:
                    findings.append(
                        _finding(
                            change,
                            suffix="connection-limit-reduced",
                            severity=Severity.MEDIUM,
                            risk_type="availability",
                            title="Database connection limit is reduced",
                            reasoning=(
                                f"{attribute} decreases from {old} to {new}; saturation "
                                "may cause requests to queue or fail."
                            ),
                            test=(
                                "Run a representative concurrency test and monitor "
                                "connection saturation, latency, and errors."
                            ),
                            uncertainty=(
                                "Peak workload concurrency and connection-pool behavior "
                                "are not available in the plan."
                            ),
                        )
                    )
    return findings
