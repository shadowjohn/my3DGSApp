import json
import subprocess
import sys
from pathlib import Path

from scripts.annotate_frame_quality_colmap import annotate_report


def test_annotate_report_marks_registered_selected_frames(tmp_path):
    report = tmp_path / "frame_quality_report.json"
    transforms = tmp_path / "processed" / "transforms.json"
    transforms.parent.mkdir()
    report.write_text(
        json.dumps(
            {
                "candidate_count": 20,
                "selected_count": 2,
                "candidate_fps": 12,
                "target_fps": 3,
                "selected": [
                    {"output_name": "frame_00001.jpg", "score": 1.2},
                    {"output_name": "frame_00002.jpg", "score": 0.8},
                ],
                "candidates": [],
            }
        )
    )
    transforms.write_text(
        json.dumps(
            {
                "frames": [
                    {
                        "file_path": "images/frame_00002.jpg",
                        "transform_matrix": [
                            [1, 0, 0, 4.0],
                            [0, 1, 0, 5.0],
                            [0, 0, 1, 6.0],
                        ],
                    }
                ]
            }
        )
    )

    annotated = annotate_report(report, transforms)

    assert annotated["selected"][0]["colmap_registered"] is False
    assert annotated["selected"][1]["colmap_registered"] is True
    assert annotated["selected"][1]["camera_position"] == [4.0, 5.0, 6.0]
    assert annotated["colmap"]["registered_count"] == 1
    assert annotated["colmap"]["registered_ratio"] == 0.5


def test_cli_updates_report_in_place(tmp_path):
    report = tmp_path / "frame_quality_report.json"
    transforms = tmp_path / "processed" / "transforms.json"
    transforms.parent.mkdir()
    report.write_text(json.dumps({"selected": [], "selected_count": 0, "candidate_count": 0, "candidate_fps": 12, "target_fps": 3}))
    transforms.write_text(json.dumps({"frames": []}))
    script = Path(__file__).resolve().parents[1] / "scripts" / "annotate_frame_quality_colmap.py"

    result = subprocess.run([sys.executable, str(script), str(report), str(transforms)], check=False, text=True, capture_output=True)

    assert result.returncode == 0, result.stderr
    assert json.loads(report.read_text())["colmap"]["registered_count"] == 0


def test_annotate_report_normalizes_malformed_selected_field(tmp_path):
    report = tmp_path / "frame_quality_report.json"
    transforms = tmp_path / "processed" / "transforms.json"
    transforms.parent.mkdir()
    report.write_text(json.dumps({"selected": {"bad": True}}))
    transforms.write_text(json.dumps({"frames": []}))

    annotated = annotate_report(report, transforms)

    assert annotated["selected"] == []
    assert annotated["colmap"]["registered_count"] == 0
    assert annotated["colmap"]["registered_ratio"] == 0.0
    assert json.loads(report.read_text())["selected"] == []


def test_annotate_report_skips_non_dict_selected_rows(tmp_path):
    report = tmp_path / "frame_quality_report.json"
    transforms = tmp_path / "processed" / "transforms.json"
    transforms.parent.mkdir()
    report.write_text(
        json.dumps(
            {
                "selected": [
                    None,
                    "bad",
                    {"output_name": "frame_00001.jpg", "score": 1.0},
                ],
            }
        )
    )
    transforms.write_text(
        json.dumps(
            {
                "frames": [
                    {
                        "file_path": "images/frame_00001.jpg",
                        "transform_matrix": [
                            [1, 0, 0, 1.0],
                            [0, 1, 0, 2.0],
                            [0, 0, 1, 3.0],
                        ],
                    }
                ]
            }
        )
    )

    annotated = annotate_report(report, transforms)

    assert annotated["selected"][0] is None
    assert annotated["selected"][1] == "bad"
    assert annotated["selected"][2]["colmap_registered"] is True
    assert annotated["selected"][2]["camera_position"] == [1.0, 2.0, 3.0]
    assert annotated["colmap"]["registered_count"] == 1
    assert annotated["colmap"]["registered_ratio"] == 1.0


def test_annotate_report_skips_malformed_transform_matrices(tmp_path):
    report = tmp_path / "frame_quality_report.json"
    transforms = tmp_path / "processed" / "transforms.json"
    transforms.parent.mkdir()
    report.write_text(
        json.dumps(
            {
                "selected": [
                    {"output_name": "frame_00001.jpg"},
                    {"output_name": "frame_00002.jpg"},
                ],
            }
        )
    )
    transforms.write_text(
        json.dumps(
            {
                "frames": [
                    {
                        "file_path": "images/frame_00001.jpg",
                        "transform_matrix": {
                            "0": [1, 0, 0, 9.0],
                            "1": [0, 1, 0, 9.0],
                            "2": [0, 0, 1, 9.0],
                        },
                    },
                    {
                        "file_path": "images/frame_00002.jpg",
                        "transform_matrix": [
                            [1, 0, 0, 4.0],
                            [0, 1, 0, 5.0],
                        ],
                    },
                ]
            }
        )
    )

    annotated = annotate_report(report, transforms)

    assert annotated["selected"][0]["colmap_registered"] is False
    assert annotated["selected"][0]["camera_position"] is None
    assert annotated["selected"][1]["colmap_registered"] is False
    assert annotated["selected"][1]["camera_position"] is None
    assert annotated["colmap"]["registered_count"] == 0
    assert annotated["colmap"]["registered_ratio"] == 0.0


def test_annotate_report_skips_non_string_output_names(tmp_path):
    report = tmp_path / "frame_quality_report.json"
    transforms = tmp_path / "processed" / "transforms.json"
    transforms.parent.mkdir()
    report.write_text(
        json.dumps(
            {
                "selected": [
                    {"output_name": ["frame_00001.jpg"]},
                    {"output_name": "frame_00002.jpg"},
                ],
            }
        )
    )
    transforms.write_text(
        json.dumps(
            {
                "frames": [
                    {
                        "file_path": "images/frame_00002.jpg",
                        "transform_matrix": [
                            [1, 0, 0, 4.0],
                            [0, 1, 0, 5.0],
                            [0, 0, 1, 6.0],
                        ],
                    }
                ]
            }
        )
    )

    annotated = annotate_report(report, transforms)

    assert "colmap_registered" not in annotated["selected"][0]
    assert annotated["selected"][1]["colmap_registered"] is True
    assert annotated["selected"][1]["camera_position"] == [4.0, 5.0, 6.0]
    assert annotated["colmap"]["registered_count"] == 1
    assert annotated["colmap"]["registered_ratio"] == 1.0
