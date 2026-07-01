#!/usr/bin/env python3
"""Build a small QA report for an OpenMVS job."""

from __future__ import annotations

import argparse
import re
import struct
import json
from pathlib import Path
from typing import Any

from PIL import Image


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}


def size_mb(path: Path) -> float | None:
    if not path.is_file():
        return None
    return round(path.stat().st_size / 1024 / 1024, 6)


def first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.is_file():
            return path
    return None


def glb_image_uris(path: Path) -> list[str]:
    if not path.is_file() or path.stat().st_size < 20:
        return []
    try:
        data = path.read_bytes()
        magic, _version, _length = struct.unpack_from("<III", data, 0)
        if magic != 0x46546C67:
            return []
        chunk_length, chunk_type = struct.unpack_from("<II", data, 12)
        if chunk_type != 0x4E4F534A:
            return []
        doc = json.loads(data[20:20 + chunk_length].decode("utf-8"))
    except (OSError, json.JSONDecodeError, struct.error, UnicodeDecodeError):
        return []
    return [
        str(image.get("uri"))
        for image in doc.get("images", [])
        if isinstance(image, dict) and image.get("uri")
    ]


def find_texture_images(exports: Path, glb_path: Path) -> list[Path]:
    image_paths = []
    for uri in glb_image_uris(glb_path):
        candidate = (exports / uri).resolve()
        try:
            candidate.relative_to(exports.resolve())
        except ValueError:
            continue
        if candidate.is_file():
            image_paths.append(candidate)
    if image_paths:
        return image_paths

    primary_patterns = [
        "scene_dense_mesh_refine_texture_*.png",
        "scene_dense_mesh_refine_texture_*.jpg",
        "scene_dense_mesh_refine_texture_*.jpeg",
    ]
    fallback_patterns = [
        "scene_dense_mesh_refine_texture*.png",
        "scene_dense_mesh_refine_texture*.jpg",
        "scene_dense_mesh_refine_texture*.jpeg",
    ]

    textures: list[Path] = []
    for pattern in primary_patterns:
        textures.extend(path for path in sorted(exports.glob(pattern)) if path.is_file())
    if not textures:
        for pattern in fallback_patterns:
            textures.extend(path for path in sorted(exports.glob(pattern)) if path.is_file())
    unique = []
    seen = set()
    for texture in textures:
        if texture in seen:
            continue
        seen.add(texture)
        unique.append(texture)
    return unique


def analyze_texture(path: Path) -> dict[str, Any] | None:
    try:
        with Image.open(path) as image:
            rgb = image.convert("RGB")
            width, height = rgb.size
            black = 0
            white = 0
            total = width * height
            for red, green, blue in rgb.getdata():
                if max(red, green, blue) < 12:
                    black += 1
                if min(red, green, blue) > 243:
                    white += 1
    except OSError:
        return None
    if total <= 0:
        return None
    return {
        "path": str(path),
        "width": width,
        "height": height,
        "black_pixel_ratio": round(black / total, 6),
        "white_empty_pixel_ratio": round(white / total, 6),
    }


def parse_texture_log(job_dir: Path) -> dict[str, int | None]:
    logs = sorted((job_dir / "mvs").glob("TextureMesh*.log"), key=lambda path: path.stat().st_mtime if path.exists() else 0)
    process_log = job_dir / "process.log"
    if process_log.is_file():
        logs.append(process_log)

    result: dict[str, int | None] = {
        "texture_patch_count": None,
        "texture_atlas_size": None,
        "texture_atlas_count": None,
        "texture_view_selection_patch_count": None,
    }
    atlas_re = re.compile(r"Generating texture atlas and image completed:\s*(\d+)\s+patches,\s*(\d+)\s+image size,\s*(\d+)\s+textures")
    view_re = re.compile(r"Assigning the best view to each face completed:\s*\d+\s+faces,\s*(\d+)\s+patches")
    for log in logs:
        try:
            text = log.read_text(errors="ignore")
        except OSError:
            continue
        for match in view_re.finditer(text):
            result["texture_view_selection_patch_count"] = int(match.group(1))
        for match in atlas_re.finditer(text):
            result["texture_patch_count"] = int(match.group(1))
            result["texture_atlas_size"] = int(match.group(2))
            result["texture_atlas_count"] = int(match.group(3))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job_id")
    parser.add_argument("job_dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    manifest = read_json(args.job_dir / "input_manifest.json")
    colmap_manifest = read_json(args.job_dir / "colmap_manifest.json")
    exports = args.job_dir / "exports"
    glb_path = exports / "model.glb"
    mesh_path = first_existing([
        exports / "scene_dense_mesh_refine_texture.ply",
        exports / "scene_dense_mesh_refine.ply",
        exports / "scene_dense_mesh.ply",
        args.job_dir / "mvs" / "scene_dense_mesh_refine_texture.ply",
        args.job_dir / "mvs" / "scene_dense_mesh_refine.ply",
        args.job_dir / "mvs" / "scene_dense_mesh.ply",
    ])
    texture_images = [
        analysis
        for analysis in (analyze_texture(path) for path in find_texture_images(exports, glb_path))
        if analysis is not None
    ]
    primary_texture = texture_images[0] if texture_images else {}
    texture_log = parse_texture_log(args.job_dir)
    texture_repair = read_json(args.job_dir / "texture_repair_report.json")

    report = {
        "job_id": str(args.job_id),
        "input_frame_count": manifest.get("frame_count"),
        "input_mask_count": manifest.get("mask_count"),
        "registered_frame_count": colmap_manifest.get("registered_frame_count"),
        "glb_file_size_mb": size_mb(glb_path),
        "mesh_file_size_mb": size_mb(mesh_path) if mesh_path else None,
        "glb_path": str(glb_path) if glb_path.is_file() else None,
        "mesh_path": str(mesh_path) if mesh_path else None,
        "texture_image_count": len(texture_images),
        "texture_width": primary_texture.get("width"),
        "texture_height": primary_texture.get("height"),
        "texture_black_pixel_ratio": primary_texture.get("black_pixel_ratio"),
        "texture_white_empty_pixel_ratio": primary_texture.get("white_empty_pixel_ratio"),
        "texture_images": texture_images,
        "texture_repair": texture_repair,
        **texture_log,
    }

    output = args.output or (args.job_dir / "qa_report.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
