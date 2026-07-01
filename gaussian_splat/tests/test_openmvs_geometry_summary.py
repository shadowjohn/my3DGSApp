import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_openmvs_geometry_summary.py"


def run_script(*args: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *(str(arg) for arg in args)],
        check=False,
        text=True,
        capture_output=True,
    )


def write_ascii_ply(path: Path, rows: list[tuple[float, float, float]], faces: int = 0, normals: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normal_props = ["property float nx", "property float ny", "property float nz"] if normals else []
    point_rows = [
        " ".join([str(x), str(y), str(z), *(["0", "0", "1"] if normals else [])])
        for x, y, z in rows
    ]
    path.write_text(
        "\n".join(
            [
                "ply",
                "format ascii 1.0",
                f"element vertex {len(rows)}",
                "property float x",
                "property float y",
                "property float z",
                *normal_props,
                f"element face {faces}",
                "property list uchar int vertex_indices",
                "end_header",
                *point_rows,
                "",
            ]
        )
    )


def test_openmvs_artifacts_emit_geometry_summary(tmp_path):
    exports = tmp_path / "exports"
    exports.mkdir()
    (exports / "model.glb").write_bytes(b"glb")
    write_ascii_ply(
        exports / "scene_dense_mesh_refine_texture.ply",
        [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)],
        faces=2,
        normals=True,
    )
    write_ascii_ply(exports / "scene_dense.ply", [(0, 0, 0), (2, 1, 3), (-1, 0, 1), (1, 1, 1), (0, 2, 2)])
    (exports / "scene_dense_mesh_refine_texture_0.png").write_bytes(b"png")
    (tmp_path / "qa_report.json").write_text(
        json.dumps(
            {
                "mesh_path": "exports/qa_mesh.ply",
                "texture_image_count": 1,
                "texture_width": 2,
                "texture_height": 2,
                "texture_black_pixel_ratio": 0.25,
                "texture_white_empty_pixel_ratio": 0.25,
                "texture_patch_count": 7,
            }
        )
    )

    result = run_script(tmp_path)

    assert result.returncode == 0, result.stderr
    summary_path = tmp_path / "evidence" / "geometry_summary.json"
    assert str(summary_path) in result.stdout
    summary = json.loads(summary_path.read_text())
    assert summary["version"] == "1.0.3"
    assert summary["coordinate_system"] == {"base": "colmap_world"}
    assert summary["artifacts"] == {
        "mesh": "exports/model.glb",
        "mesh_ply": "exports/scene_dense_mesh_refine_texture.ply",
        "dense_cloud": "exports/scene_dense.ply",
        "texture": "exports/scene_dense_mesh_refine_texture_0.png",
    }
    assert summary["mesh"] == {
        "vertex_count": 4,
        "face_count": 2,
        "bbox": {"min": [0, 0, 0], "max": [1, 1, 0]},
        "normal_available": True,
    }
    assert summary["dense_cloud"]["point_count"] == 5
    assert summary["dense_cloud"]["bbox"] == {"min": [-1, 0, 0], "max": [2, 2, 3]}
    assert summary["texture"] == {
        "available": True,
        "path": "exports/scene_dense_mesh_refine_texture_0.png",
        "image_count": 1,
        "width": 2,
        "height": 2,
        "black_pixel_ratio": 0.25,
        "white_empty_pixel_ratio": 0.25,
        "patch_count": 7,
    }
    assert summary["risks"] == {
        "hole_risk_summary": "unknown",
        "thin_geometry_risk": "unknown",
        "density_summary": "unknown",
    }


def test_missing_dense_cloud_and_texture_still_emits_summary(tmp_path):
    exports = tmp_path / "exports"
    exports.mkdir()
    write_ascii_ply(exports / "scene_dense_mesh.ply", [(0, 0, 0)])

    result = run_script(tmp_path)

    assert result.returncode == 0, result.stderr
    summary = json.loads((tmp_path / "evidence" / "geometry_summary.json").read_text())
    assert summary["artifacts"]["mesh"] is None
    assert summary["artifacts"]["dense_cloud"] is None
    assert summary["texture"]["available"] is False
    assert summary["dense_cloud"] == {"point_count": None, "bbox": None}


def test_malformed_optional_dense_cloud_does_not_abort_summary(tmp_path):
    exports = tmp_path / "exports"
    exports.mkdir()
    write_ascii_ply(exports / "scene_dense_mesh.ply", [(0, 0, 0)])
    (exports / "scene_dense.ply").write_text("ply\nformat ascii 1.0\nelement vertex 2\n")

    result = run_script(tmp_path)

    assert result.returncode == 0, result.stderr
    summary = json.loads((tmp_path / "evidence" / "geometry_summary.json").read_text())
    assert summary["mesh"]["vertex_count"] == 1
    assert summary["dense_cloud"] == {"point_count": None, "bbox": None}


