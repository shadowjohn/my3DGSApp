from __future__ import annotations

import json
import math
import struct
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "filter_splat_ply.py"
PROPERTIES = [
    "x",
    "y",
    "z",
    "nx",
    "ny",
    "nz",
    "f_dc_0",
    "f_dc_1",
    "f_dc_2",
    "f_rest_0",
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


def make_row(
    x: float,
    y: float,
    z: float,
    opacity: float,
    scale: float,
) -> list[float]:
    row = {name: 0.0 for name in PROPERTIES}
    row.update(
        {
            "x": x,
            "y": y,
            "z": z,
            "opacity": logit(opacity),
            "scale_0": math.log(scale),
            "scale_1": math.log(scale * 0.9),
            "scale_2": math.log(scale * 0.8),
            "rot_0": 1.0,
        }
    )
    return [row[name] for name in PROPERTIES]


def write_ply(path: Path, rows: list[list[float]]) -> bytes:
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
    body = b"".join(struct.pack("<" + "f" * len(PROPERTIES), *row) for row in rows)
    path.write_bytes(header + body)
    return header


def write_fixture(path: Path) -> bytes:
    return write_ply(
        path,
        [
        make_row(0.0, 0.0, 0.0, 0.95, 0.10),
        make_row(1.0, 0.0, 0.0, 0.92, 0.12),
        make_row(0.0, 1.0, 0.0, 0.90, 0.11),
        make_row(0.0, 0.0, 1.0, 0.89, 0.13),
        make_row(0.2, 0.2, 0.2, 0.03, 0.10),
        make_row(0.4, 0.4, 0.4, 0.91, 5.00),
        make_row(50.0, 50.0, 50.0, 0.94, 0.10),
        ],
    )


def read_header_and_count(path: Path) -> tuple[bytes, int]:
    data = path.read_bytes()
    header, _body = data.split(b"end_header\n", 1)
    header += b"end_header\n"
    for line in header.decode("ascii").splitlines():
        if line.startswith("element vertex "):
            return header, int(line.rsplit(" ", 1)[1])
    raise AssertionError("vertex count not found")


def test_cli_filters_binary_little_endian_ply_and_writes_metadata(tmp_path):
    source = tmp_path / "input.ply"
    output = tmp_path / "filtered.ply"
    meta_path = tmp_path / "filtered.json"
    input_header = write_fixture(source)

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(source),
            str(output),
            "--meta",
            str(meta_path),
            "--min-opacity",
            "0.18",
            "--max-scale",
            "0.25",
            "--bbox-quantile",
            "0.25",
            "--bbox-padding",
            "0.20",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    output_header, output_count = read_header_and_count(output)
    assert output_count == 4
    assert output_header == input_header.replace(b"element vertex 7", b"element vertex 4")

    meta = json.loads(meta_path.read_text())
    assert "source" not in meta
    assert "output" not in meta
    assert meta["source_name"] == source.name
    assert meta["output_name"] == output.name
    assert meta["input_count"] == 7
    assert meta["kept_count"] == 4
    assert meta["removed_count"] == 3
    assert meta["kept_ratio"] == 4 / 7
    assert meta["filters"]["min_opacity"] == 0.18
    assert meta["filters"]["max_scale_used"] == 0.25
    assert meta["filters"]["bbox_quantile"] == 0.25
    assert meta["core"]["center"] == [0.5, 0.5, 0.5]
    assert meta["core"]["bbox_min"] == [0.0, 0.0, 0.0]
    assert meta["core"]["bbox_max"] == [1.0, 1.0, 1.0]
    assert math.isclose(meta["core"]["radius"], math.sqrt(3) / 2, rel_tol=1e-6)
    assert meta["cesium"]["center_model"] == meta["core"]["center"]
    assert meta["cesium"]["radius_model"] == meta["core"]["radius"]
    assert meta["viewer"]["alpha"] == 40
    assert meta["viewer"]["splatScale"] == 0.25
    assert meta["viewer"]["rx"] == 0
    assert meta["viewer"]["ry"] == 0
    assert meta["viewer"]["rz"] == 0
    assert meta["viewer"]["upMode"] == "view"
    assert meta["viewer"]["cameraDistance"] == max(1, meta["core"]["radius"] * 2.2)

    cleanup_source = tmp_path / "cleanup-input.ply"
    cleanup_output = tmp_path / "cleanup-filtered.ply"
    cleanup_meta_path = tmp_path / "cleanup-filtered.json"
    write_ply(
        cleanup_source,
        [
            make_row(0.0, 0.0, 0.0, 0.95, 0.10),
            make_row(0.2, 0.2, 0.2, 0.03, 0.10),
            make_row(0.4, 0.4, 0.4, 0.91, 5.00),
        ],
    )

    cleanup_result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(cleanup_source),
            str(cleanup_output),
            "--meta",
            str(cleanup_meta_path),
            "--min-opacity",
            "0.18",
            "--max-scale",
            "0.25",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert cleanup_result.returncode == 0, cleanup_result.stderr
    cleanup_meta = json.loads(cleanup_meta_path.read_text())
    assert cleanup_meta["cleanup"]["source_vertex_count"] == 3
    assert cleanup_meta["cleanup"]["kept_vertex_count"] == 1
    assert cleanup_meta["cleanup"]["removed_vertex_count"] == 2
    assert cleanup_meta["cleanup"]["kept_ratio"] == 0.33
    assert cleanup_meta["cleanup"]["filters"]["min_opacity"] == 0.18
    assert "max_scale_used" in cleanup_meta["cleanup"]["filters"]


def test_cli_can_use_auto_scale_threshold(tmp_path):
    source = tmp_path / "input.ply"
    output = tmp_path / "filtered.ply"
    meta_path = tmp_path / "filtered.json"
    write_fixture(source)

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(source),
            str(output),
            "--meta",
            str(meta_path),
            "--max-scale",
            "0",
            "--scale-quantile",
            "0.8",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    _header, output_count = read_header_and_count(output)
    meta = json.loads(meta_path.read_text())
    assert output_count == meta["kept_count"]
    assert meta["filters"]["max_scale_used"] >= 0.25
    assert meta["filters"]["scale_quantile"] == 0.8


def test_small_bbox_quantile_keeps_valid_edge_splats(tmp_path):
    source = tmp_path / "input.ply"
    output = tmp_path / "filtered.ply"
    meta_path = tmp_path / "filtered.json"
    write_ply(
        source,
        [
            make_row(0.0, 0.0, 0.0, 0.95, 0.10),
            make_row(1.0, 0.0, 0.0, 0.92, 0.10),
            make_row(0.0, 1.0, 0.0, 0.90, 0.10),
            make_row(0.0, 0.0, 1.0, 0.89, 0.10),
        ],
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(source),
            str(output),
            "--meta",
            str(meta_path),
            "--max-scale",
            "0.25",
            "--bbox-quantile",
            "0.01",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    _header, output_count = read_header_and_count(output)
    meta = json.loads(meta_path.read_text())
    assert output_count == 4
    assert meta["kept_count"] == 4
    assert meta["removed_count"] == 0
    assert meta["core"]["center"] == [0.5, 0.5, 0.5]


@pytest.mark.parametrize("vertex_count", ["nope", "-1"])
def test_malformed_vertex_count_returns_clean_cli_error(tmp_path, vertex_count):
    source = tmp_path / "bad.ply"
    output = tmp_path / "filtered.ply"
    source.write_bytes(
        b"\n".join(
            [
                b"ply",
                b"format binary_little_endian 1.0",
                f"element vertex {vertex_count}".encode("ascii"),
                b"property float x",
                b"property float y",
                b"property float z",
                b"property float opacity",
                b"property float scale_0",
                b"property float scale_1",
                b"property float scale_2",
                b"end_header",
                b"",
            ]
        )
    )

    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(source), str(output)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "invalid vertex count" in result.stderr
    assert "Traceback" not in result.stderr
