#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import struct
import sys
from pathlib import Path
from typing import Any


PLY_TO_STRUCT = {
    "float": "f",
    "float32": "f",
    "double": "d",
    "float64": "d",
}
REQUIRED_PROPERTIES = {
    "x",
    "y",
    "z",
    "opacity",
    "scale_0",
    "scale_1",
    "scale_2",
}


class PlyError(ValueError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Filter low-confidence Nerfstudio Gaussian Splat binary PLY files."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--meta", type=Path)
    parser.add_argument("--min-opacity", type=float, default=0.18)
    parser.add_argument(
        "--max-scale",
        type=float,
        default=0.0,
        help="Maximum exp(max(scale_*)); 0 chooses an automatic quantile threshold.",
    )
    parser.add_argument("--scale-quantile", type=float, default=0.995)
    parser.add_argument("--bbox-quantile", type=float, default=0.01)
    parser.add_argument("--bbox-padding", type=float, default=0.20)
    return parser.parse_args()


def sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def quantile(values: list[float], q: float) -> float:
    if not values:
        raise PlyError("cannot compute quantile of an empty value set")
    q = min(1.0, max(0.0, q))
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def read_ply(path: Path) -> tuple[list[str], list[tuple[str, str]], list[tuple[float, ...]]]:
    data = path.read_bytes()
    marker = b"end_header\n"
    header_end = data.find(marker)
    if header_end < 0:
        raise PlyError("PLY header must end with end_header")

    header_bytes = data[: header_end + len(marker)]
    body = data[header_end + len(marker) :]
    header_lines = header_bytes.decode("ascii").splitlines()

    if len(header_lines) < 3 or header_lines[0] != "ply":
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
                if vertex_count < 0:
                    raise PlyError(f"invalid vertex count: {parts[2]}")
            continue
        if in_vertex and len(parts) == 3 and parts[0] == "property":
            property_type, property_name = parts[1], parts[2]
            if property_type not in PLY_TO_STRUCT:
                raise PlyError(f"unsupported vertex property type: {property_type}")
            vertex_properties.append((property_type, property_name))

    if vertex_count is None:
        raise PlyError("element vertex line not found")
    property_names = {name for _type, name in vertex_properties}
    missing = sorted(REQUIRED_PROPERTIES - property_names)
    if missing:
        raise PlyError(f"missing required properties: {', '.join(missing)}")

    struct_format = "<" + "".join(PLY_TO_STRUCT[property_type] for property_type, _ in vertex_properties)
    row_size = struct.calcsize(struct_format)
    expected_body_size = vertex_count * row_size
    if len(body) < expected_body_size:
        raise PlyError(
            f"PLY body is too short: expected {expected_body_size} bytes, got {len(body)}"
        )

    rows = [
        struct.unpack_from(struct_format, body, offset)
        for offset in range(0, expected_body_size, row_size)
    ]
    return header_lines, vertex_properties, rows