def test_corrupt_ascii_optional_dense_cloud_does_not_abort_summary(tmp_path):
    exports = tmp_path / "exports"
    exports.mkdir()
    write_ascii_ply(exports / "scene_dense_mesh.ply", [(0, 0, 0)])
    (exports / "scene_dense.ply").write_bytes(
        b"\n".join(
            [
                b"ply",
                b"format ascii 1.0",
                b"element vertex 1",
                b"property float x",
                b"property float y",
                b"property float z",
                b"end_header",
                b"\xff 0 0",
                b"",
            ]
        )
    )

    result = run_script(tmp_path)

    assert result.returncode == 0, result.stderr
    summary = json.loads((tmp_path / "evidence" / "geometry_summary.json").read_text())
    assert summary["mesh"]["vertex_count"] == 1
    assert summary["dense_cloud"] == {"point_count": None, "bbox": None}


def test_native_mvs_artifacts_are_detected(tmp_path):
    mvs = tmp_path / "mvs"
    mvs.mkdir()
    (mvs / "scene_dense_mesh_refine_texture.glb").write_bytes(b"glb")
    write_ascii_ply(mvs / "scene_dense_mesh_refine_texture.ply", [(0, 0, 0), (2, 0, 0)], faces=1)
    write_ascii_ply(mvs / "scene_dense.ply", [(0, 0, 0), (0, 3, 0)])
    (mvs / "scene_dense_mesh_refine_texture_0.jpg").write_bytes(b"jpg")

    result = run_script(tmp_path)

    assert result.returncode == 0, result.stderr
    summary = json.loads((tmp_path / "evidence" / "geometry_summary.json").read_text())
    assert summary["artifacts"] == {
        "mesh": "mvs/scene_dense_mesh_refine_texture.glb",
        "mesh_ply": "mvs/scene_dense_mesh_refine_texture.ply",
        "dense_cloud": "mvs/scene_dense.ply",
        "texture": "mvs/scene_dense_mesh_refine_texture_0.jpg",
    }
    assert summary["mesh"]["vertex_count"] == 2
    assert summary["dense_cloud"]["point_count"] == 2
    assert summary["texture"]["available"] is True


def test_qa_report_glb_and_mesh_ply_fallbacks(tmp_path):
    (tmp_path / "qa_report.json").write_text(
        json.dumps(
            {
                "glb_path": "exports/from_qa.glb",
                "mesh_path": "exports/from_qa.ply",
            }
        )
    )

    result = run_script(tmp_path)

    assert result.returncode == 0, result.stderr
    artifacts = json.loads((tmp_path / "evidence" / "geometry_summary.json").read_text())["artifacts"]
    assert artifacts["mesh"] == "exports/from_qa.glb"
    assert artifacts["mesh_ply"] == "exports/from_qa.ply"


def test_binary_ply_header_returns_counts_and_null_bbox(tmp_path):
    exports = tmp_path / "exports"
    exports.mkdir()
    (exports / "scene_dense_mesh.ply").write_bytes(
        b"\n".join(
            [
                b"ply",
                b"format binary_little_endian 1.0",
                b"element vertex 9",
                b"property float x",
                b"property float y",
                b"property float z",
                b"property float nx",
                b"property float ny",
                b"property float nz",
                b"element face 3",
                b"property list uchar int vertex_indices",
                b"end_header",
            ]
        )
    )

    result = run_script(tmp_path)

    assert result.returncode == 0, result.stderr
    mesh = json.loads((tmp_path / "evidence" / "geometry_summary.json").read_text())["mesh"]
    assert mesh == {"vertex_count": 9, "face_count": 3, "bbox": None, "normal_available": True}


def test_summary_json_contains_no_visibility_key(tmp_path):
    exports = tmp_path / "exports"
    exports.mkdir()
    write_ascii_ply(exports / "scene_dense_mesh.ply", [(0, 0, 0)])

    result = run_script(tmp_path)

    assert result.returncode == 0, result.stderr
    assert "visibility" not in (tmp_path / "evidence" / "geometry_summary.json").read_text()


def test_cli_custom_output_dir_writes_file_and_prints_path(tmp_path):
    exports = tmp_path / "exports"
    exports.mkdir()
    write_ascii_ply(exports / "scene_dense_mesh.ply", [(0, 0, 0)])
    output_dir = tmp_path / "custom_evidence"

    result = run_script(tmp_path, Path("--output-dir"), output_dir)

    assert result.returncode == 0, result.stderr
    summary_path = output_dir / "geometry_summary.json"
    assert summary_path.exists()
    assert str(summary_path) in result.stdout
