from pathlib import Path
from scripts.extract_frames import build_ffmpeg_command


def test_build_ffmpeg_command_uses_mvp_defaults(tmp_path):
    input_video = Path("/tmp/input.mp4")
    output_dir = tmp_path / "images"
    cmd = build_ffmpeg_command(input_video, output_dir, fps=2, max_frames=120, width=1600)
    assert cmd == [
        "ffmpeg",
        "-y",
        "-i",
        "/tmp/input.mp4",
        "-vf",
        "fps=2,scale=1600:-1",
        "-frames:v",
        "120",
        "-an",
        "-f",
        "image2",
        str(output_dir / "frame_%05d.jpg"),
    ]


def test_build_ffmpeg_command_allows_small_scene_settings(tmp_path):
    cmd = build_ffmpeg_command(Path("/tmp/a.mp4"), tmp_path, fps=5, max_frames=200, width=1280)
    assert "fps=5,scale=1280:-1" in cmd
    assert "200" in cmd
