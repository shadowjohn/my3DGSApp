import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.build_qa_report import build_report


def test_build_report_flags_low_registration(tmp_path):
    images = tmp_path / "images"
    processed = tmp_path / "processed"
    exports = tmp_path / "exports"
    images.mkdir()
    processed.mkdir()
    exports.mkdir()
    for i in range(10):
        (images / f"frame_{i:05d}.jpg").write_bytes(b"jpg")
    transforms = {
        "frames": [{"file_path": f"images/frame_{i:05d}.jpg"} for i in range(6)]
    }
    (processed / "transforms.json").write_text(json.dumps(transforms))
    (exports / "splat.ply").write_bytes(b"x" * 1024)

    report = build_report("site001", images, processed, exports, has_transform=True)
    assert report["frame_count"] == 10
    assert report["registered_frame_count"] == 6
    assert report["registered_ratio"] == 0.6
    assert report["viewer_ready"] is True
    assert "registered_ratio lower than 0.8" in report["warnings"]


def test_build_report_marks_missing_splat_not_ready(tmp_path):
    images = tmp_path / "images"
    processed = tmp_path / "processed"
    exports = tmp_path / "exports"
    images.mkdir()
    processed.mkdir()
    exports.mkdir()
    (processed / "transforms.json").write_text('{"frames": []}')

    report = build_report("site002", images, processed, exports, has_transform=False)
    assert report["viewer_ready"] is False
    assert "splat.ply missing" in report["warnings"]
    assert "transform.json missing" in report["warnings"]


def test_build_report_handles_malformed_transforms_json(tmp_path):
    images = tmp_path / "images"
    processed = tmp_path / "processed"
    exports = tmp_path / "exports"
    images.mkdir()
    processed.mkdir()
    exports.mkdir()
    (images / "frame_00000.jpg").write_bytes(b"jpg")
    (processed / "transforms.json").write_text("{")
    (exports / "splat.ply").write_bytes(b"x")

    report = build_report("site003", images, processed, exports, has_transform=True)
    assert report["registered_frame_count"] == 0
    assert "transforms.json invalid" in report["warnings"]


def test_build_report_flags_non_list_frames_invalid(tmp_path):
    images = tmp_path / "images"
    processed = tmp_path / "processed"
    exports = tmp_path / "exports"
    images.mkdir()
    processed.mkdir()
    exports.mkdir()
    (processed / "transforms.json").write_text(json.dumps({"frames": {"bad": True}}))

    report = build_report("site004", images, processed, exports, has_transform=True)
    assert report["registered_frame_count"] == 0
    assert "transforms.json invalid" in report["warnings"]


def test_build_report_flags_non_object_transforms_invalid(tmp_path):
    images = tmp_path / "images"
    processed = tmp_path / "processed"
    exports = tmp_path / "exports"
    images.mkdir()
    processed.mkdir()
    exports.mkdir()
    (processed / "transforms.json").write_text("[]")

    report = build_report("site005", images, processed, exports, has_transform=True)
    assert report["registered_frame_count"] == 0
    assert "transforms.json invalid" in report["warnings"]


def test_build_report_viewer_ready_only_requires_splat(tmp_path):
    images = tmp_path / "images"
    processed = tmp_path / "processed"
    exports = tmp_path / "exports"
    images.mkdir()
    processed.mkdir()
    exports.mkdir()
    (processed / "transforms.json").write_text('{"frames": []}')
    (exports / "splat.ply").write_bytes(b"x")

    report = build_report("site006", images, processed, exports, has_transform=False)
    assert report["viewer_ready"] is True
    assert "transform.json missing" in report["warnings"]


def test_build_report_includes_frame_quality_summary(tmp_path):
    images = tmp_path / "images"
    processed = tmp_path / "processed"
    exports = tmp_path / "exports"
    images.mkdir()
    processed.mkdir()
    exports.mkdir()
    (processed / "transforms.json").write_text('{"frames": []}')
    (exports / "splat.ply").write_bytes(b"x")
    (tmp_path / "frame_quality_report.json").write_text(
        json.dumps(
            {
                "candidate_count": 120,
                "selected_count": 80,
                "candidate_fps": 8,
                "target_fps": 3,
            }
        )
    )

    report = build_report("site007", images, processed, exports, has_transform=True)
    assert report["frame_quality"] == {
        "candidate_count": 120,
        "selected_count": 80,
        "candidate_fps": 8,
        "target_fps": 3,
    }


def test_build_report_includes_sfm_mapper_summary(tmp_path):
    images = tmp_path / "images"
    processed = tmp_path / "processed"
    exports = tmp_path / "exports"
    images.mkdir()
    processed.mkdir()
    exports.mkdir()
    (processed / "transforms.json").write_text('{"frames": []}')
    (processed / "sfm_report.json").write_text(
        json.dumps(
            {
                "mapper": "hierarchical",
                "matcher": "exhaustive",
                "registered_count": 37,
                "registered_ratio": 0.77,
                "sparse_model_path": "processed/colmap/sparse/0",
            }
        )
    )
    (exports / "splat.ply").write_bytes(b"x")

    report = build_report("site-sfm", images, processed, exports, has_transform=True)

    assert report["sfm"] == {
        "mapper": "hierarchical",
        "matcher": "exhaustive",
        "registered_count": 37,
        "registered_ratio": 0.77,
        "sparse_model_path": "processed/colmap/sparse/0",
    }


