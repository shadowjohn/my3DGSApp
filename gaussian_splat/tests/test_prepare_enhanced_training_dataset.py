import importlib.util
import json
from pathlib import Path
import shutil

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "prepare_enhanced_training_dataset.py"


def load_adapter():
    if not SCRIPT_PATH.exists():
        pytest.fail(f"missing adapter script: {SCRIPT_PATH}")
    spec = importlib.util.spec_from_file_location("prepare_enhanced_training_dataset", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def make_processed_dataset(root: Path):
    processed = root / "processed"
    images = processed / "images"
    images_2 = processed / "images_2"
    images.mkdir(parents=True)
    images_2.mkdir()
    (images / "frame_00001.jpg").write_bytes(b"original")
    (images_2 / "frame_00001.jpg").write_bytes(b"downscaled")
    (processed / "transforms.json").write_text(
        json.dumps({"frames": [{"file_path": "images/frame_00001.jpg"}]}),
        encoding="utf-8",
    )
    (processed / "colmap").mkdir()
    (processed / "colmap" / "database.db").write_text("pose-db", encoding="utf-8")
    return processed


def test_prepares_training_dataset_without_mutating_colmap_processed_dir(tmp_path, monkeypatch):
    adapter = load_adapter()
    processed = make_processed_dataset(tmp_path)
    enhanced = tmp_path / "enhanced_images"
    enhanced.mkdir()
    (enhanced / "frame_00001.png").write_bytes(b"enhanced")
    output = tmp_path / "processed_enhanced"
    calls = []

    def fake_image_size(path):
        calls.append(("size", Path(path).name))
        return 1600, 900

    def fake_run(command, check):
        calls.append(("run", command, check))
        output_path = Path(command[-1])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"converted")

    monkeypatch.setattr(adapter, "image_size", fake_image_size)
    monkeypatch.setattr(adapter.subprocess, "run", fake_run)

    result = adapter.main([str(processed), str(enhanced), str(output)])

    assert result == 0
    assert (processed / "images" / "frame_00001.jpg").read_bytes() == b"original"
    assert (processed / "images_2" / "frame_00001.jpg").exists()
    assert (output / "transforms.json").exists()
    assert (output / "colmap" / "database.db").read_text(encoding="utf-8") == "pose-db"
    assert (output / "images" / "frame_00001.jpg").read_bytes() == b"converted"
    assert not (output / "images_2").exists()
    assert calls == [
        ("size", "frame_00001.jpg"),
        (
            "run",
            adapter.build_ffmpeg_convert_command(
                enhanced / "frame_00001.png",
                output / "images" / "frame_00001.jpg",
                1600,
                900,
            ),
            True,
        ),
    ]


def test_missing_enhanced_frame_fails_cleanly(tmp_path, capsys):
    adapter = load_adapter()
    processed = make_processed_dataset(tmp_path)
    enhanced = tmp_path / "enhanced_images"
    enhanced.mkdir()
    output = tmp_path / "processed_enhanced"

    result = adapter.main([str(processed), str(enhanced), str(output)])

    captured = capsys.readouterr()
    assert result == 1
    assert "enhanced frame missing" in captured.err
    assert not output.exists()


def test_existing_output_dir_is_replaced(tmp_path, monkeypatch):
    adapter = load_adapter()
    processed = make_processed_dataset(tmp_path)
    enhanced = tmp_path / "enhanced_images"
    enhanced.mkdir()
    (enhanced / "frame_00001.png").write_bytes(b"enhanced")
    output = tmp_path / "processed_enhanced"
    output.mkdir()
    stale = output / "stale.txt"
    stale.write_text("remove me", encoding="utf-8")

    monkeypatch.setattr(adapter, "image_size", lambda path: (800, 450))

    def fake_run(command, check):
        Path(command[-1]).write_bytes(b"converted")

    monkeypatch.setattr(adapter.subprocess, "run", fake_run)

    result = adapter.main([str(processed), str(enhanced), str(output)])

    assert result == 0
    assert not stale.exists()
    assert (output / "images" / "frame_00001.jpg").exists()
