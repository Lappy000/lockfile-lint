"""Output formatting utilities."""
from __future__ import annotations
import json
from typing import Any


def format_sarif(findings: list[dict], lockfile_path: str) -> dict:
    """Format findings as SARIF v2.1.0 for GitHub Code Scanning."""
    rules = []
    results = []
    seen_rules: set[str] = set()

    for f in findings:
        rule_id = f["rule"]
        if rule_id not in seen_rules:
            rules.append({
                "id": rule_id,
                "shortDescription": {"text": rule_id.replace("-", " ").title()},
                "defaultConfiguration": {
                    "level": "error" if f["severity"] == "critical" else "warning"
                },
            })
            seen_rules.add(rule_id)

        results.append({
            "ruleId": rule_id,
            "level": "error" if f["severity"] == "critical" else "warning",
            "message": {"text": f["message"]},
            "locations": [{
                "physicalLocation": {
                    "artifactLocation": {"uri": lockfile_path},
                }
            }],
        })

    return {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/sarif-2.1/schema/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "lockfile-lint",
                    "version": "0.1.0",
                    "rules": rules,
                }
            },
            "results": results,
        }],
    }
