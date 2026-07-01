#!/usr/bin/env python3
import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any


DELIVERY_MODES = {"gaussian_splat", "oblique_projection", "glb_hybrid", "mixed"}
PIPELINE_MODES = {"fast", "qa", "premium"}
VERSION = "1.0.3"
SCHEMA_VERSION = "1.0"
NOTES = [
    "Gaussian Splat is the primary MVP delivery layer.",
    "Oblique projection and GLB hybrid are reserved for map-review alternatives.",
]


def build_delivery_manifest(
    job_dir: Path | str,
    delivery_mode: str = "gaussian_splat",
    oblique_projection: str | None = None,
    glb_hybrid: str | None = None,
) -> dict[str, Any]:
    if delivery_mode not in DELIVERY_MODES:
        raise ValueError(f"unsupported delivery mode: {delivery_mode}")

    exports_dir = Path(job_dir) / "exports"

    return {
        "delivery_mode": delivery_mode,
        "layers": {
            "gaussian_splat": {
                "splat": str(exports_dir / "splat.trench.ply"),
                "meta": str(exports_dir / "splat.trench.viewer.json"),
            },
            "oblique_projection": oblique_projection,
            "glb_hybrid": glb_hybrid,
        },
        "notes": NOTES.copy(),
    }


def existing_relative(job_dir: Path, *candidates: str) -> str | None:
    for candidate in candidates:
        if (job_dir / candidate).is_file():
            return candidate
    return None


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def readiness_from_validation(job_dir: Path) -> str:
    path = job_dir / "validation" / "validation_report.json"
    if not path.is_file():
        return "review_needed"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "review_needed"
    status = str(data.get("decision", {}).get("status", ""))
    if status == "deliverable":
        return "ready"
    if status in {"engine_failed", "recapture_recommended"}:
        return "not_ready"
    return "review_needed"


def mesh_engine_for(path: str) -> str:
    return "openmvs" if path == "exports/model.glb" else "mesh_extraction"


def gaussian_contract(job_dir: Path) -> dict[str, Any]:
    contract = read_json(job_dir / "engine_contract.json")
    engine = contract.get("engine_name") or contract.get("engine")
    return contract if engine == "gaussian_splat" else {}


def contract_splat_path(contract: dict[str, Any], job_dir: Path) -> str | None:
    artifacts = contract.get("artifacts")
    if not isinstance(artifacts, list):
        return None
    for artifact in artifacts:
        if not isinstance(artifact, dict) or artifact.get("type") != "splat":
            continue
        path = artifact.get("path")
        if isinstance(path, str) and (job_dir / path).is_file():
            return path
    return None


def gaussian_role(contract: dict[str, Any], pipeline_mode: str) -> str:
    role = contract.get("role")
    if isinstance(role, str) and role:
        return role
    if pipeline_mode == "qa":
        return "diagnostic"
    if pipeline_mode == "premium":
        return "delivery_capable"
    return "delivery_candidate"


def gaussian_delivery_capable(contract: dict[str, Any], pipeline_mode: str) -> bool:
    value = contract.get("delivery_capable")
    if isinstance(value, bool):
        return value
    return pipeline_mode == "premium"


def generated_at() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def delivery_status(readiness: str) -> str:
    if readiness == "ready":
        return "ready"
    if readiness == "not_ready":
        return "not_ready"
    return "review_needed"


def delivery_artifact_type(path: str) -> str:
    if path.lower().endswith(".glb"):
        return "glb"
    if path.lower().endswith((".ply", ".splat")):
        return "splat"
    return "artifact"


def delivery_artifact_format(path: str) -> str | None:
    suffix = Path(path).suffix.lower().lstrip(".")
    return suffix or None


def delivery_artifact_uuid(job_id: str, path: str) -> str:
    digest = hashlib.sha256(f"{job_id}|{path}".encode("utf-8")).hexdigest()[:32]
    return f"gs_{job_id}_{digest}"


def make_artifact(job_id: str, artifact_type: str, path: str, **extra: Any) -> dict[str, Any]:
    artifact = {"type": artifact_type, "path": path, **extra}
    if artifact_type == "splat":
        artifact["format"] = delivery_artifact_format(path)
        artifact["uuid"] = delivery_artifact_uuid(job_id, path)
    return artifact


