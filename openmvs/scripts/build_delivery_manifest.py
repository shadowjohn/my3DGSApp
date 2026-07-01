#!/usr/bin/env python3
"""Build the Fast delivery manifest for OpenMVS."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


VERSION = "1.0.3"
SCHEMA_VERSION = "1.0"


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def generated_at() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def delivery_status(decision_status: str) -> str:
    if decision_status == "deliverable":
        return "ready"
    if decision_status in {"engine_failed", "recapture_recommended"}:
        return "not_ready"
    return "review_needed"


def build_delivery_manifest(job_dir: Path) -> dict[str, Any]:
    contract = read_json(job_dir / "engine_contract.json")
    validation = read_json(job_dir / "validation" / "validation_report.json")
    decision_status = validation.get("decision", {}).get("status", "review_needed")
    return {
        "schema_version": SCHEMA_VERSION,
        "studio_job_id": None,
        "status": delivery_status(decision_status),
        "generated_at": generated_at(),
        "delivery_tracks": [
            {
                "track": "mesh",
                "engine": "openmvs",
                "role": "delivery_candidate",
                "delivery_capable": True,
                "primary_artifact": {
                    "type": "glb",
                    "path": "exports/model.glb",
                },
                "preview_artifacts": [],
                "contract_path": "engine_contract.json",
                "validation_report_path": "validation/validation_report.json",
            }
        ],
        "qa_report_path": None,
        "version": VERSION,
        "mode": contract.get("mode", "fast"),
        "job_id": job_dir.name,
        "primaryArtifact": {
            "type": "mesh",
            "path": "exports/model.glb",
            "format": "glb",
            "viewer": "viewer_mesh.html",
        },
        "debug": {
            "engineContract": "engine_contract.json",
            "validationReport": "validation/validation_report.json",
        },
        "readiness": decision_status,
        "notes": [
            "Fast mode uses the default OpenMVS mesh reconstruction engine.",
            "Gaussian Splat / Premium artifacts are intentionally not part of this delivery manifest.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job_dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    output = args.output or args.job_dir / "delivery_manifest.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        output.parent.chmod(0o755)
    except PermissionError:
        pass
    output.write_text(json.dumps(build_delivery_manifest(args.job_dir), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output.chmod(0o644)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
