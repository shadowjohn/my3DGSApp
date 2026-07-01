import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "pipeline_timing.py"


def load_adapter():
    if not SCRIPT_PATH.exists():
        pytest.fail(f"missing timing script: {SCRIPT_PATH}")
    spec = importlib.util.spec_from_file_location("pipeline_timing", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_timing_script_records_stage_duration_with_epoch_clock(tmp_path, monkeypatch):
    adapter = load_adapter()
    report = tmp_path / "timing_report.json"
    ticks = iter([100.0, 110.5, 140.25, 145.25])
    monkeypatch.setattr(adapter.time, "time", lambda: next(ticks))

    assert adapter.main(["init", str(report), "pipeline", "Gaussian Splat pipeline"]) == 0
    assert adapter.main(["start", str(report), "train", "splatfacto training"]) == 0
    assert adapter.main(["finish", str(report), "train", "success", "ok"]) == 0
    assert adapter.main(["finish", str(report), "pipeline", "success", "done"]) == 0

    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["status"] == "success"
    assert data["duration_seconds"] == 45.25
    assert data["stages"][0]["key"] == "train"
    assert data["stages"][0]["label"] == "splatfacto training"
    assert data["stages"][0]["status"] == "success"
    assert data["stages"][0]["duration_seconds"] == 29.75
    assert data["stages"][0]["message"] == "ok"


def test_timing_script_marks_open_stage_failed_when_pipeline_fails(tmp_path, monkeypatch):
    adapter = load_adapter()
    report = tmp_path / "timing_report.json"
    ticks = iter([10.0, 12.0, 20.0])
    monkeypatch.setattr(adapter.time, "time", lambda: next(ticks))

    assert adapter.main(["init", str(report), "pipeline", "Gaussian Splat pipeline"]) == 0
    assert adapter.main(["start", str(report), "colmap", "COLMAP pose estimation"]) == 0
    assert adapter.main(["fail", str(report), "pipeline", "failed", "COLMAP failed"]) == 0

    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["status"] == "failed"
    assert data["message"] == "COLMAP failed"
    assert data["duration_seconds"] == 10.0
    assert data["stages"][0]["key"] == "colmap"
    assert data["stages"][0]["status"] == "failed"
    assert data["stages"][0]["duration_seconds"] == 8.0
