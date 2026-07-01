from __future__ import annotations

import json
import math
import struct
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSPECT = ROOT / "scripts" / "inspect_gaussian_ply.py"
PRUNE = ROOT / "scripts" / "prune_gaussian_ply.py"
PROPERTIES = [
    "x",
    "y",
    "z",
    "opacity",
    "scale_0",
    "scale_1",
    "scale_2",
    "rot_0",
    "rot_1",
    "rot_2",
    "rot_3",
]


def logit(value: float) -> float:
    return math.log(value / (1.0 - value))


def row(
    x: float,
    y: float,
    z: float,
    opacity: float,
    scales: tuple[float, float, float],
    rotation: tuple[float, float, float, float] = (1.0, 0.0, 0.0, 0.0),
) -> list[float]:
    return [x, y, z, logit(opacity), *(math.log(scale) for scale in scales), *rotation]


def write_ply(path: Path, rows: list[list[float]]) -> None:
    header = "\n".join(
        [
            "ply",
            "format binary_little_endian 1.0",
            f"element vertex {len(rows)}",
            *[f"property float {name}" for name in PROPERTIES],
            "end_header",
            "",
        ]
    ).encode("ascii")
    body = b"".join(struct.pack("<11f", *values) for values in rows)
    path.write_bytes(header + body)


def vertex_count(path: Path) -> int:
    header, _body = path.read_bytes().split(b"end_header\n", 1)
    for line in header.decode("ascii").splitlines():
        if line.startswith("element vertex "):
            return int(line.rsplit(" ", 1)[1])
    raise AssertionError("vertex count not found")


def fixture_rows() -> list[list[float]]:
    return [
        row(0.0, 0.0, 0.0, 0.95, (0.10, 0.10, 0.10)),
        row(1.0, 0.0, 0.0, 0.92, (0.10, 0.10, 0.10)),
        row(0.0, 1.0, 0.0, 0.90, (0.10, 0.10, 0.10)),
        row(0.2, 0.2, 0.2, 0.01, (0.10, 0.10, 0.10)),
        row(0.3, 0.3, 0.3, 0.91, (5.00, 5.00, 5.00)),
        row(0.4, 0.4, 0.4, 0.91, (0.20, 0.01, 0.20), (2.0, 0.0, 0.0, 0.0)),
        row(50.0, 50.0, 50.0, 0.94, (0.10, 0.10, 0.10)),
        row(float("nan"), 0.0, 0.0, 0.90, (0.10, 0.10, 0.10)),
    ]


def test_inspect_gaussian_ply_reports_artifact_outliers(tmp_path):
    source = tmp_path / "splat.clean.ply"
    report = tmp_path / "gaussian_artifact_audit.json"
    write_ply(source, fixture_rows())

    result = subprocess.run(
        [
            sys.executable,
            str(INSPECT),
            str(source),
            "--output",
            str(report),
            "--huge-scale-percentile",
            "0.80",
            "--anisotropy-threshold",
            "10",
            "--far-out-quantile",
            "0.25",
            "--bbox-padding",
            "1",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    audit = json.loads(report.read_text())
    assert audit["splat_count"] == 8
    assert audit["nonfinite_splat_count"] == 1
    assert audit["nan_value_count"] == 1
    assert audit["bbox"]["max"] == [50, 50, 50]
    assert audit["raw"]["opacity"]["percentiles"]["p50"] > 2
    assert audit["raw"]["scale"]["raw_max_scale"]["percentiles"]["p99.9"] > 1
    assert audit["effective"]["opacity"]["percentiles"]["p50"] > 0.9
    assert audit["effective"]["scale"]["effective_max_scale"]["percentiles"]["p99.9"] >= 4.9
    assert audit["effective"]["scale"]["scale_0"]["percentiles"]["p95"] > 1
    assert audit["opacity"] == audit["effective"]["opacity"]
    assert audit["scale"] == audit["effective"]["scale"]
    assert audit["huge_scale_splat_count"] >= 1
    assert audit["anisotropy"]["extreme_count"] == 1
    assert audit["effective"]["anisotropy"]["extreme_count"] == 1
    assert audit["quaternion_norm"]["available"] is True
    assert audit["quaternion_norm"]["percentiles"]["p100"] == 2
    assert audit["quaternion_norm"]["non_unit_count"] == 1
    assert audit["far_out_splat_count"] == 1


def test_prune_gaussian_ply_writes_pruned_ply_and_cleanup_summary(tmp_path):
    source = tmp_path / "splat.clean.ply"
    output = tmp_path / "splat.pruned.ply"
    summary_path = tmp_path / "gaussian_cleanup_summary.json"
    write_ply(source, fixture_rows())

    result = subprocess.run(
        [
            sys.executable,
            str(PRUNE),
            str(source),
            str(output),
            "--summary",
            str(summary_path),
            "--min-opacity",
            "0.05",
            "--max-scale",
            "1",
            "--anisotropy-threshold",
            "10",
            "--bbox-quantile",
            "0.25",
            "--bbox-padding",
            "0",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert vertex_count(output) == 3
    summary = json.loads(summary_path.read_text())
    assert summary["input_count"] == 8
    assert summary["kept_count"] == 3
    assert summary["removed_count"] == 5
    assert summary["removed"]["nonfinite"] == 1
    assert summary["removed"]["low_opacity"] == 1
    assert summary["removed"]["huge_scale"] == 1
    assert summary["removed"]["extreme_anisotropy"] == 1
    assert summary["removed"]["far_out_bbox"] == 1
    assert summary["filters"]["value_space"] == "effective"
    assert summary["filters"]["opacity"] == "sigmoid(opacity)"
    assert summary["filters"]["scale"] == "exp(scale_*)"
    assert summary["filters"]["anisotropy"] == "exp(max(scale_*) - min(scale_*))"
