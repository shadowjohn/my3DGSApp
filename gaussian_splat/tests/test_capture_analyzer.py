from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def require_cv2() -> None:
    if cv2 is None or np is None:
        pytest.skip("OpenCV and numpy are required for synthetic image tests")


def analyze_capture(path: Path) -> dict:
    from scripts.capture_analyzer import analyze_capture as run

    return run(path)


def write_image(path: Path, image) -> None:
    require_cv2()
    path.parent.mkdir(parents=True, exist_ok=True)
    ok = cv2.imwrite(str(path), image)
    assert ok


def checkerboard(size: int = 128, square_size: int = 8):
    require_cv2()
    coords = np.indices((size, size)) // square_size
    grid = coords.sum(axis=0) % 2
    return (grid * 255).astype(np.uint8)


def shifted_checkerboard(shift: int):
    require_cv2()
    return np.roll(checkerboard(), shift=shift, axis=1)


def test_diverse_sharp_frames_get_high_confidence_run_decision(tmp_path):
    require_cv2()
    frames = tmp_path / "frames"
    for index, shift in enumerate(range(0, 36, 3), start=1):
        write_image(frames / f"frame_{index:03d}.png", shifted_checkerboard(shift))

    report = analyze_capture(frames)

    assert report["confidenceScore"] >= 0.8
    assert report["decision"] == "run"
    assert report["metrics"]["frameCount"] == 12
    assert report["estimatedRisk"]["blur"] == "low"
    assert report["estimatedRisk"]["motion"] == "low"


def test_blurry_duplicate_low_frame_input_gets_lower_confidence(tmp_path):
    require_cv2()
    frames = tmp_path / "frames"
    blurry = cv2.GaussianBlur(checkerboard(), (31, 31), 0)
    for index in range(1, 4):
        write_image(frames / f"frame_{index:03d}.png", blurry)

    report = analyze_capture(frames)

    assert report["confidenceScore"] < 0.6
    assert report["decision"] in {
        "warn",
        "require_override",
        "recapture_recommended",
    }
    assert report["metrics"]["frameCount"] == 3
    assert report["estimatedRisk"]["blur"] in {"medium", "high"}
    assert report["estimatedRisk"]["duplicates"] in {"medium", "high"}
    assert report["recommendations"]


def test_report_contains_required_top_level_fields(tmp_path):
    require_cv2()
    frames = tmp_path / "frames"
    for index, shift in enumerate((0, 4, 8, 12, 16, 20), start=1):
        write_image(frames / f"frame_{index:03d}.png", shifted_checkerboard(shift))

    report = analyze_capture(frames)

    assert set(report) >= {
        "confidenceScore",
        "grade",
        "decision",
        "estimatedRisk",
        "metrics",
        "recommendations",
    }
    assert 0.0 <= report["confidenceScore"] <= 1.0
    assert report["decision"] in {
        "run",
        "warn",
        "require_override",
        "recapture_recommended",
    }
    assert isinstance(report["estimatedRisk"], dict)
    assert isinstance(report["metrics"], dict)
    assert isinstance(report["recommendations"], list)


def test_cli_writes_output_path_and_prints_it(tmp_path):
    require_cv2()
    frames = tmp_path / "frames"
    output = tmp_path / "confidence_report.json"
    for index, shift in enumerate((0, 4, 8, 12, 16, 20), start=1):
        write_image(frames / f"frame_{index:03d}.png", shifted_checkerboard(shift))

    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "capture_analyzer.py"),
            str(frames),
            "--output",
            str(output),
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.stdout.strip() == str(output)
    data = json.loads(output.read_text())
    assert data["metrics"]["frameCount"] == 6
    assert set(data) >= {
        "confidenceScore",
        "grade",
        "decision",
        "estimatedRisk",
        "metrics",
        "recommendations",
    }


