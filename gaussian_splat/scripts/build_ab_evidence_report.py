#!/usr/bin/env python3
import argparse
import json
import math
from pathlib import Path
from typing import Any
from urllib.parse import quote


DEFAULT_VIEWER_BASE_URL = "https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_splat.php"
PSNR_STATUS = "not_computed_requires_rendered_eval_images"


def count_images(images_dir: Path) -> int:
    if not images_dir.is_dir():
        return 0
    suffixes = {".jpg", ".jpeg", ".png"}
    return sum(1 for path in images_dir.iterdir() if path.is_file() and path.suffix.lower() in suffixes)


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def registered_frames(transforms_json: Path) -> int:
    data = load_json(transforms_json)
    frames = data.get("frames", [])
    return len(frames) if isinstance(frames, list) else 0


def splat_count_from_ply(ply_path: Path) -> int | None:
    if not ply_path.is_file():
        return None
    with ply_path.open("rb") as handle:
        for raw_line in handle:
            line = raw_line.decode("utf-8", errors="ignore").strip()
            if line.startswith("element vertex "):
                try:
                    return int(line.split()[-1])
                except ValueError:
                    return None
            if line == "end_header":
                return None
    return None


def latest_config(job_dir: Path) -> Path | None:
    outputs_dir = job_dir / "outputs"
    if not outputs_dir.is_dir():
        return None
    configs = [path for path in outputs_dir.rglob("config.yml") if path.is_file()]
    if not configs:
        return None
    return max(configs, key=lambda path: path.stat().st_mtime)


def relative_url_path(path: Path, project_root: Path) -> str:
    try:
        relative = path.resolve().relative_to(project_root.resolve())
    except ValueError:
        relative = path.resolve()
    return quote(relative.as_posix(), safe="/")


def cleanup_stats(metadata_path: Path) -> dict[str, Any]:
    data = load_json(metadata_path)
    cleanup = data.get("cleanup", {})
    return cleanup if isinstance(cleanup, dict) else {}


def coerce_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if math.isfinite(value) and value.is_integer() else None
    if isinstance(value, str):
        try:
            parsed = int(value)
        except ValueError:
            return None
        return parsed
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


def clean_output_metadata(clean_splat_path: Path, clean_metadata_path: Path) -> dict[str, Any]:
    empty = {
        "source_vertex_count": None,
        "kept_vertex_count": None,
        "removed_vertex_count": None,
        "kept_ratio": None,
        "filters": None,
    }
    if not clean_splat_path.is_file():
        return empty

    cleanup = cleanup_stats(clean_metadata_path)
    return {
        "source_vertex_count": coerce_int(cleanup.get("source_vertex_count")),
        "kept_vertex_count": coerce_int(cleanup.get("kept_vertex_count")),
        "removed_vertex_count": coerce_int(cleanup.get("removed_vertex_count")),
        "kept_ratio": coerce_float(cleanup.get("kept_ratio")),
        "filters": cleanup.get("filters") if isinstance(cleanup.get("filters"), dict) else None,
    }


def variant_record(
    variant: str,
    job_dir: Path,
    viewer_base_url: str,
    project_root: Path,
) -> dict[str, Any]:
    images_dir = job_dir / "images"
    processed_dir = job_dir / "processed"
    exports_dir = job_dir / "exports"
    splat_path = exports_dir / "splat.ply"
    clean_splat_path = exports_dir / "splat.clean.ply"
    clean_metadata_path = exports_dir / "splat.clean.viewer.json"
    frame_count = count_images(images_dir)
    registered_count = registered_frames(processed_dir / "transforms.json")
    ratio = round(registered_count / frame_count, 2) if frame_count else 0.0
    splat_size_mb = round(splat_path.stat().st_size / 1024 / 1024, 2) if splat_path.is_file() else 0.0
    timing = load_json(job_dir / "timing_report.json")
    qa = load_json(job_dir / "qa_report.json")
    cleanup = clean_output_metadata(clean_splat_path, clean_metadata_path)
    config_path = latest_config(job_dir)
    if config_path is None:
        official_viewer_command = f"ns-viewer --load-config {job_dir / 'outputs' / '*' / 'splatfacto' / '*' / 'config.yml'} # config.yml not found"
    else:
        official_viewer_command = f"ns-viewer --load-config {config_path}"
    clean_web_viewer_url = None
    if clean_splat_path.is_file():
        clean_web_viewer_url = viewer_base_url + "?src=" + relative_url_path(clean_splat_path, project_root)

    return {
        "variant": variant,
        "job_dir": str(job_dir),
        "frame_count": frame_count,
        "registered_count": registered_count,
        "registered_ratio": ratio,
        "splat_count": splat_count_from_ply(splat_path),
        "cleanup_source_vertex_count": cleanup["source_vertex_count"],
        "cleanup_kept_vertex_count": cleanup["kept_vertex_count"],
        "cleanup_removed_vertex_count": cleanup["removed_vertex_count"],
        "cleanup_kept_ratio": cleanup["kept_ratio"],
        "cleanup_filters": cleanup["filters"],
        "clean_splat_path": str(clean_splat_path) if clean_splat_path.is_file() else None,
        "splat_file_size_mb": splat_size_mb,
        "duration_seconds": timing.get("duration_seconds"),
        "quality_grade": qa.get("quality_grade"),
        "warnings": qa.get("warnings", []) if isinstance(qa.get("warnings", []), list) else [],
        "psnr": None,
        "psnr_status": PSNR_STATUS,
        "official_viewer_command": official_viewer_command,
        "web_viewer_url": viewer_base_url + "?src=" + relative_url_path(splat_path, project_root),
        "clean_web_viewer_url": clean_web_viewer_url,
    }


