#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path
from typing import Any


VERSION = "1.0.3"
GLB_CANDIDATES = (
    "exports/model.glb",
    "mvs/scene_dense_mesh_refine_texture.glb",
    "scene_dense_mesh_refine_texture.glb",
    "model.glb",
)
MESH_PLY_CANDIDATES = (
    "exports/scene_dense_mesh_refine_texture.ply",
    "exports/scene_dense_mesh_refine.ply",
    "exports/scene_dense_mesh.ply",
    "mvs/scene_dense_mesh_refine_texture.ply",
    "mvs/scene_dense_mesh_refine.ply",
    "mvs/scene_dense_mesh.ply",
    "scene_dense_mesh_refine_texture.ply",
    "scene_dense_mesh_refine.ply",
    "scene_dense_mesh.ply",
)
DENSE_CLOUD_CANDIDATES = ("exports/scene_dense.ply", "mvs/scene_dense.ply", "scene_dense.ply")
TEXTURE_PATTERNS = (
    "scene_dense_mesh_refine_texture_*.png",
    "scene_dense_mesh_refine_texture_*.jpg",
    "scene_dense_mesh_refine_texture_*.jpeg",
    "scene_dense_mesh_refine_texture*.png",
    "scene_dense_mesh_refine_texture*.jpg",
    "scene_dense_mesh_refine_texture*.jpeg",
)


class OpenMVSGeometryError(Exception):
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


def first_file(job_dir: Path, names: tuple[str, ...]) -> Path | None:
    for name in names:
        path = job_dir / name
        if path.is_file():
            return path
    return None


def texture_files(job_dir: Path) -> list[Path]:
    seen: set[Path] = set()
    paths: list[Path] = []
    for directory in (job_dir / "exports", job_dir / "mvs", job_dir):
        if not directory.is_dir():
            continue
        for pattern in TEXTURE_PATTERNS:
            for path in sorted(directory.glob(pattern)):
                if path.is_file() and path not in seen:
                    seen.add(path)
                    paths.append(path)
    return paths


def load_qa_report(job_dir: Path) -> dict[str, Any]:
    path = job_dir / "qa_report.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def parse_ply(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as ply:
            header = read_ply_header(ply, path)
            info = parse_ply_header(header, path)
            if info["format"] == "ascii":
                info["bbox"] = ascii_bbox(ply, path, info["vertex_count"], info["vertex_props"])
            else:
                info["bbox"] = None
            return {
                "vertex_count": info["vertex_count"],
                "face_count": info["face_count"],
                "bbox": info["bbox"],
                "normal_available": all(prop in info["vertex_props"] for prop in ("nx", "ny", "nz")),
            }
    except OSError as exc:
        raise OpenMVSGeometryError(f"Cannot read PLY file: {path}") from exc


def read_ply_header(ply, path: Path) -> list[str]:
    header: list[str] = []
    for raw_line in ply:
        try:
            line = raw_line.decode("ascii").strip()
        except UnicodeDecodeError as exc:
            raise OpenMVSGeometryError(f"Malformed PLY header in {path}") from exc
        header.append(line)
        if line == "end_header":
            break
    else:
        raise OpenMVSGeometryError(f"Malformed PLY file missing end_header: {path}")
    if not header or header[0] != "ply":
        raise OpenMVSGeometryError(f"Malformed PLY file missing magic header: {path}")
    return header


def parse_ply_header(header: list[str], path: Path) -> dict[str, Any]:
    ply_format = None
    vertex_count = None
    face_count = 0
    element = None
    vertex_props: list[str] = []
    for line in header[1:]:
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "format" and len(parts) >= 2:
            ply_format = parts[1]
        elif parts[0] == "element" and len(parts) >= 3:
            element = parts[1]
            try:
                count = int(parts[2])
            except ValueError as exc:
                raise OpenMVSGeometryError(f"Malformed PLY element count in {path}") from exc
            if element == "vertex":
                vertex_count = count
            elif element == "face":
                face_count = count
        elif parts[0] == "property" and element == "vertex":
            vertex_props.append(parts[-1])

    if vertex_count is None or ply_format is None:
        raise OpenMVSGeometryError(f"Malformed PLY header in {path}")
    if ply_format != "ascii" and not ply_format.startswith("binary_"):
        raise OpenMVSGeometryError(f"Unsupported PLY format {ply_format} in {path}")
    return {
        "format": ply_format,
        "vertex_count": vertex_count,
        "face_count": face_count,
        "vertex_props": vertex_props,
    }


