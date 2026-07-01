#!/usr/bin/env python3
"""Write failure_summary, failed engine_contract, and validation_report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


VERSION = "1.0.3"
CAPTURE_STAGES = {"prepare_images", "prepare_masks", "colmap_feature", "colmap_matcher", "colmap_mapper", "colmap_undistort"}


def classify(stage: str, reason: str) -> tuple[str, bool, bool, list[str]]:
    text = f"{stage} {reason}".lower()
    if "input file missing" in text or "zip" in text or "影片太短" in text:
        return "input", False, False, ["請重新確認上傳檔案是否完整，必要時重新上傳。"]
    if stage in CAPTURE_STAGES or "registered" in text or "no good initial image pair" in text:
        return "capture", False, True, ["補拍更多重疊影像，避免模糊、反光、下雨與大面積無紋理區域。"]
    return "engine", True, False, ["可先重轉一次；若再次失敗，查看 OpenMVS/COLMAP log 與 GPU/記憶體狀態。"]


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.parent.chmod(0o755)
    except PermissionError:
        pass
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        path.chmod(0o644)
    except PermissionError:
        pass


def build_failure_documents(job_dir: Path, failed_stage: str, reason: str, warnings: list[str]) -> dict[str, Any]:
    failed_stage = failed_stage or "unknown"
    root_cause, retryable, recapture, recommendations = classify(failed_stage, reason)
    summary = {
        "version": VERSION,
        "job_id": job_dir.name,
        "engine": "openmvs",
        "engine_failed": True,
        "root_cause": root_cause,
        "failed_stage": failed_stage,
        "reason": reason,
        "retryable": retryable,
        "recapture_recommended": recapture,
        "recommendations": recommendations,
        "diagnostic_warnings": [item for item in warnings if item],
    }
    contract = {
        "version": VERSION,
        "engine": "openmvs",
        "engineType": "mesh_reconstruction",
        "status": "failed",
        "mode": "fast",
        "job_id": job_dir.name,
        "artifacts": [],
        "metrics": {},
        "errors": [{
            "stage": failed_stage,
            "reason": reason,
            "root_cause": root_cause,
            "retryable": retryable,
        }],
    }
    validation = {
        "version": VERSION,
        "job_id": job_dir.name,
        "mode": "fast",
        "engine": "openmvs",
        "scores": {"capture": 0, "geometry": 0, "texture": 0, "cross_validation": 0},
        "decision": {
            "status": "engine_failed",
            "root_cause": root_cause,
            "summary": reason,
            "grade": "D",
            "retryable": retryable,
            "recapture_recommended": recapture,
        },
        "inputs": {"failure_summary": "failure_summary.json"},
        "evidence_regions": [],
    }
    return {"summary": summary, "contract": contract, "validation": validation}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job_dir", type=Path)
    parser.add_argument("--failed-stage", default="unknown")
    parser.add_argument("--reason", default="")
    parser.add_argument("--diagnostic-warning", action="append", default=[])
    args = parser.parse_args()

    docs = build_failure_documents(args.job_dir, args.failed_stage, args.reason, args.diagnostic_warning)
    write_json(args.job_dir / "failure_summary.json", docs["summary"])
    write_json(args.job_dir / "engine_contract.json", docs["contract"])
    write_json(args.job_dir / "validation" / "validation_report.json", docs["validation"])
    print(args.job_dir / "failure_summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
