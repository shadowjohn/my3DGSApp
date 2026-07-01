import json

from scripts.build_trench_coverage_report import build_coverage_report


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def test_build_coverage_report_from_frame_quality_and_transforms(tmp_path):
    job = tmp_path / "job"
    write_json(
        job / "input_manifest.json",
        {"input_mode": "walk_video", "warnings": []},
    )
    write_json(
        job / "frame_quality_report.json",
        {
            "candidate_count": 120,
            "selected_count": 60,
            "candidate_fps": 12,
            "target_fps": 3,
        },
    )
    write_json(
        job / "processed" / "transforms.json",
        {
            "frames": [
                {
                    "file_path": "images/frame_00001.jpg",
                    "transform_matrix": [
                        [1, 0, 0, 0],
                        [0, 1, 0, 0],
                        [0, 0, 1, 0],
                        [0, 0, 0, 1],
                    ],
                },
                {
                    "file_path": "images/frame_00002.jpg",
                    "transform_matrix": [
                        [1, 0, 0, 3],
                        [0, 1, 0, 4],
                        [0, 0, 1, 0],
                        [0, 0, 0, 1],
                    ],
                },
            ]
        },
    )

    report = build_coverage_report(job)

    assert report["input_mode"] == "walk_video"
    assert report["candidate_count"] == 120
    assert report["selected_count"] == 60
    assert report["registered_count"] == 2
    assert report["registered_ratio"] == 0.03
    assert report["camera_path_span"] == 5.0
    assert "registered_ratio lower than 0.65" in report["warnings"]
    assert report["coverage_decision"] == "retake"


def test_build_coverage_report_photo_set_with_sparse_images_warns(tmp_path):
    job = tmp_path / "job"
    write_json(
        job / "input_manifest.json",
        {
            "input_mode": "photo_set",
            "photos": [{"filename": "a.jpg"}],
            "warnings": ["photo_set lower than 8 images"],
        },
    )
    write_json(job / "processed" / "transforms.json", {"frames": []})

    report = build_coverage_report(job)

    assert report["input_mode"] == "photo_set"
    assert report["selected_count"] == 1
    assert report["registered_count"] == 0
    assert report["coverage_decision"] == "retake"
    assert "photo_set lower than 8 images" in report["warnings"]


def test_build_coverage_report_tolerates_malformed_transform_rows(tmp_path):
    job = tmp_path / "job"
    write_json(
        job / "frame_quality_report.json",
        {"candidate_count": 2, "selected_count": 2},
    )
    write_json(
        job / "processed" / "transforms.json",
        {
            "frames": [
                {"transform_matrix": [{}, {}, {}]},
                {"transform_matrix": [[1, 0], [0, 1], [0, 0]]},
            ]
        },
    )

    report = build_coverage_report(job)

    assert report["registered_count"] == 2
    assert report["camera_path_span"] == 0.0
