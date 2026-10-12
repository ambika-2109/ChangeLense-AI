"""Analysis orchestration for the deterministic MVP."""

from collections.abc import Mapping
from typing import Any

from changelens.dependency_graph.impact import build_graph, downstream_impact
from changelens.policy_engine.rules import evaluate_policies
from changelens.schemas.report import AnalysisReport
from changelens.terraform_parser.parser import configuration_dependencies, parse_plan


def analyze_plan(data: Mapping[str, Any]) -> AnalysisReport:
    plan, changes = parse_plan(data)
    graph = build_graph(changes, configuration_dependencies(data.get("configuration", {})))
    roots = [change.address for change in changes if change.operation not in {"no-op", "read"}]
    affected = downstream_impact(graph, roots)
    findings = evaluate_policies(changes)
    for finding in findings:
        finding.affected_resources = downstream_impact(graph, [finding.change_id])
    warnings: list[str] = []
    if roots and graph.number_of_edges() == 0:
        warnings.append(
            "No dependency edges were available; blast-radius results may be incomplete."
        )
    return AnalysisReport(
        plan_format_version=plan.format_version,
        terraform_version=plan.terraform_version,
        changes=changes,
        findings=findings,
        affected_resources=affected,
        warnings=warnings,
    )
