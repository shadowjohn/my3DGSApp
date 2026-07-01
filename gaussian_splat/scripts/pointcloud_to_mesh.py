#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import trimesh


class MeshError(ValueError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reconstruct a preview mesh from a colored point cloud."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--depth", type=int, default=9)
    parser.add_argument(
        "--method",
        choices=("auto", "open3d", "convex_hull"),
        default="auto",
    )
    parser.add_argument("--density-quantile", type=float, default=0.02)
    return parser.parse_args()


def read_ascii_pointcloud(path: Path) -> tuple[np.ndarray, np.ndarray | None]:
    lines = path.read_text(encoding="ascii", errors="strict").splitlines()
    if not lines or lines[0] != "ply":
        raise MeshError("not a PLY file")
    if "format ascii 1.0" not in lines[:4]:
        raise MeshError("only ASCII point-cloud PLY input is supported")

    vertex_count: int | None = None
    properties: list[str] = []
    in_vertex = False
    data_start: int | None = None
    for line_number, line in enumerate(lines):
        parts = line.split()
        if line == "end_header":
            data_start = line_number + 1
            break
        if len(parts) >= 3 and parts[0] == "element":
            in_vertex = parts[1] == "vertex"
            if in_vertex:
                try:
                    vertex_count = int(parts[2])
                except ValueError as exc:
                    raise MeshError(f"invalid vertex count: {parts[2]}") from exc
            continue
        if in_vertex and len(parts) == 3 and parts[0] == "property":
            properties.append(parts[2])

    if vertex_count is None:
        raise MeshError("element vertex line not found")
    if data_start is None:
        raise MeshError("PLY header must end with end_header")

    required = {"x", "y", "z"}
    missing = sorted(required - set(properties))
    if missing:
        raise MeshError(f"missing required properties: {', '.join(missing)}")

    indexes = {name: index for index, name in enumerate(properties)}
    points: list[list[float]] = []
    colors: list[list[int]] = []
    has_color = {"red", "green", "blue"} <= indexes.keys()

    for raw_line in lines[data_start : data_start + vertex_count]:
        if not raw_line.strip():
            continue
        parts = raw_line.split()
        points.append(
            [
                float(parts[indexes["x"]]),
                float(parts[indexes["y"]]),
                float(parts[indexes["z"]]),
            ]
        )
        if has_color:
            colors.append(
                [
                    int(round(float(parts[indexes["red"]]))),
                    int(round(float(parts[indexes["green"]]))),
                    int(round(float(parts[indexes["blue"]]))),
                    255,
                ]
            )

    point_array = np.asarray(points, dtype=np.float64)
    if len(point_array) != vertex_count:
        raise MeshError(f"expected {vertex_count} vertices, got {len(point_array)}")
    if len(point_array) < 4:
        raise MeshError("at least four points are required for mesh reconstruction")

    color_array = np.asarray(colors, dtype=np.uint8) if has_color else None
    return point_array, color_array


def nearest_colors(
    mesh_vertices: np.ndarray,
    source_points: np.ndarray,
    source_colors: np.ndarray | None,
) -> np.ndarray | None:
    if source_colors is None or len(source_colors) == 0:
        return None
    try:
        from scipy.spatial import cKDTree

        tree = cKDTree(source_points)
        _distances, indexes = tree.query(mesh_vertices, k=1)
    except Exception:
        distances = np.linalg.norm(mesh_vertices[:, None, :] - source_points[None, :, :], axis=2)
        indexes = np.argmin(distances, axis=1)
    return source_colors[indexes]


def convex_hull_mesh(points: np.ndarray, colors: np.ndarray | None) -> trimesh.Trimesh:
    point_cloud = trimesh.PointCloud(points, colors=colors)
    mesh = point_cloud.convex_hull
    vertex_colors = nearest_colors(np.asarray(mesh.vertices), points, colors)
    if vertex_colors is not None:
        mesh.visual.vertex_colors = vertex_colors
    return mesh


def open3d_mesh(
    points: np.ndarray,
    colors: np.ndarray | None,
    depth: int,
    density_quantile: float,
) -> Any:
    import open3d as o3d

    cloud = o3d.geometry.PointCloud()
    cloud.points = o3d.utility.Vector3dVector(points)
    if colors is not None:
        cloud.colors = o3d.utility.Vector3dVector(colors[:, :3].astype(np.float64) / 255.0)
    cloud.estimate_normals()
    cloud.orient_normals_consistent_tangent_plane(min(30, max(3, len(points) - 1)))

    mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
        cloud,
        depth=depth,
    )
    density_values = np.asarray(densities)
    if len(density_values):
        if len(density_values) == len(mesh.vertices):
            q = min(1.0, max(0.0, density_quantile))
            threshold = float(np.quantile(density_values, q))
            mesh.remove_vertices_by_mask(density_values < threshold)
    bbox = cloud.get_axis_aligned_bounding_box()
    mesh = mesh.crop(bbox)
    return mesh


