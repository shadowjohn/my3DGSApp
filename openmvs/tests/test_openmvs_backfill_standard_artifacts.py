import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "backfill_standard_artifacts.py"


def write_qa(job: Path) -> None:
    exports = job / "exports"
    exports.mkdir(parents=True)
    (exports / "model.glb").write_bytes(b"glb")
    (job / "qa_report.json").write_text(json.dumps({
        "input_frame_count": 10,
        "registered_frame_count": 8,
        "glb_file_size_mb": 2,
        "mesh_file_size_mb": 1,
        "glb_path": str(exports / "model.glb"),
        "texture_image_count": 0,
    }))


def run_backfill(uploads: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), str(uploads), *args], text=True, capture_output=True, check=False)


def test_backfill_success_jobs_writes_standard_artifacts(tmp_path):
    uploads = tmp_path / "uploads"
    job = uploads / "1"
    job.mkdir(parents=True)
    write_qa(job)

    result = run_backfill(uploads)

    assert result.returncode == 0, result.stderr
    assert "1 success" in result.stdout
    assert (job / "engine_contract.json").is_file()
    assert (job / "validation" / "validation_report.json").is_file()
    assert (job / "delivery_manifest.json").is_file()
    assert json.loads((job / "engine_contract.json").read_text())["status"] == "completed"


def test_backfill_failures_requires_flag_and_uses_last_stage(tmp_path):
    uploads = tmp_path / "uploads"
    job = uploads / "2"
    (job / "logs").mkdir(parents=True)
    (job / "logs" / "openmvs_pipeline.log").write_text("[timing] START colmap_mapper COLMAP\nregistered images 2/20\n")

    skipped = run_backfill(uploads)
    assert skipped.returncode == 0
    assert not (job / "failure_summary.json").exists()

    result = run_backfill(uploads, "--include-failures")

    assert result.returncode == 0, result.stderr
    summary = json.loads((job / "failure_summary.json").read_text())
    assert summary["failed_stage"] == "colmap_mapper"
    assert summary["root_cause"] == "capture"
    assert summary["recapture_recommended"] is True


def test_backfill_skips_unreadable_job_dirs(tmp_path):
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    blocked = uploads / "blocked"
    blocked.mkdir()
    blocked.chmod(0)
    try:
        result = run_backfill(uploads)
    finally:
        blocked.chmod(0o755)

    assert result.returncode == 0, result.stderr
    assert "skipped=1" in result.stdout
