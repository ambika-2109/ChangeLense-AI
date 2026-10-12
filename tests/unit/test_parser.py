import json
from pathlib import Path

import pytest

from changelens.terraform_parser.parser import parse_plan

FIXTURES = Path(__file__).parents[2] / "fixtures" / "terraform_plans"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_parses_tag_update_and_changed_attribute() -> None:
    plan, changes = parse_plan(load_fixture("tag_update.json"))
    assert plan.format_version == "1.2"
    assert changes[0].operation == "update"
    assert changes[0].changed_attributes["tags.Owner"] == {"before": None, "after": "platform"}


def test_parses_delete_and_replace_actions() -> None:
    _, changes = parse_plan(load_fixture("delete_shared_database.json"))
    assert changes[0].operation == "delete"
    plan = {
        "resource_changes": [
            {"address": "aws_db_instance.main", "change": {"actions": ["create", "delete"]}}
        ]
    }
    assert parse_plan(plan)[1][0].operation == "replace"


def test_redacts_sensitive_values() -> None:
    plan = {
        "resource_changes": [{
            "address": "aws_db_instance.main",
            "change": {
                "actions": ["update"],
                "before": {"password": "old-secret"},
                "after": {"password": "new-secret"},
                "before_sensitive": {"password": True},
                "after_sensitive": {"password": True},
            },
        }]
    }
    _, changes = parse_plan(plan)
    assert changes[0].changed_attributes["password"] == {
        "before": "[REDACTED]",
        "after": "[REDACTED]",
    }
    assert "new-secret" not in str(changes)


def test_rejects_resource_without_address() -> None:
    with pytest.raises(ValueError, match="valid address"):
        parse_plan({"resource_changes": [{"change": {"actions": ["delete"]}}]})


def test_invalid_plan_error_does_not_echo_input_values() -> None:
    secret = "sensitive-value-must-not-appear"
    with pytest.raises(ValueError) as error:
        parse_plan({"resource_changes": secret})
    assert secret not in str(error.value)
