from __future__ import annotations

import json
import math
import struct
import subprocess
import sys
from pathlib import Path

from scripts.build_confidence_regions import build_confidence_regions


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_confidence_regions.py"
SPLAT_PROPERTIES = [
    "x",
    "y",
    "z",
    "nx",
    "ny",
    "nz",
    "f_dc_0",
    "f_dc_1",
    "f_dc_2",
    "opacity",
    "scale_0",
    "scale_1",
    "scale_2",
]


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def write_sparse_points(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "ply",
                "format ascii 1.0",
                "element vertex 4",
                "property float x",
                "property float y",
                "property float z",
                "property uchar red",
                "property uchar green",
                "property uchar blue",
                "end_header",
                "0 0 0 255 0 0",
                "1 0 0 255 0 0",
                "0 1 0 255 0 0",
                "0 0 1 255 0 0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def splat_row(x: float, y: float, z: float) -> list[float]:
    row = {name: 0.0 for name in SPLAT_PROPERTIES}
    row.update(
        {
            "x": x,
            "y": y,
            "z": z,
            "opacity": 4.0,
            "scale_0": math.log(0.1),
            "scale_1": math.log(0.1),
            "scale_2": math.log(0.1),
        }
    )
    return [row[name] for name in SPLAT_PROPERTIES]


def write_splat(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [splat_row(i / 19, i / 19, i / 19) for i in range(20)]
    rows.extend([splat_row(10.0, 10.0, 10.0), splat_row(-10.0, -10.0, -10.0)])
    header = "\n".join(
        [
            "ply",
            "format binary_little_endian 1.0",
            f"element vertex {len(rows)}",
            *[f"property float {name}" for name in SPLAT_PROPERTIES],
            "end_header",
            "",
        ]
    ).encode("ascii")
    body = b"".join(struct.pack("<" + "f" * len(SPLAT_PROPERTIES), *row) for row in rows)
    path.write_bytes(header + body)


def make_job(tmp_path: Path) -> Path:
    job = tmp_path / "job"
    write_sparse_points(job / "blender-pack" / "import" / "sparse_points.ply")
    write_json(
        job / "blender-pack" / "import" / "camera_path.json",
        {
            "cameraCount": 2,
            "pathSpan": 3.0,
            "cameras": [
                {"id": 1, "center": [0.0, -1.0, 0.5]},
                {"id": 2, "center": [1.0, -1.0, 0.5]},
            ],
        },
    )
    write_splat(job / "exports" / "splat.clean.ply")
    return job


def test_build_confidence_regions_writes_roi_and_low_confidence(tmp_path):
    job = make_job(tmp_path)

    outputs = build_confidence_regions(job, bbox_quantile=0.05, bbox_padding=0.1)

    assert outputs["roi"] == job / "exports" / "roi_candidates.json"
    assert outputs["low_confidence"] == job / "exports" / "low_confidence_regions.json"

    roi = json.loads(outputs["roi"].read_text(encoding="utf-8"))
    low = json.loads(outputs["low_confidence"].read_text(encoding="utf-8"))

    candidates = {candidate["id"]: candidate for candidate in roi["roi_candidates"]}
    assert roi["recommended"] == "splat-clean-robust-bbox"
    assert candidates["splat-clean-robust-bbox"]["coordinate_space"] == "splat_ply"
    assert candidates["sparse-core-robust-bbox"]["coordinate_space"] == "colmap_sparse"
    assert roi["summary"]["sparse_point_count"] == 4
    assert roi["summary"]["camera_count"] == 2
    assert roi["summary"]["splat_count"] == 22

    assert low["roi_source"] == "roi_candidates.json#splat-clean-robust-bbox"
    assert low["regions"][0]["action"] == "fade_or_remove"
    assert low["viewer_hint"]["fadeOutsideRoi"] is True
    assert low["splat_statistics"]["total_count"] == 22
    assert low["splat_statistics"]["inside_roi_count"] == 20
    assert low["splat_statistics"]["outside_roi_count"] == 2
    assert low["splat_statistics"]["outside_roi_ratio"] == 0.0909


def test_cli_prints_written_paths(tmp_path):
    job = make_job(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(job),
            "--bbox-quantile",
            "0.05",
            "--bbox-padding",
            "0.1",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert str(job / "exports" / "roi_candidates.json") in result.stdout
    assert str(job / "exports" / "low_confidence_regions.json") in result.stdout
