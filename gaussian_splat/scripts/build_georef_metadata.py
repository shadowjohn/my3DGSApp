#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


CONFIDENCE_FOR_MODE = {
    "none": "none",
    "exif": "low",
    "manual": "low",
    "gcp": "medium",
    "rtk": "high",
}


def confidence_for_mode(mode: str) -> str:
    try:
        return CONFIDENCE_FOR_MODE[mode]
    except KeyError as exc:
        raise ValueError(f"unsupported georef mode: {mode}") from exc


def build_georef_metadata(
    mode: str = "none",
    lat: float | None = None,
    lng: float | None = None,
    height: float | None = None,
    heading: float | None = None,
    scale: float | None = None,
    crs: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    return {
        "mode": mode,
        "crs": crs,
        "origin": {"lat": lat, "lng": lng, "height": height},
        "headingDegrees": heading,
        "scaleMetersPerUnit": scale,
        "controlPoints": [],
        "confidence": confidence_for_mode(mode),
        "notes": [note] if note else [],
    }


def write_georef_metadata(output: Path, **kwargs: Any) -> dict[str, Any]:
    data = build_georef_metadata(**kwargs)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    return data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build georeference metadata.")
    parser.add_argument("output", type=Path)
    parser.add_argument("--mode", default="none", choices=sorted(CONFIDENCE_FOR_MODE))
    parser.add_argument("--lat", type=float)
    parser.add_argument("--lng", type=float)
    parser.add_argument("--height", type=float)
    parser.add_argument("--heading", type=float)
    parser.add_argument("--scale", type=float)
    parser.add_argument("--crs")
    parser.add_argument("--note")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    write_georef_metadata(
        args.output,
        mode=args.mode,
        lat=args.lat,
        lng=args.lng,
        height=args.height,
        heading=args.heading,
        scale=args.scale,
        crs=args.crs,
        note=args.note,
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