def make_delivery_track(
    job_id: str,
    track: str,
    engine: str,
    role: str,
    delivery_capable: bool,
    artifact_path: str,
    validation_report_path: str,
) -> dict[str, Any]:
    return {
        "track": track,
        "engine": engine,
        "role": role,
        "delivery_capable": delivery_capable,
        "primary_artifact": make_artifact(job_id, delivery_artifact_type(artifact_path), artifact_path),
        "preview_artifacts": [],
        "contract_path": "engine_contract.json",
        "validation_report_path": validation_report_path,
    }


def build_studio_delivery_manifest(job_dir: Path | str, pipeline_mode: str = "fast") -> dict[str, Any]:
    if pipeline_mode not in PIPELINE_MODES:
        raise ValueError(f"unsupported pipeline mode: {pipeline_mode}")
    job_dir = Path(job_dir)
    artifacts = []
    delivery_tracks = []
    mesh = existing_relative(job_dir, "exports/model.glb", "compare/mesh/cleaned_mesh.glb")
    contract = gaussian_contract(job_dir)
    splat = contract_splat_path(contract, job_dir) or existing_relative(job_dir, "exports/splat.clean.ply", "exports/splat.trench.ply", "exports/splat.ply")
    if mesh:
        mesh_engine = mesh_engine_for(mesh)
        artifacts.append(make_artifact(job_dir.name, "mesh", mesh, engine=mesh_engine, role="primary"))
        delivery_tracks.append(
            make_delivery_track(job_dir.name, "mesh", mesh_engine, "delivery_candidate", True, mesh, "validation/validation_report.json")
        )
    if splat and pipeline_mode != "fast":
        role = gaussian_role(contract, pipeline_mode)
        delivery_capable = gaussian_delivery_capable(contract, pipeline_mode)
        artifacts.append(make_artifact(job_dir.name, "splat", splat, engine="gaussian_splat", role=role))
        delivery_tracks.append(
            make_delivery_track(
                job_dir.name,
                "splat",
                "gaussian_splat",
                role,
                delivery_capable,
                splat,
                "evidence/appearance_summary.json",
            )
        )
    elif splat and not mesh:
        artifacts.append(make_artifact(job_dir.name, "splat", splat, engine="gaussian_splat", role="primary"))
        delivery_tracks.append(
            make_delivery_track(job_dir.name, "splat", "gaussian_splat", "delivery_candidate", True, splat, "evidence/appearance_summary.json")
        )
    artifacts.append({"type": "validation_report", "path": "validation/validation_report.json", "role": "supporting"})
    primary = next((item for item in artifacts if item["role"] == "primary"), None)
    readiness = readiness_from_validation(job_dir)
    return {
        "schema_version": SCHEMA_VERSION,
        "studio_job_id": None,
        "status": delivery_status(readiness),
        "generated_at": generated_at(),
        "delivery_tracks": delivery_tracks,
        "qa_report_path": "validation/qa_validation_report.json" if pipeline_mode == "qa" else None,
        "version": VERSION,
        "job_id": job_dir.name,
        "mode": pipeline_mode,
        "primary_artifact": primary,
        "artifacts": artifacts,
        "validation_report": "validation/validation_report.json",
        "readiness": readiness,
        "notes": [
            "Fast uses the primary delivery artifact only.",
            "QA keeps Gaussian Splat diagnostic-only.",
            "Premium may include Gaussian Splat as fidelity evidence.",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build reality-layer delivery manifest.")
    parser.add_argument("job_dir", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--delivery-mode", default="gaussian_splat", choices=sorted(DELIVERY_MODES))
    parser.add_argument("--pipeline-mode", choices=sorted(PIPELINE_MODES))
    parser.add_argument("--oblique-projection")
    parser.add_argument("--glb-hybrid")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = args.output or args.job_dir / "delivery_manifest.json"
    manifest = (
        build_studio_delivery_manifest(args.job_dir, args.pipeline_mode)
        if args.pipeline_mode
        else build_delivery_manifest(
            args.job_dir,
            delivery_mode=args.delivery_mode,
            oblique_projection=args.oblique_projection,
            glb_hybrid=args.glb_hybrid,
        )
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
