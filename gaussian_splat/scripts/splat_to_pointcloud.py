#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import struct
import sys
from pathlib import Path
from typing import Any

import numpy as np


SH_C0 = 0.28209479177387814
REQUIRED_PROPERTIES = {
    "x",
    "y",
    "z",
    "opacity",
    "scale_0",
    "scale_1",
    "scale_2",
}
FLOAT_TYPES = {
    "float": "f",
    "float32": "f",
    "double": "d",
    "float64": "d",
}
PLY_TYPES = {
    **FLOAT_TYPES,
    "uchar": "B",
    "uint8": "B",
    "char": "b",
    "int8": "b",
    "ushort": "H",
    "uint16": "H",
    "short": "h",
    "int16": "h",
    "uint": "I",
    "uint32": "I",
    "int": "i",
    "int32": "i",
}


class PlyError(ValueError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a Nerfstudio Gaussian Splat PLY into a filtered colored point cloud."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--min-opacity", type=float, default=0.18)
    parser.add_argument(
        "--max-scale",
        type=float,
        default=0.0,
        help="Maximum exp(max(scale_*)); 0 chooses an automatic quantile threshold.",
    )
    parser.add_argument("--scale-quantile", type=float, default=0.995)
    parser.add_argument("--limit", type=int, default=0)
    return parser.parse_args()


def sigmoid(values: np.ndarray) -> np.ndarray:
    result = np.empty_like(values, dtype=np.float64)
    positive = values >= 0
    result[positive] = 1.0 / (1.0 + np.exp(-values[positive]))
    exp_values = np.exp(values[~positive])
    result[~positive] = exp_values / (1.0 + exp_values)
    return result


def clamp_rgb(values: np.ndarray) -> np.ndarray:
    return np.rint(np.clip(values, 0, 255)).astype(np.uint8)


def read_binary_ply(path: Path) -> tuple[int, dict[str, np.ndarray]]:
    data = path.read_bytes()
    marker = b"end_header\n"
    header_end = data.find(marker)
    if header_end < 0:
        raise PlyError("PLY header must end with end_header")

    header_lines = data[: header_end + len(marker)].decode("ascii").splitlines()
    body = data[header_end + len(marker) :]
    if not header_lines or header_lines[0] != "ply":
        raise PlyError("not a PLY file")
    if "format binary_little_endian 1.0" not in header_lines:
        raise PlyError("only format binary_little_endian 1.0 is supported")

    vertex_count: int | None = None
    vertex_properties: list[tuple[str, str]] = []
    in_vertex = False
    for line in header_lines:
        parts = line.split()
        if len(parts) >= 3 and parts[0] == "element":
            in_vertex = parts[1] == "vertex"
            if in_vertex:
                try:
                    vertex_count = int(parts[2])
                except ValueError as exc:
                    raise PlyError(f"invalid vertex count: {parts[2]}") from exc
            continue
        if in_vertex and len(parts) == 3 and parts[0] == "property":
            property_type, property_name = parts[1], parts[2]
            if property_type not in PLY_TYPES:
                raise PlyError(f"unsupported vertex property type: {property_type}")
            vertex_properties.append((property_type, property_name))

    if vertex_count is None:
        raise PlyError("element vertex line not found")

    names = {name for _property_type, name in vertex_properties}
    missing = sorted(REQUIRED_PROPERTIES - names)
    if missing:
        raise PlyError(f"missing required properties: {', '.join(missing)}")
    color_properties = {"red", "green", "blue"}
    sh_properties = {"f_dc_0", "f_dc_1", "f_dc_2"}
    if color_properties <= names:
        needed = REQUIRED_PROPERTIES | color_properties
    elif sh_properties <= names:
        needed = REQUIRED_PROPERTIES | sh_properties
    else:
        missing = sorted(sh_properties - names)
        raise PlyError(
            "missing RGB properties and spherical harmonic color properties: "
            + ", ".join(missing)
        )

    struct_format = "<" + "".join(PLY_TYPES[property_type] for property_type, _ in vertex_properties)
    row_size = struct.calcsize(struct_format)
    expected_size = vertex_count * row_size
    if len(body) < expected_size:
        raise PlyError(f"PLY body is too short: expected {expected_size} bytes, got {len(body)}")

    needed_indexes = [
        (index, name)
        for index, (_property_type, name) in enumerate(vertex_properties)
        if name in needed
    ]
    columns: dict[str, list[float]] = {name: [] for name in needed}
    for offset in range(0, expected_size, row_size):
        row = struct.unpack_from(struct_format, body, offset)
        for index, name in needed_indexes:
            columns[name].append(row[index])

    arrays = {
        name: np.asarray(values, dtype=np.float64)
        for name, values in columns.items()
    }
    return vertex_count, arrays


