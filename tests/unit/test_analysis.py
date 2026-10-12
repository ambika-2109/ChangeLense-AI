import json
from pathlib import Path

from changelens.schemas.report import Severity
from changelens.service import analyze_plan

FIXTURES = Path(__file__).parents[2] / "fixtures" / "terraform_plans"


def analyze(name: str):
    plan = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    return analyze_plan(plan)


def test_tag_update_is_low_risk_with_no_findings() -> None:
    report = analyze("tag_update.json")
    assert report.findings == []
    assert report.affected_resources == ["aws_s3_bucket.assets"]


def test_database_delete_expands_transitive_blast_radius() -> None:
    report = analyze("delete_shared_database.json")
    assert len(report.findings) == 1
    assert report.findings[0].severity == Severity.CRITICAL
    assert report.affected_resources == [
        "aws_cloudwatch_alarm.checkout",
        "aws_db_instance.shared",
        "aws_ecs_service.checkout",
    ]
    assert report.warnings == []


def test_connection_limit_reduction_is_flagged() -> None:
    report = analyze("reduce_connection_limit.json")
    assert any(finding.risk_type == "availability" for finding in report.findings)
    assert "workload concurrency" in report.findings[0].uncertainties[0]
