#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any


VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".avi"}
PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".JPG", ".JPEG", ".PNG", ".HEIC"}


def photo_records(directory: Path) -> list[dict[str, Any]]:
    photos = [
        path
        for path in sorted(directory.iterdir(), key=lambda item: item.name)
        if path.is_file() and path.suffix in PHOTO_EXTENSIONS
    ]
    return [
        {
            "filename": path.name,
            "path": str(path),
            "size_bytes": path.stat().st_size,
        }
        for path in photos
    ]


def build_input_manifest(source: Path) -> dict[str, Any]:
    source = Path(source)
    warnings: list[str] = []

    if source.is_file() and source.suffix.lower() in VIDEO_EXTENSIONS:
        return {
            "input_mode": "walk_video",
            "source": str(source),
            "video": {
                "filename": source.name,
                "path": str(source),
                "size_bytes": source.stat().st_size,
            },
            "photos": [],
            "warnings": warnings,
        }

    if source.is_dir():
        photos = photo_records(source)
        if len(photos) < 8:
            warnings.append("photo_set lower than 8 images")
        if not photos:
            warnings.append("photo_set has no supported images")
        return {
            "input_mode": "photo_set",
            "source": str(source),
            "video": None,
            "photos": photos,
            "warnings": warnings,
        }

    raise ValueError(f"unsupported outdoor input source: {source}")


def write_input_manifest(source: Path, output: Path) -> dict[str, Any]:
    manifest = build_input_manifest(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build outdoor trench input manifest.")
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    write_input_manifest(args.source, args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
