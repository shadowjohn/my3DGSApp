from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def sample_report(decision: str = "run") -> dict:
    return {
        "confidenceScore": 0.82,
        "grade": "B+",
        "decision": decision,
        "estimatedRisk": {"registration": "low"},
        "metrics": {"frameCount": 12},
        "recommendations": ["keep orbiting slowly"],
    }


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_missing_report_runs_analyzer_and_writes_report_and_gate(tmp_path, monkeypatch):
    from scripts import confidence_gate

    job_dir = tmp_path / "job"
    input_path = tmp_path / "input.mp4"
    input_path.write_bytes(b"fake")
    calls = []

    def fake_analyze(path):
        calls.append(Path(path))
        return sample_report("warn")

    monkeypatch.setattr(confidence_gate, "analyze_capture", fake_analyze)

    gate = confidence_gate.run_confidence_gate(job_dir, input_path)

    assert calls == [input_path]
    assert (job_dir / "confidence_report.json").is_file()
    assert (job_dir / "confidence_gate.json").is_file()
    assert read_json(job_dir / "confidence_report.json")["decision"] == "warn"
    assert gate["decision"] == "warn"
    assert gate["effectiveDecision"] == "warn"
    assert gate["score"] == 0.82
    assert gate["grade"] == "B+"
    assert gate["risks"] == {"registration": "low"}
    assert gate["recommendations"] == ["keep orbiting slowly"]


def test_existing_report_is_reused_without_analyzer(tmp_path, monkeypatch):
    from scripts import confidence_gate

    job_dir = tmp_path / "job"
    job_dir.mkdir()
    (job_dir / "confidence_report.json").write_text(
        json.dumps(sample_report("run")), encoding="utf-8"
    )
    input_path = tmp_path / "missing-input.mp4"
    monkeypatch.setattr(
        confidence_gate,
        "analyze_capture",
        lambda path: (_ for _ in ()).throw(AssertionError("analyzer should not run")),
    )

    gate = confidence_gate.run_confidence_gate(job_dir, input_path)

    assert gate["decision"] == "run"
    assert gate["effectiveDecision"] == "run"
    assert gate["reportPath"].endswith("confidence_report.json")


def test_gate_maps_analyzer_decisions(tmp_path, monkeypatch):
    from scripts import confidence_gate

    expected = {
        "run": "run",
        "warn": "warn",
        "require_override": "hold",
        "recapture_recommended": "reject",
        "hold": "hold",
        "reject": "reject",
        "mystery": "reject",
    }

    for original, decision in expected.items():
        job_dir = tmp_path / original
        job_dir.mkdir()
        (job_dir / "confidence_report.json").write_text(
            json.dumps(sample_report(original)), encoding="utf-8"
        )
        gate = confidence_gate.run_confidence_gate(job_dir, tmp_path / "input.mp4")
        assert gate["originalDecision"] == original
        assert gate["decision"] == decision
        assert gate["effectiveDecision"] == decision


def test_override_allows_hold_but_preserves_original_decision(tmp_path):
    from scripts import confidence_gate

    job_dir = tmp_path / "job"
    job_dir.mkdir()
    (job_dir / "confidence_report.json").write_text(
        json.dumps(sample_report("require_override")), encoding="utf-8"
    )

    gate = confidence_gate.run_confidence_gate(
        job_dir,
        tmp_path / "input.mp4",
        override=True,
        override_reason="site owner accepts risk",
    )

    assert gate["originalDecision"] == "require_override"
    assert gate["decision"] == "hold"
    assert gate["effectiveDecision"] == "run_with_override"
    assert gate["override"]["enabled"] is True
    assert gate["override"]["reason"] == "site owner accepts risk"


def test_override_does_not_allow_reject(tmp_path):
    from scripts import confidence_gate

    job_dir = tmp_path / "job"
    job_dir.mkdir()
    (job_dir / "confidence_report.json").write_text(
        json.dumps(sample_report("recapture_recommended")), encoding="utf-8"
    )

    gate = confidence_gate.run_confidence_gate(
        job_dir,
        tmp_path / "input.mp4",
        override=True,
        override_reason="try anyway",
    )

    assert gate["decision"] == "reject"
    assert gate["effectiveDecision"] == "reject"


def test_malformed_existing_report_rejects_without_analyzer(tmp_path, monkeypatch):
    from scripts import confidence_gate

    job_dir = tmp_path / "job"
    job_dir.mkdir()
    (job_dir / "confidence_report.json").write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(
        confidence_gate,
        "analyze_capture",
        lambda path: (_ for _ in ()).throw(AssertionError("analyzer should not run")),
    )

    gate = confidence_gate.run_confidence_gate(job_dir, tmp_path / "input.mp4")

    assert gate["decision"] == "reject"
    assert gate["effectiveDecision"] == "reject"
    assert "Malformed confidence_report.json" in gate["reason"]
    assert read_json(job_dir / "confidence_gate.json")["decision"] == "reject"


def test_analyzer_exception_fails_closed_with_visible_reason(tmp_path, monkeypatch):
    from scripts import confidence_gate

    job_dir = tmp_path / "job"
    input_path = tmp_path / "input.mp4"
    input_path.write_bytes(b"fake")

    def fail_analyze(path):
        raise ValueError("OpenCV cannot read video")

    monkeypatch.setattr(confidence_gate, "analyze_capture", fail_analyze)

    gate = confidence_gate.run_confidence_gate(job_dir, input_path)

    assert gate["decision"] == "reject"
    assert gate["effectiveDecision"] == "reject"
    assert "Capture analysis failed: OpenCV cannot read video" in gate["reason"]
    assert "Capture analysis failed: OpenCV cannot read video" in gate["recommendations"]
    assert read_json(job_dir / "confidence_report.json")["decision"] == "reject"


def test_cli_writes_gate_json_and_prints_path(tmp_path):
    job_dir = tmp_path / "job"
    job_dir.mkdir()
    (job_dir / "confidence_report.json").write_text(
        json.dumps(sample_report("hold")), encoding="utf-8"
    )
    input_path = tmp_path / "input.mp4"
    input_path.write_bytes(b"fake")

    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "confidence_gate.py"),
            str(job_dir),
            str(input_path),
            "--override",
            "--override-reason",
            "reviewed",
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.stdout.strip() == str(job_dir / "confidence_gate.json")
    gate = read_json(job_dir / "confidence_gate.json")
    assert gate["originalDecision"] == "hold"
    assert gate["effectiveDecision"] == "run_with_override"
