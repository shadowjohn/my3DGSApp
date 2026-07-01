#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path


VERSION = "1.0.3"
MODEL_FILES = ("cameras.txt", "images.txt", "points3D.txt")


class ColmapEvidenceError(Exception):
    pass


def non_comment_lines(path: Path) -> list[tuple[int, str]]:
    return [
        (line_no, line.strip())
        for line_no, line in enumerate(path.read_text().splitlines(), start=1)
        if line.strip() and not line.lstrip().startswith("#")
    ]


def image_lines(path: Path) -> list[tuple[int, str]]:
    return [
        (line_no, line.strip())
        for line_no, line in enumerate(path.read_text().splitlines(), start=1)
        if not line.lstrip().startswith("#")
    ]


def parse_float(token: str, path: Path, line_no: int) -> float:
    try:
        return float(token)
    except ValueError as exc:
        raise ColmapEvidenceError(f"Malformed {path.name} line {line_no}: expected number") from exc


def parse_int(token: str, path: Path, line_no: int) -> int:
    try:
        return int(token)
    except ValueError as exc:
        raise ColmapEvidenceError(f"Malformed {path.name} line {line_no}: expected integer") from exc


def require_model_dir(colmap_dir: Path) -> Path:
    if not colmap_dir.is_dir():
        raise ColmapEvidenceError(f"COLMAP directory not found: {colmap_dir}")

    direct_missing = [name for name in MODEL_FILES if not (colmap_dir / name).is_file()]
    if not direct_missing:
        return colmap_dir

    sparse0 = colmap_dir / "sparse" / "0"
    sparse_missing = [name for name in MODEL_FILES if not (sparse0 / name).is_file()]
    if not sparse_missing:
        return sparse0

    candidate = sparse0 if sparse0.exists() and not any((colmap_dir / name).is_file() for name in MODEL_FILES) else colmap_dir
    missing = sparse_missing if candidate == sparse0 else direct_missing
    raise ColmapEvidenceError(f"Missing COLMAP text file(s) in {candidate}: {', '.join(missing)}")


def parse_cameras(path: Path) -> dict[str, dict]:
    cameras = {}
    for line_no, line in non_comment_lines(path):
        parts = line.split()
        if len(parts) < 5:
            raise ColmapEvidenceError(f"Malformed {path.name} line {line_no}: expected CAMERA_ID MODEL WIDTH HEIGHT PARAMS")
        camera_id = parse_int(parts[0], path, line_no)
        cameras[str(camera_id)] = {
            "model": parts[1],
            "width": parse_int(parts[2], path, line_no),
            "height": parse_int(parts[3], path, line_no),
            "params": [parse_float(token, path, line_no) for token in parts[4:]],
        }
    return cameras


def parse_images(path: Path) -> list[dict]:
    lines = image_lines(path)
    if len(lines) % 2:
        line_no = lines[-1][0]
        raise ColmapEvidenceError(f"Malformed {path.name} line {line_no}: expected 2D observations line")

    images = []
    for i in range(0, len(lines), 2):
        line_no, line = lines[i]
        points2d_line_no, points2d_line = lines[i + 1]
        parts = line.split(maxsplit=9)
        if len(parts) != 10:
            raise ColmapEvidenceError(f"Malformed {path.name} line {line_no}: expected IMAGE_ID QW QX QY QZ TX TY TZ CAMERA_ID NAME")
        validate_points2d(points2d_line, path, points2d_line_no)
        images.append(
            {
                "image_id": parse_int(parts[0], path, line_no),
                "camera_id": parse_int(parts[8], path, line_no),
                "name": parts[9],
                "qvec": [parse_float(token, path, line_no) for token in parts[1:5]],
                "tvec": [parse_float(token, path, line_no) for token in parts[5:8]],
            }
        )
    return images


def validate_points2d(line: str, path: Path, line_no: int) -> None:
    parts = line.split()
    if not parts:
        return
    if len(parts) % 3:
        raise ColmapEvidenceError(f"Malformed {path.name} line {line_no}: expected POINTS2D triples")
    for i in range(0, len(parts), 3):
        parse_float(parts[i], path, line_no)
        parse_float(parts[i + 1], path, line_no)
        parse_int(parts[i + 2], path, line_no)


def parse_points3d(path: Path) -> list[dict]:
    points = []
    for line_no, line in non_comment_lines(path):
        parts = line.split()
        if len(parts) < 8 or len(parts[8:]) % 2:
            raise ColmapEvidenceError(f"Malformed {path.name} line {line_no}: expected POINT3D_ID X Y Z R G B ERROR TRACK pairs")
        track_tokens = parts[8:]
        points.append(
            {
                "point3d_id": parse_int(parts[0], path, line_no),
                "xyz": [parse_float(token, path, line_no) for token in parts[1:4]],
                "rgb": [parse_int(token, path, line_no) for token in parts[4:7]],
                "error": parse_float(parts[7], path, line_no),
                "track": [
                    {
                        "image_id": parse_int(track_tokens[i], path, line_no),
                        "point2d_idx": parse_int(track_tokens[i + 1], path, line_no),
                    }
                    for i in range(0, len(track_tokens), 2)
                ],
            }
        )
    return points


def stats(values: list[float | int]) -> dict:
    if not values:
        return {"min": 0, "max": 0, "avg": 0}
    return {"min": min(values), "max": max(values), "avg": round(sum(values) / len(values), 2)}


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n")


def build_sfm_evidence(colmap_dir: Path, output_dir: Path | None = None) -> Path:
    model_dir = require_model_dir(colmap_dir)
    output_dir = output_dir or colmap_dir / "evidence"
    output_dir.mkdir(parents=True, exist_ok=True)

    cameras = parse_cameras(model_dir / "cameras.txt")
    images = parse_images(model_dir / "images.txt")
    points = parse_points3d(model_dir / "points3D.txt")

    coordinate_system = {"base": "colmap_world"}
    write_json(
        output_dir / "cameras.json",
        {
            "version": VERSION,
            "coordinate_system": coordinate_system,
            "cameras": images,
            "camera_models": cameras,
        },
    )

    with (output_dir / "points3d_tracks.jsonl").open("w") as out:
        for point in points:
            out.write(json.dumps(point) + "\n")

    track_lengths = [len(point["track"]) for point in points]
    errors = [point["error"] for point in points]
    write_json(
        output_dir / "coverage_summary.json",
        {
            "version": VERSION,
            "coordinate_system": coordinate_system,
            "camera_count": len(images),
            "sparse_point_count": len(points),
            "track_length": stats(track_lengths),
            "reprojection_error": stats(errors),
            "visible_camera_count": stats(track_lengths),
        },
    )
    return output_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build minimal SfM evidence from COLMAP text exports.")
    parser.add_argument("colmap_dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)

    try:
        output_dir = build_sfm_evidence(args.colmap_dir, args.output_dir)
    except ColmapEvidenceError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote SfM evidence to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
