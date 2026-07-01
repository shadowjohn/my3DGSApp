#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import struct
import sys
from pathlib import Path
from typing import Any

from filter_splat_ply import PlyError, property_indexes, quantile, read_ply, sigmoid


PERCENTILES = [
    ("p0", 0.0),
    ("p50", 0.5),
    ("p90", 0.9),
    ("p95", 0.95),
    ("p99", 0.99),
    ("p99.5", 0.995),
    ("p99.9", 0.999),
    ("p100", 1.0),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit Nerfstudio Gaussian Splat PLY artifact outliers."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--huge-scale-percentile", type=float, default=0.999)
    parser.add_argument("--anisotropy-threshold", type=float, default=100.0)
    parser.add_argument("--far-out-quantile", type=float, default=0.001)
    parser.add_argument("--bbox-padding", type=float, default=0.2)
    return parser.parse_args()


def clean_number(value: float) -> int | float:
    value = float(value)
    return int(value) if value.is_integer() else value


def exp_or_inf(value: float) -> float:
    try:
        return math.exp(value)
    except OverflowError:
        return math.inf


def percentile_summary(values: list[float]) -> dict[str, Any]:
    finite = [float(value) for value in values if math.isfinite(value)]
    if not finite:
        return {"count": 0, "percentiles": {name: None for name, _q in PERCENTILES}}
    return {
        "count": len(finite),
        "percentiles": {
            name: clean_number(quantile(finite, q))
            for name, q in PERCENTILES
        },
    }


def row_has_nonfinite(row: tuple[float, ...]) -> bool:
    return any(not math.isfinite(value) for value in row)


def row_metrics(row: tuple[float, ...], indexes: dict[str, int]) -> dict[str, Any]:
    raw_scales = [
        row[indexes["scale_0"]],
        row[indexes["scale_1"]],
        row[indexes["scale_2"]],
    ]
    effective_scales = [exp_or_inf(value) for value in raw_scales]
    effective_scale_min = min(effective_scales)
    effective_scale_max = max(effective_scales)
    effective_anisotropy = math.inf if effective_scale_min <= 0 else effective_scale_max / effective_scale_min
    point = [row[indexes[axis]] for axis in ("x", "y", "z")]
    quaternion_norm = None
    rotation_keys = ["rot_0", "rot_1", "rot_2", "rot_3"]
    if all(key in indexes for key in rotation_keys):
        quaternion_norm = math.sqrt(sum(row[indexes[key]] ** 2 for key in rotation_keys))
    return {
        "point": point,
        "raw_opacity": row[indexes["opacity"]],
        "effective_opacity": sigmoid(row[indexes["opacity"]]),
        "raw_scales": raw_scales,
        "raw_max_scale": max(raw_scales),
        "effective_scales": effective_scales,
        "effective_max_scale": effective_scale_max,
        "effective_anisotropy": effective_anisotropy,
        "quaternion_norm": quaternion_norm,
    }


def robust_bbox(
    points: list[list[float]],
    q: float,
    padding: float,
) -> tuple[list[float], list[float]]:
    if not points:
        return [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]
    q = min(0.49, max(0.0, q))
    mins: list[float] = []
    maxs: list[float] = []
    for axis in range(3):
        values = [point[axis] for point in points]
        low = quantile(values, q)
        high = quantile(values, 1.0 - q)
        span = high - low
        mins.append(low - span * padding)
        maxs.append(high + span * padding)
    return mins, maxs


def point_outside_bbox(point: list[float], bbox_min: list[float], bbox_max: list[float]) -> bool:
    return any(point[index] < bbox_min[index] or point[index] > bbox_max[index] for index in range(3))


