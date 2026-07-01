#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path


def import_hloc():
    try:
        import pycolmap
        import torch
        from hloc import extract_features, match_features, reconstruction
    except ModuleNotFoundError as exc:
        print(
            "hloc_lightglue requires hloc, pycolmap, and torch in GS_CONDA_ENV "
            f"(missing: {exc.name})",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    return pycolmap, torch, extract_features, match_features, reconstruction


def list_images(images_dir: Path) -> list[str]:
    suffixes = {".jpg", ".jpeg", ".png"}
    names = [
        path.relative_to(images_dir).as_posix()
        for path in images_dir.iterdir()
        if path.is_file() and path.suffix.lower() in suffixes
    ]
    return sorted(names)


def write_pairs(names: list[str], pairs_path: Path, window: int) -> int:
    if len(names) < 2:
        raise SystemExit(f"hloc_lightglue needs at least 2 images: {len(names)}")

    rows: list[str] = []
    for index, name in enumerate(names):
        end = len(names) if window == 0 else min(len(names), index + window + 1)
        for other in names[index + 1 : end]:
            rows.append(f"{name} {other}\n")

    if not rows:
        raise SystemExit("hloc_lightglue generated no image pairs")

    pairs_path.write_text("".join(rows))
    return len(rows)


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: run_hloc_reconstruction.py images_dir sparse_root",
            file=sys.stderr,
        )
        return 2

    images_dir = Path(sys.argv[1])
    sparse_root = Path(sys.argv[2])
    outputs_dir = sparse_root / "hloc"
    pairs_path = outputs_dir / "pairs.txt"
    window = int(os.environ.get("GS_HLOC_MATCH_WINDOW", "0"))
    if window < 0:
        print("GS_HLOC_MATCH_WINDOW must be 0 or a positive integer", file=sys.stderr)
        return 2

    pycolmap, torch, extract_features, match_features, reconstruction = import_hloc()

    sparse_root.mkdir(parents=True, exist_ok=True)
    outputs_dir.mkdir(parents=True, exist_ok=True)

    names = list_images(images_dir)
    pair_count = write_pairs(names, pairs_path, window)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(
        f"[hloc] device={device} images={len(names)} pairs={pair_count} "
        f"window={window or 'all'}",
        file=sys.stderr,
    )

    feature_conf = extract_features.confs["superpoint_max"]
    matcher_conf = match_features.confs["superpoint+lightglue"]
    features = extract_features.main(
        feature_conf,
        images_dir,
        outputs_dir,
        image_list=names,
        overwrite=True,
    )
    matches = match_features.main(
        matcher_conf,
        pairs_path,
        feature_conf["output"],
        outputs_dir,
        overwrite=True,
    )

    model = reconstruction.main(
        sparse_root,
        images_dir,
        pairs_path,
        features,
        matches,
        camera_mode=pycolmap.CameraMode.SINGLE,
        image_list=names,
        image_options={"camera_model": "OPENCV"},
        verbose=True,
    )
    if model is None:
        print("hloc_lightglue reconstruction failed: no COLMAP model", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
