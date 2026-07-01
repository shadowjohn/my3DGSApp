import json
import subprocess
import sys
from pathlib import Path

from scripts.build_golden_benchmark_pack import build_benchmark_pack


VIEWER_BASE_URL = "https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_splat.php"


def write_ply(path: Path, vertices: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "ply\n"
        "format binary_little_endian 1.0\n"
        f"element vertex {vertices}\n"
        "property float x\n"
        "end_header\n",
        encoding="utf-8",
    )


def make_old_job(tmp_path: Path) -> Path:
    job = tmp_path / "uploads" / "3"
    (job / "input").mkdir(parents=True)
    (job / "input" / "input.mp4").write_bytes(b"mp4")
    (job / "qa_report.json").write_text(
        json.dumps(
            {
                "job_id": "3",
                "frame_count": 32,
                "registered_frame_count": 25,
                "registered_ratio": 0.78,
                "warnings": ["registered_ratio lower than 0.8"],
            }
        ),
        encoding="utf-8",
    )
    (job / "transform.json").write_text(json.dumps({"job_id": "3"}), encoding="utf-8")
    write_ply(job / "exports" / "splat.ply", 1234)
    write_ply(job / "exports" / "splat.core-20260605-1100.ply", 1000)
    (job / "exports" / "splat.core-20260605-1100.viewer.json").write_text(
        json.dumps({"viewer": {"rx": 0, "ry": 0, "rz": 0, "upMode": "view"}}),
        encoding="utf-8",
    )
    return job


def make_new_job(tmp_path: Path) -> Path:
    job = tmp_path / "uploads" / "benchmark-uploads-3" / "new-selected-30k"
    (job / "exports").mkdir(parents=True)
    (job / "qa_report.json").write_text(
        json.dumps(
            {
                "frame_count": 60,
                "selected_frame_count": 42,
                "registered_frame_count": 38,
                "registered_ratio": 0.9,
                "quality_grade": "A",
                "warnings": [],
            }
        ),
        encoding="utf-8",
    )
    (job / "frame_quality_report.json").write_text(
        json.dumps({"frame_count": 60, "selected_frame_count": 42}),
        encoding="utf-8",
    )
    (job / "timing_report.json").write_text(
        json.dumps(
            {
                "duration_seconds": 456.7,
                "stages": [
                    {"key": "extract_frames", "duration_seconds": 12.3},
                    {"key": "train", "duration_seconds": 400.0},
                ],
            }
        ),
        encoding="utf-8",
    )
    write_ply(job / "exports" / "splat.ply", 3000)
    write_ply(job / "exports" / "splat.clean.ply", 2400)
    (job / "exports" / "splat.clean.viewer.json").write_text(
        json.dumps(
            {
                "cleanup": {
                    "source_vertex_count": 3000,
                    "kept_vertex_count": 2400,
                    "removed_vertex_count": 600,
                    "kept_ratio": 0.8,
                }
            }
        ),
        encoding="utf-8",
    )
    return job


def test_build_benchmark_pack_writes_artifact_mapping_and_viewer_folders(tmp_path):
    old_job = make_old_job(tmp_path)
    output_dir = tmp_path / "uploads" / "benchmark-uploads-3"

    report = build_benchmark_pack(
        benchmark_id="benchmark-uploads-3",
        source_job=old_job,
        output_dir=output_dir,
        project_root=tmp_path,
        viewer_base_url=VIEWER_BASE_URL,
        new_job=None,
        portable_mode=False,
    )

    assert report["benchmarkId"] == "benchmark-uploads-3"
    assert report["sourceJob"].endswith("uploads/3")
    assert report["artifactPolicy"] == {"portableMode": False}
    assert report["cases"]["old"]["rawSplat"].endswith("uploads/3/exports/splat.ply")
    assert report["cases"]["old"]["coreSplat"].endswith("uploads/3/exports/splat.core-20260605-1100.ply")
    assert report["cases"]["old"]["qaReport"].endswith("uploads/3/qa_report.json")
    assert report["cases"]["old"]["transform"].endswith("uploads/3/transform.json")
    assert set(report["cases"]["old"]["viewerUrls"]) == {"raw", "core"}
    assert report["cases"]["reference"]["externalDemo"].endswith("references/external-demo")
    assert (output_dir / "benchmark.json").is_file()
    assert (output_dir / "benchmark.md").is_file()
    assert (output_dir / "scorecard.md").is_file()
    assert (output_dir / "capture_diagnosis.md").is_file()
    assert (output_dir / "new-selected-30k" / "official-viewer" / "screenshots").is_dir()
    assert (output_dir / "new-selected-30k" / "official-viewer" / "notes.md").is_file()
    assert (output_dir / "new-selected-30k" / "custom-viewer" / "screenshots").is_dir()
    assert (output_dir / "new-selected-30k" / "custom-viewer" / "notes.md").is_file()
    assert (output_dir / "references" / "external-demo" / "screenshots").is_dir()


