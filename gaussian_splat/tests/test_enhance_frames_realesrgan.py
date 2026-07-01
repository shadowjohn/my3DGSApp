import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "enhance_frames_realesrgan.py"


def load_adapter():
    if not SCRIPT_PATH.exists():
        pytest.fail(f"missing adapter script: {SCRIPT_PATH}")
    spec = importlib.util.spec_from_file_location("enhance_frames_realesrgan", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def make_executable(path: Path) -> Path:
    path.write_text("#!/usr/bin/env bash\n")
    path.chmod(0o755)
    return path


def test_build_realesrgan_command_uses_ncnn_vulkan_png_output():
    adapter = load_adapter()

    command = adapter.build_realesrgan_command(
        "/opt/realesrgan-ncnn-vulkan",
        "/tmp/job/images",
        "/tmp/job/enhanced_images",
        2,
        "realesrgan-x4plus",
    )

    assert command == [
        "/opt/realesrgan-ncnn-vulkan",
        "-i",
        "/tmp/job/images",
        "-o",
        "/tmp/job/enhanced_images",
        "-s",
        "2",
        "-n",
        "realesrgan-x4plus",
        "-f",
        "png",
    ]


def test_dry_run_prints_command_without_creating_output_dir(tmp_path, capsys):
    adapter = load_adapter()
    binary = make_executable(tmp_path / "realesrgan-ncnn-vulkan")
    input_dir = tmp_path / "images"
    output_dir = tmp_path / "enhanced_images"
    input_dir.mkdir()

    result = adapter.main(
        [
            str(input_dir),
            str(output_dir),
            "--binary",
            str(binary),
            "--scale",
            "2",
            "--model-name",
            "realesrgan-x4plus",
            "--dry-run",
        ]
    )

    assert result == 0
    assert capsys.readouterr().out.strip() == " ".join(
        adapter.build_realesrgan_command(
            str(binary),
            str(input_dir),
            str(output_dir),
            2,
            "realesrgan-x4plus",
        )
    )
    assert not output_dir.exists()


@pytest.mark.parametrize(
    ("binary_factory", "expected_message"),
    [
        (lambda tmp_path: tmp_path / "missing-binary", "binary not found"),
        (
            lambda tmp_path: (tmp_path / "non-executable-binary"),
            "binary is not executable",
        ),
        (lambda tmp_path: (tmp_path / "binary-directory"), "binary is not a file"),
    ],
)
def test_binary_validation_fails_cleanly(
    tmp_path, capsys, binary_factory, expected_message
):
    adapter = load_adapter()
    input_dir = tmp_path / "images"
    output_dir = tmp_path / "enhanced_images"
    input_dir.mkdir()
    binary = binary_factory(tmp_path)
    if binary.name == "non-executable-binary":
        binary.write_text("#!/usr/bin/env bash\n")
        binary.chmod(0o644)
    elif binary.name == "binary-directory":
        binary.mkdir()

    result = adapter.main([str(input_dir), str(output_dir), "--binary", str(binary)])

    captured = capsys.readouterr()
    assert result == 1
    assert expected_message in captured.err
    assert "Traceback" not in captured.err
    assert not output_dir.exists()


def test_input_path_that_is_file_fails_cleanly(tmp_path, capsys):
    adapter = load_adapter()
    binary = make_executable(tmp_path / "realesrgan-ncnn-vulkan")
    input_file = tmp_path / "images"
    output_dir = tmp_path / "enhanced_images"
    input_file.write_text("not a directory")

    result = adapter.main([str(input_file), str(output_dir), "--binary", str(binary)])

    captured = capsys.readouterr()
    assert result == 1
    assert "input_dir is not a directory" in captured.err
    assert "Traceback" not in captured.err
    assert not output_dir.exists()


def test_stale_generated_frames_are_cleared_before_subprocess_run(
    tmp_path, monkeypatch
):
    adapter = load_adapter()
    binary = make_executable(tmp_path / "realesrgan-ncnn-vulkan")
    input_dir = tmp_path / "images"
    output_dir = tmp_path / "enhanced_images"
    input_dir.mkdir()
    output_dir.mkdir()
    stale_frame = output_dir / "frame_00001.png"
    stale_frame.write_text("stale")
    calls = []

    def fake_run(command, check):
        calls.append((command, check))

    monkeypatch.setattr(adapter.subprocess, "run", fake_run)

    result = adapter.main([str(input_dir), str(output_dir), "--binary", str(binary)])

    assert result == 0
    assert not stale_frame.exists()
    assert calls == [
        (
            adapter.build_realesrgan_command(
                str(binary),
                str(input_dir),
                str(output_dir),
                adapter.DEFAULT_SCALE,
                adapter.DEFAULT_MODEL_NAME,
            ),
            True,
        )
    ]


@pytest.mark.parametrize("unsafe_name", ["keep.txt", "frame_reference.png"])
def test_unrelated_output_files_fail_and_are_left_untouched(
    tmp_path, monkeypatch, capsys, unsafe_name
):
    adapter = load_adapter()
    binary = make_executable(tmp_path / "realesrgan-ncnn-vulkan")
    input_dir = tmp_path / "images"
    output_dir = tmp_path / "enhanced_images"
    input_dir.mkdir()
    output_dir.mkdir()
    unsafe_file = output_dir / unsafe_name
    unsafe_file.write_text("keep")

    def fail_run(command, check):
        raise AssertionError("subprocess.run should not be called")

    monkeypatch.setattr(adapter.subprocess, "run", fail_run)

    result = adapter.main([str(input_dir), str(output_dir), "--binary", str(binary)])

    captured = capsys.readouterr()
    assert result == 1
    assert "output_dir contains unrelated file" in captured.err
    assert unsafe_file.read_text() == "keep"
