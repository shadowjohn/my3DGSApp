#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]


def read_json(path: Path) -> tuple[dict[str, Any] | None, str]:
    if not path.is_file():
        return None, "missing"
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return None, "malformed"
    return (data if isinstance(data, dict) else None), "ok" if isinstance(data, dict) else "malformed"


def resolve_path(root: Path, base_file: Path | None, value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    if base_file and (value.startswith(".") or not (root / path).exists()):
        return (base_file.parent / path).resolve()
    return (root / path).resolve()


def relative_or_abs(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def manifest_path_from_detail(root: Path, detail: dict[str, Any]) -> Path | None:
    value = detail.get("delivery_manifest_path") or detail.get("job", {}).get("delivery_manifest_path")
    return resolve_path(root, None, value)


def find_manifest(root: Path, job_id: str = "") -> Path | None:
    if job_id:
        path = root / "studio" / "jobs" / str(job_id) / "delivery_manifest.json"
        return path if path.is_file() else None
    manifests = sorted((root / "studio" / "jobs").glob("*/delivery_manifest.json"), key=lambda item: item.stat().st_mtime, reverse=True)
    return manifests[0] if manifests else None


def path_status(path: Path | None) -> str:
    if path is None:
        return "not_available"
    return "ok" if path.is_file() else "missing"


def evidence_check(root: Path, manifest_path: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    value = (
        manifest.get("evidence_manifest_path")
        or manifest.get("evidence_manifest")
        or manifest.get("evidence", {}).get("manifest_path")
        or manifest.get("evidence", {}).get("path")
    )
    evidence_path = resolve_path(root, manifest_path, value)
    if evidence_path is None:
        return {"status": "not_available"}
    evidence, status = read_json(evidence_path)
    if status != "ok" or evidence is None:
        return {"status": status, "path": relative_or_abs(root, evidence_path)}

    assets = evidence.get("assets") if isinstance(evidence.get("assets"), dict) else {}
    cameras = resolve_path(root, evidence_path, assets.get("cameras") or evidence.get("cameras"))
    spatial = resolve_path(root, evidence_path, evidence.get("spatial_index_path") or assets.get("spatial_index") or assets.get("evidence_index"))
    lod = resolve_path(root, evidence_path, evidence.get("lod_sparse_points_path") or assets.get("lod_sparse_points"))
    return {
        "status": "ok",
        "path": relative_or_abs(root, evidence_path),
        "cameras": path_status(cameras),
        "spatial_index": path_status(spatial),
        "lod_sparse_points": path_status(lod),
    }


def report_for(root: Path, manifest_path: Path, detail: dict[str, Any] | None = None) -> dict[str, Any]:
    manifest, status = read_json(manifest_path)
    if status != "ok" or manifest is None:
        return {"status": status, "reason": f"delivery_manifest.json {status}", "path": relative_or_abs(root, manifest_path)}

    job = detail.get("job", {}) if detail else {}
    studio_job_id = manifest.get("studio_job_id") or job.get("id") or manifest_path.parent.name
    tracks = [
        f"{track.get('track', 'unknown')}/{track.get('engine', 'unknown')}"
        for track in manifest.get("delivery_tracks", [])
        if isinstance(track, dict)
    ]
    preflight_path = resolve_path(root, None, (detail or {}).get("preflight_report_path")) if detail else None
    validation_path = resolve_path(root, manifest_path, (detail or {}).get("qa_validation_report_path") or manifest.get("qa_report_path"))
    checks = {
        "job_detail": {"status": "ok" if detail else "not_checked", "job_status": job.get("status")},
        "engine_runs": {"count": len((detail or {}).get("engine_runs", [])), "items": (detail or {}).get("engine_runs", [])},
        "preflight": {"status": path_status(preflight_path)},
        "gate_decision": (detail or {}).get("gate_decision", {"decision": "not_checked"}),
        "validation": {"status": path_status(validation_path)},
        "delivery_manifest": {"status": "ok", "path": relative_or_abs(root, manifest_path), "tracks": tracks},
        "evidence": evidence_check(root, manifest_path, manifest),
    }
    if studio_job_id:
        viewer = f"viewer_compare_splat_mesh.html?studio_job_id={studio_job_id}"
    else:
        viewer = f"viewer_compare_splat_mesh.html?manifest={relative_or_abs(root, manifest_path)}"
    return {
        "status": "ok",
        "studio_job_id": int(studio_job_id) if str(studio_job_id).isdigit() else studio_job_id,
        "mode": manifest.get("mode") or job.get("pipeline_mode"),
        "viewer_link": viewer,
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-check existing Studio QA/Premium outputs without running workers.")
    parser.add_argument("--root", type=Path, default=ROOT, help="3D app root containing studio/, openmvs/, gaussian_splat/")
    parser.add_argument("--job-id", default="", help="Studio job id to inspect from studio/jobs/{id}/delivery_manifest.json")
    parser.add_argument("--manifest", type=Path, help="delivery_manifest.json path")
    parser.add_argument("--job-detail-json", type=Path, help="Captured studio/api.php?mode=job_detail JSON")
    args = parser.parse_args()

    root = args.root.resolve()
    detail = None
    if args.job_detail_json:
        detail, status = read_json(args.job_detail_json)
        if status != "ok" or detail is None:
            print(json.dumps({"status": status, "reason": f"job_detail JSON {status}"}, ensure_ascii=False, indent=2))
            return 0

    manifest_path = args.manifest.resolve() if args.manifest else None
    if manifest_path is None and detail:
        manifest_path = manifest_path_from_detail(root, detail)
    if manifest_path is None:
        manifest_path = find_manifest(root, args.job_id)
    if manifest_path is None:
        print(json.dumps({
            "status": "missing_completed_job",
            "reason": "missing completed Studio delivery_manifest.json; create or finish a QA/Premium job before real E2E smoke",
        }, ensure_ascii=False, indent=2))
        return 0

    print(json.dumps(report_for(root, manifest_path, detail), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