def test_image_directory_analysis_imports_and_reports_without_opencv(tmp_path):
    frames = tmp_path / "frames"
    frames.mkdir()
    for index in range(1, 4):
        (frames / f"frame_{index:03d}.jpg").write_bytes(b"not-a-real-image")

    code = f"""
import importlib.abc
import json
import sys

class BlockCv2(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "cv2" or fullname.startswith("cv2."):
            raise ModuleNotFoundError("No module named 'cv2'")
        return None

sys.meta_path.insert(0, BlockCv2())
sys.path.insert(0, {str(PROJECT_ROOT)!r})

from scripts.capture_analyzer import analyze_capture

print(json.dumps(analyze_capture({str(frames)!r}), sort_keys=True))
"""

    result = subprocess.run(
        [sys.executable, "-c", code],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["metrics"]["frameCount"] == 3
    assert set(data) >= {
        "confidenceScore",
        "grade",
        "decision",
        "estimatedRisk",
        "metrics",
        "recommendations",
    }


def test_video_without_opencv_fails_with_clear_error(tmp_path, monkeypatch):
    import scripts.capture_analyzer as capture_analyzer

    monkeypatch.setattr(capture_analyzer, "cv2", None)
    video = tmp_path / "capture.mp4"
    video.write_bytes(b"fake-video")

    with pytest.raises(ValueError, match="Video input requires OpenCV"):
        capture_analyzer.analyze_capture(video)


def test_video_sampling_seeks_to_bounded_frame_indices(monkeypatch, tmp_path):
    import scripts.capture_analyzer as capture_analyzer

    reads = []
    seeks = []

    class FakeCapture:
        def __init__(self, path):
            self.path = path
            self.position = 0

        def isOpened(self):
            return True

        def get(self, prop):
            if prop == fake_cv2.CAP_PROP_FRAME_COUNT:
                return 10000
            return 0

        def set(self, prop, value):
            seeks.append((prop, int(value)))
            self.position = int(value)
            return True

        def read(self):
            reads.append(self.position)
            self.position += 1
            return True, object()

        def release(self):
            pass

    class FakeCv2:
        CAP_PROP_FRAME_COUNT = 7
        CAP_PROP_POS_FRAMES = 1
        COLOR_BGR2GRAY = 2

        def VideoCapture(self, path):
            return FakeCapture(path)

        def cvtColor(self, frame, mode):
            return frame

    fake_cv2 = FakeCv2()
    monkeypatch.setattr(capture_analyzer, "cv2", fake_cv2)
    monkeypatch.setattr(
        capture_analyzer,
        "opencv_sample",
        lambda frame: capture_analyzer.FrameSample(1.0, 0.5, 0.5, [0]),
    )

    video = tmp_path / "capture.mp4"
    video.write_bytes(b"fake-video")

    samples = capture_analyzer.load_video_frames(video, max_frames=5)

    assert len(samples) == 5
    assert len(reads) <= 6
    assert reads == [0, 2499, 4999, 7499, 9999]
    assert [value for prop, value in seeks] == reads


def test_existing_colmap_sfm_report_updates_registration_risk(tmp_path):
    require_cv2()
    job = tmp_path / "job"
    frames = job / "images"
    for index, shift in enumerate(range(0, 36, 3), start=1):
        write_image(frames / f"frame_{index:03d}.png", shifted_checkerboard(shift))
    sfm_report = job / "processed" / "sfm_report.json"
    sfm_report.parent.mkdir(parents=True)
    sfm_report.write_text(
        json.dumps({"image_count": 12, "registered_count": 3, "registered_ratio": 0.25}),
        encoding="utf-8",
    )

    report = analyze_capture(frames)

    assert report["metrics"]["colmapRegistrationProbe"] == {
        "source": "processed/sfm_report.json",
        "registeredRatio": 0.25,
        "registeredCount": 3,
        "imageCount": 12,
    }
    assert report["estimatedRisk"]["registration"] == "high"
    assert any("COLMAP" in item for item in report["recommendations"])
