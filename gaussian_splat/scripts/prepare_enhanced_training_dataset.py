#!/usr/bin/env python3
"""Build a Nerfstudio training dataset that reuses COLMAP poses with enhanced images."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys


def load_transform_frame_paths(transforms_path: Path):
    data = json.loads(transforms_path.read_text(encoding="utf-8"))
    frame_paths = []
    for frame in data.get("frames", []):
        file_path = frame.get("file_path")
        if isinstance(file_path, str) and file_path:
            frame_paths.append(Path(file_path))
    return frame_paths


def image_size(path: Path):
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=p=0:s=x",
            str(path),
        ],
        text=True,
        capture_output=True,
        check=True,
    )
    width, height = result.stdout.strip().split("x", 1)
    return int(width), int(height)


def build_ffmpeg_convert_command(enhanced_path: Path, output_path: Path, width: int, height: int):
    return [
        "ffmpeg",
        "-y",
        "-i",
        str(enhanced_path),
        "-vf",
        f"scale={width}:{height}:flags=lanczos",
        "-q:v",
        "2",
        str(output_path),
    ]


def remove_processed_image_dirs(output_path: Path):
    for child in output_path.iterdir():
        if child.is_dir() and child.name.startswith("images"):
            shutil.rmtree(child)


def prepare_dataset(processed_path: Path, enhanced_path: Path, output_path: Path):
    transforms_path = processed_path / "transforms.json"
    if not transforms_path.is_file():
        raise FileNotFoundError(f"transforms.json not found: {transforms_path}")
    if not enhanced_path.is_dir():
        raise FileNotFoundError(f"enhanced_images not found: {enhanced_path}")

    frame_paths = load_transform_frame_paths(transforms_path)
    if not frame_paths:
        raise ValueError(f"no frames found in: {transforms_path}")

    for frame_path in frame_paths:
        original_path = processed_path / frame_path
        enhanced_frame = enhanced_path / f"{frame_path.stem}.png"
        if not original_path.is_file():
            raise FileNotFoundError(f"processed frame missing: {original_path}")
        if not enhanced_frame.is_file():
            raise FileNotFoundError(f"enhanced frame missing: {enhanced_frame}")

    if output_path.exists():
        shutil.rmtree(output_path)
    shutil.copytree(processed_path, output_path)
    remove_processed_image_dirs(output_path)

    for frame_path in frame_paths:
        original_path = processed_path / frame_path
        enhanced_frame = enhanced_path / f"{frame_path.stem}.png"
        output_frame = output_path / frame_path
        output_frame.parent.mkdir(parents=True, exist_ok=True)
        width, height = image_size(original_path)
        subprocess.run(
            build_ffmpeg_convert_command(enhanced_frame, output_frame, width, height),
            check=True,
        )


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Reuse selected-frame COLMAP poses with Real-ESRGAN enhanced training images."
    )
    parser.add_argument("processed_dir")
    parser.add_argument("enhanced_images_dir")
    parser.add_argument("output_processed_dir")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        prepare_dataset(
            Path(args.processed_dir),
            Path(args.enhanced_images_dir),
            Path(args.output_processed_dir),
        )
    except Exception as exc:
        print(f"prepare_enhanced_training_dataset.py: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
