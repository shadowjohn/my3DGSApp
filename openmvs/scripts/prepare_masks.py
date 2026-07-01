#!/usr/bin/env python3
"""Prepare OpenMVS .mask.png files next to COLMAP undistorted images."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

try:
    import cv2  # type: ignore
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover - depends on host packages
    cv2 = None
    np = None


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}
MASK_SUFFIX = ".mask.png"


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}


def image_files(path: Path) -> list[Path]:
    return sorted(
        item
        for item in path.iterdir()
        if item.is_file()
        and item.suffix.lower() in IMAGE_EXTENSIONS
        and not item.name.lower().endswith(MASK_SUFFIX)
    )


def clean_dense_masks(dense_images: Path) -> None:
    if not dense_images.is_dir():
        return
    for mask in dense_images.glob(f"*{MASK_SUFFIX}"):
        mask.unlink()


def parse_rect(value: str) -> tuple[float, float, float, float]:
    try:
        parts = [float(part.strip()) for part in value.split(",")]
    except ValueError:
        parts = []
    if len(parts) != 4:
        return (0.12, 0.08, 0.88, 0.96)
    x1, y1, x2, y2 = parts
    x1 = min(max(x1, 0.0), 0.98)
    y1 = min(max(y1, 0.0), 0.98)
    x2 = min(max(x2, x1 + 0.01), 1.0)
    y2 = min(max(y2, y1 + 0.01), 1.0)
    return (x1, y1, x2, y2)


def threshold_mask(mask: Image.Image, size: tuple[int, int]) -> Image.Image:
    resampling = getattr(Image, "Resampling", Image).NEAREST
    return mask.convert("L").resize(size, resampling).point(lambda value: 255 if value >= 128 else 0)


def save_provided_masks(manifest: dict[str, Any], raw_images: Path, dense_images: Path) -> list[dict[str, str]]:
    generated: list[dict[str, str]] = []
    for item in manifest.get("images", []):
        if not isinstance(item, dict):
            continue
        filename = str(item.get("filename") or "")
        mask_filename = str(item.get("mask_filename") or "")
        if not filename or not mask_filename:
            continue
        dense_image = dense_images / filename
        raw_mask = raw_images / mask_filename
        if not dense_image.is_file() or not raw_mask.is_file():
            continue
        with Image.open(dense_image) as image, Image.open(raw_mask) as mask:
            target_name = f"{dense_image.stem}{MASK_SUFFIX}"
            target = dense_images / target_name
            threshold_mask(mask, image.size).save(target)
        generated.append({
            "image": filename,
            "mask": target_name,
            "source": mask_filename,
        })
    return generated


def ellipse_mask(size: tuple[int, int], rect: tuple[float, float, float, float]) -> Image.Image:
    width, height = size
    x1, y1, x2, y2 = rect
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((int(x1 * width), int(y1 * height), int(x2 * width), int(y2 * height)), fill=255)
    return mask


def grabcut_mask(image: Image.Image, rect: tuple[float, float, float, float]) -> Image.Image | None:
    if cv2 is None or np is None:
        return None
    rgb = image.convert("RGB")
    width, height = rgb.size
    scale = min(1.0, 900.0 / max(width, height))
    work = rgb
    if scale < 1.0:
        resampling = getattr(Image, "Resampling", Image).BILINEAR
        work = rgb.resize((max(2, int(width * scale)), max(2, int(height * scale))), resampling)

    work_arr = cv2.cvtColor(np.array(work), cv2.COLOR_RGB2BGR)
    work_h, work_w = work_arr.shape[:2]
    x1, y1, x2, y2 = rect
    rect_px = (
        max(1, int(x1 * work_w)),
        max(1, int(y1 * work_h)),
        max(2, int((x2 - x1) * work_w)),
        max(2, int((y2 - y1) * work_h)),
    )
    if rect_px[0] + rect_px[2] >= work_w:
        rect_px = (rect_px[0], rect_px[1], max(2, work_w - rect_px[0] - 1), rect_px[3])
    if rect_px[1] + rect_px[3] >= work_h:
        rect_px = (rect_px[0], rect_px[1], rect_px[2], max(2, work_h - rect_px[1] - 1))

    mask = np.zeros((work_h, work_w), np.uint8)
    bgd_model = np.zeros((1, 65), np.float64)
    fgd_model = np.zeros((1, 65), np.float64)
    try:
        cv2.grabCut(work_arr, mask, rect_px, bgd_model, fgd_model, 4, cv2.GC_INIT_WITH_RECT)
    except Exception:
        return None

    foreground = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype("uint8")
    ratio = float(np.count_nonzero(foreground)) / float(foreground.size)
    if ratio < 0.02 or ratio > 0.98:
        return None
    kernel = np.ones((5, 5), np.uint8)
    foreground = cv2.morphologyEx(foreground, cv2.MORPH_OPEN, kernel)
    foreground = cv2.morphologyEx(foreground, cv2.MORPH_CLOSE, kernel)
    result = Image.fromarray(foreground, mode="L")
    if result.size != (width, height):
        resampling = getattr(Image, "Resampling", Image).NEAREST
        result = result.resize((width, height), resampling)
    return result


def save_auto_masks(dense_images: Path, rect: tuple[float, float, float, float]) -> tuple[list[dict[str, str]], str]:
    generated: list[dict[str, str]] = []
    used_grabcut = False
    for image_path in image_files(dense_images):
        with Image.open(image_path) as image:
            mask = grabcut_mask(image, rect)
            method = "grabcut"
            if mask is None:
                mask = ellipse_mask(image.size, rect)
                method = "ellipse"
            else:
                used_grabcut = True
            target_name = f"{image_path.stem}{MASK_SUFFIX}"
            mask.save(dense_images / target_name)
        generated.append({"image": image_path.name, "mask": target_name, "method": method})
    return generated, "grabcut" if used_grabcut else "ellipse"


def write_report(path: Path | None, report: dict[str, Any]) -> None:
    if not path:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["none", "provided", "auto"], default="none")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--raw-images", type=Path, required=True)
    parser.add_argument("--dense-images", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--auto-rect", default="0.12,0.08,0.88,0.96")
    args = parser.parse_args()

    if not args.dense_images.is_dir():
        print(f"dense image folder missing: {args.dense_images}", file=sys.stderr)
        return 2

    clean_dense_masks(args.dense_images)
    manifest = read_json(args.manifest)
    report: dict[str, Any] = {
        "mode": args.mode,
        "enabled": args.mode != "none",
        "generated_count": 0,
        "ignore_mask_label": 0,
        "masks": [],
    }

    if args.mode == "none":
        write_report(args.report, report)
        print(json.dumps(report, ensure_ascii=False))
        return 0

    if args.mode == "provided":
        masks = save_provided_masks(manifest, args.raw_images, args.dense_images)
        report["masks"] = masks
        report["generated_count"] = len(masks)
        if not masks:
            write_report(args.report, report)
            print("mask mode 'provided' selected, but no matching .mask.png files were found", file=sys.stderr)
            return 1
    else:
        rect = parse_rect(args.auto_rect)
        masks, method = save_auto_masks(args.dense_images, rect)
        report["masks"] = masks
        report["generated_count"] = len(masks)
        report["auto_rect"] = rect
        report["auto_method"] = method

    write_report(args.report, report)
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
