import json
import subprocess
from pathlib import Path

from scripts.build_trench_qa_report import build_trench_qa_report

ROOT = Path(__file__).resolve().parents[1]


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def test_build_trench_qa_report_deliverable(tmp_path):
    job = tmp_path / "job"
    write_json(job / "qa_report.json", {"registered_ratio": 0.86, "splat_count": 1000, "quality_grade": "B", "warnings": []})
    write_json(job / "trench_coverage_report.json", {"input_mode": "walk_video", "selected_count": 90, "registered_count": 78, "registered_ratio": 0.87, "warnings": []})
    write_json(job / "georef.json", {"confidence": "low"})
    write_json(job / "exports" / "splat.trench.viewer.json", {"delivery": {"deliveryMode": "gaussian_splat"}})
    (job / "exports" / "splat.trench.ply").write_bytes(b"ply\nformat binary_little_endian 1.0\nelement vertex 800\nend_header\n")

    report = build_trench_qa_report(job)

    assert report["input_mode"] == "walk_video"
    assert report["registered_ratio"] == 0.87
    assert report["splat_count"] == 1000
    assert report["trench_splat_count"] == 800
    assert report["georef_confidence"] == "low"
    assert report["delivery_grade"] == "B"
    assert report["decision"] == "deliverable"
    assert report["delivery_mode"] == "gaussian_splat"


def test_build_trench_qa_report_requests_supplemental_capture(tmp_path):
    job = tmp_path / "job"
    write_json(job / "qa_report.json", {"registered_ratio": 0.55, "splat_count": 100, "quality_grade": "C", "warnings": ["registered_ratio lower than 0.8"]})
    write_json(job / "trench_coverage_report.json", {"input_mode": "photo_set", "selected_count": 12, "registered_count": 6, "registered_ratio": 0.5, "warnings": ["registered_ratio lower than 0.65"]})
    write_json(job / "georef.json", {"confidence": "none"})
    (job / "exports").mkdir(parents=True)
    (job / "exports" / "splat.trench.ply").write_bytes(b"ply\nformat binary_little_endian 1.0\nelement vertex 50\nend_header\n")

    report = build_trench_qa_report(job)

    assert report["decision"] == "supplemental_capture_needed"
    assert report["delivery_grade"] == "C"
    assert "registered_ratio lower than 0.65" in report["warnings"]


def test_build_trench_qa_report_missing_trench_ply_retake(tmp_path):
    job = tmp_path / "job"
    write_json(job / "qa_report.json", {"registered_ratio": 0.86, "splat_count": 1000, "quality_grade": "B", "warnings": []})
    write_json(job / "trench_coverage_report.json", {"input_mode": "walk_video", "selected_count": 90, "registered_count": 78, "registered_ratio": 0.87, "warnings": []})
    write_json(job / "georef.json", {"confidence": "low"})

    report = build_trench_qa_report(job)

    assert report["trench_splat_count"] == 0
    assert report["delivery_grade"] == "D"
    assert report["decision"] == "retake"


def test_build_trench_qa_report_preserves_explicit_zero_coverage_values(tmp_path):
    job = tmp_path / "job"
    write_json(job / "qa_report.json", {"registered_ratio": 0.86, "frame_count": 100, "registered_count": 86, "splat_count": 1000, "quality_grade": "B", "warnings": []})
    write_json(job / "trench_coverage_report.json", {"input_mode": "walk_video", "selected_count": 0, "registered_count": 0, "registered_ratio": 0.0, "warnings": []})
    (job / "exports").mkdir(parents=True)
    (job / "exports" / "splat.trench.ply").write_bytes(b"ply\nformat binary_little_endian 1.0\nelement vertex 50\nend_header\n")

    report = build_trench_qa_report(job)

    assert report["selected_count"] == 0
    assert report["registered_count"] == 0
    assert report["registered_ratio"] == 0.0
    assert report["decision"] == "retake"


def test_build_trench_qa_report_rejects_non_finite_integer_fields(tmp_path):
    job = tmp_path / "job"
    write_json(job / "qa_report.json", {"registered_ratio": 0.86, "frame_count": float("inf"), "registered_count": 86, "splat_count": float("inf"), "quality_grade": "B", "warnings": []})
    write_json(job / "trench_coverage_report.json", {"input_mode": "walk_video", "selected_count": None, "registered_count": None, "registered_ratio": 0.87, "warnings": []})
    (job / "exports").mkdir(parents=True)
    (job / "exports" / "splat.trench.ply").write_bytes(b"ply\nformat binary_little_endian 1.0\nelement vertex 50\nend_header\n")

    report = build_trench_qa_report(job)

    assert report["frame_count"] == 0
    assert report["selected_count"] == 0
    assert report["registered_count"] == 86
    assert report["splat_count"] == 0
    assert report["trench_kept_ratio"] == 0.0


def test_build_trench_qa_report_cli_runs_from_repo_root(tmp_path):
    job = tmp_path / "job"
    write_json(job / "qa_report.json", {"registered_ratio": 0.86, "splat_count": 1000, "quality_grade": "B", "warnings": []})
    write_json(job / "trench_coverage_report.json", {"input_mode": "walk_video", "selected_count": 90, "registered_count": 78, "registered_ratio": 0.87, "warnings": []})
    write_json(job / "georef.json", {"confidence": "low"})
    write_json(job / "exports" / "splat.trench.viewer.json", {"delivery": {"deliveryMode": "gaussian_splat"}})
    (job / "exports" / "splat.trench.ply").write_bytes(b"ply\nformat binary_little_endian 1.0\nelement vertex 800\nend_header\n")

    result = subprocess.run(
        ["python3", "scripts/build_trench_qa_report.py", str(job)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout == f"{job / 'trench_qa_report.json'}\n"
    report = json.loads((job / "trench_qa_report.json").read_text())
    assert report["trench_splat_count"] == 800