def quality_rank(value: Any) -> int:
    ranks = {"A": 4, "B": 3, "C": 2, "D": 1}
    return ranks.get(str(value).upper(), 0)


def build_conclusion(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "recommended_variant": None,
            "reason": "No variants were provided.",
            "known_issues": ["No evidence rows available."],
            "next_action": "Run at least one Gaussian Splat pipeline variant.",
        }

    recommended = max(
        rows,
        key=lambda row: (
            row["registered_ratio"],
            quality_rank(row["quality_grade"]),
            row["cleanup_kept_vertex_count"] or 0,
        ),
    )
    variant = recommended["variant"]
    ratio = recommended["registered_ratio"]
    grade = recommended["quality_grade"] or "unknown"
    known_issues: list[str] = []
    if ratio < 0.8:
        known_issues.append(f"registered_ratio is {ratio:.2f}, below the customer-demo target 0.80.")
    if recommended["clean_splat_path"] is None:
        known_issues.append("Clean splat output is missing.")
    warnings = recommended.get("warnings", [])
    if isinstance(warnings, list):
        known_issues.extend(str(warning) for warning in warnings if warning)
    known_issues.append("PSNR is not computed until rendered eval images are available.")

    if ratio < 0.5:
        next_action = "Retake footage before tuning viewer or cleanup."
    elif ratio < 0.8:
        next_action = "Use only for internal review; tune frame selector and COLMAP coverage before customer demo."
    elif recommended["clean_splat_path"] is None:
        next_action = "Run splat cleanup and review official viewer before customer demo."
    else:
        next_action = "Review clean viewer; if artifacts remain, tune cleanup clustering before Real-ESRGAN."

    return {
        "recommended_variant": variant,
        "reason": f"{variant} has registered_ratio {ratio:.2f} and quality_grade {grade}.",
        "known_issues": known_issues,
        "next_action": next_action,
    }


def build_evidence_report(
    variants: list[tuple[str, Path]],
    viewer_base_url: str,
    project_root: Path,
) -> dict[str, Any]:
    rows = [
        variant_record(name, Path(job_dir), viewer_base_url, project_root)
        for name, job_dir in variants
    ]
    best_ratio = max((row["registered_ratio"] for row in rows), default=0.0)
    return {
        "summary": {
            "variant_count": len(rows),
            "best_registered_ratio": best_ratio,
            "psnr_status": PSNR_STATUS,
        },
        "conclusion": build_conclusion(rows),
        "variants": rows,
    }


def parse_variant(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("--variant must be in name=job_dir format")
    name, job_dir = value.split("=", 1)
    if not name or not job_dir:
        raise argparse.ArgumentTypeError("--variant must include both name and job_dir")
    return name, Path(job_dir)


def write_markdown(report: dict[str, Any], output: Path) -> None:
    conclusion = report.get("conclusion", {})
    known_issues = conclusion.get("known_issues", [])
    if isinstance(known_issues, list) and known_issues:
        known_issues_text = "; ".join(str(issue) for issue in known_issues)
    else:
        known_issues_text = "None"
    lines = [
        "# Gaussian Splat A/B Evidence Report",
        "",
        "## Conclusion",
        "",
        f"Recommended Variant: {conclusion.get('recommended_variant') or 'None'}",
        "",
        f"Reason: {conclusion.get('reason') or ''}",
        "",
        f"Known Issues: {known_issues_text}",
        "",
        f"Next Action: {conclusion.get('next_action') or ''}",
        "",
        "## Scorecard",
        "",
        "| Variant | Frames | Registered | Registered ratio | Splats | Cleanup kept | Cleanup kept ratio | Splat MB | Duration seconds | Grade | PSNR status |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for row in report["variants"]:
        lines.append(
            "| {variant} | {frame_count} | {registered_count} | {registered_ratio:.2f} | {splats} | {cleanup_kept} | {cleanup_ratio} | {splat_file_size_mb:.2f} | {duration} | {grade} | {psnr_status} |".format(
                variant=row["variant"],
                frame_count=row["frame_count"],
                registered_count=row["registered_count"],
                registered_ratio=row["registered_ratio"],
                splats=row["splat_count"] if row["splat_count"] is not None else "",
                cleanup_kept=row["cleanup_kept_vertex_count"] if row["cleanup_kept_vertex_count"] is not None else "",
                cleanup_ratio=f"{row['cleanup_kept_ratio']:.2f}" if row["cleanup_kept_ratio"] is not None else "",
                splat_file_size_mb=row["splat_file_size_mb"],
                duration=row["duration_seconds"] if row["duration_seconds"] is not None else "",
                grade=row["quality_grade"] if row["quality_grade"] is not None else "",
                psnr_status=row["psnr_status"],
            )
        )
    lines.extend(["", "## Viewer Commands", ""])
    for row in report["variants"]:
        lines.extend(
            [
                f"### {row['variant']}",
                "",
                "```bash",
                row["official_viewer_command"],
                "```",
                "",
                f"Raw viewer: {row['web_viewer_url']}",
                "",
            ]
        )
        if row["clean_web_viewer_url"] is not None:
            lines.extend(
                [
                    f"Clean viewer: {row['clean_web_viewer_url']}",
                    "",
                ]
            )
    output.write_text("\n".join(lines).rstrip() + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Gaussian Splat A/B evidence report.")
    parser.add_argument("--variant", action="append", type=parse_variant, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--viewer-base-url", default=DEFAULT_VIEWER_BASE_URL)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_evidence_report(args.variant, args.viewer_base_url, args.project_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    if args.markdown is not None:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        write_markdown(report, args.markdown)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
