import json
import subprocess
import sys
from pathlib import Path

from scripts.build_ab_evidence_report import build_evidence_report


def make_job(
    tmp_path: Path,
    name: str,
    frames: int,
    registered: int,
    splat_count: int,
    cleanup: dict | None = None,
    write_clean_ply: bool = True,
    quality_grade: str = "B",
    warnings: list[str] | None = None,
) -> Path:
    job = tmp_path / name
    images = job / "images"
    processed = job / "processed"
    exports = job / "exports"
    images.mkdir(parents=True)
    processed.mkdir()
    exports.mkdir()
    for index in range(frames):
        (images / f"frame_{index + 1:05d}.jpg").write_bytes(b"jpg")
    (processed / "transforms.json").write_text(
        json.dumps(
            {
                "frames": [
                    {
                        "file_path": f"images/frame_{index + 1:05d}.jpg",
                        "transform_matrix": [
                            [1, 0, 0, float(index)],
                            [0, 1, 0, 2.0],
                            [0, 0, 1, 3.0],
                        ],
                    }
                    for index in range(registered)
                ]
            }
        )
    )
    (exports / "splat.ply").write_text(
        "ply\nformat binary_little_endian 1.0\nelement vertex "
        + str(splat_count)
        + "\nproperty float x\nend_header\n"
    )
    if cleanup is not None:
        if write_clean_ply:
            (exports / "splat.clean.ply").write_text(
                "ply\nformat binary_little_endian 1.0\nelement vertex "
                + str(cleanup["kept_vertex_count"])
                + "\nproperty float x\nend_header\n"
            )
        (exports / "splat.clean.viewer.json").write_text(json.dumps({"cleanup": cleanup}))
    (job / "timing_report.json").write_text(
        json.dumps({"duration_seconds": 123.4, "stages": [{"key": "train", "duration_seconds": 90.0}]})
    )
    (job / "qa_report.json").write_text(
        json.dumps({"quality_grade": quality_grade, "warnings": warnings or []})
    )
    return job


def test_build_evidence_report_compares_variants(tmp_path):
    baseline = make_job(
        tmp_path,
        "baseline",
        frames=90,
        registered=60,
        splat_count=1000,
        cleanup={
            "source_vertex_count": 1000,
            "kept_vertex_count": 875,
            "removed_vertex_count": 125,
            "kept_ratio": 0.88,
            "filters": {"min_opacity": 0.18, "max_scale_used": 0.25},
        },
    )
    selected = make_job(
        tmp_path,
        "selected",
        frames=120,
        registered=110,
        splat_count=1500,
        cleanup={
            "source_vertex_count": 1500,
            "kept_vertex_count": 1300,
            "removed_vertex_count": 200,
            "kept_ratio": 0.87,
            "filters": {"min_opacity": 0.18, "max_scale_used": 0.25},
        },
    )

    report = build_evidence_report(
        [
            ("baseline_30k", baseline),
            ("selected_30k", selected),
        ],
        viewer_base_url="https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_splat.php",
        project_root=tmp_path,
    )

    assert report["summary"]["variant_count"] == 2
    assert report["conclusion"]["recommended_variant"] == "selected_30k"
    assert "selected_30k" in report["conclusion"]["reason"]
    assert "registered_ratio 0.92" in report["conclusion"]["reason"]
    assert "Review clean viewer" in report["conclusion"]["next_action"]
    assert report["variants"][0]["variant"] == "baseline_30k"
    assert report["variants"][0]["registered_ratio"] == 0.67
    assert report["variants"][0]["splat_count"] == 1000
    assert report["variants"][0]["cleanup_source_vertex_count"] == 1000
    assert report["variants"][0]["cleanup_kept_vertex_count"] == 875
    assert report["variants"][0]["cleanup_removed_vertex_count"] == 125
    assert report["variants"][0]["cleanup_kept_ratio"] == 0.88
    assert report["variants"][0]["cleanup_filters"] == {"min_opacity": 0.18, "max_scale_used": 0.25}
    assert report["variants"][0]["clean_splat_path"].endswith("exports/splat.clean.ply")
    assert "viewer_splat.php?src=" in report["variants"][0]["clean_web_viewer_url"]
    assert "splat.clean.ply" in report["variants"][0]["clean_web_viewer_url"]
    assert report["variants"][0]["psnr_status"] == "not_computed_requires_rendered_eval_images"
    assert "ns-viewer --load-config" in report["variants"][0]["official_viewer_command"]
    assert "outputs/*/splatfacto/*/config.yml" in report["variants"][0]["official_viewer_command"]
    assert "viewer_splat.php?src=" in report["variants"][1]["web_viewer_url"]


