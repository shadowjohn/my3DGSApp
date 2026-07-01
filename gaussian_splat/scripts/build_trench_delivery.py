#!/usr/bin/env python3
import argparse
import json
import shutil
from pathlib import Path
from typing import Any


DELIVERY_MODE = "gaussian_splat"
POLICY = "v1_clean_splat_as_trench_focus"


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def select_source_splat(exports_dir: Path) -> Path:
    clean_splat = exports_dir / "splat.clean.ply"
    if clean_splat.is_file():
        return clean_splat

    splat = exports_dir / "splat.ply"
    if splat.is_file():
        return splat

    raise FileNotFoundError(
        f"No source splat found at {clean_splat} or {splat}"
    )


def build_trench_delivery(job_dir: Path | str) -> dict[str, Any]:
    job_dir = Path(job_dir)
    exports_dir = job_dir / "exports"
    source_splat = select_source_splat(exports_dir)
    trench_splat = exports_dir / "splat.trench.ply"
    trench_viewer_meta = exports_dir / "splat.trench.viewer.json"

    metadata = load_json(exports_dir / "splat.clean.viewer.json")
    viewer = metadata.get("viewer", {})
    viewer = viewer.copy() if isinstance(viewer, dict) else {}
    viewer["focusMode"] = "trench"

    metadata["mode"] = "trench"
    metadata["delivery"] = {
        "deliveryMode": DELIVERY_MODE,
        "sourceSplat": str(source_splat),
        "policy": POLICY,
    }
    metadata["viewer"] = viewer

    exports_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_splat, trench_splat)
    trench_viewer_meta.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return {
        "delivery_mode": DELIVERY_MODE,
        "source_splat": str(source_splat),
        "trench_splat": str(trench_splat),
        "trench_viewer_meta": str(trench_viewer_meta),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build trench delivery export.")
    parser.add_argument("job_dir", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_trench_delivery(args.job_dir)
    print(result["trench_splat"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
