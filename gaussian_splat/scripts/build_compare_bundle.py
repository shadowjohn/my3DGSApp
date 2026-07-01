#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode

import trimesh


VERDICT_TEMPLATE = """# Gaussian Splat vs Mesh Verdict

## Input

- Source:
- Job:
- Date:

## Numeric Summary

| Variant | File | Size | Count | Load Time | Notes |
| --- | --- | ---: | ---: | ---: | --- |
| Clean Splat | splat.clean.ply | | splats | | |
| Mesh GLB | cleaned_mesh.glb | | triangles | | |

## Visual Verdict

| Criterion | Gaussian Splat | Mesh GLB |
| --- | --- | --- |
| Photo realism | | |
| Geometry clarity | | |
| Close-view stability | | |
| Artifact amount | | |
| File size | | |
| Load speed | | |
| WebGIS suitability | | |
| Engineering usefulness | | |

## Conclusion

Gaussian Splat is better for:

-

Mesh / GLB is better for:

-

Recommended product usage:

-
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a comparison bundle for Gaussian Splat and extracted mesh outputs."
    )
    parser.add_argument("--job-dir", type=Path, required=True)
    parser.add_argument("--mesh-method", default="auto")
    parser.add_argument("--point-limit", type=int, default=0)
    parser.add_argument("--target-faces", type=int, default=100000)
    parser.add_argument("--skip-blender", action="store_true")
    return parser.parse_args()


def relative_upload_path(job_dir: Path, target: Path) -> str:
    uploads_dir = job_dir.parent
    try:
        return str(target.resolve().relative_to(uploads_dir.parent.resolve()))
    except ValueError:
        return str(target)


def viewer_url(viewer: str, src: str, extra: dict[str, Any] | None = None) -> str:
    params: dict[str, Any] = {"src": src}
    if extra:
        params.update(extra)
    return f"{viewer}?{urlencode(params)}"


def build_viewer_urls(
    job_dir: Path,
    splat_viewer: dict[str, Any],
    mesh_src: str,
) -> dict[str, str]:
    splat_params = {
        "rx": splat_viewer["rx"],
        "ry": splat_viewer["ry"],
        "rz": splat_viewer["rz"],
        "up": splat_viewer["up"],
        "distance": splat_viewer["distance"],
        "alpha": splat_viewer["alpha"],
        "splatScale": splat_viewer["splatScale"],
    }
    return {
        "splat": viewer_url("viewer_splat.php", splat_viewer["src"], splat_params),
        "mesh": viewer_url("viewer_mesh.html", mesh_src),
        "compare": f"viewer_compare_splat_mesh.html?job={quote(job_dir.name)}",
    }


def ensure_safe_compare_tree(path: Path) -> None:
    if path.is_symlink():
        raise RuntimeError(f"compare path is a symlink: {path}")
    if not path.exists():
        return
    for child in path.rglob("*"):
        if child.is_symlink():
            raise RuntimeError(f"compare tree contains symlink: {child}")


def ensure_not_symlink(path: Path) -> None:
    if path.is_symlink():
        raise RuntimeError(f"refusing to overwrite symlink: {path}")


def copy_if_present(source: Path, destination: Path) -> str | None:
    if not source.is_file():
        return None
    destination.parent.mkdir(parents=True, exist_ok=True)
    ensure_not_symlink(destination)
    shutil.copy2(source, destination)
    return str(destination)


def run_command(command: list[str]) -> None:
    result = subprocess.run(
        command,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "command failed: "
            + " ".join(command)
            + ("\nSTDOUT:\n" + result.stdout if result.stdout else "")
            + ("\nSTDERR:\n" + result.stderr if result.stderr else "")
        )


def load_trimesh(raw_mesh: Path) -> trimesh.Trimesh:
    loaded = trimesh.load(raw_mesh, process=False)
    if isinstance(loaded, trimesh.Scene):
        geometries = [
            geometry
            for geometry in loaded.geometry.values()
            if isinstance(geometry, trimesh.Trimesh)
        ]
        if not geometries:
            raise RuntimeError(f"mesh scene has no trimesh geometry: {raw_mesh}")
        return trimesh.util.concatenate(geometries)
    if not isinstance(loaded, trimesh.Trimesh):
        raise RuntimeError(f"unsupported mesh type: {type(loaded).__name__}")
    return loaded


def cleanup_trimesh(mesh: trimesh.Trimesh, target_faces: int) -> tuple[trimesh.Trimesh, dict[str, Any]]:
    original_vertex_count = int(len(mesh.vertices))
    original_face_count = int(len(mesh.faces))
    mesh = mesh.copy()

    if len(mesh.faces):
        if hasattr(mesh, "nondegenerate_faces"):
            mesh.update_faces(mesh.nondegenerate_faces())
        else:
            mesh.remove_degenerate_faces()
        if hasattr(mesh, "unique_faces"):
            mesh.update_faces(mesh.unique_faces())
        else:
            mesh.remove_duplicate_faces()

    mesh.remove_unreferenced_vertices()
    if len(mesh.faces):
        mesh.fix_normals()

    simplified = False
    simplification_error = None
    if target_faces > 0 and len(mesh.faces) > target_faces:
        try:
            mesh = mesh.simplify_quadric_decimation(face_count=target_faces)
            mesh.remove_unreferenced_vertices()
            simplified = True
        except Exception as exc:  # pragma: no cover - optional simplifier dependency varies.
            simplification_error = str(exc)

    stats: dict[str, Any] = {
        "exporter": "trimesh",
        "original_vertex_count": original_vertex_count,
        "original_face_count": original_face_count,
        "vertex_count": int(len(mesh.vertices)),
        "face_count": int(len(mesh.faces)),
        "target_faces": target_faces,
        "simplified": simplified,
        "removed_vertex_count": original_vertex_count - int(len(mesh.vertices)),
        "removed_face_count": original_face_count - int(len(mesh.faces)),
    }
    if simplification_error:
        stats["simplification_error"] = simplification_error
    return mesh, stats


def export_glb_with_trimesh(raw_mesh: Path, output: Path, target_faces: int = 100000) -> dict[str, Any]:
    output.parent.mkdir(parents=True, exist_ok=True)
    ensure_not_symlink(output)
    mesh, stats = cleanup_trimesh(load_trimesh(raw_mesh), target_faces)
    mesh.export(output)
    return stats


def make_public_readable(path: Path) -> None:
    ensure_safe_compare_tree(path)
    for child in path.rglob("*"):
        if child.is_dir():
            child.chmod(0o755)
        elif child.is_file():
            child.chmod(0o644)
    path.chmod(0o755)


def build_splat_viewer_json(job_dir: Path, clean_splat: Path, output: Path) -> dict[str, Any]:
    src = relative_upload_path(job_dir, clean_splat)
    data = {
        "type": "gaussian_splat",
        "src": src,
        "rx": 0,
        "ry": 0,
        "rz": 0,
        "up": "view",
        "upMode": "view",
        "distance": 12,
        "alpha": 40,
        "splatScale": 0.35,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    ensure_not_symlink(output)
    output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return data


def maybe_blender_cleanup(
    script_dir: Path,
    raw_mesh: Path,
    output: Path,
    skip_blender: bool,
    target_faces: int,
) -> bool:
    blender = shutil.which("blender")
    if skip_blender or not blender:
        return False
    ensure_not_symlink(output)

    result = subprocess.run(
        [
            blender,
            "-b",
            "--python",
            str(script_dir / "blender_mesh_cleanup.py"),
            "--",
            "--input",
            str(raw_mesh),
            "--output",
            str(output),
            "--target_faces",
            str(target_faces),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    return result.returncode == 0 and output.is_file()


def main() -> int:
    args = parse_args()
    try:
        job_dir = args.job_dir
        exports_dir = job_dir / "exports"
        compare_dir = job_dir / "compare"
        splat_dir = compare_dir / "splat"
        mesh_dir = compare_dir / "mesh"
        screenshots_dir = compare_dir / "screenshots"
        ensure_safe_compare_tree(compare_dir)
        for directory in (splat_dir, mesh_dir, screenshots_dir):
            directory.mkdir(parents=True, exist_ok=True)

        copied = {
            "splat": copy_if_present(exports_dir / "splat.ply", splat_dir / "splat.ply"),
            "splat_clean": copy_if_present(
                exports_dir / "splat.clean.ply",
                splat_dir / "splat.clean.ply",
            ),
            "splat_clean_viewer": copy_if_present(
                exports_dir / "splat.clean.viewer.json",
                splat_dir / "splat.clean.viewer.json",
            ),
        }

        clean_splat = exports_dir / "splat.clean.ply"
        if not clean_splat.is_file():
            raise RuntimeError(f"missing clean splat: {clean_splat}")

        splat_viewer_json = splat_dir / "viewer.json"
        splat_viewer = build_splat_viewer_json(job_dir, clean_splat, splat_viewer_json)

        script_dir = Path(__file__).resolve().parent
        point_cloud = mesh_dir / "point_cloud.ply"
        point_report = mesh_dir / "point_cloud_report.json"
        raw_mesh = mesh_dir / "raw_mesh.ply"
        mesh_report = mesh_dir / "mesh_report.json"
        cleaned_mesh = mesh_dir / "cleaned_mesh.glb"

        point_command = [
            sys.executable,
            str(script_dir / "splat_to_pointcloud.py"),
            "--input",
            str(clean_splat),
            "--output",
            str(point_cloud),
            "--report",
            str(point_report),
        ]
        if args.point_limit > 0:
            point_command.extend(["--limit", str(args.point_limit)])
        run_command(point_command)

        run_command(
            [
                sys.executable,
                str(script_dir / "pointcloud_to_mesh.py"),
                "--input",
                str(point_cloud),
                "--output",
                str(raw_mesh),
                "--report",
                str(mesh_report),
                "--method",
                args.mesh_method,
            ]
        )
        mesh_report_data = json.loads(mesh_report.read_text(encoding="utf-8"))
        mesh_method_used = mesh_report_data.get("method", args.mesh_method)

        used_blender = maybe_blender_cleanup(
            script_dir,
            raw_mesh,
            cleaned_mesh,
            args.skip_blender,
            args.target_faces,
        )
        glb_export: dict[str, Any] = {
            "exporter": "blender",
            "target_faces": args.target_faces,
        }
        if not used_blender:
            glb_export = export_glb_with_trimesh(
                raw_mesh,
                cleaned_mesh,
                target_faces=args.target_faces,
            )

        verdict = compare_dir / "verdict.md"
        ensure_not_symlink(verdict)
        verdict.write_text(VERDICT_TEMPLATE, encoding="utf-8")

        mesh_src = relative_upload_path(job_dir, cleaned_mesh)
        viewer_urls = build_viewer_urls(job_dir, splat_viewer, mesh_src)
        report = {
            "job_dir": str(job_dir),
            "compare_dir": str(compare_dir),
            "artifacts": {
                **copied,
                "splat_viewer_json": str(splat_viewer_json),
                "point_cloud": str(point_cloud),
                "point_cloud_report": str(point_report),
                "raw_mesh": str(raw_mesh),
                "mesh_report": str(mesh_report),
                "cleaned_mesh_glb": str(cleaned_mesh),
                "verdict": str(verdict),
                "screenshots_dir": str(screenshots_dir),
            },
            "splat_viewer": splat_viewer,
            "viewer_urls": viewer_urls,
            "mesh_method_requested": args.mesh_method,
            "mesh_method": mesh_method_used,
            "used_blender": used_blender,
            "glb_export": glb_export,
        }
        report_path = compare_dir / "compare_report.json"
        ensure_not_symlink(report_path)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        make_public_readable(compare_dir)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"build_compare_bundle.py: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