def write_ply(
    path: Path,
    header_lines: list[str],
    vertex_properties: list[tuple[str, str]],
    rows: list[tuple[float, ...]],
) -> None:
    output_lines = []
    replaced_count = False
    for line in header_lines:
        if line.startswith("element vertex "):
            output_lines.append(f"element vertex {len(rows)}")
            replaced_count = True
        else:
            output_lines.append(line)
    if not replaced_count:
        raise PlyError("element vertex line not found")

    struct_format = "<" + "".join(PLY_TO_STRUCT[property_type] for property_type, _ in vertex_properties)
    body = b"".join(struct.pack(struct_format, *row) for row in rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(("\n".join(output_lines) + "\n").encode("ascii") + body)


def property_indexes(vertex_properties: list[tuple[str, str]]) -> dict[str, int]:
    return {name: index for index, (_type, name) in enumerate(vertex_properties)}


def row_scale(row: tuple[float, ...], indexes: dict[str, int]) -> float:
    raw_scale = max(
        row[indexes["scale_0"]],
        row[indexes["scale_1"]],
        row[indexes["scale_2"]],
    )
    return math.exp(raw_scale)


def bbox_from_rows(
    rows: list[tuple[float, ...]],
    indexes: dict[str, int],
    bbox_quantile: float,
    bbox_padding: float,
) -> tuple[list[float], list[float]]:
    mins: list[float] = []
    maxs: list[float] = []
    q = min(0.5, max(0.0, bbox_quantile))
    for axis in ("x", "y", "z"):
        values = [row[indexes[axis]] for row in rows]
        low = quantile(values, q)
        high = quantile(values, 1.0 - q)
        span = high - low
        padding = span * bbox_padding
        mins.append(low - padding)
        maxs.append(high + padding)
    return mins, maxs


def filter_rows(
    rows: list[tuple[float, ...]],
    indexes: dict[str, int],
    min_opacity: float,
    max_scale: float,
    scale_quantile: float,
    bbox_quantile: float,
    bbox_padding: float,
) -> tuple[list[tuple[float, ...]], float]:
    opacity_rows = [
        row for row in rows if sigmoid(row[indexes["opacity"]]) >= min_opacity
    ]
    if max_scale > 0:
        max_scale_used = max_scale
    elif opacity_rows:
        max_scale_used = max(0.25, quantile([row_scale(row, indexes) for row in opacity_rows], scale_quantile))
    else:
        max_scale_used = 0.25

    confidence_rows = [
        row for row in opacity_rows if row_scale(row, indexes) <= max_scale_used
    ]
    if not confidence_rows:
        return [], max_scale_used

    bbox_min, bbox_max = bbox_from_rows(
        confidence_rows, indexes, bbox_quantile, bbox_padding
    )
    kept_rows = [
        row
        for row in confidence_rows
        if all(
            bbox_min[axis_index]
            <= row[indexes[axis_name]]
            <= bbox_max[axis_index]
            for axis_index, axis_name in enumerate(("x", "y", "z"))
        )
    ]
    return kept_rows, max_scale_used


def core_metadata(rows: list[tuple[float, ...]], indexes: dict[str, int]) -> dict[str, Any]:
    if not rows:
        return {
            "center": [0.0, 0.0, 0.0],
            "bbox_min": [0.0, 0.0, 0.0],
            "bbox_max": [0.0, 0.0, 0.0],
            "radius": 0.0,
        }

    bbox_min = [
        min(row[indexes[axis]] for row in rows)
        for axis in ("x", "y", "z")
    ]
    bbox_max = [
        max(row[indexes[axis]] for row in rows)
        for axis in ("x", "y", "z")
    ]
    center = [
        (low + high) / 2.0
        for low, high in zip(bbox_min, bbox_max)
    ]
    radius = math.sqrt(
        sum((high - low) ** 2 for low, high in zip(bbox_min, bbox_max))
    ) / 2.0
    return {
        "center": center,
        "bbox_min": bbox_min,
        "bbox_max": bbox_max,
        "radius": radius,
    }


def build_metadata(
    source: Path,
    output: Path,
    source_count: int,
    kept_count: int,
    kept_rows: list[tuple[float, ...]],
    indexes: dict[str, int],
    min_opacity: float,
    max_scale_used: float,
    scale_quantile: float,
    bbox_quantile: float,
    bbox_padding: float,
) -> dict[str, Any]:
    core = core_metadata(kept_rows, indexes)
    radius = core["radius"]
    return {
        "source_name": source.name,
        "output_name": output.name,
        "input_count": source_count,
        "kept_count": kept_count,
        "removed_count": source_count - kept_count,
        "kept_ratio": kept_count / source_count if source_count else 0.0,
        "filters": {
            "min_opacity": min_opacity,
            "max_scale_used": max_scale_used,
            "scale_quantile": scale_quantile,
            "bbox_quantile": bbox_quantile,
            "bbox_padding": bbox_padding,
        },
        "cleanup": {
            "source_vertex_count": source_count,
            "kept_vertex_count": kept_count,
            "removed_vertex_count": source_count - kept_count,
            "kept_ratio": round(kept_count / source_count, 2) if source_count else 0.0,
            "filters": {
                "min_opacity": min_opacity,
                "max_scale_used": max_scale_used,
            },
        },
        "core": core,
        "cesium": {
            "center_model": core["center"],
            "radius_model": radius,
        },
        "viewer": {
            "alpha": 40,
            "splatScale": 0.25,
            "rx": 0,
            "ry": 0,
            "rz": 0,
            "upMode": "view",
            "cameraDistance": max(1, radius * 2.2),
        },
    }


def main() -> int:
    args = parse_args()
    try:
        header_lines, vertex_properties, rows = read_ply(args.source)
        indexes = property_indexes(vertex_properties)
        kept_rows, max_scale_used = filter_rows(
            rows,
            indexes,
            args.min_opacity,
            args.max_scale,
            args.scale_quantile,
            args.bbox_quantile,
            args.bbox_padding,
        )
        write_ply(args.output, header_lines, vertex_properties, kept_rows)
        if args.meta:
            metadata = build_metadata(
                args.source,
                args.output,
                len(rows),
                len(kept_rows),
                kept_rows,
                indexes,
                args.min_opacity,
                max_scale_used,
                args.scale_quantile,
                args.bbox_quantile,
                args.bbox_padding,
            )
            args.meta.parent.mkdir(parents=True, exist_ok=True)
            args.meta.write_text(json.dumps(metadata, indent=2) + "\n")
    except (OSError, PlyError, struct.error, OverflowError) as exc:
        print(f"filter_splat_ply.py: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
