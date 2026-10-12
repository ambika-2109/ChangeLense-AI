import json
from pathlib import Path

from changelens.service import analyze_plan

FIXTURES = Path(__file__).parents[2] / "fixtures" / "terraform_plans"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_public_access_block_change_is_flagged() -> None:
    report = analyze_plan(load_fixture("public_access.json"))
    assert [(finding.risk_type, finding.severity) for finding in report.findings] == [
        ("security", "high")
    ]


def test_explicit_encryption_disablement_is_flagged() -> None:
    report = analyze_plan(load_fixture("disable_encryption.json"))
    assert [(finding.risk_type, finding.severity) for finding in report.findings] == [
        ("security", "high")
    ]


def test_resource_replacement_is_flagged() -> None:
    report = analyze_plan(load_fixture("replace_resource.json"))
    assert [(finding.risk_type, finding.severity) for finding in report.findings] == [
        ("availability", "high")
    ]
