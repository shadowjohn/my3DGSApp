#!/usr/bin/env python3
"""Build a Gaussian Splat engine contract from appearance evidence."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


VERSION = "1.0.3"
SCHEMA_VERSION = "1.0"
MODES = {"fast", "qa", "premium"}


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def role_for(mode: str) -> str:
    if mode == "qa":
        return "diagnostic"
    if mode == "premium":
        return "delivery_capable"
    return "supporting"


def number(value: Any) -> int | float | None:
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def generated_at() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def build_gaussian_engine_contract(job_dir: Path, mode: str = "qa") -> dict[str, Any]:
    if mode not in MODES:
        raise ValueError(f"unsupported mode: {mode}")

    appearance = read_json(job_dir / "evidence" / "appearance_summary.json")
    splat = appearance.get("splat") if isinstance(appearance.get("splat"), dict) else {}
    cameras = appearance.get("cameras") if isinstance(appearance.get("cameras"), dict) else {}
    training = appearance.get("training") if isinstance(appearance.get("training"), dict) else {}
    quality = appearance.get("quality") if isinstance(appearance.get("quality"), dict) else {}
    validation = appearance.get("validation") if isinstance(appearance.get("validation"), dict) else {}
    splat_path = splat.get("path") if splat.get("available") is True else None
    role = role_for(mode)
    delivery_capable = mode == "premium"
    artifacts = []
    if splat_path:
        artifacts.append(
            {
                "type": "splat",
                "path": splat_path,
                "format": "ply",
                "engine": "gaussian_splat",
                "role": role,
                "delivery_capable": delivery_capable,
                "deliveryCapable": delivery_capable,
            }
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
        "engine_name": "gaussian_splat",
        "engine_version": VERSION,
        "engine": "gaussian_splat",
        "engineType": "appearance_reconstruction",
        "status": "completed" if artifacts else "review_required",
        "pipeline_mode": mode,
        "mode": mode,
        "role": role,
        "delivery_capable": delivery_capable,
        "generated_at": generated_at(),
        "job_id": job_dir.name,
        "input": {
            "type": "frames",
            "count": number(cameras.get("frame_count")),
            "registeredCount": number(cameras.get("registered_count")),
        },
        "artifacts": artifacts,
        "metrics": {
            "registeredFrames": number(cameras.get("registered_count")),
            "registrationRatio": number(cameras.get("registered_ratio")),
            "splatCount": number(splat.get("count")),
            "splatFileSizeMb": number(splat.get("file_size_mb")),
            "trainingIterations": number(training.get("iterations")),
            "trainingTimeSeconds": number(training.get("training_time_seconds")),
            "qualityGrade": quality.get("grade"),
        },
        "diagnostics": {
            "appearance_summary_path": "evidence/appearance_summary.json" if (job_dir / "evidence" / "appearance_summary.json").is_file() else None,
            "splat": splat,
            "cameras": cameras,
            "training": training,
            "quality": quality,
            "validation": validation,
        },
        "validation_summary": {
            "quality_grade": quality.get("grade"),
            "quality_label": quality.get("label"),
            "registered_ratio": number(cameras.get("registered_ratio")),
            "floating_artifact_risk": validation.get("floating_artifact_risk"),
            "black_ratio": number(validation.get("black_ratio")),
            "transparent_ratio": number(validation.get("transparent_ratio")),
        },
        "errors": [] if artifacts else ["splat artifact missing"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job_dir", type=Path)
    parser.add_argument("--mode", default="qa", choices=sorted(MODES))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    output = args.output or args.job_dir / "engine_contract.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(build_gaussian_engine_contract(args.job_dir, args.mode), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    output.chmod(0o644)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
