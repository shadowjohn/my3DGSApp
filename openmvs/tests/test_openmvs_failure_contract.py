import json
import importlib.util
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_failure(job: Path, *args: str) -> None:
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build_failure_summary.py"), str(job), *args], check=True)


def load_failure_summary_module():
    spec = importlib.util.spec_from_file_location(
        "build_failure_summary",
        ROOT / "scripts" / "build_failure_summary.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_script_module(name: str):
    spec = importlib.util.spec_from_file_location(
        name,
        ROOT / "scripts" / f"{name}.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_failure_summary_writes_contract_validation_and_summary(tmp_path):
    job = tmp_path / "failed"
    job.mkdir()

    run_failure(
        job,
        "--failed-stage",
        "colmap_mapper",
        "--reason",
        "registered images 2/20",
        "--diagnostic-warning",
        "openmvs.nonzero_exit failed",
    )

    summary = json.loads((job / "failure_summary.json").read_text())
    contract = json.loads((job / "engine_contract.json").read_text())
    validation = json.loads((job / "validation" / "validation_report.json").read_text())

    assert summary["engine_failed"] is True
    assert summary["root_cause"] == "capture"
    assert summary["failed_stage"] == "colmap_mapper"
    assert summary["retryable"] is False
    assert summary["recapture_recommended"] is True
    assert summary["recommendations"]
    assert summary["diagnostic_warnings"] == ["openmvs.nonzero_exit failed"]
    assert contract["status"] == "failed"
    assert contract["errors"][0]["stage"] == "colmap_mapper"
    assert validation["decision"]["status"] == "engine_failed"
    assert validation["decision"]["root_cause"] == "capture"


def test_failure_summary_marks_texture_failures_retryable(tmp_path):
    job = tmp_path / "texture"
    job.mkdir()

    run_failure(job, "--failed-stage", "openmvs_texture", "--reason", "TextureMesh failed")

    summary = json.loads((job / "failure_summary.json").read_text())
    assert summary["root_cause"] == "engine"
    assert summary["retryable"] is True
    assert summary["recapture_recommended"] is False


def test_failure_summary_ignores_parent_chmod_permission_error(tmp_path, monkeypatch):
    module = load_failure_summary_module()
    original_chmod = Path.chmod

    def chmod_maybe_denied(path: Path, mode: int, *args, **kwargs):
        if path.is_dir():
            raise PermissionError("chmod denied")
        return original_chmod(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "chmod", chmod_maybe_denied)

    output = tmp_path / "job" / "failure_summary.json"
    module.write_json(output, {"ok": True})

    assert json.loads(output.read_text()) == {"ok": True}


def test_standard_artifact_scripts_ignore_parent_chmod_permission_error(tmp_path, monkeypatch):
    original_chmod = Path.chmod

    def chmod_maybe_denied(path: Path, mode: int, *args, **kwargs):
        if path.is_dir():
            raise PermissionError("chmod denied")
        return original_chmod(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "chmod", chmod_maybe_denied)

    job = tmp_path / "job"
    job.mkdir()
    scripts = [
        ("build_engine_contract", [str(job), "--mode", "fast", "--pipeline-mode", "openmvs_native"]),
        ("build_validation_report", [str(job)]),
        ("build_delivery_manifest", [str(job)]),
    ]
    for script_name, args in scripts:
        module = load_script_module(script_name)
        monkeypatch.setattr(sys, "argv", [f"{script_name}.py", *args])
        assert module.main() == 0

    assert (job / "engine_contract.json").is_file()
    assert (job / "validation" / "validation_report.json").is_file()
    assert (job / "delivery_manifest.json").is_file()
