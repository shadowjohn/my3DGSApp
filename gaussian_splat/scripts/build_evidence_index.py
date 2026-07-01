#!/usr/bin/env python3
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


VERSION = "1.0.3"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n")


def read_points(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def finite_vector3(value) -> list[float] | None:
    if not isinstance(value, list) or len(value) < 3:
        return None
    try:
        return [float(value[0]), float(value[1]), float(value[2])]
    except (TypeError, ValueError):
        return None


def camera_vector(camera: dict) -> list[float] | None:
    return finite_vector3(camera.get("position")) or finite_vector3(camera.get("center")) or finite_vector3(camera.get("tvec"))


def public_point(point: dict) -> dict:
    return {
        "point3d_id": point.get("point3d_id"),
        "xyz": point.get("xyz", []),
        "rgb": point.get("rgb", []),
        "error": point.get("error"),
    }


def point_camera_ids(point: dict) -> list[int]:
    ids = []
    for item in point.get("track", []):
        try:
            ids.append(int(item["image_id"]))
        except (KeyError, TypeError, ValueError):
            pass
    return sorted(set(ids))


def bbox_for(points: list[dict]) -> list[float]:
    coords = [finite_vector3(point.get("xyz")) for point in points]
    coords = [coord for coord in coords if coord]
    if not coords:
        return [0, 0, 0, 0, 0, 0]
    xs, ys, zs = zip(*coords)
    return [min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)]


def grid_coord(value: float, lo: float, hi: float, size: int) -> int:
    if hi == lo:
        return 0
    return min(size - 1, max(0, int((value - lo) / (hi - lo) * size)))


def tile_id_for_xyz(xyz: list[float], grid: dict) -> str:
    ix = grid_coord(xyz[0], grid["min_x"], grid["max_x"], grid["size"])
    iz = grid_coord(xyz[2], grid["min_z"], grid["max_z"], grid["size"])
    return f"{ix}_{iz}"


def build_spatial_index(points: list[dict], camera_count: int, grid_size: int, sample_limit: int) -> dict:
    bbox = bbox_for(points)
    grid = {"type": "xz", "size": max(1, int(grid_size)), "min_x": bbox[0], "max_x": bbox[3], "min_z": bbox[2], "max_z": bbox[5]}
    buckets: dict[str, list[dict]] = {}
    for point in points:
        xyz = finite_vector3(point.get("xyz"))
        if not xyz:
            continue
        buckets.setdefault(tile_id_for_xyz(xyz, grid), []).append(point)

    tiles = []
    for tile_id, tile_points in sorted(buckets.items()):
        visible_ids = sorted({image_id for point in tile_points for image_id in point_camera_ids(point)})
        tiles.append({
            "tile_id": tile_id,
            "bbox": bbox_for(tile_points),
            "point_count": len(tile_points),
            "sample_sparse_points": [public_point(point) for point in tile_points[:sample_limit]],
            "visible_camera_ids": visible_ids,
            "coverage_score": round(len(visible_ids) / camera_count, 3) if camera_count else 0,
        })
    # ponytail: uniform x/z grid is the first cheap index; switch to R-tree if tile counts get large.
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "spatial_index_type": "grid",
        "grid": grid,
        "bbox": bbox,
        "tile_count": len(tiles),
        "tiles": tiles,
    }


def query_spatial_tile(index: dict, xyz: list[float]) -> dict:
    tile_id = tile_id_for_xyz([float(xyz[0]), float(xyz[1]), float(xyz[2])], index["grid"])
    for tile in index.get("tiles", []):
        if tile.get("tile_id") == tile_id:
            return tile
    return {}


def build_camera_path(cameras: list[dict]) -> dict:
    rows = []
    for camera in cameras:
        vector = camera_vector(camera)
        if vector:
            rows.append({"image_id": camera.get("image_id"), "name": camera.get("name"), "position": vector})
    return {"schema_version": "1.0", "camera_count": len(rows), "cameras": rows}


def build_evidence_index(evidence_dir: Path, grid_size: int = 8, sample_limit: int = 16) -> Path:
    cameras_path = evidence_dir / "cameras.json"
    tracks_path = evidence_dir / "points3d_tracks.jsonl"
    cameras = read_json(cameras_path).get("cameras", [])
    points = read_points(tracks_path)

    write_json(evidence_dir / "camera_path.json", build_camera_path(cameras))
    write_json(evidence_dir / "lod_sparse_points.json", {
        "schema_version": "1.0",
        "point_count": len(points),
        "points": [public_point(point) for point in points[: max(1, sample_limit * max(1, grid_size))]],
    })
    write_json(evidence_dir / "spatial_index.json", build_spatial_index(points, len(cameras), grid_size, sample_limit))

    manifest = {
        "schema_version": "1.0",
        "version": VERSION,
        "job_id": evidence_dir.parent.name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "coordinate_system": {"base": "colmap_world", "viewer_transform": None},
        "camera_count": len(cameras),
        "sparse_point_count": len(points),
        "cameras_path": "cameras.json",
        "camera_path_path": "camera_path.json",
        "spatial_index_type": "grid",
        "spatial_index_path": "spatial_index.json",
        "lod_sparse_points_path": "lod_sparse_points.json",
        "coverage_query_ready": bool(points),
        "assets": {
            "cameras": "cameras.json",
            "camera_path": "camera_path.json",
            "spatial_index": "spatial_index.json",
            "lod_sparse_points": "lod_sparse_points.json",
        },
        "capabilities": {
            "camera_cones": True,
            "coverage_summary": (evidence_dir / "coverage_summary.json").is_file(),
            "click_evidence_query": bool(points),
            "cross_engine_validation": False,
        },
    }
    if (evidence_dir / "coverage_summary.json").is_file():
        manifest["assets"]["coverage_summary"] = "coverage_summary.json"

    manifest_path = evidence_dir / "evidence_manifest.json"
    write_json(manifest_path, manifest)
    return manifest_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build lightweight viewer evidence index from SfM evidence files.")
    parser.add_argument("evidence_dir", type=Path)
    parser.add_argument("--grid-size", type=int, default=8)
    parser.add_argument("--sample-limit", type=int, default=16)
    args = parser.parse_args(argv)

    print(build_evidence_index(args.evidence_dir, args.grid_size, args.sample_limit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
