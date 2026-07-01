import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_gaussian_engine_contract.py"


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def run_contract(job: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(job), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def write_appearance(job: Path) -> None:
    write_json(
        job / "evidence" / "appearance_summary.json",
        {
            "cameras": {"frame_count": 20, "registered_count": 18, "registered_ratio": 0.9},
            "splat": {
                "available": True,
                "path": "exports/splat.clean.ply",
                "count": 1234,
                "file_size_mb": 2.5,
            },
            "training": {"iterations": 30000, "training_time_seconds": 120.5},
            "validation": {
                "black_ratio": 0.03,
                "transparent_ratio": 0.12,
                "floating_artifact_risk": "medium",
            },
            "quality": {"grade": "A", "label": "good"},
        },
    )


def test_qa_contract_marks_gaussian_splat_as_diagnostic_only(tmp_path):
    write_appearance(tmp_path)

    result = run_contract(tmp_path, "--mode", "qa")

    assert result.returncode == 0, result.stderr
    contract = json.loads((tmp_path / "engine_contract.json").read_text())
    assert contract["schema_version"] == "1.0"
    assert contract["engine_name"] == "gaussian_splat"
    assert contract["engine_version"] == "1.0.3"
    assert contract["engine"] == "gaussian_splat"
    assert contract["engineType"] == "appearance_reconstruction"
    assert contract["pipeline_mode"] == "qa"
    assert contract["mode"] == "qa"
    assert contract["role"] == "diagnostic"
    assert contract["delivery_capable"] is False
    assert contract["status"] == "completed"
    assert contract["artifacts"][0]["role"] == "diagnostic"
    assert contract["artifacts"][0]["delivery_capable"] is False
    assert contract["artifacts"][0]["deliveryCapable"] is False
    assert contract["diagnostics"]["appearance_summary_path"] == "evidence/appearance_summary.json"
    assert contract["diagnostics"]["validation"]["floating_artifact_risk"] == "medium"
    assert contract["validation_summary"]["quality_grade"] == "A"
    assert contract["validation_summary"]["black_ratio"] == 0.03
    assert contract["metrics"]["splatCount"] == 1234
    assert contract["metrics"]["registrationRatio"] == 0.9
    assert "generated_at" in contract


def test_premium_contract_marks_gaussian_splat_as_delivery_capable(tmp_path):
    write_appearance(tmp_path)

    result = run_contract(tmp_path, "--mode", "premium")

    assert result.returncode == 0, result.stderr
    contract = json.loads((tmp_path / "engine_contract.json").read_text())
    assert contract["pipeline_mode"] == "premium"
    assert contract["role"] == "delivery_capable"
    assert contract["delivery_capable"] is True
    assert contract["artifacts"][0]["role"] == "delivery_capable"
    assert contract["artifacts"][0]["delivery_capable"] is True
    assert contract["artifacts"][0]["deliveryCapable"] is True


def test_missing_splat_writes_review_required_contract(tmp_path):
    write_json(tmp_path / "evidence" / "appearance_summary.json", {"splat": {"available": False}})

    result = run_contract(tmp_path, "--mode", "qa")

    assert result.returncode == 0, result.stderr
    contract = json.loads((tmp_path / "engine_contract.json").read_text())
    assert contract["status"] == "review_required"
    assert contract["artifacts"] == []
    assert contract["errors"] == ["splat artifact missing"]
