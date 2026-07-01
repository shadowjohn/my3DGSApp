import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_qa_validation_report.py"


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


def write_default_report(job: Path, status: str, root_cause: str, score: int = 90) -> None:
    write_json(
        job / "validation" / "validation_report.json",
        {
            "version": "1.0.3",
            "decision": {
                "status": status,
                "root_cause": root_cause,
                "grade": "A" if score >= 90 else "C",
                "summary": "default engine summary",
            },
            "scores": {
                "capture": score,
                "geometry": score,
                "appearance": score,
                "cross_validation": score,
            },
        },
    )


def write_appearance(job: Path, available: bool = True) -> None:
    write_json(
        job / "evidence" / "appearance_summary.json",
        {
            "splat": {"available": available, "count": 1200 if available else 0},
            "opacity": {"available": available},
            "scale": {"available": available},
            "render_quality": {"available": available},
        },
    )


def load_qa(job: Path) -> dict:
    return json.loads((job / "validation" / "qa_validation_report.json").read_text())


def test_qa_report_marks_gaussian_as_diagnostic_only(tmp_path):
    write_default_report(tmp_path, "deliverable", "unknown")
    write_appearance(tmp_path, True)

    result = run_script(tmp_path)

    assert result.returncode == 0, result.stderr
    report = load_qa(tmp_path)
    assert report["mode"] == "qa"
    assert report["engines"]["default"]["role"] == "delivery_candidate"
    assert report["engines"]["diagnostic"]["engine"] == "gaussian_splat"
    assert report["engines"]["diagnostic"]["role"] == "diagnostic"
    assert report["engines"]["diagnostic"]["delivery"] is False
    assert report["decision"]["issue_type"] == "none"


def test_capture_issue_when_default_engine_recommends_recapture(tmp_path):
    write_default_report(tmp_path, "recapture_recommended", "capture", 25)
    write_appearance(tmp_path, True)

    result = run_script(tmp_path)

    assert result.returncode == 0, result.stderr
    report = load_qa(tmp_path)
    assert report["decision"]["issue_type"] == "capture_issue"
    assert report["issue_counts"]["capture_issue"] == 1
    assert report["issue_counts"]["mesh_issue"] == 0


def test_mesh_issue_when_default_engine_is_weak_but_splat_exists(tmp_path):
    write_default_report(tmp_path, "review_needed", "engine", 55)
    write_appearance(tmp_path, True)

    result = run_script(tmp_path)

    assert result.returncode == 0, result.stderr
    report = load_qa(tmp_path)
    assert report["decision"]["issue_type"] == "mesh_issue"
    assert report["issue_counts"]["mesh_issue"] == 1


def test_splat_issue_when_delivery_candidate_is_ok_but_splat_is_weak(tmp_path):
    write_default_report(tmp_path, "deliverable", "unknown", 95)
    write_appearance(tmp_path, False)

    result = run_script(tmp_path)

    assert result.returncode == 0, result.stderr
    report = load_qa(tmp_path)
    assert report["decision"]["issue_type"] == "splat_issue"
    assert report["issue_counts"]["splat_issue"] == 1
