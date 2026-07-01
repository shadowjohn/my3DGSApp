#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts.capture_analyzer import analyze_capture
except ModuleNotFoundError:  # Allows direct `python scripts/confidence_gate.py`.
    from capture_analyzer import analyze_capture


REPORT_NAME = "confidence_report.json"
GATE_NAME = "confidence_gate.json"

DECISION_MAP = {
    "run": "run",
    "warn": "warn",
    "require_override": "hold",
    "recapture_recommended": "reject",
    "hold": "hold",
    "reject": "reject",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def read_report(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("report root is not an object")
    return data


def failure_report(reason: str) -> dict[str, Any]:
    return {
        "confidenceScore": None,
        "grade": "",
        "decision": "reject",
        "estimatedRisk": {"analysis": "high"},
        "metrics": {},
        "recommendations": [reason],
    }


def load_or_create_report(
    job_dir: Path, input_path: Path, force: bool = False
) -> tuple[dict[str, Any] | None, str]:
    report_path = job_dir / REPORT_NAME
    if report_path.is_file() and not force:
        try:
            return read_report(report_path), ""
        except (json.JSONDecodeError, OSError, ValueError) as exc:
            return None, f"Malformed {REPORT_NAME}: {exc}"

    try:
        report = analyze_capture(input_path)
    except Exception as exc:  # Fail closed before heavy reconstruction.
        report = failure_report(f"Capture analysis failed: {exc}")
    write_json(report_path, report)
    return report, ""


def normalize_decision(original: str) -> str:
    return DECISION_MAP.get(original, "reject")


def gate_reason(
    original: str,
    decision: str,
    malformed_reason: str,
    recommendations: list[Any] | None = None,
) -> str:
    if malformed_reason:
        return malformed_reason
    for item in recommendations or []:
        item = str(item)
        if item.startswith("Capture analysis failed:"):
            return item
    if original not in DECISION_MAP:
        return f"Unsupported confidence decision: {original}"
    if decision == "hold":
        return "Confidence gate requires manual override."
    if decision == "reject":
        return "Confidence gate rejected capture."
    if decision == "warn":
        return "Confidence gate warning."
    return ""


def list_or_empty(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def dict_or_empty(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def run_confidence_gate(
    job_dir: str | Path,
    input_path: str | Path,
    override: bool = False,
    override_reason: str = "",
    force: bool = False,
) -> dict[str, Any]:
    job_dir = Path(job_dir)
    input_path = Path(input_path)
    job_dir.mkdir(parents=True, exist_ok=True)

    report, malformed_reason = load_or_create_report(job_dir, input_path, force=force)
    if report is None:
        original = "malformed_report"
        decision = "reject"
        score = None
        grade = ""
        risks: dict[str, Any] = {"analysis": "high"}
        metrics: dict[str, Any] = {}
        recommendations = [malformed_reason]
    else:
        original = str(report.get("decision") or "").strip() or "unknown"
        decision = normalize_decision(original)
        score = report.get("confidenceScore")
        grade = str(report.get("grade") or "")
        risks = dict_or_empty(report.get("estimatedRisk"))
        metrics = dict_or_empty(report.get("metrics"))
        recommendations = list_or_empty(report.get("recommendations"))

    effective = decision
    if decision == "hold" and override:
        effective = "run_with_override"
    if decision == "reject":
        effective = "reject"

    gate = {
        "createdAt": utc_now(),
        "score": score,
        "grade": grade,
        "originalDecision": original,
        "decision": decision,
        "effectiveDecision": effective,
        "override": {
            "enabled": bool(override),
            "reason": str(override_reason or ""),
        },
        "reason": gate_reason(original, decision, malformed_reason, recommendations),
        "risks": risks,
        "metrics": metrics,
        "recommendations": recommendations,
        "reportPath": str(job_dir / REPORT_NAME),
        "gatePath": str(job_dir / GATE_NAME),
    }
    write_json(job_dir / GATE_NAME, gate)
    return gate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gate Gaussian Splat jobs using capture confidence."
    )
    parser.add_argument("job_dir")
    parser.add_argument("input_path")
    parser.add_argument("--override", action="store_true")
    parser.add_argument("--override-reason", default="")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    gate = run_confidence_gate(
        args.job_dir,
        args.input_path,
        override=args.override,
        override_reason=args.override_reason,
        force=args.force,
    )
    print(gate["gatePath"])


if __name__ == "__main__":
    main()
