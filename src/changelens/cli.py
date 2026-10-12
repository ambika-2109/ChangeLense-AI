"""Command-line interface for analyzing a saved Terraform plan JSON file."""

import argparse
import json
from pathlib import Path

from changelens.service import analyze_plan


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze Terraform plan JSON with ChangeLens.")
    parser.add_argument("plan", type=Path, help="Path to `terraform show -json` output")
    args = parser.parse_args()
    try:
        with args.plan.open(encoding="utf-8") as plan_file:
            plan = json.load(plan_file)
        report = analyze_plan(plan)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))
    print(report.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
