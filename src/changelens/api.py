"""FastAPI application for Terraform plan analysis."""

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from changelens.schemas.report import AnalysisReport
from changelens.service import analyze_plan

app = FastAPI(
    title="ChangeLens AI API",
    version="0.1.0",
    description=(
        "Deterministic Terraform plan analysis. "
        "No LLM or deployment actions are performed."
    ),
)
STATIC_DIR = Path(__file__).resolve().parent / "static"
FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "terraform_plans"
EXAMPLE_PLANS = {
    "delete_shared_database": "delete_shared_database.json",
    "reduce_connection_limit": "reduce_connection_limit.json",
    "public_access": "public_access.json",
    "disable_encryption": "disable_encryption.json",
    "replace_resource": "replace_resource.json",
    "tag_update": "tag_update.json",
    "upload_demo": "upload_demo.json",
}

app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/examples/{name}", include_in_schema=False)
def example_plan(name: str) -> dict[str, Any]:
    filename = EXAMPLE_PLANS.get(name)
    if filename is None:
        raise HTTPException(status_code=404, detail="Unknown demo plan.")
    try:
        with (FIXTURE_DIR / filename).open(encoding="utf-8") as fixture:
            return json.load(fixture)
    except OSError as exc:
        raise HTTPException(status_code=404, detail="Demo plan is unavailable.") from exc


@app.post("/analyze", response_model=AnalysisReport)
def analyze(payload: dict[str, Any]) -> AnalysisReport:
    try:
        return analyze_plan(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