def test_build_report_warns_when_selected_frame_quality_count_low(tmp_path):
    images = tmp_path / "images"
    processed = tmp_path / "processed"
    exports = tmp_path / "exports"
    images.mkdir()
    processed.mkdir()
    exports.mkdir()
    (processed / "transforms.json").write_text('{"frames": []}')
    (exports / "splat.ply").write_bytes(b"x")
    (tmp_path / "frame_quality_report.json").write_text(
        json.dumps(
            {
                "candidate_count": 120,
                "selected_count": 59,
                "candidate_fps": 8,
                "target_fps": 3,
            }
        )
    )

    report = build_report("site008", images, processed, exports, has_transform=True)
    assert "selected frame count lower than 60" in report["warnings"]


@pytest.mark.parametrize(
    "report_body",
    [
        "{",
        "[]",
        json.dumps(
            {
                "selected_count": 80,
                "candidate_fps": 8,
                "target_fps": 3,
            }
        ),
        json.dumps(
            {
                "candidate_count": 120,
                "selected_count": "many",
                "candidate_fps": 8,
                "target_fps": 3,
            }
        ),
    ],
)
def test_build_report_warns_and_skips_invalid_frame_quality_report(
    tmp_path, report_body
):
    images = tmp_path / "images"
    processed = tmp_path / "processed"
    exports = tmp_path / "exports"
    images.mkdir()
    processed.mkdir()
    exports.mkdir()
    (processed / "transforms.json").write_text('{"frames": []}')
    (exports / "splat.ply").write_bytes(b"x")
    (tmp_path / "frame_quality_report.json").write_text(report_body)

    report = build_report("site009", images, processed, exports, has_transform=True)
    assert "frame_quality" not in report
    assert "frame_quality_report.json invalid" in report["warnings"]


def test_cli_writes_qa_report_and_prints_output_path(tmp_path):
    job_dir = tmp_path / "job"
    images = job_dir / "images"
    processed = job_dir / "processed"
    exports = job_dir / "exports"
    images.mkdir(parents=True)
    processed.mkdir()
    exports.mkdir()
    (images / "frame_00000.jpg").write_bytes(b"jpg")
    (processed / "transforms.json").write_text('{"frames": []}')
    (exports / "splat.ply").write_bytes(b"x")

    script = Path(__file__).resolve().parents[1] / "scripts" / "build_qa_report.py"
    result = subprocess.run(
        [sys.executable, str(script), "site007", str(job_dir)],
        check=True,
        capture_output=True,
        text=True,
    )

    output = job_dir / "qa_report.json"
    assert output.is_file()
    assert str(output) in result.stdout
    report = json.loads(output.read_text())
    assert report["job_id"] == "site007"


def test_build_report_includes_customer_quality_grade(tmp_path):
    images = tmp_path / "images"
    processed = tmp_path / "processed"
    exports = tmp_path / "exports"
    images.mkdir()
    processed.mkdir()
    exports.mkdir()
    for index in range(100):
        (images / f"frame_{index:05d}.jpg").write_bytes(b"jpg")
    (processed / "transforms.json").write_text(
        json.dumps(
            {
                "frames": [
                    {"file_path": f"images/frame_{index:05d}.jpg"}
                    for index in range(92)
                ]
            }
        )
    )
    (exports / "splat.ply").write_text(
        "ply\nformat binary_little_endian 1.0\nelement vertex 1328456\nproperty float x\nend_header\n"
    )

    report = build_report("site-grade", images, processed, exports, has_transform=True)

    assert report["registered_count"] == 92
    assert report["registered_ratio"] == 0.92
    assert report["splat_count"] == 1328456
    assert report["quality_grade"] == "A"
    assert report["quality_label"] == "excellent"


def test_build_report_grades_low_registration_as_d(tmp_path):
    images = tmp_path / "images"
    processed = tmp_path / "processed"
    exports = tmp_path / "exports"
    images.mkdir()
    processed.mkdir()
    exports.mkdir()
    for index in range(100):
        (images / f"frame_{index:05d}.jpg").write_bytes(b"jpg")
    (processed / "transforms.json").write_text(
        json.dumps(
            {
                "frames": [
                    {"file_path": f"images/frame_{index:05d}.jpg"}
                    for index in range(40)
                ]
            }
        )
    )
    (exports / "splat.ply").write_text(
        "ply\nformat binary_little_endian 1.0\nelement vertex 100\nproperty float x\nend_header\n"
    )

    report = build_report("site-low", images, processed, exports, has_transform=True)

    assert report["splat_count"] == 100
    assert report["quality_grade"] == "D"
    assert report["quality_label"] == "retake_recommended"