def build_audit(
    source: Path,
    rows: list[tuple[float, ...]],
    indexes: dict[str, int],
    huge_scale_percentile: float,
    anisotropy_threshold: float,
    far_out_quantile: float,
    bbox_padding: float,
) -> dict[str, Any]:
    nan_value_count = sum(1 for row in rows for value in row if math.isnan(value))
    inf_value_count = sum(1 for row in rows for value in row if math.isinf(value))
    finite_metrics = [
        row_metrics(row, indexes)
        for row in rows
        if not row_has_nonfinite(row)
    ]
    points = [metric["point"] for metric in finite_metrics]
    bbox_min = [clean_number(min(point[axis] for point in points)) for axis in range(3)] if points else [0, 0, 0]
    bbox_max = [clean_number(max(point[axis] for point in points)) for axis in range(3)] if points else [0, 0, 0]
    max_scales = [metric["effective_max_scale"] for metric in finite_metrics]
    huge_threshold = quantile(max_scales, huge_scale_percentile) if max_scales else 0.0
    robust_min, robust_max = robust_bbox(points, far_out_quantile, bbox_padding)
    raw = {
        "opacity": percentile_summary([metric["raw_opacity"] for metric in finite_metrics]),
        "scale": {
            "interpreted_as": "raw scale_*",
            "scale_0": percentile_summary([metric["raw_scales"][0] for metric in finite_metrics]),
            "scale_1": percentile_summary([metric["raw_scales"][1] for metric in finite_metrics]),
            "scale_2": percentile_summary([metric["raw_scales"][2] for metric in finite_metrics]),
            "raw_max_scale": percentile_summary([metric["raw_max_scale"] for metric in finite_metrics]),
        },
    }
    effective_anisotropy = {
        **percentile_summary([metric["effective_anisotropy"] for metric in finite_metrics]),
        "threshold": anisotropy_threshold,
        "extreme_count": sum(metric["effective_anisotropy"] > anisotropy_threshold for metric in finite_metrics),
    }
    effective = {
        "opacity": percentile_summary([metric["effective_opacity"] for metric in finite_metrics]),
        "scale": {
            "interpreted_as": "exp(scale_*)",
            "scale_0": percentile_summary([metric["effective_scales"][0] for metric in finite_metrics]),
            "scale_1": percentile_summary([metric["effective_scales"][1] for metric in finite_metrics]),
            "scale_2": percentile_summary([metric["effective_scales"][2] for metric in finite_metrics]),
            "effective_max_scale": percentile_summary(max_scales),
            "max_scale": percentile_summary(max_scales),
        },
        "anisotropy": effective_anisotropy,
    }
    quaternion_norms = [
        metric["quaternion_norm"]
        for metric in finite_metrics
        if metric["quaternion_norm"] is not None
    ]
    quaternion_summary = {
        **percentile_summary(quaternion_norms),
        "available": bool(quaternion_norms),
        "non_unit_count": sum(abs(value - 1.0) > 0.01 for value in quaternion_norms),
    }

    return {
        "version": "1.0.0",
        "source": str(source),
        "source_name": source.name,
        "splat_count": len(rows),
        "finite_splat_count": len(finite_metrics),
        "nonfinite_splat_count": len(rows) - len(finite_metrics),
        "nan_value_count": nan_value_count,
        "inf_value_count": inf_value_count,
        "bbox": {"min": bbox_min, "max": bbox_max},
        "robust_bbox": {
            "min": [clean_number(value) for value in robust_min],
            "max": [clean_number(value) for value in robust_max],
            "quantile": far_out_quantile,
            "padding": bbox_padding,
        },
        "raw": raw,
        "effective": effective,
        "opacity": effective["opacity"],
        "scale": effective["scale"],
        "huge_scale_threshold": clean_number(huge_threshold),
        "huge_scale_percentile": huge_scale_percentile,
        "huge_scale_splat_count": sum(metric["effective_max_scale"] > huge_threshold for metric in finite_metrics),
        "anisotropy": effective_anisotropy,
        "quaternion_norm": quaternion_summary,
        "far_out_splat_count": sum(point_outside_bbox(metric["point"], robust_min, robust_max) for metric in finite_metrics),
    }


def main() -> int:
    args = parse_args()
    output = args.output or args.source.with_name("gaussian_artifact_audit.json")
    try:
        _header, vertex_properties, rows = read_ply(args.source)
        audit = build_audit(
            args.source,
            rows,
            property_indexes(vertex_properties),
            args.huge_scale_percentile,
            args.anisotropy_threshold,
            args.far_out_quantile,
            args.bbox_padding,
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(audit, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        print(output)
    except (OSError, PlyError, struct.error, ValueError, OverflowError) as exc:
        print(f"inspect_gaussian_ply.py: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
