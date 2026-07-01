#!/usr/bin/env python3
"""Build the OpenMVS engine contract for a completed job."""

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


def rel(job_dir: Path, path: str | None) -> str | None:
    if not path:
        return None
    candidate = Path(path)
    if not candidate.is_absolute():
        return candidate.as_posix()
    try:
        return candidate.relative_to(job_dir).as_posix()
    except ValueError:
        return candidate.as_posix()


def ratio(numerator: Any, denominator: Any) -> float | None:
    if not isinstance(numerator, (int, float)) or not isinstance(denominator, (int, float)) or denominator <= 0:
        return None
    return round(float(numerator) / float(denominator), 6)


def artifact(kind: str, path: str | None, fmt: str, primary: bool = False) -> dict[str, Any] | None:
    if not path:
        return None
    item = {"type": kind, "path": path, "format": fmt, "engine": "openmvs"}
    if primary:
        item["primary"] = True
    return item


def build_engine_contract(job_dir: Path, mode: str = "fast", pipeline_mode: str = "openmvs_native") -> dict[str, Any]:
    qa = read_json(job_dir / "qa_report.json")
    input_frames = qa.get("input_frame_count")
    registered = qa.get("registered_frame_count")
    artifacts = [
        artifact("mesh", rel(job_dir, qa.get("glb_path") or "exports/model.glb"), "glb", True),
        artifact("mesh_source", rel(job_dir, qa.get("mesh_path")), "ply"),
    ]
    artifacts.extend(
        artifact("texture", rel(job_dir, image.get("path")), "png")
        for image in qa.get("texture_images", [])
        if isinstance(image, dict)
    )

    return {
        "version": VERSION,
        "engine": "openmvs",
        "engineType": "mesh_reconstruction",
        "status": "completed",
        "mode": mode,
        "pipelineMode": pipeline_mode,
        "job_id": job_dir.name,
        "input": {
            "type": "frames",
            "count": input_frames,
            "registeredCount": registered,
        },
        "artifacts": [item for item in artifacts if item],
        "metrics": {
            "registeredFrames": registered,
            "registrationRatio": ratio(registered, input_frames),
            "textureBlackRatio": qa.get("texture_black_pixel_ratio"),
            "textureWhiteEmptyRatio": qa.get("texture_white_empty_pixel_ratio"),
            "texturePatchCount": qa.get("texture_patch_count"),
            "glbFileSizeMb": qa.get("glb_file_size_mb"),
            "meshFileSizeMb": qa.get("mesh_file_size_mb"),
        },
        "errors": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job_dir", type=Path)
    parser.add_argument("--mode", default="fast")
    parser.add_argument("--pipeline-mode", default="openmvs_native")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    output = args.output or args.job_dir / "engine_contract.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        output.parent.chmod(0o755)
    except PermissionError:
        pass
    output.write_text(
        json.dumps(build_engine_contract(args.job_dir, args.mode, args.pipeline_mode), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    output.chmod(0o644)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
