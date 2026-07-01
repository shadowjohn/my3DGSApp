#!/usr/bin/env python3
import argparse
import json
import math
from pathlib import Path
from typing import Any
from urllib.parse import quote


DEFAULT_VIEWER_BASE_URL = "https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_splat.php"
SCORECARD_COLUMNS = [
    "Variant",
    "Geometry",
    "Recognizability",
    "Floaters",
    "Registration",
    "Viewer Quality",
    "Overall",
    "Notes",
]


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text_if_missing(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(text, encoding="utf-8")


def resolve_under_project(path: Path, project_root: Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else project_root / path


def relative_path(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def viewer_url(path: Path, project_root: Path, viewer_base_url: str, meta: Path | None = None) -> str:
    url = viewer_base_url + "?src=" + quote(relative_path(path, project_root), safe="")
    if meta is not None:
        url += "&meta=" + quote(relative_path(meta, project_root), safe="")
    return url + "&rx=0&ry=0&rz=0&up=view"


def coerce_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if math.isfinite(value) and value.is_integer() else None
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def coerce_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        parsed = float(value)
    elif isinstance(value, str):
        try:
            parsed = float(value)
        except ValueError:
            return None
    else:
        return None
    return parsed if math.isfinite(parsed) else None


def splat_count_from_ply(ply_path: Path) -> int | None:
    if not ply_path.is_file():
        return None
    with ply_path.open("rb") as handle:
        for raw_line in handle:
            line = raw_line.decode("utf-8", errors="ignore").strip()
            if line.startswith("element vertex "):
                return coerce_int(line.split()[-1])
            if line == "end_header":
                return None
    return None


def stage_durations(timing: dict[str, Any]) -> dict[str, float]:
    stages = timing.get("stages", [])
    if not isinstance(stages, list):
        return {}
    durations: dict[str, float] = {}
    for stage in stages:
        if not isinstance(stage, dict):
            continue
        key = stage.get("key") or stage.get("name") or stage.get("stage")
        duration = coerce_float(stage.get("duration_seconds"))
        if key and duration is not None:
            durations[str(key)] = duration
    return durations


def cleanup_metrics(meta_path: Path) -> dict[str, Any]:
    cleanup = load_json(meta_path).get("cleanup", {})
    if not isinstance(cleanup, dict):
        cleanup = {}
    return {
        "cleanKeptCount": coerce_int(cleanup.get("kept_vertex_count")),
        "cleanKeptRatio": coerce_float(cleanup.get("kept_ratio")),
    }


def qa_warnings(qa: dict[str, Any]) -> list[Any]:
    warnings = qa.get("warnings", [])
    return warnings if isinstance(warnings, list) else []


def machine_metrics(job_dir: Path) -> dict[str, Any]:
    qa = load_json(job_dir / "qa_report.json")
    frame_report = load_json(job_dir / "frame_quality_report.json")
    timing = load_json(job_dir / "timing_report.json")
    cleanup = cleanup_metrics(job_dir / "exports" / "splat.clean.viewer.json")
    return {
        "frameCount": coerce_int(qa.get("frame_count")) or coerce_int(frame_report.get("frame_count")),
        "selectedFrameCount": coerce_int(frame_report.get("selected_frame_count")) or coerce_int(qa.get("selected_frame_count")),
        "registeredFrameCount": coerce_int(qa.get("registered_frame_count")),
        "registeredRatio": coerce_float(qa.get("registered_ratio")),
        "splatCount": splat_count_from_ply(job_dir / "exports" / "splat.ply"),
        "cleanKeptCount": cleanup["cleanKeptCount"],
        "cleanKeptRatio": cleanup["cleanKeptRatio"],
        "totalDurationSeconds": coerce_float(timing.get("duration_seconds")),
        "stageDurationsSeconds": stage_durations(timing),
        "qualityGrade": qa.get("quality_grade") if isinstance(qa.get("quality_grade"), str) else None,
        "warnings": qa_warnings(qa),
    }


def ensure_directories(output_dir: Path) -> None:
    for path in [
        output_dir,
        output_dir / "old",
        output_dir / "new-selected-30k" / "official-viewer" / "screenshots",
        output_dir / "new-selected-30k" / "custom-viewer" / "screenshots",
        output_dir / "references" / "external-demo" / "screenshots",
        output_dir / "screenshots" / "old",
        output_dir / "screenshots" / "new-raw",
        output_dir / "screenshots" / "new-clean",
        output_dir / "screenshots" / "official-viewer",
    ]:
        path.mkdir(parents=True, exist_ok=True)


def write_viewer_notes(output_dir: Path) -> None:
    write_text_if_missing(
        output_dir / "new-selected-30k" / "official-viewer" / "notes.md",
        "# Official Viewer Notes\n\n- Screenshot set:\n- Reconstruction quality observations:\n- Viewer-specific issues:\n",
    )
    write_text_if_missing(
        output_dir / "new-selected-30k" / "custom-viewer" / "notes.md",
        "# Custom Viewer Notes\n\n- Screenshot set:\n- Rendering quality observations:\n- Viewer-specific issues:\n",
    )
    write_text_if_missing(
        output_dir / "references" / "external-demo" / "notes.md",
        "# External Demo Reference Notes\n\n- Source:\n- Screenshot set:\n- Comparison notes:\n",
    )


def old_case(source_job: Path, project_root: Path, viewer_base_url: str) -> dict[str, Any]:
    raw = source_job / "exports" / "splat.ply"
    core = source_job / "exports" / "splat.core-20260605-1100.ply"
    core_meta = source_job / "exports" / "splat.core-20260605-1100.viewer.json"
    return {
        "jobDir": relative_path(source_job, project_root),
        "rawSplat": relative_path(raw, project_root),
        "coreSplat": relative_path(core, project_root),
        "qaReport": relative_path(source_job / "qa_report.json", project_root),
        "transform": relative_path(source_job / "transform.json", project_root),
        "viewerUrls": {
            "raw": viewer_url(raw, project_root, viewer_base_url),
            "core": viewer_url(core, project_root, viewer_base_url, core_meta),
        },
    }


def new_case(output_dir: Path, project_root: Path, new_job: Path | None, viewer_base_url: str) -> dict[str, Any]:
    job = new_job if new_job is not None else output_dir / "new-selected-30k"
    raw = job / "exports" / "splat.ply"
    clean = job / "exports" / "splat.clean.ply"
    clean_meta = job / "exports" / "splat.clean.viewer.json"
    return {
        "jobDir": relative_path(job, project_root),
        "rawSplat": relative_path(raw, project_root),
        "cleanSplat": relative_path(clean, project_root),
        "cleanViewerMeta": relative_path(clean_meta, project_root),
        "qaReport": relative_path(job / "qa_report.json", project_root),
        "frameReport": relative_path(job / "frame_quality_report.json", project_root),
        "timingReport": relative_path(job / "timing_report.json", project_root),
        "officialViewer": relative_path(output_dir / "new-selected-30k" / "official-viewer", project_root),
        "customViewer": relative_path(output_dir / "new-selected-30k" / "custom-viewer", project_root),
        "viewerUrls": {
            "raw": viewer_url(raw, project_root, viewer_base_url),
            "clean": viewer_url(clean, project_root, viewer_base_url, clean_meta),
        },
    }


def scorecard_markdown() -> str:
    header = "| " + " | ".join(SCORECARD_COLUMNS) + " |"
    divider = "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |"
    rows = [
        "| old_uploads_3_raw |  |  |  |  |  |  |  |",
        "| old_uploads_3_core |  |  |  |  |  |  |  |",
        "| new_selected_30k_raw |  |  |  |  |  |  |  |",
        "| new_selected_30k_clean |  |  |  |  |  |  |  |",
        "| official_viewer_new |  |  |  |  |  |  |  |",
        "| external_reference |  |  |  |  |  |  |  |",
    ]
    lines = [
        "# Golden Benchmark Scorecard",
        "",
        header,
        divider,
        *rows,
        "",
        "Recommended Variant:",
        "",
        "Reason:",
        "",
        "Known Issues:",
        "",
        "Next Action:",
        "",
    ]
    return "\n".join(lines)


def capture_diagnosis_markdown() -> str:
    return "\n".join(
        [
            "# Capture Diagnosis",
            "",
            "| Risk Area | Observation | Capture risk | Pipeline implication |",
            "| --- | --- | --- | --- |",
            "| reflective surfaces |  |  |  |",
            "| moving people/objects |  |  |  |",
            "| low texture |  |  |  |",
            "| camera path |  |  |  |",
            "| focus/exposure stability |  |  |  |",
            "",
            "Overall capture risk:",
            "",
        ]
    )


def metric_value(metrics: dict[str, Any], key: str) -> str:
    value = metrics.get(key)
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def warning_text(metrics: dict[str, Any]) -> str:
    warnings = metrics.get("warnings", [])
    if not isinstance(warnings, list) or not warnings:
        return ""
    return "; ".join(str(warning) for warning in warnings if warning)


def stage_duration_lines(case_name: str, metrics: dict[str, Any]) -> list[str]:
    durations = metrics.get("stageDurationsSeconds", {})
    if not isinstance(durations, dict) or not durations:
        return [f"| {case_name} | (none) |  |"]
    lines = []
    for stage, duration in durations.items():
        if isinstance(duration, (int, float)):
            lines.append(f"| {case_name} | {stage} | {float(duration):.2f} |")
    return lines or [f"| {case_name} | (none) |  |"]


def benchmark_markdown(report: dict[str, Any]) -> str:
    old = report["cases"]["old"]
    new = report["cases"]["newSelected30k"]
    old_metrics = report["machineMetrics"]["old"]
    new_metrics = report["machineMetrics"]["newSelected30k"]
    lines = [
        "# Golden Benchmark Pack",
        "",
        f"Benchmark ID: {report['benchmarkId']}",
        "",
        f"Source job: {report['sourceJob']}",
        "",
        f"portableMode: {str(report['artifactPolicy']['portableMode']).lower()}",
        "",
        "## Conclusion",
        "",
        "Recommended Variant:",
        "",
        "Reason:",
        "",
        "Known Issues:",
        "",
        "Next Action:",
        "",
        "Route Confidence:",
        "",
        "## Viewer Links",
        "",
        f"Old raw viewer: {old['viewerUrls']['raw']}",
        "",
        f"Old core viewer: {old['viewerUrls']['core']}",
        "",
        f"New raw viewer: {new['viewerUrls']['raw']}",
        "",
        f"New clean viewer: {new['viewerUrls']['clean']}",
        "",
        "## Scorecard Summary",
        "",
        "See `scorecard.md` for fixed human review columns.",
        "",
        "## Machine Metrics",
        "",
        "| Case | Frames | Selected | Registered | Registered ratio | Splats | Clean kept | Clean kept ratio | Duration seconds |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        "| old | {frames} | {selected} | {registered} | {ratio} | {splats} | {clean_kept} | {clean_ratio} | {duration} |".format(
            frames=metric_value(old_metrics, "frameCount"),
            selected=metric_value(old_metrics, "selectedFrameCount"),
            registered=metric_value(old_metrics, "registeredFrameCount"),
            ratio=metric_value(old_metrics, "registeredRatio"),
            splats=metric_value(old_metrics, "splatCount"),
            clean_kept=metric_value(old_metrics, "cleanKeptCount"),
            clean_ratio=metric_value(old_metrics, "cleanKeptRatio"),
            duration=metric_value(old_metrics, "totalDurationSeconds"),
        ),
        "| newSelected30k | {frames} | {selected} | {registered} | {ratio} | {splats} | {clean_kept} | {clean_ratio} | {duration} |".format(
            frames=metric_value(new_metrics, "frameCount"),
            selected=metric_value(new_metrics, "selectedFrameCount"),
            registered=metric_value(new_metrics, "registeredFrameCount"),
            ratio=metric_value(new_metrics, "registeredRatio"),
            splats=metric_value(new_metrics, "splatCount"),
            clean_kept=metric_value(new_metrics, "cleanKeptCount"),
            clean_ratio=metric_value(new_metrics, "cleanKeptRatio"),
            duration=metric_value(new_metrics, "totalDurationSeconds"),
        ),
        "",
        "## QA Summary",
        "",
        "| Case | Quality grade | Warnings |",
        "| --- | --- | --- |",
        f"| old | {metric_value(old_metrics, 'qualityGrade')} | {warning_text(old_metrics)} |",
        f"| newSelected30k | {metric_value(new_metrics, 'qualityGrade')} | {warning_text(new_metrics)} |",
        "",
        "## Stage Durations",
        "",
        "| Case | Stage | Duration seconds |",
        "| --- | --- | ---: |",
        *stage_duration_lines("old", old_metrics),
        *stage_duration_lines("newSelected30k", new_metrics),
        "",
    ]
    return "\n".join(lines)


def write_markdown_files(output_dir: Path, report: dict[str, Any]) -> None:
    generated = benchmark_markdown(report)
    (output_dir / "benchmark.generated.md").write_text(generated, encoding="utf-8")
    write_text_if_missing(output_dir / "scorecard.md", scorecard_markdown())
    write_text_if_missing(output_dir / "capture_diagnosis.md", capture_diagnosis_markdown())
    write_text_if_missing(output_dir / "benchmark.md", generated)


def build_benchmark_pack(
    benchmark_id: str,
    source_job: Path,
    output_dir: Path,
    project_root: Path,
    viewer_base_url: str = DEFAULT_VIEWER_BASE_URL,
    new_job: Path | None = None,
    portable_mode: bool = False,
) -> dict[str, Any]:
    project_root = Path(project_root).resolve()
    source_job = resolve_under_project(Path(source_job), project_root)
    output_dir = resolve_under_project(Path(output_dir), project_root)
    new_job = resolve_under_project(Path(new_job), project_root) if new_job is not None else None

    ensure_directories(output_dir)
    write_viewer_notes(output_dir)

    new_metrics_job = new_job if new_job is not None else output_dir / "new-selected-30k"
    report = {
        "benchmarkId": benchmark_id,
        "sourceJob": relative_path(source_job, project_root),
        "artifactPolicy": {"portableMode": portable_mode},
        "cases": {
            "old": old_case(source_job, project_root, viewer_base_url),
            "newSelected30k": new_case(output_dir, project_root, new_job, viewer_base_url),
            "reference": {
                "externalDemo": relative_path(output_dir / "references" / "external-demo", project_root)
            },
        },
        "machineMetrics": {
            "old": machine_metrics(source_job),
            "newSelected30k": machine_metrics(new_metrics_job),
        },
    }

    write_json(output_dir / "benchmark.json", report)
    write_markdown_files(output_dir, report)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a Gaussian Splat golden benchmark pack.")
    parser.add_argument("--benchmark-id", required=True)
    parser.add_argument("--source-job", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--viewer-base-url", default=DEFAULT_VIEWER_BASE_URL)
    parser.add_argument("--new-job", type=Path)
    parser.add_argument("--portable-mode", action="store_true", default=False)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = args.project_root.resolve()
    output_dir = resolve_under_project(args.output_dir, project_root)
    build_benchmark_pack(
        benchmark_id=args.benchmark_id,
        source_job=args.source_job,
        output_dir=output_dir,
        project_root=project_root,
        viewer_base_url=args.viewer_base_url,
        new_job=args.new_job,
        portable_mode=args.portable_mode,
    )
    print(output_dir / "benchmark.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
