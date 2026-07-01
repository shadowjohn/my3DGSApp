#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path


VERSION = "1.0.3"
INPUTS = {
    "coverage_summary": Path("evidence/coverage_summary.json"),
    "geometry_summary": Path("evidence/geometry_summary.json"),
    "appearance_summary": Path("evidence/appearance_summary.json"),
    "engine_contract": Path("engine_contract.json"),
    "evidence_manifest": Path("evidence_manifest.json"),
}


class ValidationReportError(Exception):
    pass


def clamp_score(value: float) -> int:
    return max(0, min(100, int(round(value))))


def number(value) -> float:
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def avg(summary: dict, *keys: str) -> float:
    for key in keys:
        value = summary.get(key)
        if isinstance(value, dict):
            return number(value.get("avg"))
        if value is not None:
            return number(value)
    return 0.0


def score_capture(summary) -> int:
    if not isinstance(summary, dict):
        return 0
    track = avg(summary, "avg_track_length", "average_track_length", "track_length")
    reprojection = avg(summary, "avg_reprojection_error", "average_reprojection_error", "reprojection_error")
    cameras = number(summary.get("camera_count"))
    points = number(summary.get("sparse_point_count"))
    score = min(100, track / 3 * 60 + min(cameras, 20) / 20 * 20 + min(points, 1000) / 1000 * 20)
    return clamp_score(score - min(reprojection * 5, 30))


def score_geometry(summary) -> int:
    if not isinstance(summary, dict):
        return 0
    mesh = summary.get("mesh") if isinstance(summary.get("mesh"), dict) else {}
    dense = summary.get("dense_cloud") if isinstance(summary.get("dense_cloud"), dict) else {}
    texture = summary.get("texture") if isinstance(summary.get("texture"), dict) else {}
    score = 0
    if mesh.get("vertex_count") is not None or mesh.get("face_count") is not None:
        score += 40
    if mesh.get("bbox") or dense.get("bbox"):
        score += 20
    if dense.get("point_count") is not None:
        score += 20
    if texture.get("available") is True:
        score += 10
    if mesh.get("normal_available") is True:
        score += 10
    return clamp_score(score)


def score_appearance(summary) -> int:
    if not isinstance(summary, dict):
        return 0
    splat = summary.get("splat") if isinstance(summary.get("splat"), dict) else {}
    opacity = summary.get("opacity") if isinstance(summary.get("opacity"), dict) else {}
    scale = summary.get("scale") if isinstance(summary.get("scale"), dict) else {}
    render = summary.get("render_quality") if isinstance(summary.get("render_quality"), dict) else {}
    score = 0
    if splat.get("available") is True or number(splat.get("count")) > 0:
        score += 40
    if splat.get("bbox"):
        score += 20
    if opacity.get("available") is True:
        score += 15
    if scale.get("available") is True:
        score += 15
    if render.get("available") is True:
        score += 10
    return clamp_score(score)


def grade(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "B-"
    if score >= 60:
        return "C+"
    if score >= 50:
        return "C"
    return "D"


def engine_failed_decision(contract: dict) -> dict | None:
    if not isinstance(contract, dict) or contract.get("status") != "failed":
        return None
    errors = contract.get("errors")
    if not isinstance(errors, list):
        errors = []
    summary = "Engine failed."
    details = [str(item) for item in errors if str(item).strip()]
    if details:
        summary += " " + "; ".join(details[:3])
    return {"grade": "D", "status": "engine_failed", "root_cause": "engine", "summary": summary}


def decision(scores: dict, contract: dict | None = None) -> dict:
    failed = engine_failed_decision(contract or {})
    if failed:
        return failed
    capture_high = scores["capture"] >= 70
    geometry_high = scores["geometry"] >= 70
    appearance_high = scores["appearance"] >= 70
    if capture_high and geometry_high and appearance_high:
        status, root, summary = "deliverable", "unknown", "Good Dataset: capture, geometry, and appearance evidence are all high."
    elif not capture_high and not geometry_high and appearance_high:
        status, root, summary = "review_needed", "capture", "Mesh Risk / Possible 3DGS Overfit: appearance is strong but capture and mesh evidence are weak."
    elif capture_high and geometry_high and not appearance_high:
        status, root, summary = "review_needed", "texture", "Texture / Lighting / Appearance Issue: capture and geometry are high but appearance evidence is weak."
    elif not capture_high and not geometry_high and not appearance_high:
        status, root, summary = "recapture_recommended", "capture", "Capture Failure: capture, geometry, and appearance evidence are all weak."
    else:
        status, root, summary = "review_needed", "unknown", "Mixed validation signals; manual review recommended."
    return {"grade": grade(scores["cross_validation"]), "status": status, "root_cause": root, "summary": summary}


def report_text(scores: dict, result: dict) -> str:
    return (
        f"Decision: {result['status']} / {result['grade']} / root cause: {result['root_cause']}\n"
        f"Capture {scores['capture']} / Geometry {scores['geometry']} / Appearance {scores['appearance']} / Cross {scores['cross_validation']}\n"
        f"{result['summary']}"
    )


def load_json(path: Path):
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ValidationReportError(f"Malformed JSON in {path}: {exc.msg}") from exc
    except OSError as exc:
        raise ValidationReportError(f"Cannot read input {path}: {exc}") from exc


def build_validation_report(job_dir: Path, output: Path | None = None) -> Path:
    if not job_dir.is_dir():
        raise ValidationReportError(f"Job directory not found: {job_dir}")

    loaded = {}
    inputs = {}
    for name, relative in INPUTS.items():
        path = job_dir / relative
        if path.is_file():
            loaded[name] = load_json(path)
            inputs[name] = relative.as_posix()

    scores = {
        "capture": score_capture(loaded.get("coverage_summary")),
        "geometry": score_geometry(loaded.get("geometry_summary")),
        "appearance": score_appearance(loaded.get("appearance_summary")),
    }
    available = [
        scores["capture"] if "coverage_summary" in loaded else None,
        scores["geometry"] if "geometry_summary" in loaded else None,
        scores["appearance"] if "appearance_summary" in loaded else None,
    ]
    present_scores = [score for score in available if score is not None]
    scores["cross_validation"] = clamp_score(sum(present_scores) / len(present_scores)) if present_scores else 0

    result = decision(scores, loaded.get("engine_contract"))
    report = {
        "version": VERSION,
        "job_id": job_dir.name,
        "scores": scores,
        "decision": result,
        "report_text": report_text(scores, result),
        "evidence_regions": [],
        "inputs": inputs,
    }

    output_path = output or job_dir / "validation" / "validation_report.json"
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2) + "\n")
    except OSError as exc:
        raise ValidationReportError(f"Cannot write output {output_path}: {exc}") from exc
    return output_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a platform validation report from evidence summaries.")
    parser.add_argument("job_dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    try:
        output = build_validation_report(args.job_dir, args.output)
    except ValidationReportError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
