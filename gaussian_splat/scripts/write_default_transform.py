#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any


def build_transform(job_id: str, lng: float, lat: float, height: float) -> dict[str, Any]:
    return {
        "job_id": job_id,
        "source_type": "gaussian_splat",
        "origin": {
            "lng": lng,
            "lat": lat,
            "height": height,
        },
        "transform": {
            "heading": 0.0,
            "pitch": 0.0,
            "roll": 0.0,
            "scale": 1.0,
        },
        "camera": {
            "lng": None,
            "lat": None,
            "height": None,
            "heading": None,
            "pitch": None,
            "roll": None,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write default transform.json for a Gaussian Splat job.")
    parser.add_argument("job_id")
    parser.add_argument("output", type=Path)
    parser.add_argument("--lng", type=float, default=120.6647066)
    parser.add_argument("--lat", type=float, default=24.1504731)
    parser.add_argument("--height", type=float, default=0.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data = build_transform(args.job_id, args.lng, args.lat, args.height)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
