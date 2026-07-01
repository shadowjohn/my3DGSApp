#!/usr/bin/env python3
import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.build_qa_report import splat_count_from_ply


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def delivery_grade(registered_ratio: float, trench_splat_count: int) -> str:
    if trench_splat_count <= 0 or registered_ratio < 0.3:
        return "D"
    if registered_ratio >= 0.9:
        return "A"
    if registered_ratio >= 0.8:
        return "B"
    if registered_ratio >= 0.5:
        return "C"
    return "D"


def decision_for_grade(grade: str, registered_ratio: float) -> str:
    if grade in {"A", "B"}:
        return "deliverable"
    if grade == "C" and registered_ratio >= 0.5:
        return "supplemental_capture_needed"
    if grade == "C":
        return "review_needed"
    return "retake"


def _number(data: dict[str, Any], key: str, default: float = 0.0) -> float:
    value = data.get(key, default)
    if value is None:
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _int_value(data: dict[str, Any], key: str, default: int = 0) -> int:
    value = data.get(key, default)
    if value is None:
        return default
    try:
        number = float(value)
        if not math.isfinite(number):
            return default
        return int(number)
    except (TypeError, ValueError, OverflowError):
        return default


def _delivery_mode(trench_meta: dict[str, Any]) -> str:
    delivery = trench_meta.get("delivery", {})
    if not isinstance(delivery, dict):
        return "gaussian_splat"
    mode = delivery.get("deliveryMode")
    return str(mode) if mode else "gaussian_splat"


def _warnings(*sources: Any) -> list[str]:
    warnings: set[str] = set()
    for source in sources:
        if isinstance(source, list):
            warnings.update(str(item) for item in source)
    return sorted(warnings)


def build_trench_qa_report(job_dir: Path | str) -> dict[str, Any]:
    job_dir = Path(job_dir)
    qa = load_json(job_dir / "qa_report.json")
    coverage = load_json(job_dir / "trench_coverage_report.json")
    georef = load_json(job_dir / "georef.json")
    trench_meta = load_json(job_dir / "exports" / "splat.trench.viewer.json")

    registered_ratio = _number(
        coverage,
        "registered_ratio",
        _number(qa, "registered_ratio"),
    )
    splat_count = _int_value(qa, "splat_count")
    trench_splat_count = splat_count_from_ply(job_dir / "exports" / "splat.trench.ply")
    grade = delivery_grade(registered_ratio, trench_splat_count)

    return {
        "input_mode": coverage.get("input_mode", "walk_video"),
        "frame_count": _int_value(qa, "frame_count"),
        "selected_count": _int_value(coverage, "selected_count", _int_value(qa, "frame_count")),
        "registered_count": _int_value(coverage, "registered_count", _int_value(qa, "registered_count")),
        "registered_ratio": registered_ratio,
        "splat_count": splat_count,
        "trench_splat_count": trench_splat_count,
        "trench_kept_ratio": round(trench_splat_count / splat_count, 2)
        if splat_count
        else 0.0,
        "surface_readability": "good"
        if grade in {"A", "B"}
        else "fair"
        if grade == "C"
        else "poor",
        "texture_realism": "good"
        if grade in {"A", "B"}
        else "fair"
        if grade == "C"
        else "poor",
        "background_artifact_score": 3
        if grade in {"A", "B"}
        else 2
        if grade == "C"
        else 1,
        "georef_confidence": georef.get("confidence", "none"),
        "delivery_grade": grade,
        "decision": decision_for_grade(grade, registered_ratio),
        "delivery_mode": _delivery_mode(trench_meta),
        "warnings": _warnings(qa.get("warnings", []), coverage.get("warnings", [])),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build engineering trench QA report.")
    parser.add_argument("job_dir", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = args.output or args.job_dir / "trench_qa_report.json"
    report = build_trench_qa_report(args.job_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
