import json
from pathlib import Path

from scripts.outdoor_intake import build_input_manifest, write_input_manifest


def test_build_input_manifest_detects_video(tmp_path):
    video = tmp_path / "input.mp4"
    video.write_bytes(b"fake-video")

    manifest = build_input_manifest(video)

    assert manifest["input_mode"] == "walk_video"
    assert manifest["source"] == str(video)
    assert manifest["video"]["filename"] == "input.mp4"
    assert manifest["photos"] == []
    assert manifest["warnings"] == []


def test_build_input_manifest_detects_photo_set(tmp_path):
    images = tmp_path / "images"
    images.mkdir()
    for index in range(8):
        (images / f"image-{index:02d}.jpg").write_bytes(b"image")
    (images / "ignore.txt").write_text("ignore")

    manifest = build_input_manifest(images)

    assert manifest["input_mode"] == "photo_set"
    assert manifest["source"] == str(images)
    assert manifest["video"] is None
    assert [photo["filename"] for photo in manifest["photos"]] == [
        f"image-{index:02d}.jpg" for index in range(8)
    ]
    assert manifest["warnings"] == []


def test_build_input_manifest_warns_for_sparse_photo_set(tmp_path):
    images = tmp_path / "images"
    images.mkdir()
    (images / "one.jpg").write_bytes(b"one")

    manifest = build_input_manifest(images)

    assert manifest["input_mode"] == "photo_set"
    assert "photo_set lower than 8 images" in manifest["warnings"]


def test_write_input_manifest_creates_json(tmp_path):
    video = tmp_path / "input.mp4"
    video.write_bytes(b"fake-video")
    output = tmp_path / "job" / "input_manifest.json"

    write_input_manifest(video, output)

    data = json.loads(output.read_text())
    assert data["input_mode"] == "walk_video"
    assert data["source"] == str(video)
