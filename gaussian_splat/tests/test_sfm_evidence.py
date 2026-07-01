import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_sfm_evidence.py"


def write_colmap_text_model(model_dir: Path) -> None:
    model_dir.mkdir(parents=True, exist_ok=True)
    (model_dir / "cameras.txt").write_text(
        "\n".join(
            [
                "# Camera list",
                "1 OPENCV 1920 1080 1000 1001 960 540 0.1 0.2 0.3 0.4",
                "",
            ]
        )
    )
    (model_dir / "images.txt").write_text(
        "\n".join(
            [
                "# Image list",
                "1 1 0 0 0 0 0 0 1 frame_0001.jpg",
                "0 0 10",
                "2 0.707 0 0.707 0 1 2 3 1 frame_0002.jpg",
                "1 1 10 2 2 11",
                "",
            ]
        )
    )
    (model_dir / "points3D.txt").write_text(
        "\n".join(
            [
                "# 3D point list",
                "10 0 1 2 255 128 0 0.7 1 0 2 1",
                "11 3 4 5 0 255 128 0.1 1 3 2 4",
                "12 6 7 8 10 20 30 1.2 2 8",
                "",
            ]
        )
    )


def run_script(*args: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *(str(arg) for arg in args)],
        check=False,
        text=True,
        capture_output=True,
    )


def test_sparse_dir_input_writes_evidence_outputs(tmp_path):
    write_colmap_text_model(tmp_path)

    result = run_script(tmp_path)

    assert result.returncode == 0, result.stderr
    evidence = tmp_path / "evidence"
    cameras = json.loads((evidence / "cameras.json").read_text())
    summary = json.loads((evidence / "coverage_summary.json").read_text())
    assert (evidence / "points3d_tracks.jsonl").exists()
    assert cameras["version"] == "1.0.3"
    assert cameras["coordinate_system"] == {"base": "colmap_world"}
    assert cameras["cameras"][0]["name"] == "frame_0001.jpg"
    assert cameras["camera_models"]["1"]["model"] == "OPENCV"
    assert summary["camera_count"] == 2
    assert summary["sparse_point_count"] == 3
    assert summary["track_length"] == {"min": 1, "max": 2, "avg": 1.67}
    assert summary["visible_camera_count"] == {"min": 1, "max": 2, "avg": 1.67}
    assert summary["reprojection_error"] == {"min": 0.1, "max": 1.2, "avg": 0.67}


def test_workspace_dir_input_writes_evidence_under_workspace(tmp_path):
    write_colmap_text_model(tmp_path / "sparse" / "0")

    result = run_script(tmp_path)

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "evidence" / "cameras.json").exists()
    assert (tmp_path / "evidence" / "points3d_tracks.jsonl").exists()
    assert (tmp_path / "evidence" / "coverage_summary.json").exists()


def test_points3d_track_parsing_writes_image_id_and_point2d_idx(tmp_path):
    write_colmap_text_model(tmp_path)

    result = run_script(tmp_path)

    assert result.returncode == 0, result.stderr
    rows = [
        json.loads(line)
        for line in (tmp_path / "evidence" / "points3d_tracks.jsonl").read_text().splitlines()
    ]
    assert rows[0]["point3d_id"] == 10
    assert rows[0]["track"] == [{"image_id": 1, "point2d_idx": 0}, {"image_id": 2, "point2d_idx": 1}]


def test_empty_points2d_line_is_valid(tmp_path):
    write_colmap_text_model(tmp_path)
    (tmp_path / "images.txt").write_text(
        "\n".join(
            [
                "# Image list",
                "1 1 0 0 0 0 0 0 1 frame_0001.jpg",
                "",
                "2 0.707 0 0.707 0 1 2 3 1 frame_0002.jpg",
                "1 1 10 2 2 11",
                "",
            ]
        )
    )

    result = run_script(tmp_path)

    assert result.returncode == 0, result.stderr
    cameras = json.loads((tmp_path / "evidence" / "cameras.json").read_text())
    assert [camera["name"] for camera in cameras["cameras"]] == ["frame_0001.jpg", "frame_0002.jpg"]


def test_malformed_points2d_line_exits_with_clear_message(tmp_path):
    write_colmap_text_model(tmp_path)
    (tmp_path / "images.txt").write_text(
        "\n".join(
            [
                "# Image list",
                "1 1 0 0 0 0 0 0 1 frame_0001.jpg",
                "0 0",
                "",
            ]
        )
    )

    result = run_script(tmp_path)

    assert result.returncode != 0
    assert "Malformed images.txt line 3" in result.stderr
    assert "POINTS2D triples" in result.stderr


def test_missing_colmap_file_exits_with_clear_message(tmp_path):
    (tmp_path / "cameras.txt").write_text("1 SIMPLE_PINHOLE 10 10 1 5 5\n")
    (tmp_path / "images.txt").write_text("")

    result = run_script(tmp_path)

    assert result.returncode != 0
    assert "Missing COLMAP text file" in result.stderr
    assert "points3D.txt" in result.stderr


def test_cli_writes_custom_output_dir_and_prints_path(tmp_path):
    write_colmap_text_model(tmp_path / "sparse" / "0")
    output_dir = tmp_path / "custom_evidence"

    result = run_script(tmp_path, Path("--output-dir"), output_dir)

    assert result.returncode == 0, result.stderr
    assert (output_dir / "cameras.json").exists()
    assert str(output_dir) in result.stdout
