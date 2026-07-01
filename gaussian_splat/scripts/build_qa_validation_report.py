#!/usr/bin/env python3
"""Build the QA-mode validation contract from default and diagnostic evidence."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from build_validation_report import VERSION, score_appearance


class QaValidationError(Exception):
    pass


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise QaValidationError(f"Malformed JSON in {path}: {exc.msg}") from exc
    except OSError as exc:
        raise QaValidationError(f"Cannot read input {path}: {exc}") from exc
    return data if isinstance(data, dict) else {}


def rel(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def issue_counts(issue_type: str) -> dict[str, int]:
    return {
        "capture_issue": 1 if issue_type == "capture_issue" else 0,
        "mesh_issue": 1 if issue_type == "mesh_issue" else 0,
        "splat_issue": 1 if issue_type == "splat_issue" else 0,
    }


def classify(default_report: dict[str, Any], appearance: dict[str, Any]) -> dict[str, str]:
    decision = default_report.get("decision") if isinstance(default_report.get("decision"), dict) else {}
    default_status = str(decision.get("status") or "unknown")
    root_cause = str(decision.get("root_cause") or "unknown")
    splat_ok = score_appearance(appearance) >= 70

    if default_status == "deliverable" and splat_ok:
        return {
            "status": "deliverable",
            "root_cause": "unknown",
            "issue_type": "none",
            "summary": "QA 模式：交付候選與 3DGS 診斷訊號都正常。",
        }
    if default_status == "recapture_recommended" or root_cause == "capture":
        return {
            "status": "recapture_recommended",
            "root_cause": "capture",
            "issue_type": "capture_issue",
            "summary": "COLMAP / 拍攝來源訊號不足，建議補拍後再重建。",
        }
    if default_status == "deliverable" and not splat_ok:
        return {
            "status": "review_needed",
            "root_cause": "splat",
            "issue_type": "splat_issue",
            "summary": "OpenMVS 交付候選可用，但 3DGS 診斷訊號偏弱；QA 模式不把 Splat 當交付。",
        }
    if splat_ok:
        return {
            "status": "review_needed",
            "root_cause": "mesh",
            "issue_type": "mesh_issue",
            "summary": "3DGS 診斷訊號存在，但 OpenMVS 交付候選偏弱，優先檢查 Mesh / 貼圖流程。",
        }
    return {
        "status": "review_needed",
        "root_cause": "unknown",
        "issue_type": "unknown",
        "summary": "QA 訊號不足，需人工檢查 default engine 與 diagnostic engine 輸出。",
    }


def build_qa_validation_report(
    job_dir: Path,
    default_report_path: Path | None = None,
    appearance_path: Path | None = None,
) -> dict[str, Any]:
    default_path = default_report_path or job_dir / "validation" / "validation_report.json"
    diagnostic_path = appearance_path or job_dir / "evidence" / "appearance_summary.json"
    default_report = load_json(default_path)
    appearance = load_json(diagnostic_path)
    default_decision = default_report.get("decision") if isinstance(default_report.get("decision"), dict) else {}
    decision = classify(default_report, appearance)
    issues = []
    if decision["issue_type"] != "none":
        issues.append(
            {
                "type": decision["issue_type"],
                "severity": "error" if decision["issue_type"] == "capture_issue" else "warning",
                "message": decision["summary"],
            }
        )

    return {
        "version": VERSION,
        "job_id": job_dir.name,
        "mode": "qa",
        "pipeline": {
            "default_engine": "openmvs",
            "diagnostic_engine": "gaussian_splat",
        },
        "engines": {
            "default": {
                "engine": default_report.get("engine") or "openmvs",
                "role": "delivery_candidate",
                "delivery": True,
                "status": default_decision.get("status") or "unknown",
            },
            "diagnostic": {
                "engine": "gaussian_splat",
                "role": "diagnostic",
                "delivery": False,
                "status": "available" if appearance else "missing",
                "appearance_score": score_appearance(appearance),
            },
        },
        "scores": {
            "default": default_report.get("scores") if isinstance(default_report.get("scores"), dict) else {},
            "diagnostic_appearance": score_appearance(appearance),
        },
        "decision": decision,
        "issue_counts": issue_counts(decision["issue_type"]),
        "issues": issues,
        "inputs": {
            "default_validation_report": rel(default_path, job_dir) if default_path.is_file() else None,
            "diagnostic_appearance_summary": rel(diagnostic_path, job_dir) if diagnostic_path.is_file() else None,
        },
    }


def write_report(path: Path, report: dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        path.chmod(0o644)
    except OSError as exc:
        raise QaValidationError(f"Cannot write output {path}: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job_dir", type=Path)
    parser.add_argument("--default-report", type=Path)
    parser.add_argument("--appearance-summary", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    try:
        report = build_qa_validation_report(args.job_dir, args.default_report, args.appearance_summary)
        output = args.output or args.job_dir / "validation" / "qa_validation_report.json"
        write_report(output, report)
    except QaValidationError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
