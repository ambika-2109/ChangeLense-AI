"""Parse Terraform show -json output into a safe normalized change model."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from changelens.schemas.report import ResourceChange


class TerraformPlan(BaseModel):
    """Minimal version-tolerant schema for Terraform plan JSON."""

    model_config = ConfigDict(extra="allow")

    format_version: str | None = None
    terraform_version: str | None = None
    resource_changes: list[dict[str, Any]] = Field(default_factory=list)


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    if isinstance(value, Mapping):
        output: dict[str, Any] = {}
        for key, nested in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            output.update(_flatten(nested, path))
        return output
    if isinstance(value, list):
        output = {}
        for index, nested in enumerate(value):
            path = f"{prefix}[{index}]" if prefix else f"[{index}]"
            output.update(_flatten(nested, path))
        return output
    return {prefix: value} if prefix else {}


def _display_path(value: Any, path: str) -> str:
    """Replace numeric indices with stable names for Terraform named blocks."""
    tokens = re.findall(r"([^.[\]]+)|\[(\d+)\]", path)
    current = value
    output = ""
    for name, index in tokens:
        if index:
            position = int(index)
            if isinstance(current, list) and position < len(current):
                item = current[position]
                label = item.get("name") if isinstance(item, Mapping) else None
                output += f"[name={label}]" if isinstance(label, str) else f"[{index}]"
                current = item
            else:
                output += f"[{index}]"
        else:
            output += f".{name}" if output else name
            current = current.get(name) if isinstance(current, Mapping) else None
    return output


def _marked(tree: Any, path: str) -> bool:
    """Check Terraform's nested sensitive/unknown marker tree for a leaf path."""
    current = tree
    for part in path.replace("]", "").replace("[", ".").split("."):
        if not part:
            continue
        if isinstance(current, Mapping):
            current = current.get(part, False)
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            return current is True
    return current is True


def _operation(actions: list[str]) -> str:
    action_set = set(actions)
    if action_set == {"no-op"}:
        return "no-op"
    if action_set == {"read"}:
        return "read"
    if "delete" in action_set and "create" in action_set:
        return "replace"
    if action_set == {"delete"}:
        return "delete"
    if action_set == {"create"}:
        return "create"
    if action_set == {"update"}:
        return "update"
    return "unknown"


def configuration_dependencies(configuration: Any) -> dict[str, list[str]]:
    dependencies: dict[str, list[str]] = {}

    def visit(module: Any) -> None:
        if not isinstance(module, Mapping):
            return
        for resource in module.get("resources", []):
            if not isinstance(resource, Mapping):
                continue
            address = resource.get("address")
            depends_on = resource.get("depends_on", [])
            if isinstance(address, str) and isinstance(depends_on, list):
                dependencies[address] = [item for item in depends_on if isinstance(item, str)]
        for child in module.get("module_calls", {}).values():
            if isinstance(child, Mapping):
                visit(child.get("module"))

    if isinstance(configuration, Mapping):
        visit(configuration.get("root_module"))
    return dependencies


def parse_plan(data: Mapping[str, Any]) -> tuple[TerraformPlan, list[ResourceChange]]:
    """Validate a plan and return normalized resource changes with JSON pointers.

    Sensitive values are never copied into the returned object. Unknown after-values
    are represented explicitly instead of being treated as known runtime values.
    """
    try:
        plan = TerraformPlan.model_validate(data)
    except ValidationError as exc:
        # Do not echo Pydantic's input_value details: malformed plan values may
        # contain secrets even when Terraform's sensitive markers are missing.
        raise ValueError(
            "Invalid Terraform plan: expected an object with valid resource_changes."
        ) from exc

    dependencies = configuration_dependencies(data.get("configuration", {}))
    changes: list[ResourceChange] = []
    for index, raw in enumerate(plan.resource_changes):
        address = raw.get("address")
        if not isinstance(address, str) or not address:
            raise ValueError(f"resource_changes[{index}] is missing a valid address")
        change = raw.get("change") or {}
        if not isinstance(change, Mapping):
            raise ValueError(f"resource_changes[{index}].change must be an object")
        actions = change.get("actions", [])
        if not isinstance(actions, list) or not all(isinstance(a, str) for a in actions):
            raise ValueError(f"resource_changes[{index}].change.actions must be a list of strings")

        before = _flatten(change.get("before"))
        after = _flatten(change.get("after"))
        sensitive_before = change.get("before_sensitive", {})
        sensitive_after = change.get("after_sensitive", {})
        unknown_after = change.get("after_unknown", {})
        attributes: dict[str, dict[str, Any]] = {}
        for path in sorted(before.keys() | after.keys()):
            old, new = before.get(path), after.get(path)
            is_unknown = _marked(unknown_after, path)
            if old == new and not is_unknown:
                continue
            if _marked(sensitive_before, path) or _marked(sensitive_after, path):
                old = new = "[REDACTED]"
            elif is_unknown:
                new = "[UNKNOWN_AFTER_APPLY]"
            display_path = _display_path(change.get("after") or change.get("before"), path)
            attributes[display_path] = {"before": old, "after": new}

        depends_on = raw.get("depends_on", dependencies.get(address, []))
        if not isinstance(depends_on, list) or not all(
            isinstance(item, str) for item in depends_on
        ):
            depends_on = []
        changes.append(
            ResourceChange(
                address=address,
                resource_type=str(raw.get("type") or address.split(".")[0]),
                actions=actions,
                operation=_operation(actions),
                changed_attributes=attributes,
                depends_on=depends_on,
                evidence_ref=f"plan.json#/resource_changes/{index}",
            )
        )
    return plan, changes
