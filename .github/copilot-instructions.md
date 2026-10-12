# ChangeLens AI workspace guidance

- Keep Terraform parsing, dependency traversal, policy checks, and observed measurements deterministic; an LLM may explain evidence but must not invent facts.
- Maintain version-tolerant plan ingestion, explicit uncertainty, and secret redaction. Never log sensitive plan values.
- Add fixtures and focused tests for each new policy or parsing behavior.
- Keep verification actions isolated and approval-gated. This MVP does not apply infrastructure changes or write to production.
- Run `pytest` and `ruff check .` before proposing changes.
