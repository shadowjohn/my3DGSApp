#!/usr/bin/env python3
"""Prepare OpenMVS input images from MP4 or ZIP."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath

from PIL import Image, ImageOps


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}
MASK_SUFFIX = ".mask.png"
RESAMPLE_IMAGE = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
RESAMPLE_MASK = getattr(getattr(Image, "Resampling", Image), "NEAREST")


def is_safe_zip_member(name: str) -> bool:
    name = name.replace("\\", "/")
    if not name or name.startswith("/"):
        return False
    parts = PurePosixPath(name).parts
    return ".." not in parts


def is_zip_symlink(info: zipfile.ZipInfo) -> bool:
    return ((info.external_attr >> 16) & 0o170000) == 0o120000


def is_mask_name(name: str) -> bool:
    return name.lower().endswith(MASK_SUFFIX)


def mask_lookup_key(name: str) -> str:
    return name.replace("\\", "/")[: -len(MASK_SUFFIX)]


def image_mask_keys(name: str) -> list[str]:
    normalized = name.replace("\\", "/")
    without_ext = str(PurePosixPath(normalized).with_suffix(""))
    return [without_ext, normalized]


def clean_output_dir(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for child in output_dir.iterdir():
        if child.is_file() or child.is_symlink():
            child.unlink()
        elif child.is_dir():
            shutil.rmtree(child)


def resize_size(size: tuple[int, int], width: int) -> tuple[int, int]:
    if width <= 0 or size[0] <= width:
        return size
    return (width, max(1, round(size[1] * width / size[0])))


def save_zip_image(src, target_path: Path, width: int, target_size: tuple[int, int] | None = None, is_mask: bool = False) -> tuple[int, int] | None:
    try:
        with Image.open(src) as image:
            image = ImageOps.exif_transpose(image)
            size = target_size or resize_size(image.size, width)
            if image.size != size:
                image = image.resize(size, RESAMPLE_MASK if is_mask else RESAMPLE_IMAGE)
            if target_path.suffix.lower() in {".jpg", ".jpeg"}:
                image = image.convert("RGB")
                image.save(target_path, quality=95)
            else:
                image.save(target_path)
            return size
    except OSError:
        src.seek(0)
        with target_path.open("wb") as dst:
            shutil.copyfileobj(src, dst)
        return target_size


def extract_zip_images(zip_path: Path, output_dir: Path, max_frames: int, width: int) -> list[dict[str, str]]:
    extracted: list[dict[str, str]] = []
    with zipfile.ZipFile(zip_path) as zf:
        masks: dict[str, zipfile.ZipInfo] = {}
        for info in zf.infolist():
            name = info.filename.replace("\\", "/")
            if info.is_dir() or is_zip_symlink(info) or not is_safe_zip_member(name):
                continue
            if is_mask_name(name):
                masks[mask_lookup_key(name)] = info

        for info in zf.infolist():
            if len(extracted) >= max_frames:
                break
            name = info.filename.replace("\\", "/")
            suffix = Path(name).suffix.lower()
            if info.is_dir() or is_zip_symlink(info):
                continue
            if is_mask_name(name):
                continue
            if suffix not in IMAGE_EXTENSIONS:
                continue
            if not is_safe_zip_member(name):
                continue
            target_name = f"frame_{len(extracted) + 1:05d}{'.jpg' if suffix == '.jpeg' else suffix}"
            target_path = output_dir / target_name
            with zf.open(info, "r") as src:
                image_size = save_zip_image(src, target_path, width)
            item = {"original_name": name, "filename": target_name}
            mask_info = next((masks[key] for key in image_mask_keys(name) if key in masks), None)
            if mask_info is not None:
                mask_name = f"{Path(target_name).stem}.mask.png"
                with zf.open(mask_info, "r") as src:
                    save_zip_image(src, output_dir / mask_name, width, image_size, is_mask=True)
                item["mask_original_name"] = mask_info.filename.replace("\\", "/")
                item["mask_filename"] = mask_name
            extracted.append(item)
    return extracted


def extract_video_frames(input_path: Path, output_dir: Path, fps: float, width: int, max_frames: int) -> list[dict[str, str]]:
    pattern = output_dir / "frame_%05d.jpg"
    vf = f"fps={fps},scale={width}:-2"
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(input_path),
        "-vf",
        vf,
        "-frames:v",
        str(max_frames),
        "-q:v",
        "2",
        str(pattern),
    ]
    subprocess.run(cmd, check=True)
    return [
        {"original_name": path.name, "filename": path.name}
        for path in sorted(output_dir.glob("frame_*.jpg"))
    ]


def build_manifest(source_path: Path, source_type: str, images: list[dict[str, str]]) -> dict[str, object]:
    return {
        "source": str(source_path),
        "source_type": source_type,
        "frame_count": len(images),
        "mask_count": sum(1 for image in images if image.get("mask_filename")),
        "images": images,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_path", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--fps", type=float, default=3.0)
    parser.add_argument("--width", type=int, default=1600)
    parser.add_argument("--max-frames", type=int, default=240)
    parser.add_argument("--min-frames", type=int, default=8)
    args = parser.parse_args()

    if not args.input_path.is_file():
        print(f"input file missing: {args.input_path}", file=sys.stderr)
        return 2

    clean_output_dir(args.output_dir)
    suffix = args.input_path.suffix.lower()
    try:
        if suffix == ".zip":
            source_type = "zip"
            images = extract_zip_images(args.input_path, args.output_dir, args.max_frames, args.width)
        elif suffix == ".mp4":
            source_type = "mp4"
            images = extract_video_frames(args.input_path, args.output_dir, args.fps, args.width, args.max_frames)
        else:
            print("unsupported input type; expected .mp4 or .zip", file=sys.stderr)
            return 2
    except (OSError, zipfile.BadZipFile, subprocess.CalledProcessError) as exc:
        print(f"prepare images failed: {exc}", file=sys.stderr)
        return 1

    if len(images) < args.min_frames:
        print(f"no usable images: selected {len(images)} image(s), require at least {args.min_frames}", file=sys.stderr)
        return 1

    manifest = build_manifest(args.input_path, source_type, images)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"frame_count": len(images), "source_type": source_type}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
