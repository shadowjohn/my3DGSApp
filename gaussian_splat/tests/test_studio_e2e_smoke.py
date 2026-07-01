import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "studio_e2e_smoke.py"


def run_smoke(*args):
    return subprocess.run(
        ["python3", str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_studio_e2e_smoke_reports_missing_completed_job_without_worker(tmp_path):
    result = run_smoke("--root", tmp_path)

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "missing_completed_job"
    assert "completed Studio delivery_manifest.json" in report["reason"]
    assert "worker" not in result.stdout.lower()


def test_studio_e2e_smoke_summarizes_job_detail_manifest_and_evidence(tmp_path):
    manifest = tmp_path / "studio" / "jobs" / "123" / "delivery_manifest.json"
    evidence = manifest.parent / "evidence" / "evidence_manifest.json"
    cameras = evidence.parent / "cameras.json"
    spatial = evidence.parent / "spatial_index.json"
    lod = evidence.parent / "lod_sparse_points.json"
    preflight = manifest.parent / "preflight" / "preflight_report.json"
    validation = manifest.parent / "validation" / "qa_validation_report.json"
    for path in (manifest, evidence, cameras, spatial, lod, preflight, validation):
        path.parent.mkdir(parents=True, exist_ok=True)

    cameras.write_text(json.dumps({"cameras": [{"name": "frame_1", "position": [0, 0, 0]}]}))
    spatial.write_text(json.dumps({"grid": {"size": 1}, "tiles": []}))
    lod.write_text(json.dumps({"point_count": 1, "points": [{"point3d_id": 1, "xyz": [0, 0, 0]}]}))
    evidence.write_text(json.dumps({
        "assets": {
            "cameras": "cameras.json",
            "spatial_index": "spatial_index.json",
            "lod_sparse_points": "lod_sparse_points.json",
        }
    }))
    preflight.write_text(json.dumps({"confidence_score": 0.92, "confidence_level": "high"}))
    validation.write_text(json.dumps({"conclusion": "ok"}))
    manifest.write_text(json.dumps({
        "schema_version": "1.0",
        "studio_job_id": 123,
        "mode": "qa",
        "status": "ready",
        "delivery_tracks": [
            {"track": "mesh", "engine": "openmvs", "role": "delivery_candidate", "delivery_capable": True, "primary_artifact": {"type": "glb", "path": "mesh.glb"}},
            {"track": "splat", "engine": "gaussian_splat", "role": "diagnostic", "delivery_capable": False, "primary_artifact": {"type": "splat", "path": "splat.ply"}},
        ],
        "evidence_manifest_path": "evidence/evidence_manifest.json",
        "qa_report_path": "validation/qa_validation_report.json",
    }))
    job_detail = tmp_path / "job_detail.json"
    job_detail.write_text(json.dumps({
        "status": "OK",
        "job": {
            "id": 123,
            "pipeline_mode": "qa",
            "status": "completed",
            "delivery_manifest_path": "studio/jobs/123/delivery_manifest.json",
        },
        "engine_runs": [
            {"engine_name": "openmvs", "role": "delivery_candidate", "status": "completed"},
            {"engine_name": "gaussian_splat", "role": "diagnostic", "status": "completed"},
        ],
        "preflight_report_path": "studio/jobs/123/preflight/preflight_report.json",
        "gate_decision": {"decision": "pass"},
        "qa_validation_report_path": "studio/jobs/123/validation/qa_validation_report.json",
    }))

    result = run_smoke("--root", tmp_path, "--job-detail-json", job_detail)

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "ok"
    assert report["studio_job_id"] == 123
    assert report["viewer_link"] == "viewer_compare_splat_mesh.html?studio_job_id=123"
    assert report["checks"]["engine_runs"]["count"] == 2
    assert report["checks"]["preflight"]["status"] == "ok"
    assert report["checks"]["gate_decision"]["decision"] == "pass"
    assert report["checks"]["validation"]["status"] == "ok"
    assert report["checks"]["delivery_manifest"]["tracks"] == ["mesh/openmvs", "splat/gaussian_splat"]
    assert report["checks"]["evidence"]["status"] == "ok"
    assert report["checks"]["evidence"]["cameras"] == "ok"
    assert report["checks"]["evidence"]["spatial_index"] == "ok"
    assert report["checks"]["evidence"]["lod_sparse_points"] == "ok"
