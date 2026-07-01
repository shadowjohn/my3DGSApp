import importlib.util
import json
import math
import subprocess
import struct
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_gaussian_appearance_summary.py"


def load_script_module():
    spec = importlib.util.spec_from_file_location("build_gaussian_appearance_summary", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def run_script(*args: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *(str(arg) for arg in args)],
        check=False,
        text=True,
        capture_output=True,
    )


def write_ascii_splat(path: Path, rows: list[tuple[float, float, float, float, float, float, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "ply",
                "format ascii 1.0",
                f"element vertex {len(rows)}",
                "property float x",
                "property float y",
                "property float z",
                "property float opacity",
                "property float scale_0",
                "property float scale_1",
                "property float scale_2",
                "end_header",
                *[" ".join(str(value) for value in row) for row in rows],
                "",
            ]
        )
    )


def write_binary_splat(path: Path, rows: list[tuple[float, ...]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    header = "\n".join(
        [
            "ply",
            "format binary_little_endian 1.0",
            f"element vertex {len(rows)}",
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
    payload = b"".join(struct.pack("<10f", *row) for row in rows)
    path.write_bytes(header + payload)


def test_splat_and_qa_emit_both_summaries(tmp_path):
    write_ascii_splat(
        tmp_path / "exports" / "splat.ply",
        [
            (0, 1, 2, 0.0, math.log(0.25), math.log(0.5), math.log(0.125)),
            (4, 5, 6, math.log(3), math.log(2), math.log(4), math.log(1)),
        ],
    )
    (tmp_path / "processed" / "colmap").mkdir(parents=True)
    (tmp_path / "qa_report.json").write_text(
        json.dumps(
            {
                "splat_count": 99,
                "splat_file_size_mb": 12.3,
                "frame_count": 100,
                "registered_count": 86,
                "registered_ratio": 0.86,
                "psnr": 28.5,
            }
        )
    )
    (tmp_path / "timing_report.json").write_text(
        json.dumps({"duration_seconds": 120, "stages": [{"key": "train", "duration_seconds": 90}]})
    )

    result = run_script(tmp_path)

    assert result.returncode == 0, result.stderr
    appearance_path = tmp_path / "evidence" / "appearance_summary.json"
    splat_path = tmp_path / "evidence" / "splat_summary.json"
    assert str(appearance_path) in result.stdout
    assert splat_path.exists()
    appearance = json.loads(appearance_path.read_text())
    splat = json.loads(splat_path.read_text())
    assert appearance["version"] == "1.0.3"
    assert appearance["coordinate_system"] == {"base": "colmap_world"}
    assert appearance["artifacts"]["splat"] == "exports/splat.ply"
    assert appearance["artifacts"]["qa_report"] == "qa_report.json"
    assert appearance["artifacts"]["timing_report"] == "timing_report.json"
    assert appearance["artifacts"]["colmap_workspace"] == "processed/colmap"
    assert appearance["cameras"] == {
        "source": "processed/colmap",
        "frame_count": 100,
        "registered_count": 86,
        "registered_ratio": 0.86,
    }
    assert appearance["splat"]["available"] is True
    assert appearance["splat"]["path"] == "exports/splat.ply"
    assert appearance["splat"]["count"] == 2
    assert appearance["splat"]["bbox"] == {"min": [0, 1, 2], "max": [4, 5, 6]}
    assert appearance["splat"]["file_size_mb"] == 12.3
    assert appearance["opacity"]["available"] is True
    assert appearance["opacity"]["min"] == pytest.approx(0.5)
    assert appearance["opacity"]["max"] == pytest.approx(0.75)
    assert appearance["opacity"]["avg"] == pytest.approx(0.625)
    assert appearance["scale"]["available"] is True
    assert appearance["scale"]["min"] == pytest.approx(0.5)
    assert appearance["scale"]["max"] == pytest.approx(4)
    assert appearance["scale"]["avg"] == pytest.approx(2.25)
    assert appearance["training"]["training_time_seconds"] == 90.0
    assert appearance["render_quality"] == {"available": True, "psnr": 28.5, "ssim": None}
    assert splat["splat_path"] == "exports/splat.ply"
    assert splat["splat_count"] == 2
    assert splat["bbox"] == {"min": [0, 1, 2], "max": [4, 5, 6]}


def test_missing_timing_and_metrics_still_emits_unknowns(tmp_path):
    write_ascii_splat(tmp_path / "splat.ply", [(1, 2, 3, 0.2, -1, -1, -1)])

    result = run_script(tmp_path)

    assert result.returncode == 0, result.stderr
    summary = json.loads((tmp_path / "evidence" / "appearance_summary.json").read_text())
    assert summary["training"] == {
        "iterations": None,
        "training_time_seconds": None,
        "final_loss": None,
        "psnr": None,
        "ssim": None,
    }
    assert summary["render_quality"] == {"available": False, "psnr": None, "ssim": None}


def test_binary_splat_validation_metrics_include_black_transparent_and_outlier_ratios(tmp_path):
    write_binary_splat(
        tmp_path / "exports" / "splat.ply",
        [
            (0, 0, 0, -2, -2, -2, -8, 0, 0, 0),
            (1, 1, 1, 4, 4, 4, 0, 0, 0, 0),
            (2_000_000, 0, 0, 4, 4, 4, 0, 5, 5, 5),
        ],
    )

    result = run_script(tmp_path)

    assert result.returncode == 0, result.stderr
    summary = json.loads((tmp_path / "evidence" / "appearance_summary.json").read_text())
    validation = summary["validation"]
    assert validation["black_ratio"] == pytest.approx(1 / 3)
    assert validation["transparent_ratio"] == pytest.approx(1 / 3)
    assert validation["scale_outlier_ratio"] == pytest.approx(1 / 3)
    assert validation["bbox_outlier_ratio"] == pytest.approx(1 / 3)
    assert validation["floating_artifact_risk"] == "medium"


def test_missing_opacity_and_scale_are_unavailable(tmp_path):
    ply = tmp_path / "exports" / "splat.ply"
    ply.parent.mkdir()
    ply.write_text(
        "\n".join(
            [
                "ply",
                "format ascii 1.0",
                "element vertex 1",
                "property float x",
                "property float y",
                "property float z",
                "end_header",
                "1 2 3",
                "",
            ]
        )
    )

    result = run_script(tmp_path)

    assert result.returncode == 0, result.stderr
    summary = json.loads((tmp_path / "evidence" / "appearance_summary.json").read_text())
    assert summary["opacity"] == {"available": False, "min": None, "max": None, "avg": None}
    assert summary["scale"] == {"available": False, "min": None, "max": None, "avg": None}


def test_missing_splat_still_emits_summary_with_qa_fields(tmp_path):
    (tmp_path / "qa_report.json").write_text(
        json.dumps({"splat_count": 44, "splat_file_size_mb": 5.5, "registered_frame_count": 7})
    )

    result = run_script(tmp_path)

    assert result.returncode == 0, result.stderr
    summary = json.loads((tmp_path / "evidence" / "appearance_summary.json").read_text())
    splat = json.loads((tmp_path / "evidence" / "splat_summary.json").read_text())
    assert summary["splat"] == {
        "available": False,
        "path": None,
        "count": 44,
        "bbox": None,
        "file_size_mb": 5.5,
    }
    assert summary["cameras"]["registered_count"] == 7
    assert splat["splat_path"] is None
    assert splat["splat_count"] == 44


def test_qa_sfm_sparse_model_path_fills_camera_source(tmp_path):
    (tmp_path / "qa_report.json").write_text(json.dumps({"sfm": {"sparse_model_path": "processed/sparse/0"}}))

    result = run_script(tmp_path)

    assert result.returncode == 0, result.stderr
    summary = json.loads((tmp_path / "evidence" / "appearance_summary.json").read_text())
    assert summary["cameras"]["source"] == "processed/sparse/0"
    assert summary["artifacts"]["colmap_workspace"] == "processed/sparse/0"


def test_missing_splat_summary_marks_unavailable(tmp_path):
    result = run_script(tmp_path)

    assert result.returncode == 0, result.stderr
    splat = json.loads((tmp_path / "evidence" / "splat_summary.json").read_text())
    assert splat["available"] is False


def test_quality_grade_and_label_are_preserved(tmp_path):
    (tmp_path / "qa_report.json").write_text(json.dumps({"quality_grade": "B", "quality_label": "good"}))

    result = run_script(tmp_path)

    assert result.returncode == 0, result.stderr
    summary = json.loads((tmp_path / "evidence" / "appearance_summary.json").read_text())
    assert summary["quality"] == {"grade": "B", "label": "good"}


def test_zero_qa_values_are_not_treated_as_missing(tmp_path):
    (tmp_path / "qa_report.json").write_text(
        json.dumps(
            {
                "registered_count": 0,
                "splat_file_size_mb": 0.0,
                "training_iterations": 0,
                "final_loss": 0.0,
            }
        )
    )

    result = run_script(tmp_path)

    assert result.returncode == 0, result.stderr
    summary = json.loads((tmp_path / "evidence" / "appearance_summary.json").read_text())
    assert summary["cameras"]["registered_count"] == 0
    assert summary["splat"]["file_size_mb"] == 0.0
    assert summary["training"]["iterations"] == 0
    assert summary["training"]["final_loss"] == 0.0


def test_malformed_selected_splat_fails_clearly(tmp_path):
    bad = tmp_path / "exports" / "splat.clean.ply"
    bad.parent.mkdir()
    bad.write_text("not a ply\n")

    result = run_script(tmp_path)

    assert result.returncode != 0
    assert "Malformed PLY" in result.stderr
    assert str(bad) in result.stderr


def test_non_finite_ascii_ply_value_fails_clearly(tmp_path):
    bad = tmp_path / "exports" / "splat.ply"
    write_ascii_splat(bad, [(0, 1, 2, float("nan"), 0, 0, 0)])

    result = run_script(tmp_path)

    assert result.returncode != 0
    assert "Malformed PLY vertex value" in result.stderr
    assert str(bad) in result.stderr


def test_write_json_is_strict_and_wraps_write_errors(tmp_path, monkeypatch):
    module = load_script_module()

    with pytest.raises(ValueError):
        module.write_json(tmp_path / "nan.json", {"bad": float("nan")})

    def fail_write_text(*args, **kwargs):
        raise OSError("no space")

    monkeypatch.setattr(Path, "write_text", fail_write_text)
    with pytest.raises(module.GaussianAppearanceError, match="Cannot write output JSON"):
        module.write_json(tmp_path / "out.json", {"ok": True})


def test_cli_custom_output_dir_writes_both_files_and_prints_appearance_path(tmp_path):
    write_ascii_splat(tmp_path / "exports" / "splat.ply", [(0, 0, 0, 0, -1, -2, -3)])
    output_dir = tmp_path / "custom_evidence"

    result = run_script(tmp_path, Path("--output-dir"), output_dir)

    assert result.returncode == 0, result.stderr
    appearance_path = output_dir / "appearance_summary.json"
    assert appearance_path.exists()
    assert (output_dir / "splat_summary.json").exists()
    assert str(appearance_path) in result.stdout
