#!/usr/bin/env python3
"""Run Real-ESRGAN NCNN Vulkan over selected frame images."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys


DEFAULT_BINARY = "/var/www/html/demo/php/ai_video/binary/realesrgan-ncnn-vulkan"
DEFAULT_SCALE = 2
DEFAULT_MODEL_NAME = "realesrgan-x4plus"


def is_generated_output(path: Path) -> bool:
    name = path.name
    return (
        path.is_file()
        and name.startswith("frame_")
        and name.endswith(".png")
        and name[len("frame_") : -len(".png")].isascii()
        and name[len("frame_") : -len(".png")].isdigit()
    )


def build_realesrgan_command(binary, input_dir, output_dir, scale, model_name):
    return [
        str(binary),
        "-i",
        str(input_dir),
        "-o",
        str(output_dir),
        "-s",
        str(scale),
        "-n",
        str(model_name),
        "-f",
        "png",
    ]


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Enhance selected frame images with Real-ESRGAN NCNN Vulkan."
    )
    parser.add_argument("input_dir")
    parser.add_argument("output_dir")
    parser.add_argument("--binary", default=DEFAULT_BINARY)
    parser.add_argument("--scale", type=int, default=DEFAULT_SCALE)
    parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def validate_paths(binary_path: Path, input_path: Path) -> bool:
    if not binary_path.exists():
        print(f"Real-ESRGAN binary not found: {binary_path}", file=sys.stderr)
        return False
    if not binary_path.is_file():
        print(f"Real-ESRGAN binary is not a file: {binary_path}", file=sys.stderr)
        return False
    if not os.access(binary_path, os.X_OK):
        print(f"Real-ESRGAN binary is not executable: {binary_path}", file=sys.stderr)
        return False
    if not input_path.exists():
        print(f"input_dir not found: {input_path}", file=sys.stderr)
        return False
    if not input_path.is_dir():
        print(f"input_dir is not a directory: {input_path}", file=sys.stderr)
        return False
    return True


def validate_output_dir(output_path: Path) -> bool:
    if not output_path.exists():
        return True
    if not output_path.is_dir():
        print(f"output_dir is not a directory: {output_path}", file=sys.stderr)
        return False

    for child in output_path.iterdir():
        if not is_generated_output(child):
            print(f"output_dir contains unrelated file: {child}", file=sys.stderr)
            return False
    return True


def prepare_output_dir(output_path: Path):
    if not output_path.exists():
        output_path.mkdir(parents=True)
        return

    for child in output_path.iterdir():
        child.unlink()


def main(argv=None):
    args = parse_args(argv)
    binary_path = Path(args.binary)
    input_path = Path(args.input_dir)
    output_path = Path(args.output_dir)

    if not validate_paths(binary_path, input_path):
        return 1
    if not validate_output_dir(output_path):
        return 1

    command = build_realesrgan_command(
        args.binary,
        args.input_dir,
        args.output_dir,
        args.scale,
        args.model_name,
    )
    if args.dry_run:
        print(" ".join(command))
        return 0

    prepare_output_dir(output_path)
    subprocess.run(command, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
