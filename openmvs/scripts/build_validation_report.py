#!/usr/bin/env python3
"""Build a small validation report from OpenMVS QA artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


VERSION = "1.0.3"


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def clamp(value: float) -> int:
    return max(0, min(100, int(round(value))))


def number(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    return default


def grade(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "B-"
    if score >= 60:
        return "C+"
    if score >= 50:
        return "C"
    return "D"


def score_capture(qa: dict[str, Any]) -> int:
    frames = number(qa.get("input_frame_count"))
    registered = number(qa.get("registered_frame_count"))
    if frames <= 0:
        return 0
    return clamp((registered / frames) * 100)


def score_geometry(qa: dict[str, Any]) -> int:
    score = 0
    if number(qa.get("glb_file_size_mb")) > 0:
        score += 50
    if number(qa.get("mesh_file_size_mb")) > 0:
        score += 30
    if qa.get("glb_path"):
        score += 20
    return clamp(score)


def score_texture(qa: dict[str, Any]) -> int:
    if not qa.get("texture_image_count"):
        return 0
    black = number(qa.get("texture_black_pixel_ratio"))
    empty = number(qa.get("texture_white_empty_pixel_ratio"))
    score = 100 - min(60, black * 100) - min(50, empty * 80)
    if number(qa.get("texture_width")) < 1024 or number(qa.get("texture_height")) < 1024:
        score -= 15
    return clamp(score)


def decide(scores: dict[str, int]) -> dict[str, str]:
    capture_high = scores["capture"] >= 70
    geometry_high = scores["geometry"] >= 70
    texture_high = scores["texture"] >= 70
    if capture_high and geometry_high and texture_high:
        return {"status": "deliverable", "root_cause": "unknown", "summary": "OpenMVS Fast output is deliverable."}
    if not capture_high:
        return {"status": "recapture_recommended", "root_cause": "capture", "summary": "Capture registration is weak; recapture is recommended."}
    if not geometry_high:
        return {"status": "review_needed", "root_cause": "engine", "summary": "Mesh / GLB artifact is weak or missing."}
    return {"status": "review_needed", "root_cause": "texture", "summary": "Texture quality needs review."}


def build_validation_report(job_dir: Path) -> dict[str, Any]:
    qa = read_json(job_dir / "qa_report.json")
    contract = read_json(job_dir / "engine_contract.json")
    scores = {
        "capture": score_capture(qa),
        "geometry": score_geometry(qa),
        "texture": score_texture(qa),
    }
    scores["cross_validation"] = clamp(sum(scores.values()) / len(scores))
    decision = decide(scores)
    decision["grade"] = grade(scores["cross_validation"])

    return {
        "version": VERSION,
        "job_id": job_dir.name,
        "mode": contract.get("mode", "fast"),
        "engine": contract.get("engine", "openmvs"),
        "scores": scores,
        "decision": decision,
        "inputs": {
            "qa_report": "qa_report.json" if (job_dir / "qa_report.json").is_file() else None,
            "engine_contract": "engine_contract.json" if (job_dir / "engine_contract.json").is_file() else None,
        },
        "evidence_regions": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job_dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    output = args.output or args.job_dir / "validation" / "validation_report.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        output.parent.chmod(0o755)
    except PermissionError:
        pass
    output.write_text(json.dumps(build_validation_report(args.job_dir), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output.chmod(0o644)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
