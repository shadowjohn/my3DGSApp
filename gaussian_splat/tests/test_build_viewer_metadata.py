import json
from pathlib import Path

import pytest

from scripts.build_viewer_metadata import (
    apply_dataparser_transform,
    first_registered_frame,
    first_photo_metadata,
)


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data) + "\n")


def test_first_registered_frame_reads_transforms_path_and_uses_chronological_filename(tmp_path):
    transforms_path = tmp_path / "transforms.json"
    write_json(
        transforms_path,
        {
            "frames": [
                {
                    "file_path": "images/frame_00089.jpg",
                    "transform_matrix": [
                        [1, 0, 0, 89],
                        [0, 1, 0, 0],
                        [0, 0, 1, 0],
                        [0, 0, 0, 1],
                    ],
                },
                {
                    "file_path": "images/frame_00001.jpg",
                    "transform_matrix": [
                        [1, 0, 0, 1],
                        [0, 1, 0, 2],
                        [0, 0, 1, 3],
                        [0, 0, 0, 1],
                    ],
                },
            ],
        },
    )

    frame = first_registered_frame(transforms_path)

    assert frame["file_path"] == "images/frame_00001.jpg"


def test_first_photo_metadata_uses_chronological_filename_not_transforms_order(tmp_path):
    transforms_path = tmp_path / "transforms.json"
    dataparser_path = tmp_path / "dataparser_transforms.json"
    write_json(
        transforms_path,
        {
            "frames": [
                {
                    "file_path": "images/frame_00089.jpg",
                    "transform_matrix": [
                        [1, 0, 0, 89],
                        [0, 1, 0, 0],
                        [0, 0, 1, 0],
                        [0, 0, 0, 1],
                    ],
                },
                {
                    "file_path": "images/frame_00001.jpg",
                    "transform_matrix": [
                        [1, 0, 0, 1],
                        [0, 1, 0, 2],
                        [0, 0, 1, 3],
                        [0, 0, 0, 1],
                    ],
                },
            ],
        },
    )
    write_json(
        dataparser_path,
        {
            "transform": [
                [1, 0, 0, 0],
                [0, 1, 0, 0],
                [0, 0, 1, 0],
            ],
            "scale": 1.0,
        },
    )

    metadata = first_photo_metadata(transforms_path, dataparser_path, look_distance=2.0)

    assert metadata["firstFrame"]["filePath"] == "images/frame_00001.jpg"
    assert metadata["firstFrame"]["transformMatrix"] == [
        [1, 0, 0, 1],
        [0, 1, 0, 2],
        [0, 0, 1, 3],
        [0, 0, 0, 1],
    ]
    assert metadata["firstFrame"]["cameraPosition"] == [1.0, 2.0, 3.0]
    assert metadata["firstFrame"]["cameraForward"] == [0.0, 0.0, -1.0]
    assert metadata["firstFrame"]["cameraLookAt"] == [1.0, 2.0, 1.0]


def test_apply_dataparser_transform_applies_translation_scale_and_forward():
    camera_to_world = [
        [1, 0, 0, 10],
        [0, 1, 0, 20],
        [0, 0, 1, 30],
        [0, 0, 0, 1],
    ]
    dataparser = {
        "transform": [
            [1, 0, 0, 1],
            [0, 1, 0, 2],
            [0, 0, 1, 3],
        ],
        "scale": 0.5,
    }

    transformed = apply_dataparser_transform(camera_to_world, dataparser)

    assert transformed["position"] == pytest.approx([5.5, 11.0, 16.5])
    assert transformed["forward"] == pytest.approx([0.0, 0.0, -1.0])