def test_markdown_templates_include_scorecard_diagnosis_and_summary(tmp_path):
    old_job = make_old_job(tmp_path)
    output_dir = tmp_path / "uploads" / "benchmark-uploads-3"

    build_benchmark_pack(
        benchmark_id="benchmark-uploads-3",
        source_job=old_job,
        output_dir=output_dir,
        project_root=tmp_path,
        viewer_base_url=VIEWER_BASE_URL,
    )

    scorecard = (output_dir / "scorecard.md").read_text(encoding="utf-8")
    assert "| Variant | Geometry | Recognizability | Floaters | Registration | Viewer Quality | Overall | Notes |" in scorecard
    assert "Recommended Variant:" in scorecard
    assert "Next Action:" in scorecard

    diagnosis = (output_dir / "capture_diagnosis.md").read_text(encoding="utf-8")
    for phrase in [
        "reflective surfaces",
        "moving people/objects",
        "low texture",
        "camera path",
        "focus/exposure stability",
        "capture risk",
    ]:
        assert phrase in diagnosis

    benchmark = (output_dir / "benchmark.md").read_text(encoding="utf-8")
    assert "## Conclusion" in benchmark
    assert "Recommended Variant:" in benchmark
    assert "Known Issues:" in benchmark
    assert "portableMode: false" in benchmark
    assert "Old raw viewer:" in benchmark
    assert "Old core viewer:" in benchmark
    assert "New raw viewer:" in benchmark
    assert "New clean viewer:" in benchmark
    assert "## Scorecard Summary" in benchmark
    assert "Route Confidence:" in benchmark


def test_new_selected_30k_mapping_and_machine_metrics(tmp_path):
    old_job = make_old_job(tmp_path)
    new_job = make_new_job(tmp_path)
    output_dir = tmp_path / "uploads" / "benchmark-uploads-3"

    report = build_benchmark_pack(
        benchmark_id="benchmark-uploads-3",
        source_job=old_job,
        output_dir=output_dir,
        project_root=tmp_path,
        viewer_base_url=VIEWER_BASE_URL,
        new_job=new_job,
    )

    new_case = report["cases"]["newSelected30k"]
    assert new_case["rawSplat"].endswith("new-selected-30k/exports/splat.ply")
    assert new_case["cleanSplat"].endswith("new-selected-30k/exports/splat.clean.ply")
    assert new_case["cleanViewerMeta"].endswith("new-selected-30k/exports/splat.clean.viewer.json")
    assert new_case["qaReport"].endswith("new-selected-30k/qa_report.json")
    assert new_case["frameReport"].endswith("new-selected-30k/frame_quality_report.json")
    assert new_case["timingReport"].endswith("new-selected-30k/timing_report.json")
    assert new_case["officialViewer"].endswith("new-selected-30k/official-viewer")
    assert new_case["customViewer"].endswith("new-selected-30k/custom-viewer")
    assert set(new_case["viewerUrls"]) == {"raw", "clean"}

    metrics = report["machineMetrics"]["newSelected30k"]
    assert metrics["frameCount"] == 60
    assert metrics["selectedFrameCount"] == 42
    assert metrics["registeredFrameCount"] == 38
    assert metrics["registeredRatio"] == 0.9
    assert metrics["splatCount"] == 3000
    assert metrics["cleanKeptCount"] == 2400
    assert metrics["cleanKeptRatio"] == 0.8
    assert metrics["totalDurationSeconds"] == 456.7
    assert metrics["stageDurationsSeconds"] == {"extract_frames": 12.3, "train": 400.0}
    assert metrics["qualityGrade"] == "A"
    assert metrics["warnings"] == []

    old_metrics = report["machineMetrics"]["old"]
    assert old_metrics["warnings"] == ["registered_ratio lower than 0.8"]

    generated = (output_dir / "benchmark.generated.md").read_text(encoding="utf-8")
    assert "A" in generated
    assert "registered_ratio lower than 0.8" in generated
    assert "extract_frames" in generated
    assert "train" in generated
    assert "12.30" in generated
    assert "400.00" in generated


