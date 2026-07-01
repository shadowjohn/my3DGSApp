import json
import struct
import subprocess
from pathlib import Path

from scripts import generate_blender_pack as blender_pack_module
from scripts.generate_blender_pack import (
    generate_blender_pack,
    parse_images_bin,
    parse_points3d_bin,
)


ROOT = Path(__file__).resolve().parents[1]


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def write_points3d_bin(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fh:
        fh.write(struct.pack("<Q", 2))
        fh.write(struct.pack("<QdddBBBdQ", 10, 1.0, 2.0, 3.0, 255, 100, 50, 0.2, 1))
        fh.write(struct.pack("<ii", 7, 3))
        fh.write(struct.pack("<QdddBBBdQ", 11, -1.0, -2.0, -3.0, 10, 20, 30, 0.4, 0))


def write_images_bin(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fh:
        fh.write(struct.pack("<Q", 2))
        fh.write(struct.pack("<idddddddi", 7, 1.0, 0.0, 0.0, 0.0, -1.0, -2.0, -3.0, 1))
        fh.write(b"frame_00001.jpg\x00")
        fh.write(struct.pack("<Q", 0))
        fh.write(struct.pack("<idddddddi", 8, 1.0, 0.0, 0.0, 0.0, -4.0, -5.0, -6.0, 1))
        fh.write(b"frame_00002.jpg\x00")
        fh.write(struct.pack("<Q", 0))


def write_malformed_points3d_bin_with_huge_track(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fh:
        fh.write(struct.pack("<Q", 1))
        fh.write(struct.pack("<QdddBBBdQ", 10, 1.0, 2.0, 3.0, 255, 100, 50, 0.2, 2**63))


def write_malformed_images_bin_with_huge_points2d(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fh:
        fh.write(struct.pack("<Q", 1))
        fh.write(struct.pack("<idddddddi", 7, 1.0, 0.0, 0.0, 0.0, -1.0, -2.0, -3.0, 1))
        fh.write(b"frame_00001.jpg\x00")
        fh.write(struct.pack("<Q", 2**63))


def make_job(tmp_path: Path) -> Path:
    job = tmp_path / "selected-30k-hierarchical"
    (job / "processed" / "images").mkdir(parents=True)
    (job / "processed" / "images" / "frame_00001.jpg").write_bytes(b"jpg1")
    (job / "processed" / "images" / "frame_00002.jpg").write_bytes(b"jpg2")
    sparse = job / "processed" / "colmap" / "sparse" / "0"
    write_points3d_bin(sparse / "points3D.bin")
    write_images_bin(sparse / "images.bin")
    (job / "processed" / "colmap" / "database.db").write_bytes(b"sqlite")
    (job / "exports").mkdir()
    (job / "exports" / "splat.ply").write_text("ply\n", encoding="utf-8")
    (job / "exports" / "splat.clean.ply").write_text("ply\n", encoding="utf-8")
    write_json(job / "qa_report.json", {"registered_count": 2, "frame_count": 2, "quality_grade": "B"})
    write_json(job / "frame_quality_report.json", {"selected_count": 2, "candidate_count": 6})
    write_json(job / "processed" / "sfm_report.json", {"mapper": "hierarchical", "registered_ratio": 1.0})
    return job


def test_parse_points3d_bin_reads_colmap_sparse_points(tmp_path):
    points_path = tmp_path / "points3D.bin"
    write_points3d_bin(points_path)

    points = parse_points3d_bin(points_path)

    assert points == [
        {
            "id": 10,
            "x": 1.0,
            "y": 2.0,
            "z": 3.0,
            "red": 255,
            "green": 100,
            "blue": 50,
            "error": 0.2,
            "track_length": 1,
        },
        {
            "id": 11,
            "x": -1.0,
            "y": -2.0,
            "z": -3.0,
            "red": 10,
            "green": 20,
            "blue": 30,
            "error": 0.4,
            "track_length": 0,
        },
    ]


def test_parse_images_bin_outputs_camera_centers(tmp_path):
    images_path = tmp_path / "images.bin"
    write_images_bin(images_path)

    cameras = parse_images_bin(images_path)

    assert cameras == [
        {"id": 7, "name": "frame_00001.jpg", "camera_id": 1, "center": [1.0, 2.0, 3.0]},
        {"id": 8, "name": "frame_00002.jpg", "camera_id": 1, "center": [4.0, 5.0, 6.0]},
    ]


def test_parse_points3d_bin_stops_on_huge_track_length(tmp_path):
    points_path = tmp_path / "points3D.bin"
    write_malformed_points3d_bin_with_huge_track(points_path)

    assert parse_points3d_bin(points_path) == []


def test_parse_images_bin_stops_on_huge_points2d_count(tmp_path):
    images_path = tmp_path / "images.bin"
    write_malformed_images_bin_with_huge_points2d(images_path)

    assert parse_images_bin(images_path) == []


def test_generate_blender_pack_writes_manifest_assets_and_docs(tmp_path):
    job = make_job(tmp_path)

    pack_dir = generate_blender_pack(job)

    manifest = json.loads((pack_dir / "blender_qa_manifest.json").read_text(encoding="utf-8"))
    report = json.loads((pack_dir / "blender_qa_report.json").read_text(encoding="utf-8"))
    camera_path = json.loads((pack_dir / "import" / "camera_path.json").read_text(encoding="utf-8"))
    image_manifest = json.loads((pack_dir / "import" / "image_manifest.json").read_text(encoding="utf-8"))
    sparse_ply = (pack_dir / "import" / "sparse_points.ply").read_text(encoding="utf-8")
    preview_ply = (pack_dir / "proxies" / "sparse_points_preview.ply").read_text(encoding="utf-8")
    readme = (pack_dir / "README.md").read_text(encoding="utf-8")

    assert manifest["jobId"] == str(job)
    assert manifest["colmapSparseModel"] == "processed/colmap/sparse/0"
    assert manifest["database"] == "processed/colmap/database.db"
    assert manifest["splatClean"] == "exports/splat.clean.ply"
    assert manifest["blender"]["importer"] == "SBCV/Blender-Addon-Photogrammetry-Importer"
    assert manifest["proxyFrames"]["scales"] == [50, 25]
    assert (pack_dir / "import" / "colmap" / "points3D.bin").is_file()
    assert (pack_dir / "import" / "colmap" / "images.bin").is_file()
    assert report["cameraPath"]["registeredFrames"] == 2
    assert report["cameraPath"]["selectedFrames"] == 2
    assert report["cameraPath"]["registeredRatio"] == 1.0
    assert report["artifactDiagnosis"]["recommendedAction"] == "open Blender QA Pack and classify ROI/periphery artifacts"
    assert camera_path["cameras"][0]["center"] == [1.0, 2.0, 3.0]
    assert image_manifest["imageCount"] == 2
    assert "element vertex 2" in sparse_ply
    assert "255 100 50" in sparse_ply
    assert "element vertex 2" in preview_ply
    assert (pack_dir / "proxies" / "frames_50").is_dir()
    assert (pack_dir / "proxies" / "frames_25").is_dir()
    assert "File > Import > COLMAP" in readme


def test_generate_blender_pack_records_proxy_failures_when_ffmpeg_times_out(tmp_path, monkeypatch):
    job = make_job(tmp_path)

    def timeout_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs["timeout"])

    monkeypatch.setattr(blender_pack_module.shutil, "which", lambda name: "/usr/bin/ffmpeg")
    monkeypatch.setattr(blender_pack_module.subprocess, "run", timeout_run)

    pack_dir = generate_blender_pack(job)

    manifest = json.loads((pack_dir / "blender_qa_manifest.json").read_text(encoding="utf-8"))
    assert manifest["proxyFrames"]["status"] == "failed"
    assert manifest["proxyFrames"]["failed"] == {"50": 2, "25": 2}
    assert (pack_dir / "proxies" / "frames_50").is_dir()
    assert (pack_dir / "proxies" / "frames_25").is_dir()


def test_generate_blender_pack_cli_prints_output_path(tmp_path):
    job = make_job(tmp_path)

    result = subprocess.run(
        [
            "python3",
            str(ROOT / "scripts" / "generate_blender_pack.py"),
            str(job),
        ],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    assert str(job / "blender-pack") in result.stdout
    assert (job / "blender-pack" / "blender_qa_manifest.json").is_file()