def test_build_evidence_report_ignores_malformed_cleanup_values(tmp_path):
    malformed = make_job(
        tmp_path,
        "malformed",
        frames=12,
        registered=9,
        splat_count=200,
        cleanup={
            "source_vertex_count": "200",
            "kept_vertex_count": "oops",
            "removed_vertex_count": "nope",
            "kept_ratio": "bad",
            "filters": "not-a-dict",
        },
    )

    report = build_evidence_report(
        [("malformed_30k", malformed)],
        viewer_base_url="https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_splat.php",
        project_root=tmp_path,
    )

    row = report["variants"][0]
    assert row["cleanup_source_vertex_count"] == 200
    assert row["cleanup_kept_vertex_count"] is None
    assert row["cleanup_removed_vertex_count"] is None
    assert row["cleanup_kept_ratio"] is None
    assert row["cleanup_filters"] is None
    assert row["clean_splat_path"].endswith("exports/splat.clean.ply")


def test_build_evidence_report_hides_cleanup_stats_without_clean_ply(tmp_path):
    job = make_job(
        tmp_path,
        "metadata-only",
        frames=12,
        registered=9,
        splat_count=200,
        cleanup={
            "source_vertex_count": 200,
            "kept_vertex_count": 180,
            "removed_vertex_count": 20,
            "kept_ratio": 0.9,
            "filters": {"min_opacity": 0.18},
        },
        write_clean_ply=False,
    )

    report = build_evidence_report(
        [("metadata_only_30k", job)],
        viewer_base_url="https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_splat.php",
        project_root=tmp_path,
    )

    row = report["variants"][0]
    assert row["clean_splat_path"] is None
    assert row["clean_web_viewer_url"] is None
    assert row["cleanup_source_vertex_count"] is None
    assert row["cleanup_kept_vertex_count"] is None
    assert row["cleanup_removed_vertex_count"] is None
    assert row["cleanup_kept_ratio"] is None
    assert row["cleanup_filters"] is None


def test_cli_writes_json_and_markdown(tmp_path):
    baseline = make_job(
        tmp_path,
        "baseline",
        frames=10,
        registered=8,
        splat_count=100,
        cleanup={
            "source_vertex_count": 100,
            "kept_vertex_count": 91,
            "removed_vertex_count": 9,
            "kept_ratio": 0.91,
            "filters": {"min_opacity": 0.18, "max_scale_used": 0.25},
        },
        quality_grade="A",
    )
    output = tmp_path / "evidence.json"
    markdown = tmp_path / "evidence.md"
    script = Path(__file__).resolve().parents[1] / "scripts" / "build_ab_evidence_report.py"

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--variant",
            f"baseline_30k={baseline}",
            "--output",
            str(output),
            "--markdown",
            str(markdown),
            "--viewer-base-url",
            "https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_splat.php",
        ],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    assert output.is_file()
    assert markdown.is_file()
    markdown_text = markdown.read_text()
    assert "## Conclusion" in markdown_text
    assert "Recommended Variant: baseline_30k" in markdown_text
    assert "Reason: baseline_30k has registered_ratio 0.80 and quality_grade A." in markdown_text
    assert "Known Issues:" in markdown_text
    assert "Next Action: Review clean viewer" in markdown_text
    assert "baseline_30k" in markdown_text
    assert "Cleanup kept" in markdown_text
    assert "Cleanup kept ratio" in markdown_text
    assert "| baseline_30k | 10 | 8 | 0.80 | 100 | 91 | 0.91 |" in markdown_text
    assert "Raw viewer: https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_splat.php?src=" in markdown_text
    assert "Clean viewer: https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_splat.php?src=" in markdown_text
    assert "splat.clean.ply" in markdown_text


def test_cli_writes_markdown_with_malformed_cleanup_metadata(tmp_path):
    malformed = make_job(
        tmp_path,
        "malformed",
        frames=10,
        registered=8,
        splat_count=100,
        cleanup={
            "source_vertex_count": "100",
            "kept_vertex_count": "oops",
            "removed_vertex_count": "bad",
            "kept_ratio": "bad",
            "filters": "not-a-dict",
        },
    )
    output = tmp_path / "evidence.json"
    markdown = tmp_path / "evidence.md"
    script = Path(__file__).resolve().parents[1] / "scripts" / "build_ab_evidence_report.py"

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--variant",
            f"malformed_30k={malformed}",
            "--output",
            str(output),
            "--markdown",
            str(markdown),
            "--viewer-base-url",
            "https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_splat.php",
        ],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_text())
    row = report["variants"][0]
    assert row["cleanup_kept_vertex_count"] is None
    assert row["cleanup_kept_ratio"] is None
    markdown_text = markdown.read_text()
    assert "malformed_30k" in markdown_text
    assert "Raw viewer:" in markdown_text
    assert "Clean viewer:" in markdown_text
