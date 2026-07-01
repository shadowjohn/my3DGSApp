#!/usr/bin/env python3
"""Repair OpenMVS texture atlases before browser preview."""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image


PRIMARY_PATTERNS = [
    "scene_dense_mesh_refine_texture_*.png",
    "scene_dense_mesh_refine_texture_*.jpg",
    "scene_dense_mesh_refine_texture_*.jpeg",
]
FALLBACK_PATTERNS = [
    "scene_dense_mesh_refine_texture*.png",
    "scene_dense_mesh_refine_texture*.jpg",
    "scene_dense_mesh_refine_texture*.jpeg",
]


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


def find_texture_images(exports: Path) -> list[Path]:
    image_paths: list[Path] = []
    glb_path = exports / "model.glb"
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

    textures: list[Path] = []
    for pattern in PRIMARY_PATTERNS:
        textures.extend(path for path in sorted(exports.glob(pattern)) if path.is_file())
    if not textures:
        for pattern in FALLBACK_PATTERNS:
            textures.extend(path for path in sorted(exports.glob(pattern)) if path.is_file())
    unique: list[Path] = []
    seen: set[Path] = set()
    for texture in textures:
        if texture in seen:
            continue
        seen.add(texture)
        unique.append(texture)
    return unique


def analyze_texture(path: Path, black_threshold: int) -> dict[str, Any]:
    with Image.open(path) as image:
        rgb = image.convert("RGB")
        width, height = rgb.size
        total = width * height
        black = 0
        white = 0
        for red, green, blue in rgb.getdata():
            if max(red, green, blue) < black_threshold:
                black += 1
            if min(red, green, blue) > 243:
                white += 1
    return {
        "path": str(path),
        "width": width,
        "height": height,
        "black_pixel_ratio": round(black / total, 6) if total else None,
        "white_empty_pixel_ratio": round(white / total, 6) if total else None,
    }


def should_repair(mode: str, before: dict[str, Any], trigger_black_ratio: float, max_white_ratio: float) -> tuple[bool, str]:
    black_ratio = float(before.get("black_pixel_ratio") or 0)
    white_ratio = float(before.get("white_empty_pixel_ratio") or 0)
    if mode == "off":
        return False, "mode is off"
    if mode == "deblack":
        return black_ratio > 0, "forced deblack"
    if black_ratio < trigger_black_ratio:
        return False, "black ratio below trigger"
    if white_ratio > max_white_ratio:
        return False, "white empty ratio above limit"
    return True, "auto trigger matched"


def repair_black_pixels(path: Path, black_threshold: int, inpaint_radius: int) -> int:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise OSError(f"cannot read image: {path}")
    mask = np.max(image, axis=2) < black_threshold
    mask_count = int(mask.sum())
    if mask_count <= 0:
        return 0
    repaired = cv2.inpaint(image, (mask.astype(np.uint8) * 255), inpaint_radius, cv2.INPAINT_TELEA)
    if not cv2.imwrite(str(path), repaired):
        raise OSError(f"cannot write image: {path}")
    return mask_count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exports", type=Path)
    parser.add_argument("--mode", choices=["off", "auto", "deblack"], default="auto")
    parser.add_argument("--black-threshold", type=int, default=18)
    parser.add_argument("--trigger-black-ratio", type=float, default=0.20)
    parser.add_argument("--max-white-ratio", type=float, default=0.42)
    parser.add_argument("--inpaint-radius", type=int, default=5)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    textures = find_texture_images(args.exports)
    report: dict[str, Any] = {
        "mode": args.mode,
        "black_threshold": args.black_threshold,
        "trigger_black_ratio": args.trigger_black_ratio,
        "max_white_ratio": args.max_white_ratio,
        "inpaint_radius": args.inpaint_radius,
        "repaired_count": 0,
        "textures": [],
    }

    for texture in textures:
        before = analyze_texture(texture, args.black_threshold)
        repair, reason = should_repair(args.mode, before, args.trigger_black_ratio, args.max_white_ratio)
        item: dict[str, Any] = {
            "path": str(texture),
            "action": "skipped",
            "reason": reason,
            "before": before,
            "after": before,
        }
        if repair:
            repaired_pixels = repair_black_pixels(texture, args.black_threshold, args.inpaint_radius)
            after = analyze_texture(texture, args.black_threshold)
            item.update({
                "action": "repaired" if repaired_pixels else "skipped",
                "repaired_pixels": repaired_pixels,
                "after": after,
            })
            if repaired_pixels:
                report["repaired_count"] += 1
        report["textures"].append(item)

    output = args.report
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
