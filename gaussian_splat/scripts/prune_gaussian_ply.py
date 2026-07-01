#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import struct
import sys
from pathlib import Path
from typing import Any

from filter_splat_ply import PlyError, property_indexes, quantile, read_ply, write_ply
from inspect_gaussian_ply import clean_number, point_outside_bbox, robust_bbox, row_has_nonfinite, row_metrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prune obvious Gaussian Splat PLY artifact outliers."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path, nargs="?")
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--min-opacity", type=float, default=0.05)
    parser.add_argument("--max-scale", type=float, default=0.0)
    parser.add_argument("--max-scale-percentile", type=float, default=0.999)
    parser.add_argument("--anisotropy-threshold", type=float, default=100.0)
    parser.add_argument("--bbox-quantile", type=float, default=0.001)
    parser.add_argument("--bbox-padding", type=float, default=0.2)
    return parser.parse_args()


def max_scale_threshold(metrics: list[dict[str, Any]], min_opacity: float, max_scale: float, percentile: float) -> float:
    if max_scale > 0:
        return max_scale
    values = [metric["effective_max_scale"] for metric in metrics if metric["effective_opacity"] >= min_opacity]
    return quantile(values, percentile) if values else 0.0


def prune_rows(
    rows: list[tuple[float, ...]],
    indexes: dict[str, int],
    min_opacity: float,
    max_scale: float,
    max_scale_percentile: float,
    anisotropy_threshold: float,
    bbox_quantile: float,
    bbox_padding: float,
) -> tuple[list[tuple[float, ...]], dict[str, Any]]:
    metrics_by_index: dict[int, dict[str, Any]] = {
        index: row_metrics(row, indexes)
        for index, row in enumerate(rows)
        if not row_has_nonfinite(row)
    }
    max_scale_used = max_scale_threshold(
        list(metrics_by_index.values()),
        min_opacity,
        max_scale,
        max_scale_percentile,
    )
    bbox_seed = [
        metric["point"]
        for metric in metrics_by_index.values()
        if metric["effective_opacity"] >= min_opacity
        and metric["effective_max_scale"] <= max_scale_used
        and (anisotropy_threshold <= 0 or metric["effective_anisotropy"] <= anisotropy_threshold)
    ]
    bbox_min, bbox_max = robust_bbox(bbox_seed, bbox_quantile, bbox_padding)

    removed = {
        "nonfinite": 0,
        "low_opacity": 0,
        "huge_scale": 0,
        "extreme_anisotropy": 0,
        "far_out_bbox": 0,
    }
    kept: list[tuple[float, ...]] = []
    for index, row in enumerate(rows):
        metric = metrics_by_index.get(index)
        if metric is None:
            removed["nonfinite"] += 1
        elif metric["effective_opacity"] < min_opacity:
            removed["low_opacity"] += 1
        elif metric["effective_max_scale"] > max_scale_used:
            removed["huge_scale"] += 1
        elif anisotropy_threshold > 0 and metric["effective_anisotropy"] > anisotropy_threshold:
            removed["extreme_anisotropy"] += 1
        elif point_outside_bbox(metric["point"], bbox_min, bbox_max):
            removed["far_out_bbox"] += 1
        else:
            kept.append(row)

    return kept, {
        "removed": removed,
        "filters": {
            "min_opacity": min_opacity,
            "max_scale": max_scale,
            "max_scale_used": clean_number(max_scale_used),
            "max_scale_percentile": max_scale_percentile,
            "anisotropy_threshold": anisotropy_threshold,
            "bbox_quantile": bbox_quantile,
            "bbox_padding": bbox_padding,
            "value_space": "effective",
            "opacity": "sigmoid(opacity)",
            "scale": "exp(scale_*)",
            "anisotropy": "exp(max(scale_*) - min(scale_*))",
        },
        "bbox": {
            "min": [clean_number(value) for value in bbox_min],
            "max": [clean_number(value) for value in bbox_max],
        },
    }


def build_summary(
    source: Path,
    output: Path,
    input_count: int,
    kept_count: int,
    details: dict[str, Any],
) -> dict[str, Any]:
    return {
        "version": "1.0.0",
        "source": str(source),
        "output": str(output),
        "source_name": source.name,
        "output_name": output.name,
        "input_count": input_count,
        "kept_count": kept_count,
        "removed_count": input_count - kept_count,
        "kept_ratio": round(kept_count / input_count, 6) if input_count else 0.0,
        **details,
    }


def main() -> int:
    args = parse_args()
    output = args.output or args.source.with_name("splat.pruned.ply")
    summary_path = args.summary or args.source.with_name("gaussian_cleanup_summary.json")
    try:
        header, vertex_properties, rows = read_ply(args.source)
        kept, details = prune_rows(
            rows,
            property_indexes(vertex_properties),
            args.min_opacity,
            args.max_scale,
            args.max_scale_percentile,
            args.anisotropy_threshold,
            args.bbox_quantile,
            args.bbox_padding,
        )
        write_ply(output, header, vertex_properties, kept)
        summary = build_summary(args.source, output, len(rows), len(kept), details)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        print(output)
    except (OSError, PlyError, struct.error, ValueError, OverflowError) as exc:
        print(f"prune_gaussian_ply.py: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
