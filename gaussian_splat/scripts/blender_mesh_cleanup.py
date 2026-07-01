#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    if argv is None:
        argv = sys.argv
    blender_args = argv
    if "--" in argv:
        blender_args = argv[argv.index("--") + 1 :]
    else:
        blender_args = argv[1:]

    parser = argparse.ArgumentParser(
        description="Clean up a mesh in Blender and export it as GLB."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target_faces", type=int, default=100000)
    return parser.parse_args(blender_args)


def import_mesh(bpy, path: Path) -> None:
    suffix = path.suffix.lower()
    if suffix == ".ply":
        if hasattr(bpy.ops.wm, "ply_import"):
            bpy.ops.wm.ply_import(filepath=str(path))
        else:
            bpy.ops.import_mesh.ply(filepath=str(path))
    elif suffix == ".obj":
        if hasattr(bpy.ops.wm, "obj_import"):
            bpy.ops.wm.obj_import(filepath=str(path))
        else:
            bpy.ops.import_scene.obj(filepath=str(path))
    else:
        raise ValueError(f"unsupported input format: {suffix}")


def mesh_objects(bpy):
    return [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]


def cleanup_object(bpy, obj, target_faces: int) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    try:
        bpy.ops.mesh.delete_loose()
    except Exception:
        pass
    bpy.ops.object.mode_set(mode="OBJECT")

    face_count = len(obj.data.polygons)
    if target_faces > 0 and face_count > target_faces:
        modifier = obj.modifiers.new("Target face decimation", "DECIMATE")
        modifier.ratio = max(0.01, min(1.0, target_faces / face_count))
        bpy.ops.object.modifier_apply(modifier=modifier.name)

    for polygon in obj.data.polygons:
        polygon.use_smooth = True


def main() -> int:
    args = parse_args()
    try:
        import bpy

        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete()
        import_mesh(bpy, args.input)

        objects = mesh_objects(bpy)
        if not objects:
            raise ValueError("no mesh objects were imported")

        for obj in objects:
            cleanup_object(bpy, obj, args.target_faces)

        args.output.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.object.select_all(action="DESELECT")
        for obj in objects:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = objects[0]
        bpy.ops.export_scene.gltf(
            filepath=str(args.output),
            export_format="GLB",
            use_selection=True,
        )
    except Exception as exc:
        print(f"blender_mesh_cleanup.py: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
