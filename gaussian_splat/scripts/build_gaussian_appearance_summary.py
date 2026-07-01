#!/usr/bin/env python3
import argparse
import json
import math
import sys
from pathlib import Path
from statistics import median
import struct
from typing import Any


VERSION = "1.0.3"
SPLAT_CANDIDATES = (
    "exports/splat.clean.ply",
    "exports/splat.trench.ply",
    "exports/splat.ply",
    "splat.ply",
)


class GaussianAppearanceError(Exception):
    pass


def rel(path: Path | None, base: Path) -> str | None:
    if path is None:
        return None
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def clean_number(value: float) -> int | float:
    return int(value) if value.is_integer() else value


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def write_json(path: Path, data: dict[str, Any]) -> None:
    try:
        path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
    except OSError as exc:
        raise GaussianAppearanceError(f"Cannot write output JSON: {path}") from exc


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


def coerce_int(value: Any) -> int | None:
    number = coerce_float(value)
    if number is None or not number.is_integer():
        return None
    return int(number)


def first_not_none(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def first_file(job_dir: Path, names: tuple[str, ...]) -> Path | None:
    for name in names:
        path = job_dir / name
        if path.is_file():
            return path
    return None


def summary(values: list[float]) -> dict[str, bool | int | float | None]:
    if not values:
        return {"available": False, "min": None, "max": None, "avg": None}
    return {
        "available": True,
        "min": clean_number(min(values)),
        "max": clean_number(max(values)),
        "avg": clean_number(sum(values) / len(values)),
    }


def ratio(count: int, total: int) -> float | None:
    return round(count / total, 6) if total > 0 else None


def validation_summary(
    opacities: list[float],
    scales: list[float],
    colors: list[tuple[float, float, float]],
    bbox_outliers: int,
    total: int,
) -> dict[str, Any]:
    transparent_ratio = ratio(sum(value < 0.05 for value in opacities), len(opacities))
    black_ratio = ratio(sum(max(rgb) < 0.08 for rgb in colors), len(colors))
    scale_outlier_ratio = None
    if scales:
        base = median(scales)
        scale_outlier_ratio = ratio(sum(value > base * 10 for value in scales), len(scales)) if base > 0 else 0.0
    bbox_outlier_ratio = ratio(bbox_outliers, total)
    risk = "unknown"
    # ponytail: no camera coverage here; upgrade with COLMAP evidence before strong floater claims.
    if scale_outlier_ratio is not None or bbox_outlier_ratio is not None:
        risk = "medium" if (scale_outlier_ratio or 0) > 0.05 or (bbox_outlier_ratio or 0) > 0.01 else "low"
    return {
        "black_ratio": black_ratio,
        "transparent_ratio": transparent_ratio,
        "scale_outlier_ratio": scale_outlier_ratio,
        "bbox_outlier_ratio": bbox_outlier_ratio,
        "floating_artifact_risk": risk,
    }


def read_ply_header(ply, path: Path) -> list[str]:
    header: list[str] = []
    for raw_line in ply:
        try:
            line = raw_line.decode("ascii").strip()
        except UnicodeDecodeError as exc:
            raise GaussianAppearanceError(f"Malformed PLY header in {path}") from exc
        header.append(line)
        if line == "end_header":
            break
    else:
        raise GaussianAppearanceError(f"Malformed PLY file missing end_header: {path}")
    if not header or header[0] != "ply":
        raise GaussianAppearanceError(f"Malformed PLY file missing magic header: {path}")
    return header


def parse_ply_header(header: list[str], path: Path) -> dict[str, Any]:
    ply_format = None
    vertex_count = None
    element = None
    vertex_props: list[str] = []
    vertex_types: list[str] = []
    for line in header[1:]:
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "format" and len(parts) >= 2:
            ply_format = parts[1]
        elif parts[0] == "element" and len(parts) >= 3:
            element = parts[1]
            if element == "vertex":
                try:
                    vertex_count = int(parts[2])
                except ValueError as exc:
                    raise GaussianAppearanceError(f"Malformed PLY element count in {path}") from exc
        elif parts[0] == "property" and element == "vertex" and len(parts) >= 3:
            vertex_props.append(parts[-1])
            vertex_types.append(parts[-2])

    if vertex_count is None or ply_format is None:
        raise GaussianAppearanceError(f"Malformed PLY header in {path}")
    if ply_format not in {"ascii", "binary_little_endian"}:
        raise GaussianAppearanceError(f"Unsupported PLY format {ply_format} in {path}")
    return {"format": ply_format, "vertex_count": vertex_count, "vertex_props": vertex_props, "vertex_types": vertex_types}


def parse_ply_float(value: str, path: Path) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise GaussianAppearanceError(f"Malformed PLY vertex value in {path}") from exc
    if not math.isfinite(parsed):
        raise GaussianAppearanceError(f"Malformed PLY vertex value in {path}")
    return parsed


def sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1 / (1 + z)
    z = math.exp(value)
    return z / (1 + z)


def ascii_stats(ply, path: Path, vertex_count: int, props: list[str]) -> dict[str, Any]:
    xyz = [props.index(prop) for prop in ("x", "y", "z")] if all(prop in props for prop in ("x", "y", "z")) else None
    opacity_index = props.index("opacity") if "opacity" in props else None
    scale_indexes = [props.index(prop) for prop in ("scale_0", "scale_1", "scale_2") if prop in props]
    color_indexes = [props.index(prop) for prop in ("f_dc_0", "f_dc_1", "f_dc_2") if prop in props]
    mins: list[float] | None = None
    maxs: list[float] | None = None
    opacities: list[float] = []
    scales: list[float] = []
    colors: list[tuple[float, float, float]] = []
    bbox_outliers = 0

    for _ in range(vertex_count):
        raw_line = ply.readline()
        if not raw_line:
            raise GaussianAppearanceError(f"Malformed PLY vertex rows in {path}")
        try:
            parts = raw_line.decode("ascii").split()
        except UnicodeDecodeError as exc:
            raise GaussianAppearanceError(f"Malformed PLY vertex row encoding in {path}") from exc
        needed = max([*(xyz or []), opacity_index or 0, *(scale_indexes or [0])])
        if len(parts) <= needed:
            raise GaussianAppearanceError(f"Malformed PLY vertex row in {path}")
        if xyz:
            point = [parse_ply_float(parts[index], path) for index in xyz]
            mins = point if mins is None else [min(a, b) for a, b in zip(mins, point)]
            maxs = point if maxs is None else [max(a, b) for a, b in zip(maxs, point)]
            if any(abs(value) > 1_000_000 for value in point):
                bbox_outliers += 1
        if opacity_index is not None:
            opacities.append(sigmoid(parse_ply_float(parts[opacity_index], path)))
        if len(scale_indexes) == 3:
            try:
                scales.append(math.exp(max(parse_ply_float(parts[index], path) for index in scale_indexes)))
            except OverflowError as exc:
                raise GaussianAppearanceError(f"Malformed PLY vertex value in {path}") from exc
        if len(color_indexes) == 3:
            colors.append(tuple(max(0.0, min(1.0, 0.5 + 0.28209479177387814 * parse_ply_float(parts[index], path))) for index in color_indexes))

    bbox = None
    if mins is not None and maxs is not None:
        bbox = {
            "min": [clean_number(value) for value in mins],
            "max": [clean_number(value) for value in maxs],
        }
    return {
        "bbox": bbox,
        "opacity": summary(opacities),
        "scale": summary(scales),
        "validation": validation_summary(opacities, scales, colors, bbox_outliers, vertex_count),
    }


PLY_FORMATS = {
    "char": "b",
    "int8": "b",
    "uchar": "B",
    "uint8": "B",
    "short": "h",
    "int16": "h",
    "ushort": "H",
    "uint16": "H",
    "int": "i",
    "int32": "i",
    "uint": "I",
    "uint32": "I",
    "float": "f",
    "float32": "f",
    "double": "d",
    "float64": "d",
}


def binary_stats(ply, path: Path, vertex_count: int, props: list[str], types: list[str]) -> dict[str, Any]:
    try:
        fmt = "<" + "".join(PLY_FORMATS[item] for item in types)
    except KeyError as exc:
        raise GaussianAppearanceError(f"Unsupported PLY property type {exc.args[0]} in {path}") from exc
    row_size = struct.calcsize(fmt)
    xyz = [props.index(prop) for prop in ("x", "y", "z")] if all(prop in props for prop in ("x", "y", "z")) else None
    opacity_index = props.index("opacity") if "opacity" in props else None
    scale_indexes = [props.index(prop) for prop in ("scale_0", "scale_1", "scale_2") if prop in props]
    color_indexes = [props.index(prop) for prop in ("f_dc_0", "f_dc_1", "f_dc_2") if prop in props]
    mins: list[float] | None = None
    maxs: list[float] | None = None
    opacities: list[float] = []
    scales: list[float] = []
    colors: list[tuple[float, float, float]] = []
    bbox_outliers = 0

    for _ in range(vertex_count):
        raw = ply.read(row_size)
        if len(raw) != row_size:
            raise GaussianAppearanceError(f"Malformed PLY vertex rows in {path}")
        values = struct.unpack(fmt, raw)
        if xyz:
            point = [float(values[index]) for index in xyz]
            mins = point if mins is None else [min(a, b) for a, b in zip(mins, point)]
            maxs = point if maxs is None else [max(a, b) for a, b in zip(maxs, point)]
            if any(abs(value) > 1_000_000 for value in point):
                bbox_outliers += 1
        if opacity_index is not None:
            opacities.append(sigmoid(float(values[opacity_index])))
        if len(scale_indexes) == 3:
            try:
                scales.append(math.exp(max(float(values[index]) for index in scale_indexes)))
            except OverflowError as exc:
                raise GaussianAppearanceError(f"Malformed PLY vertex value in {path}") from exc
        if len(color_indexes) == 3:
            colors.append(tuple(max(0.0, min(1.0, 0.5 + 0.28209479177387814 * float(values[index]))) for index in color_indexes))

    bbox = None
    if mins is not None and maxs is not None:
        bbox = {
            "min": [clean_number(value) for value in mins],
            "max": [clean_number(value) for value in maxs],
        }
    return {
        "bbox": bbox,
        "opacity": summary(opacities),
        "scale": summary(scales),
        "validation": validation_summary(opacities, scales, colors, bbox_outliers, vertex_count),
    }


def parse_ply(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as ply:
            info = parse_ply_header(read_ply_header(ply, path), path)
            stats = {"bbox": None, "opacity": summary([]), "scale": summary([]), "validation": validation_summary([], [], [], 0, 0)}
            if info["format"] == "ascii":
                stats = ascii_stats(ply, path, info["vertex_count"], info["vertex_props"])
            elif info["format"] == "binary_little_endian":
                stats = binary_stats(ply, path, info["vertex_count"], info["vertex_props"], info["vertex_types"])
            return {"count": info["vertex_count"], **stats}
    except OSError as exc:
        raise GaussianAppearanceError(f"Cannot read PLY file: {path}") from exc


def camera_source(job_dir: Path, sfm_report: dict[str, Any], qa_sfm: dict[str, Any] | None = None) -> tuple[str | None, str | None]:
    colmap = job_dir / "processed" / "colmap"
    if colmap.is_dir():
        return rel(colmap, job_dir), rel(colmap, job_dir)

    for report in (sfm_report, qa_sfm or {}):
        sparse = report.get("sparse_model_path")
        if isinstance(sparse, str) and sparse:
            path = Path(sparse)
            if not path.is_absolute():
                path = job_dir / path
            return rel(path, job_dir), rel(path, job_dir)

    transforms = job_dir / "processed" / "transforms.json"
    if transforms.is_file():
        return rel(transforms, job_dir), None
    return None, None


def training_time(timing: dict[str, Any]) -> float | None:
    stages = timing.get("stages", [])
    if isinstance(stages, list):
        for stage in stages:
            if not isinstance(stage, dict):
                continue
            key = str(stage.get("key", "")).lower()
            label = str(stage.get("label", "")).lower()
            if key == "train" or "train" in label:
                value = coerce_float(stage.get("duration_seconds"))
                if value is not None:
                    return value
    return coerce_float(timing.get("duration_seconds"))


def build_gaussian_appearance_summary(job_dir: Path, output_dir: Path | None = None) -> Path:
    if not job_dir.is_dir():
        raise GaussianAppearanceError(f"Job directory not found: {job_dir}")

    qa = load_json(job_dir / "qa_report.json")
    timing = load_json(job_dir / "timing_report.json")
    sfm_report = load_json(job_dir / "processed" / "sfm_report.json")
    qa_sfm = qa.get("sfm") if isinstance(qa.get("sfm"), dict) else {}
    splat_path = first_file(job_dir, SPLAT_CANDIDATES)
    splat_stats = parse_ply(splat_path) if splat_path else None
    transforms = job_dir / "processed" / "transforms.json"
    source, colmap_workspace = camera_source(job_dir, sfm_report, qa_sfm)
    psnr = coerce_float(qa.get("psnr"))
    ssim = coerce_float(qa.get("ssim"))

    output_dir = output_dir or job_dir / "evidence"
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise GaussianAppearanceError(f"Cannot create output directory: {output_dir}") from exc
    appearance_path = output_dir / "appearance_summary.json"
    splat_summary_path = output_dir / "splat_summary.json"
    coordinate_system = {"base": "colmap_world"}
    opacity = splat_stats["opacity"] if splat_stats else summary([])
    scale = splat_stats["scale"] if splat_stats else summary([])
    validation = splat_stats["validation"] if splat_stats else validation_summary([], [], [], 0, 0)
    bbox = splat_stats["bbox"] if splat_stats else None
    count = splat_stats["count"] if splat_stats else coerce_int(qa.get("splat_count"))

    appearance = {
        "version": VERSION,
        "coordinate_system": coordinate_system,
        "artifacts": {
            "splat": rel(splat_path, job_dir),
            "qa_report": "qa_report.json" if (job_dir / "qa_report.json").is_file() else None,
            "timing_report": "timing_report.json" if (job_dir / "timing_report.json").is_file() else None,
            "colmap_workspace": colmap_workspace,
            "transforms": rel(transforms, job_dir) if transforms.is_file() else None,
        },
        "cameras": {
            "source": source,
            "frame_count": coerce_int(qa.get("frame_count")),
            "registered_count": first_not_none(
                coerce_int(qa.get("registered_count")),
                coerce_int(qa.get("registered_frame_count")),
                coerce_int(qa_sfm.get("registered_count")),
            ),
            "registered_ratio": first_not_none(
                coerce_float(qa.get("registered_ratio")),
                coerce_float(qa_sfm.get("registered_ratio")),
            ),
        },
        "splat": {
            "available": splat_path is not None,
            "path": rel(splat_path, job_dir),
            "count": count,
            "bbox": bbox,
            "file_size_mb": first_not_none(
                coerce_float(qa.get("splat_file_size_mb")),
                round(splat_path.stat().st_size / 1024 / 1024, 2) if splat_path else None,
            ),
        },
        "opacity": opacity,
        "scale": scale,
        "training": {
            "iterations": first_not_none(
                coerce_int(qa.get("training_iterations")),
                coerce_int(qa.get("iterations")),
            ),
            "training_time_seconds": training_time(timing),
            "final_loss": first_not_none(
                coerce_float(qa.get("final_loss")),
                coerce_float(qa.get("loss")),
            ),
            "psnr": psnr,
            "ssim": ssim,
        },
        "render_quality": {
            "available": psnr is not None or ssim is not None,
            "psnr": psnr,
            "ssim": ssim,
        },
        "validation": validation,
        "quality": {
            "grade": qa.get("quality_grade"),
            "label": qa.get("quality_label"),
        },
    }
    splat_summary = {
        "version": VERSION,
        "available": splat_path is not None,
        "coordinate_system": coordinate_system,
        "splat_path": rel(splat_path, job_dir),
        "splat_count": count,
        "bbox": bbox,
        "opacity": opacity,
        "scale": scale,
        "validation": validation,
    }
    write_json(appearance_path, appearance)
    write_json(splat_summary_path, splat_summary)
    return appearance_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Gaussian Splat appearance evidence summaries.")
    parser.add_argument("job_dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)

    try:
        summary_path = build_gaussian_appearance_summary(args.job_dir, args.output_dir)
    except GaussianAppearanceError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(summary_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
