from pathlib import Path
import importlib.util
import json
import os
import struct
import subprocess
import sys

import pytest
import trimesh


ROOT = Path(__file__).resolve().parents[1]


def load_compare_bundle_module():
    spec = importlib.util.spec_from_file_location(
        "build_compare_bundle",
        ROOT / "scripts" / "build_compare_bundle.py",
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_tiny_splat(path: Path):
    header = "\n".join(
        [
            "ply",
            "format binary_little_endian 1.0",
            "element vertex 4",
            "property float x",
            "property float y",
            "property float z",
            "property float f_dc_0",
            "property float f_dc_1",
            "property float f_dc_2",
            "property float opacity",
            "property float scale_0",
            "property float scale_1",
            "property float scale_2",
            "end_header",
            "",
        ]
    ).encode("ascii")
    rows = [
        (0, 0, 0, 0.8, 0.0, 0.0, 4.0, -2.0, -2.0, -2.0),
        (1, 0, 0, 0.0, 0.8, 0.0, 4.0, -2.0, -2.0, -2.0),
        (0, 1, 0, 0.0, 0.0, 0.8, -8.0, -2.0, -2.0, -2.0),
        (1, 1, 0, 0.8, 0.8, 0.8, 4.0, 2.0, 2.0, 2.0),
    ]
    path.write_bytes(header + b"".join(struct.pack("<10f", *row) for row in rows))


def test_splat_to_pointcloud_filters_and_writes_rgb(tmp_path):
    source = tmp_path / "splat.clean.ply"
    output = tmp_path / "point_cloud.ply"
    report = tmp_path / "point_cloud_report.json"
    write_tiny_splat(source)

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "splat_to_pointcloud.py"),
            "--input",
            str(source),
            "--output",
            str(output),
            "--report",
            str(report),
            "--min-opacity",
            "0.2",
            "--max-scale",
            "1",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    text = output.read_text()
    assert "property uchar red" in text
    assert "element vertex 2" in text
    assert report.is_file()

    report_data = json.loads(report.read_text())
    assert report_data["input_count"] == 4
    assert report_data["kept_count"] == 2
    assert report_data["removed_count"] == 2
    report_text = json.dumps(report_data)
    assert "min_opacity" in report_text
    assert "max_scale_used" in report_text or "max_scale" in report_text

    data_rows = text.split("end_header\n", 1)[1].strip().splitlines()
    assert len(data_rows) == 2
    columns = [row.split() for row in data_rows]
    assert all(len(row) == 6 for row in columns)
    assert any(row[3:6] != ["0", "0", "0"] for row in columns)


def test_pointcloud_to_mesh_preview_fallback_writes_report(tmp_path):
    point_cloud = tmp_path / "point_cloud.ply"
    mesh = tmp_path / "raw_mesh.ply"
    report = tmp_path / "mesh_report.json"
    point_cloud.write_text(
        "ply\nformat ascii 1.0\nelement vertex 4\n"
        "property float x\nproperty float y\nproperty float z\n"
        "property uchar red\nproperty uchar green\nproperty uchar blue\n"
        "end_header\n"
        "0 0 0 255 0 0\n1 0 0 0 255 0\n0 1 0 0 0 255\n0 0 1 255 255 255\n"
    )

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "pointcloud_to_mesh.py"),
            "--input",
            str(point_cloud),
            "--output",
            str(mesh),
            "--report",
            str(report),
            "--method",
            "convex_hull",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert mesh.is_file()
    assert report.is_file()

    report_data = json.loads(report.read_text())
    assert report_data["method"] == "convex_hull"
    assert report_data["vertex_count"] > 0
    assert report_data["face_count"] > 0
    assert report_data.get("output") or report_data.get("output_path")

    mesh_text = mesh.read_text(errors="ignore")
    assert "element vertex" in mesh_text
    assert "element face" in mesh_text


def test_compare_bundle_rejects_symlinks_before_public_chmod(tmp_path):
    if not hasattr(os, "symlink"):
        pytest.skip("symlink is not available on this platform")

    module = load_compare_bundle_module()
    compare_dir = tmp_path / "uploads" / "42" / "compare"
    compare_dir.mkdir(parents=True)
    outside = tmp_path / "outside.txt"
    outside.write_text("private")
    (compare_dir / "linked.txt").symlink_to(outside)

    with pytest.raises(RuntimeError, match="symlink"):
        module.ensure_safe_compare_tree(compare_dir)


def test_compare_report_urls_are_job_specific_and_fixed_pose(tmp_path):
    module = load_compare_bundle_module()
    job_dir = tmp_path / "uploads" / "42"
    mesh_src = "uploads/42/compare/mesh/cleaned_mesh.glb"
    splat_viewer = {
        "src": "uploads/42/exports/splat.clean.ply",
        "rx": 0,
        "ry": 0,
        "rz": 0,
        "up": "view",
        "distance": 12,
        "alpha": 40,
        "splatScale": 0.35,
    }

    urls = module.build_viewer_urls(job_dir, splat_viewer, mesh_src)

    assert urls["compare"] == "viewer_compare_splat_mesh.html?job=42"
    assert urls["mesh"] == "viewer_mesh.html?src=uploads%2F42%2Fcompare%2Fmesh%2Fcleaned_mesh.glb"
    assert urls["splat"].startswith(
        "viewer_splat.php?src=uploads%2F42%2Fexports%2Fsplat.clean.ply"
    )
    for token in ("rx=0", "ry=0", "rz=0", "up=view", "distance=12", "alpha=40", "splatScale=0.35"):
        assert token in urls["splat"]


def test_trimesh_glb_export_reports_basic_cleanup(tmp_path):
    module = load_compare_bundle_module()
    raw_mesh = tmp_path / "raw_mesh.ply"
    output = tmp_path / "cleaned_mesh.glb"
    mesh = trimesh.Trimesh(
        vertices=[
            [0, 0, 0],
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 1],
            [10, 10, 10],
        ],
        faces=[
            [0, 1, 2],
            [0, 0, 0],
        ],
        process=False,
    )
    mesh.export(raw_mesh)

    stats = module.export_glb_with_trimesh(raw_mesh, output, target_faces=100000)

    assert output.is_file()
    assert stats["exporter"] == "trimesh"
    assert stats["original_vertex_count"] == 5
    assert stats["original_face_count"] == 2
    assert stats["vertex_count"] < stats["original_vertex_count"]
    assert stats["face_count"] < stats["original_face_count"]
    assert stats["target_faces"] == 100000