def build_rgb(columns: dict[str, np.ndarray]) -> np.ndarray:
    if {"red", "green", "blue"} <= columns.keys():
        return np.column_stack(
            [
                clamp_rgb(columns["red"]),
                clamp_rgb(columns["green"]),
                clamp_rgb(columns["blue"]),
            ]
        )

    required_dc = {"f_dc_0", "f_dc_1", "f_dc_2"}
    if not required_dc <= columns.keys():
        missing = sorted(required_dc - columns.keys())
        raise PlyError(
            "missing RGB properties and spherical harmonic color properties: "
            + ", ".join(missing)
        )

    return np.column_stack(
        [
            clamp_rgb((columns["f_dc_0"] * SH_C0 + 0.5) * 255.0),
            clamp_rgb((columns["f_dc_1"] * SH_C0 + 0.5) * 255.0),
            clamp_rgb((columns["f_dc_2"] * SH_C0 + 0.5) * 255.0),
        ]
    )


def filter_points(
    columns: dict[str, np.ndarray],
    min_opacity: float,
    max_scale: float,
    scale_quantile: float,
) -> tuple[np.ndarray, float, np.ndarray]:
    opacity_mask = sigmoid(columns["opacity"]) >= min_opacity
    raw_scales = np.maximum.reduce(
        [columns["scale_0"], columns["scale_1"], columns["scale_2"]]
    )
    row_scales = np.exp(raw_scales)

    if max_scale > 0:
        max_scale_used = float(max_scale)
    elif np.any(opacity_mask):
        q = min(1.0, max(0.0, scale_quantile))
        max_scale_used = max(0.25, float(np.quantile(row_scales[opacity_mask], q)))
    else:
        max_scale_used = 0.25

    final_mask = opacity_mask & (row_scales <= max_scale_used)
    return final_mask, max_scale_used, row_scales


def bbox(points: np.ndarray) -> tuple[list[float], list[float]]:
    if points.size == 0:
        return [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]
    return points.min(axis=0).astype(float).tolist(), points.max(axis=0).astype(float).tolist()


def write_pointcloud_ply(path: Path, points: np.ndarray, rgb: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    header = "\n".join(
        [
            "ply",
            "format ascii 1.0",
            f"element vertex {len(points)}",
            "property float x",
            "property float y",
            "property float z",
            "property uchar red",
            "property uchar green",
            "property uchar blue",
            "end_header",
            "",
        ]
    )
    with path.open("w", encoding="ascii") as handle:
        handle.write(header)
        for point, color in zip(points, rgb):
            handle.write(
                f"{point[0]:.9g} {point[1]:.9g} {point[2]:.9g} "
                f"{int(color[0])} {int(color[1])} {int(color[2])}\n"
            )


def build_report(
    input_path: Path,
    output_path: Path,
    input_count: int,
    filtered_count: int,
    kept_points: np.ndarray,
    min_opacity: float,
    max_scale_used: float,
    scale_quantile: float,
    limit: int,
) -> dict[str, Any]:
    bbox_min, bbox_max = bbox(kept_points)
    kept_count = int(len(kept_points))
    limited_count = max(0, filtered_count - kept_count)
    return {
        "input": str(input_path),
        "output": str(output_path),
        "output_path": str(output_path),
        "input_count": int(input_count),
        "kept_count": kept_count,
        "filtered_count": int(filtered_count),
        "removed_count": int(input_count - filtered_count),
        "limited_count": int(limited_count),
        "limit": int(limit),
        "filters": {
            "min_opacity": float(min_opacity),
            "max_scale_used": float(max_scale_used),
            "scale_quantile": float(scale_quantile),
            "limit": int(limit),
        },
        "bbox_min": bbox_min,
        "bbox_max": bbox_max,
    }


def main() -> int:
    args = parse_args()
    try:
        input_count, columns = read_binary_ply(args.input)
        points = np.column_stack([columns["x"], columns["y"], columns["z"]])
        rgb = build_rgb(columns)
        mask, max_scale_used, _row_scales = filter_points(
            columns,
            args.min_opacity,
            args.max_scale,
            args.scale_quantile,
        )

        kept_points = points[mask]
        kept_rgb = rgb[mask]
        filtered_count = int(len(kept_points))
        if args.limit > 0:
            kept_points = kept_points[: args.limit]
            kept_rgb = kept_rgb[: args.limit]

        write_pointcloud_ply(args.output, kept_points, kept_rgb)
        if args.report:
            report = build_report(
                args.input,
                args.output,
                input_count,
                filtered_count,
                kept_points,
                args.min_opacity,
                max_scale_used,
                args.scale_quantile,
                args.limit,
            )
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    except (OSError, PlyError, struct.error, OverflowError, ValueError) as exc:
        print(f"splat_to_pointcloud.py: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