def test_machine_metrics_uses_empty_warnings_for_malformed_value(tmp_path):
    old_job = make_old_job(tmp_path)
    (old_job / "qa_report.json").write_text(
        json.dumps(
            {
                "frame_count": 32,
                "registered_frame_count": 25,
                "registered_ratio": 0.78,
                "warnings": "not-a-list",
            }
        ),
        encoding="utf-8",
    )
    output_dir = tmp_path / "uploads" / "benchmark-uploads-3"

    report = build_benchmark_pack(
        benchmark_id="benchmark-uploads-3",
        source_job=old_job,
        output_dir=output_dir,
        project_root=tmp_path,
        viewer_base_url=VIEWER_BASE_URL,
    )

    assert report["machineMetrics"]["old"]["warnings"] == []


def test_rebuild_preserves_manual_review_files(tmp_path):
    old_job = make_old_job(tmp_path)
    output_dir = tmp_path / "uploads" / "benchmark-uploads-3"

    build_benchmark_pack(
        benchmark_id="benchmark-uploads-3",
        source_job=old_job,
        output_dir=output_dir,
        project_root=tmp_path,
        viewer_base_url=VIEWER_BASE_URL,
    )
    (output_dir / "scorecard.md").write_text("manual scorecard: keep this\n", encoding="utf-8")
    (output_dir / "capture_diagnosis.md").write_text("manual diagnosis: keep this\n", encoding="utf-8")
    (output_dir / "benchmark.md").write_text("manual benchmark note: keep this\n", encoding="utf-8")

    build_benchmark_pack(
        benchmark_id="benchmark-uploads-3",
        source_job=old_job,
        output_dir=output_dir,
        project_root=tmp_path,
        viewer_base_url=VIEWER_BASE_URL,
    )

    assert (output_dir / "scorecard.md").read_text(encoding="utf-8") == "manual scorecard: keep this\n"
    assert (output_dir / "capture_diagnosis.md").read_text(encoding="utf-8") == "manual diagnosis: keep this\n"
    assert (output_dir / "benchmark.md").read_text(encoding="utf-8") == "manual benchmark note: keep this\n"
    assert "Route Confidence:" in (output_dir / "benchmark.generated.md").read_text(encoding="utf-8")


def test_cli_writes_benchmark_json_and_prints_path(tmp_path):
    old_job = make_old_job(tmp_path)
    new_job = make_new_job(tmp_path)
    output_dir = tmp_path / "uploads" / "benchmark-uploads-3"
    script = Path(__file__).resolve().parents[1] / "scripts" / "build_golden_benchmark_pack.py"

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--benchmark-id",
            "benchmark-uploads-3",
            "--source-job",
            str(old_job),
            "--output-dir",
            str(output_dir),
            "--project-root",
            str(tmp_path),
            "--viewer-base-url",
            VIEWER_BASE_URL,
            "--new-job",
            str(new_job),
            "--portable-mode",
        ],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    benchmark_json = output_dir / "benchmark.json"
    assert result.stdout.strip() == str(benchmark_json)
    report = json.loads(benchmark_json.read_text(encoding="utf-8"))
    assert report["artifactPolicy"] == {"portableMode": True}
    assert report["cases"]["newSelected30k"]["jobDir"].endswith("new-selected-30k")


def test_cli_resolves_relative_paths_against_project_root_from_different_cwd(tmp_path):
    project_root = tmp_path / "project"
    other_cwd = tmp_path / "other"
    other_cwd.mkdir()
    old_job = make_old_job(project_root)
    make_new_job(project_root)
    output_dir = project_root / "uploads" / "benchmark-uploads-3"
    script = Path(__file__).resolve().parents[1] / "scripts" / "build_golden_benchmark_pack.py"

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--benchmark-id",
            "benchmark-uploads-3",
            "--source-job",
            "uploads/3",
            "--output-dir",
            "uploads/benchmark-uploads-3",
            "--project-root",
            str(project_root),
            "--viewer-base-url",
            VIEWER_BASE_URL,
            "--new-job",
            "uploads/benchmark-uploads-3/new-selected-30k",
        ],
        cwd=other_cwd,
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    assert (output_dir / "benchmark.json").is_file()
    assert not (other_cwd / "uploads" / "benchmark-uploads-3" / "benchmark.json").exists()
    assert result.stdout.strip() == str(output_dir / "benchmark.json")
    report = json.loads((output_dir / "benchmark.json").read_text(encoding="utf-8"))
    assert report["sourceJob"] == "uploads/3"
    assert old_job.is_dir()
