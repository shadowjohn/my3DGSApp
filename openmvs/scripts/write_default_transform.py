#!/usr/bin/env python3
"""Write default geolocation transform metadata."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job_id")
    parser.add_argument("output", type=Path)
    parser.add_argument("--lng", type=float, default=120.61022)
    parser.add_argument("--lat", type=float, default=24.110946)
    parser.add_argument("--height", type=float, default=0.0)
    parser.add_argument("--scale", type=float, default=1.0)
    args = parser.parse_args()

    data = {
        "job_id": str(args.job_id),
        "lon": args.lng,
        "lat": args.lat,
        "alt": args.height,
        "heading": 0.0,
        "pitch": 0.0,
        "roll": 0.0,
        "scale": args.scale,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
