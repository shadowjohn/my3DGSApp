#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any


def natural_filename_key(file_path: str) -> list[int | str]:
    name = Path(file_path).name
    parts = re.split(r"([0-9]+)", name)
    return [int(part) if part.isascii() and part.isdigit() else part for part in parts]


def mat3_vec_mul(matrix: list[list[float]], vector: list[float]) -> list[float]:
    return [
        sum(float(matrix[row][col]) * vector[col] for col in range(3))
        for row in range(3)
    ]


def vector_add(left: list[float], right: list[float]) -> list[float]:
    return [left[index] + right[index] for index in range(3)]


def vector_scale(vector: list[float], scale: float) -> list[float]:
    return [component * scale for component in vector]


def normalize(vector: list[float]) -> list[float]:
    length = math.sqrt(sum(component * component for component in vector))
    if length == 0.0:
        raise ValueError("forward vector must be non-zero")
    return [component / length for component in vector]


def dataparser_rotation_translation(dataparser: dict[str, Any]) -> tuple[list[list[float]], list[float]]:
    transform = dataparser.get("transform")
    if not isinstance(transform, list) or len(transform) < 3:
        raise ValueError("dataparser transform must contain at least 3 rows")

    rotation = []
    translation = []
    for row in transform[:3]:
        if not isinstance(row, list) or len(row) < 4:
            raise ValueError("dataparser transform rows must contain at least 4 values")
        rotation.append([float(value) for value in row[:3]])
        translation.append(float(row[3]))

    return rotation, translation


def camera_rotation_position(camera_to_world: list[list[float]]) -> tuple[list[list[float]], list[float]]:
    if not isinstance(camera_to_world, list) or len(camera_to_world) < 3:
        raise ValueError("camera_to_world must contain at least 3 rows")

    rotation = []
    position = []
    for row in camera_to_world[:3]:
        if not isinstance(row, list) or len(row) < 4:
            raise ValueError("camera_to_world rows must contain at least 4 values")
        rotation.append([float(value) for value in row[:3]])
        position.append(float(row[3]))

    return rotation, position


def apply_dataparser_transform(
    camera_to_world: list[list[float]],
    dataparser: dict[str, Any],
) -> dict[str, list[float]]:
    camera_rotation, camera_position = camera_rotation_position(camera_to_world)
    dataparser_rotation, dataparser_translation = dataparser_rotation_translation(dataparser)
    scale = float(dataparser.get("scale", 1.0))

    transformed_position = vector_scale(
        vector_add(
            mat3_vec_mul(dataparser_rotation, camera_position),
            dataparser_translation,
        ),
        scale,
    )
    camera_forward = mat3_vec_mul(camera_rotation, [0.0, 0.0, -1.0])
    transformed_forward = normalize(mat3_vec_mul(dataparser_rotation, camera_forward))

    return {"position": transformed_position, "forward": transformed_forward}


def _first_registered_frame_from_frames(frames: list[dict[str, Any]]) -> dict[str, Any]:
    registered = [
        frame
        for frame in frames
        if frame.get("file_path") and frame.get("transform_matrix") is not None
    ]
    if not registered:
        raise ValueError("transforms.json contains no registered frames")
    return sorted(registered, key=lambda frame: natural_filename_key(str(frame["file_path"])))[0]


def first_registered_frame(transforms_path: Path) -> dict[str, Any]:
    transforms = json.loads(transforms_path.read_text())
    return _first_registered_frame_from_frames(transforms.get("frames", []))


def first_photo_metadata(
    transforms_path: Path,
    dataparser_transforms_path: Path,
    look_distance: float = 1.0,
) -> dict[str, Any]:
    dataparser = json.loads(dataparser_transforms_path.read_text())
    frame = first_registered_frame(transforms_path)
    transformed = apply_dataparser_transform(frame["transform_matrix"], dataparser)
    position = transformed["position"]
    forward = transformed["forward"]
    look_at = vector_add(position, vector_scale(forward, look_distance))

    return {
        "firstFrame": {
            "filePath": frame["file_path"],
            "transformMatrix": frame["transform_matrix"],
            "cameraPosition": position,
            "cameraForward": forward,
            "cameraLookAt": look_at,
        }
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Gaussian Splat viewer metadata.")
    parser.add_argument("transforms", type=Path)
    parser.add_argument("dataparser_transforms", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--look-distance", type=float, default=1.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    metadata = first_photo_metadata(
        args.transforms,
        args.dataparser_transforms,
        look_distance=args.look_distance,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(metadata, indent=2) + "\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