def ascii_bbox(ply, path: Path, vertex_count: int, props: list[str]) -> dict[str, list[int | float]] | None:
    if vertex_count <= 0 or not all(prop in props for prop in ("x", "y", "z")):
        return None
    xyz = [props.index(prop) for prop in ("x", "y", "z")]
    mins: list[float] | None = None
    maxs: list[float] | None = None
    for _ in range(vertex_count):
        raw_line = ply.readline()
        if not raw_line:
            raise OpenMVSGeometryError(f"Malformed PLY vertex rows in {path}")
        try:
            parts = raw_line.decode("ascii").split()
        except UnicodeDecodeError as exc:
            raise OpenMVSGeometryError(f"Malformed PLY vertex row encoding in {path}") from exc
        if len(parts) <= max(xyz):
            raise OpenMVSGeometryError(f"Malformed PLY vertex row in {path}")
        try:
            point = [float(parts[index]) for index in xyz]
        except ValueError as exc:
            raise OpenMVSGeometryError(f"Malformed PLY vertex coordinate in {path}") from exc
        mins = point if mins is None else [min(a, b) for a, b in zip(mins, point)]
        maxs = point if maxs is None else [max(a, b) for a, b in zip(maxs, point)]
    return {
        "min": [clean_number(value) for value in mins or []],
        "max": [clean_number(value) for value in maxs or []],
    }


def qa_int(qa: dict[str, Any], key: str, fallback: int | None = None) -> int | None:
    try:
        return int(qa[key])
    except (KeyError, TypeError, ValueError):
        return fallback


def qa_float(qa: dict[str, Any], key: str) -> float | None:
    try:
        return float(qa[key])
    except (KeyError, TypeError, ValueError):
        return None


def build_openmvs_geometry_summary(job_dir: Path, output_dir: Path | None = None) -> Path:
    if not job_dir.is_dir():
        raise OpenMVSGeometryError(f"Job directory not found: {job_dir}")

    qa = load_qa_report(job_dir)
    mesh_path = first_file(job_dir, GLB_CANDIDATES)
    mesh_ply = first_file(job_dir, MESH_PLY_CANDIDATES)
    dense_ply = first_file(job_dir, DENSE_CLOUD_CANDIDATES)
    textures = texture_files(job_dir)
    texture_path = textures[0] if textures else None

    mesh_stats = parse_ply(mesh_ply) if mesh_ply else None
    try:
        dense_stats = parse_ply(dense_ply) if dense_ply else None
    except OpenMVSGeometryError:
        dense_stats = None
    image_count = qa_int(qa, "texture_image_count", len(textures) or None)

    output_dir = output_dir or job_dir / "evidence"
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "geometry_summary.json"
    summary = {
        "version": VERSION,
        "coordinate_system": {"base": "colmap_world"},
        "artifacts": {
            "mesh": rel(mesh_path, job_dir) or qa.get("glb_path"),
            "mesh_ply": rel(mesh_ply, job_dir) or qa.get("mesh_path"),
            "dense_cloud": rel(dense_ply, job_dir),
            "texture": rel(texture_path, job_dir),
        },
        "mesh": {
            "vertex_count": mesh_stats["vertex_count"] if mesh_stats else None,
            "face_count": mesh_stats["face_count"] if mesh_stats else None,
            "bbox": mesh_stats["bbox"] if mesh_stats else None,
            "normal_available": bool(mesh_stats and mesh_stats["normal_available"]),
        },
        "dense_cloud": {
            "point_count": dense_stats["vertex_count"] if dense_stats else None,
            "bbox": dense_stats["bbox"] if dense_stats else None,
        },
        "texture": {
            "available": bool(texture_path or image_count),
            "path": rel(texture_path, job_dir),
            "image_count": image_count,
            "width": qa_int(qa, "texture_width"),
            "height": qa_int(qa, "texture_height"),
            "black_pixel_ratio": qa_float(qa, "texture_black_pixel_ratio"),
            "white_empty_pixel_ratio": qa_float(qa, "texture_white_empty_pixel_ratio"),
            "patch_count": qa_int(qa, "texture_patch_count"),
        },
        "risks": {
            "hole_risk_summary": "unknown",
            "thin_geometry_risk": "unknown",
            "density_summary": "unknown",
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    return summary_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build an OpenMVS geometry evidence summary.")
    parser.add_argument("job_dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)

    try:
        summary_path = build_openmvs_geometry_summary(args.job_dir, args.output_dir)
    except OpenMVSGeometryError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(summary_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
