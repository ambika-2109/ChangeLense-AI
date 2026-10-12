"""Stable, provider-independent analysis report models."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ResourceChange(BaseModel):
    """A normalized Terraform resource change; values may be redacted."""

    address: str
    resource_type: str
    actions: list[str]
    operation: str
    changed_attributes: dict[str, dict[str, Any]] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    evidence_ref: str


class Evidence(BaseModel):
    evidence_id: str
    source: str
    detail: str


class Finding(BaseModel):
    finding_id: str
    change_id: str
    severity: Severity
    risk_type: str
    title: str
    affected_resources: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    reasoning: str
    uncertainties: list[str] = Field(default_factory=list)
    recommended_test: str


class AnalysisReport(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    plan_format_version: str | None = None
    terraform_version: str | None = None
    changes: list[ResourceChange] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    affected_resources: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
