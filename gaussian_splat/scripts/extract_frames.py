#!/usr/bin/env python3
import argparse
import subprocess
from pathlib import Path


def build_ffmpeg_command(input_video: Path, output_dir: Path, fps: int, max_frames: int, width: int) -> list[str]:
    return [
        "ffmpeg",
        "-y",
        "-i",
        str(input_video),
        "-vf",
        f"fps={fps},scale={width}:-1",
        "-frames:v",
        str(max_frames),
        "-an",
        "-f",
        "image2",
        str(output_dir / "frame_%05d.jpg"),
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract frames for Gaussian Splat reconstruction.")
    parser.add_argument("input_video", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--fps", type=int, default=2)
    parser.add_argument("--max-frames", type=int, default=120)
    parser.add_argument("--width", type=int, default=1600)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.input_video.is_file():
        raise SystemExit(f"input video not found: {args.input_video}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    cmd = build_ffmpeg_command(args.input_video, args.output_dir, args.fps, args.max_frames, args.width)
    if args.dry_run:
        print(" ".join(cmd))
        return 0
    subprocess.run(cmd, check=True)
    frame_count = len(list(args.output_dir.glob("frame_*.jpg")))
    print(f"frames={frame_count}")
    if frame_count < 8:
        raise SystemExit("frame count is lower than 8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