def write_ascii_mesh(path: Path, vertices: np.ndarray, faces: np.ndarray, colors: np.ndarray | None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    has_colors = colors is not None and len(colors) == len(vertices)
    with path.open("w", encoding="ascii") as handle:
        handle.write("ply\n")
        handle.write("format ascii 1.0\n")
        handle.write(f"element vertex {len(vertices)}\n")
        handle.write("property float x\n")
        handle.write("property float y\n")
        handle.write("property float z\n")
        if has_colors:
            handle.write("property uchar red\n")
            handle.write("property uchar green\n")
            handle.write("property uchar blue\n")
            handle.write("property uchar alpha\n")
        handle.write(f"element face {len(faces)}\n")
        handle.write("property list uchar int vertex_indices\n")
        handle.write("end_header\n")
        for index, vertex in enumerate(vertices):
            if has_colors:
                color = colors[index]
                handle.write(
                    f"{vertex[0]:.9g} {vertex[1]:.9g} {vertex[2]:.9g} "
                    f"{int(color[0])} {int(color[1])} {int(color[2])} {int(color[3])}\n"
                )
            else:
                handle.write(f"{vertex[0]:.9g} {vertex[1]:.9g} {vertex[2]:.9g}\n")
        for face in faces:
            handle.write(f"3 {int(face[0])} {int(face[1])} {int(face[2])}\n")


def write_trimesh(path: Path, mesh: trimesh.Trimesh) -> tuple[int, int]:
    vertices = np.asarray(mesh.vertices, dtype=np.float64)
    faces = np.asarray(mesh.faces, dtype=np.int64)
    colors = None
    if getattr(mesh.visual, "kind", None) == "vertex":
        vertex_colors = np.asarray(mesh.visual.vertex_colors)
        if len(vertex_colors) == len(vertices):
            colors = vertex_colors.astype(np.uint8)
    write_ascii_mesh(path, vertices, faces, colors)
    return int(len(vertices)), int(len(faces))


def write_open3d(path: Path, mesh: Any) -> tuple[int, int]:
    vertices = np.asarray(mesh.vertices, dtype=np.float64)
    faces = np.asarray(mesh.triangles, dtype=np.int64)
    colors = None
    if mesh.has_vertex_colors():
        rgb = np.clip(np.asarray(mesh.vertex_colors) * 255.0, 0, 255).round().astype(np.uint8)
        colors = np.column_stack([rgb, np.full(len(rgb), 255, dtype=np.uint8)])
    write_ascii_mesh(path, vertices, faces, colors)
    return int(len(vertices)), int(len(faces))


def write_report(path: Path | None, report: dict[str, Any]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def write_convex_hull(
    output: Path,
    points: np.ndarray,
    colors: np.ndarray | None,
) -> tuple[int, int]:
    mesh = convex_hull_mesh(points, colors)
    return write_trimesh(output, mesh)


def main() -> int:
    args = parse_args()
    try:
        points, colors = read_ascii_pointcloud(args.input)
        fallback_reason = None
        method_used = args.method

        if args.method in {"auto", "open3d"}:
            try:
                mesh = open3d_mesh(points, colors, args.depth, args.density_quantile)
                vertex_count, face_count = write_open3d(args.output, mesh)
                method_used = "open3d"
            except (ModuleNotFoundError, ImportError):
                if args.method == "open3d":
                    print("pointcloud_to_mesh.py: Open3D is not installed", file=sys.stderr)
                    return 1
                fallback_reason = "Open3D is not installed"
                vertex_count, face_count = write_convex_hull(args.output, points, colors)
                method_used = "convex_hull"
            except Exception as exc:
                if args.method == "open3d":
                    print(f"pointcloud_to_mesh.py: Open3D reconstruction failed: {exc}", file=sys.stderr)
                    return 1
                fallback_reason = f"Open3D reconstruction failed: {exc}"
                vertex_count, face_count = write_convex_hull(args.output, points, colors)
                method_used = "convex_hull"
        else:
            vertex_count, face_count = write_convex_hull(args.output, points, colors)

        report = {
            "method": method_used,
            "vertex_count": vertex_count,
            "face_count": face_count,
            "output": str(args.output),
            "output_path": str(args.output),
            "depth": int(args.depth),
        }
        if fallback_reason:
            report["fallback_reason"] = fallback_reason
        write_report(args.report, report)
    except (OSError, MeshError, ValueError) as exc:
        print(f"pointcloud_to_mesh.py: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
