import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_validation_report.py"


def run_script(*args: Path | str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *(str(arg) for arg in args)],
        check=False,
        text=True,
        capture_output=True,
    )


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def write_summaries(tmp_path: Path, coverage: dict | None, geometry: dict | None, appearance: dict | None) -> None:
    if coverage is not None:
        write_json(tmp_path / "evidence" / "coverage_summary.json", coverage)
    if geometry is not None:
        write_json(tmp_path / "evidence" / "geometry_summary.json", geometry)
    if appearance is not None:
        write_json(tmp_path / "evidence" / "appearance_summary.json", appearance)


def coverage(track: float, cameras: int, points: int, error: float) -> dict:
    return {
        "camera_count": cameras,
        "sparse_point_count": points,
        "track_length": {"avg": track},
        "reprojection_error": {"avg": error},
    }


def good_geometry() -> dict:
    return {
        "mesh": {"vertex_count": 10, "face_count": 20, "bbox": {"min": [0, 0, 0], "max": [1, 1, 1]}, "normal_available": True},
        "dense_cloud": {"point_count": 100},
        "texture": {"available": True},
    }


def low_geometry() -> dict:
    return {"mesh": {"vertex_count": 1}, "dense_cloud": {}, "texture": {"available": False}}


def good_appearance() -> dict:
    return {
        "splat": {"available": True, "count": 1000, "bbox": {"min": [0, 0, 0], "max": [1, 1, 1]}},
        "opacity": {"available": True},
        "scale": {"available": True},
        "render_quality": {"available": True},
    }


def low_appearance() -> dict:
    return {"splat": {"available": False, "count": 0}, "opacity": {}, "scale": {}, "render_quality": {}}


def load_report(tmp_path: Path) -> dict:
    return json.loads((tmp_path / "validation" / "validation_report.json").read_text())


def test_good_coverage_geometry_and_appearance_is_deliverable(tmp_path):
    write_summaries(tmp_path, coverage(3, 20, 1000, 0), good_geometry(), good_appearance())
    write_json(tmp_path / "engine_contract.json", {"version": "1.0.3"})
    write_json(tmp_path / "evidence_manifest.json", {"version": "1.0.3"})

    result = run_script(tmp_path)

    assert result.returncode == 0, result.stderr
    report = load_report(tmp_path)
    assert report["version"] == "1.0.3"
    assert report["job_id"] == tmp_path.name
    assert report["scores"] == {"capture": 100, "geometry": 100, "appearance": 100, "cross_validation": 100}
    assert report["decision"]["status"] == "deliverable"
    assert report["decision"]["root_cause"] == "unknown"
    assert report["decision"]["grade"] == "A"
    assert "Good Dataset" in report["decision"]["summary"]
    assert "Decision: deliverable" in report["report_text"]
    assert "Capture 100" in report["report_text"]
    assert report["evidence_regions"] == []
    assert report["inputs"]["coverage_summary"] == "evidence/coverage_summary.json"
    assert report["inputs"]["engine_contract"] == "engine_contract.json"
    assert str(tmp_path / "validation" / "validation_report.json") in result.stdout


def test_low_coverage_low_geometry_good_appearance_flags_mesh_risk(tmp_path):
    write_summaries(tmp_path, coverage(0.2, 1, 10, 5), low_geometry(), good_appearance())

    result = run_script(tmp_path)

    assert result.returncode == 0, result.stderr
    decision = load_report(tmp_path)["decision"]
    assert decision["status"] == "review_needed"
    assert decision["root_cause"] == "capture"
    assert "Mesh Risk" in decision["summary"]
    assert "Possible 3DGS Overfit" in decision["summary"]


def test_good_coverage_good_geometry_low_appearance_flags_appearance_issue(tmp_path):
    write_summaries(tmp_path, coverage(3, 20, 1000, 0), good_geometry(), low_appearance())

    result = run_script(tmp_path)

    assert result.returncode == 0, result.stderr
    decision = load_report(tmp_path)["decision"]
    assert decision["status"] == "review_needed"
    assert decision["root_cause"] == "texture"
    assert "Appearance Issue" in decision["summary"]


def test_low_coverage_low_geometry_low_appearance_recommends_recapture(tmp_path):
    write_summaries(tmp_path, coverage(0.2, 1, 10, 5), low_geometry(), low_appearance())

    result = run_script(tmp_path)

    assert result.returncode == 0, result.stderr
    decision = load_report(tmp_path)["decision"]
    assert decision["status"] == "recapture_recommended"
    assert decision["root_cause"] == "capture"
    assert "Capture Failure" in decision["summary"]


def test_missing_inputs_write_zero_score_report(tmp_path):
    result = run_script(tmp_path)

    assert result.returncode == 0, result.stderr
    report = load_report(tmp_path)
    assert report["scores"] == {"capture": 0, "geometry": 0, "appearance": 0, "cross_validation": 0}
    assert report["decision"]["status"] == "recapture_recommended"
    assert report["inputs"] == {}


def test_failed_engine_contract_emits_engine_failed_decision(tmp_path):
    write_json(
        tmp_path / "engine_contract.json",
        {
            "version": "1.0.3",
            "engine": "gaussian_splat",
            "status": "failed",
            "errors": ["training failed"],
        },
    )

    result = run_script(tmp_path)

    assert result.returncode == 0, result.stderr
    decision = load_report(tmp_path)["decision"]
    assert decision["status"] == "engine_failed"
    assert decision["root_cause"] == "engine"
    assert "training failed" in decision["summary"]


def test_malformed_json_fails_clearly(tmp_path):
    bad = tmp_path / "evidence" / "coverage_summary.json"
    bad.parent.mkdir()
    bad.write_text("{bad")

    result = run_script(tmp_path)

    assert result.returncode == 1
    assert "Malformed JSON" in result.stderr
    assert "coverage_summary.json" in result.stderr


def test_custom_output_writes_path_and_prints_it(tmp_path):
    write_summaries(tmp_path, coverage(3, 20, 1000, 0), good_geometry(), good_appearance())
    output = tmp_path / "reports" / "custom_validation.json"

    result = run_script(tmp_path, "--output", output)

    assert result.returncode == 0, result.stderr
    assert output.exists()
    assert str(output) in result.stdout
