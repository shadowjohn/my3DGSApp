import json
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

import scripts.frame_quality_select as frame_quality_select
from scripts.frame_quality_select import (
    FrameMetrics,
    clear_stale_candidates,
    compute_frame_metrics,
    load_candidate_metrics,
    normalize_scores,
    positive_int,
    select_best_frames,
    validate_output_paths,
    write_selected_frames,
)


def write_image(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ok = cv2.imwrite(str(path), image)
    assert ok


def checkerboard(size: int = 128, square_size: int = 8) -> np.ndarray:
    coords = np.indices((size, size)) // square_size
    grid = coords.sum(axis=0) % 2
    return (grid * 255).astype(np.uint8)


def test_compute_frame_metrics_scores_blurry_frame_lower(tmp_path):
    sharp = checkerboard()
    blurry = cv2.GaussianBlur(sharp, (15, 15), 0)
    sharp_path = tmp_path / "sharp.png"
    blurry_path = tmp_path / "blurry.png"
    write_image(sharp_path, sharp)
    write_image(blurry_path, blurry)

    sharp_metrics = compute_frame_metrics(sharp_path, index=1, timestamp=0.0)
    blurry_metrics = compute_frame_metrics(blurry_path, index=2, timestamp=0.1)

    assert sharp_metrics.sharpness > blurry_metrics.sharpness
    assert sharp_metrics.gradient > blurry_metrics.gradient
    assert sharp_metrics.path == sharp_path
    assert blurry_metrics.path == blurry_path


def test_normalize_scores_prefers_sharp_well_exposed_frame():
    rows = [
        FrameMetrics(
            Path("dark.jpg"),
            1,
            0.0,
            sharpness=100.0,
            gradient=30.0,
            exposure=0.2,
            clipping=0.6,
            texture=2.0,
        ),
        FrameMetrics(
            Path("sharp.jpg"),
            2,
            0.1,
            sharpness=900.0,
            gradient=120.0,
            exposure=0.9,
            clipping=0.0,
            texture=5.0,
        ),
        FrameMetrics(
            Path("flat.jpg"),
            3,
            0.2,
            sharpness=30.0,
            gradient=10.0,
            exposure=0.8,
            clipping=0.0,
            texture=0.5,
        ),
    ]

    scored = normalize_scores(rows)

    assert scored[1].score > scored[0].score
    assert scored[1].score > scored[2].score


def test_normalize_scores_returns_new_rows_without_mutating_inputs():
    rows = [
        FrameMetrics(Path("flat.jpg"), 1, 0.0, 10.0, 2.0, 0.5, 0.0, 1.0),
        FrameMetrics(Path("sharp.jpg"), 2, 0.1, 50.0, 8.0, 0.9, 0.0, 4.0),
    ]

    scored = normalize_scores(rows)

    assert scored is not rows
    assert scored[0] is not rows[0]
    assert scored[1] is not rows[1]
    assert [row.score for row in rows] == [0.0, 0.0]
    assert [row.score for row in scored] != [0.0, 0.0]


def metric(path: str, index: int, timestamp: float, score: float) -> FrameMetrics:
    return FrameMetrics(
        path=Path(path),
        index=index,
        timestamp=timestamp,
        sharpness=score * 100.0,
        gradient=score * 10.0,
        exposure=0.8,
        clipping=0.0,
        texture=score,
        score=score,
    )


def test_select_best_frames_keeps_best_candidate_per_bucket_in_chronological_order():
    rows = [
        metric("candidate_000004.jpg", 4, 0.40, 0.5),
        metric("candidate_000005.jpg", 5, 0.55, 3.0),
        metric("candidate_000003.jpg", 3, 0.20, 1.0),
        metric("candidate_000001.jpg", 1, 0.00, 0.1),
        metric("candidate_000002.jpg", 2, 0.08, 2.0),
    ]

    selected = select_best_frames(rows, target_fps=3, max_frames=10)

    assert [row.path.name for row in selected] == [
        "candidate_000002.jpg",
        "candidate_000005.jpg",
    ]
    assert [row.timestamp for row in selected] == [0.08, 0.55]


def test_select_best_frames_caps_max_frames():
    rows = [
        metric("candidate_000001.jpg", 1, 0.00, 1.0),
        metric("candidate_000002.jpg", 2, 0.40, 2.0),
        metric("candidate_000003.jpg", 3, 0.80, 3.0),
    ]

    selected = select_best_frames(rows, target_fps=3, max_frames=2)

    assert [row.path.name for row in selected] == [
        "candidate_000001.jpg",
        "candidate_000002.jpg",
    ]


def test_select_best_frames_requires_positive_target_fps():
    with pytest.raises(ValueError, match="target_fps must be positive"):
        select_best_frames([], target_fps=0, max_frames=10)


def test_validate_output_paths_rejects_overlapping_candidate_and_images_dirs(tmp_path):
    candidates = tmp_path / "candidates"
    images = tmp_path / "images"
    report = tmp_path / "frame_quality_report.json"

    with pytest.raises(ValueError, match="images_dir must not overlap candidates_dir"):
        validate_output_paths(candidates, candidates, report)

    with pytest.raises(ValueError, match="images_dir must not overlap candidates_dir"):
        validate_output_paths(candidates, candidates / "selected", report)

    with pytest.raises(ValueError, match="images_dir must not overlap candidates_dir"):
        validate_output_paths(images / "candidates", images, report)


def test_validate_output_paths_rejects_report_inside_images_dir(tmp_path):
    candidates = tmp_path / "candidates"
    images = tmp_path / "images"

    with pytest.raises(ValueError, match="report_path must not be inside images_dir"):
        validate_output_paths(images, candidates, images / "frame_quality_report.json")


def test_validate_output_paths_rejects_report_inside_candidates_dir(tmp_path):
    candidates = tmp_path / "candidates"
    images = tmp_path / "images"

    with pytest.raises(ValueError, match="report_path must not overlap candidates_dir"):
        validate_output_paths(images, candidates, candidates / "frame_quality.json")


def test_write_selected_frames_rejects_images_dir_inside_candidate_sources(tmp_path):
    source = tmp_path / "candidates"
    images = source / "images"
    report = tmp_path / "frame_quality_report.json"
    write_image(source / "candidate_000001.jpg", checkerboard())
    rows = [metric(str(source / "candidate_000001.jpg"), 1, 0.0, 2.0)]

    with pytest.raises(ValueError, match="images_dir must not overlap candidates_dir"):
        write_selected_frames(rows, rows, images, report, candidate_fps=12, target_fps=3)


def test_write_selected_frames_rejects_unrelated_images_dir_contents(tmp_path):
    source = tmp_path / "candidates"
    images = tmp_path / "images"
    report = tmp_path / "frame_quality_report.json"
    keep = images / "keep.txt"
    write_image(source / "candidate_000001.jpg", checkerboard())
    keep.parent.mkdir()
    keep.write_text("do not delete")
    rows = [metric(str(source / "candidate_000001.jpg"), 1, 0.0, 2.0)]

    with pytest.raises(ValueError, match="images_dir contains unexpected content"):
        write_selected_frames(rows, rows, images, report, candidate_fps=12, target_fps=3)

    assert keep.read_text() == "do not delete"
    assert not report.exists()


def test_write_selected_frames_rejects_non_numeric_frame_prefixed_files(tmp_path):
    source = tmp_path / "candidates"
    images = tmp_path / "images"
    report = tmp_path / "frame_quality_report.json"
    reference = images / "frame_reference.jpg"
    write_image(source / "candidate_000001.jpg", checkerboard())
    images.mkdir()
    reference.write_bytes(b"reference")
    rows = [metric(str(source / "candidate_000001.jpg"), 1, 0.0, 2.0)]

    with pytest.raises(ValueError, match="images_dir contains unexpected content"):
        write_selected_frames(rows, rows, images, report, candidate_fps=12, target_fps=3)

    assert reference.read_bytes() == b"reference"
    assert not report.exists()


def test_write_selected_frames_rejects_unicode_digit_frame_files(tmp_path):
    source = tmp_path / "candidates"
    images = tmp_path / "images"
    report = tmp_path / "frame_quality_report.json"
    unicode_digits = images / "frame_１２３.jpg"
    write_image(source / "candidate_000001.jpg", checkerboard())
    images.mkdir()
    unicode_digits.write_bytes(b"unicode")
    rows = [metric(str(source / "candidate_000001.jpg"), 1, 0.0, 2.0)]

    with pytest.raises(ValueError, match="images_dir contains unexpected content"):
        write_selected_frames(rows, rows, images, report, candidate_fps=12, target_fps=3)

    assert unicode_digits.read_bytes() == b"unicode"
    assert not report.exists()


def test_write_selected_frames_replaces_only_stale_generated_frames(tmp_path):
    source = tmp_path / "candidates"
    images = tmp_path / "images"
    report = tmp_path / "frame_quality_report.json"
    elsewhere = tmp_path / "elsewhere"
    stale = images / "frame_00001.jpg"
    unrelated_elsewhere = elsewhere / "keep.txt"
    write_image(source / "candidate_000001.jpg", checkerboard())
    images.mkdir()
    stale.write_bytes(b"stale")
    elsewhere.mkdir()
    unrelated_elsewhere.write_text("untouched")
    rows = [metric(str(source / "candidate_000001.jpg"), 1, 0.0, 2.0)]

    write_selected_frames(rows, rows, images, report, candidate_fps=12, target_fps=3)

    assert stale.read_bytes() == (source / "candidate_000001.jpg").read_bytes()
    assert unrelated_elsewhere.read_text() == "untouched"
    assert json.loads(report.read_text())["selected_count"] == 1


def test_write_selected_frames_rejects_images_dir_subdirectories(tmp_path):
    source = tmp_path / "candidates"
    images = tmp_path / "images"
    report = tmp_path / "frame_quality_report.json"
    nested = images / "nested"
    write_image(source / "candidate_000001.jpg", checkerboard())
    nested.mkdir(parents=True)
    (nested / "frame_00001.jpg").write_bytes(b"nested")
    rows = [metric(str(source / "candidate_000001.jpg"), 1, 0.0, 2.0)]

    with pytest.raises(ValueError, match="images_dir contains unexpected content"):
        write_selected_frames(rows, rows, images, report, candidate_fps=12, target_fps=3)

    assert (nested / "frame_00001.jpg").read_bytes() == b"nested"
    assert not report.exists()


def test_clear_stale_candidates_removes_only_candidate_jpegs(tmp_path):
    candidates = tmp_path / "candidates"
    candidates.mkdir()
    stale = candidates / "candidate_000001.jpg"
    unrelated_jpg = candidates / "keep.jpg"
    unrelated_txt = candidates / "candidate_notes.txt"
    nested_stale = candidates / "nested" / "candidate_000002.jpg"
    stale.write_bytes(b"stale")
    unrelated_jpg.write_bytes(b"keep")
    unrelated_txt.write_text("keep")
    nested_stale.parent.mkdir()
    nested_stale.write_bytes(b"nested")

    clear_stale_candidates(candidates)

    assert not stale.exists()
    assert unrelated_jpg.read_bytes() == b"keep"
    assert unrelated_txt.read_text() == "keep"
    assert nested_stale.read_bytes() == b"nested"


def test_clear_stale_candidates_keeps_non_numeric_candidate_jpegs(tmp_path):
    candidates = tmp_path / "candidates"
    candidates.mkdir()
    generated = candidates / "candidate_000001.jpg"
    reference = candidates / "candidate_reference.jpg"
    generated.write_bytes(b"generated")
    reference.write_bytes(b"reference")

    clear_stale_candidates(candidates)

    assert not generated.exists()
    assert reference.read_bytes() == b"reference"


def test_clear_stale_candidates_keeps_unicode_digit_candidate_jpegs(tmp_path):
    candidates = tmp_path / "candidates"
    candidates.mkdir()
    generated = candidates / "candidate_000001.jpg"
    unicode_digits = candidates / "candidate_１２３.jpg"
    generated.write_bytes(b"generated")
    unicode_digits.write_bytes(b"unicode")

    clear_stale_candidates(candidates)

    assert not generated.exists()
    assert unicode_digits.read_bytes() == b"unicode"


def test_load_candidate_metrics_ignores_non_numeric_candidate_jpegs(tmp_path, monkeypatch):
    candidates = tmp_path / "candidates"
    candidates.mkdir()
    (candidates / "candidate_000002.jpg").write_bytes(b"second")
    (candidates / "candidate_reference.jpg").write_bytes(b"reference")
    (candidates / "candidate_000001.jpg").write_bytes(b"first")
    loaded = []

    def fake_compute_frame_metrics(path: Path, index: int, timestamp: float) -> FrameMetrics:
        loaded.append((path.name, index, timestamp))
        return FrameMetrics(path, index, timestamp, 1.0, 1.0, 0.8, 0.0, 1.0)

    monkeypatch.setattr(
        frame_quality_select,
        "compute_frame_metrics",
        fake_compute_frame_metrics,
    )

    rows = load_candidate_metrics(candidates, candidate_fps=10)

    assert [row.path.name for row in rows] == [
        "candidate_000001.jpg",
        "candidate_000002.jpg",
    ]
    assert loaded == [
        ("candidate_000001.jpg", 1, 0.0),
        ("candidate_000002.jpg", 2, 0.1),
    ]


def test_load_candidate_metrics_ignores_unicode_digit_candidate_jpegs(
    tmp_path,
    monkeypatch,
):
    candidates = tmp_path / "candidates"
    candidates.mkdir()
    (candidates / "candidate_000001.jpg").write_bytes(b"first")
    (candidates / "candidate_１２３.jpg").write_bytes(b"unicode")
    loaded = []

    def fake_compute_frame_metrics(path: Path, index: int, timestamp: float) -> FrameMetrics:
        loaded.append((path.name, index, timestamp))
        return FrameMetrics(path, index, timestamp, 1.0, 1.0, 0.8, 0.0, 1.0)

    monkeypatch.setattr(
        frame_quality_select,
        "compute_frame_metrics",
        fake_compute_frame_metrics,
    )

    rows = load_candidate_metrics(candidates, candidate_fps=10)

    assert [row.path.name for row in rows] == ["candidate_000001.jpg"]
    assert loaded == [("candidate_000001.jpg", 1, 0.0)]


@pytest.mark.parametrize("value", ["0", "-1"])
def test_positive_int_rejects_non_positive_values(value):
    with pytest.raises(ValueError, match="must be positive"):
        positive_int(value)


def test_write_selected_frames_copies_chronological_images_and_report(tmp_path):
    source = tmp_path / "candidates"
    images = tmp_path / "images"
    report = tmp_path / "frame_quality_report.json"
    write_image(source / "candidate_000001.jpg", checkerboard())
    write_image(
        source / "candidate_000002.jpg",
        cv2.GaussianBlur(checkerboard(), (7, 7), 0),
    )
    rows = [
        metric(str(source / "candidate_000001.jpg"), 1, 0.0, 2.0),
        metric(str(source / "candidate_000002.jpg"), 2, 0.3, 1.0),
    ]

    write_selected_frames(rows, rows, images, report, candidate_fps=12, target_fps=3)

    first_output = images / "frame_00001.jpg"
    second_output = images / "frame_00002.jpg"
    assert first_output.is_file()
    assert second_output.is_file()
    assert first_output.read_bytes() == (source / "candidate_000001.jpg").read_bytes()
    assert second_output.read_bytes() == (source / "candidate_000002.jpg").read_bytes()
    data = json.loads(report.read_text())
    assert data["candidate_count"] == 2
    assert data["selected_count"] == 2
    assert data["candidate_fps"] == 12
    assert data["target_fps"] == 3
    assert [
        (row["output_name"], row["source_name"])
        for row in data["selected"]
    ] == [
        ("frame_00001.jpg", "candidate_000001.jpg"),
        ("frame_00002.jpg", "candidate_000002.jpg"),
    ]
    assert "source_path" not in data["selected"][0]
    assert len(data["candidates"]) == 2
    assert data["candidates"][0]["source_name"] == "candidate_000001.jpg"
    assert "path" not in data["candidates"][0]


def set_cli_args(monkeypatch, *args: str) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["frame_quality_select.py", *args],
    )


def test_main_dry_run_validates_paths_before_printing_command(
    tmp_path,
    monkeypatch,
    capsys,
):
    input_video = tmp_path / "input.mp4"
    input_video.write_bytes(b"video")
    candidates = tmp_path / "candidates"
    report = candidates / "frame_quality.json"
    set_cli_args(
        monkeypatch,
        str(input_video),
        str(candidates),
        str(tmp_path / "images"),
        "--report",
        str(report),
        "--dry-run",
    )

    with pytest.raises(ValueError, match="report_path must not overlap candidates_dir"):
        frame_quality_select.main()

    assert capsys.readouterr().out == ""
    assert not candidates.exists()


def test_main_rejects_overlapping_paths_before_extraction_side_effects(
    tmp_path,
    monkeypatch,
):
    input_video = tmp_path / "input.mp4"
    input_video.write_bytes(b"video")
    candidates = tmp_path / "candidates"
    side_effects = []
    set_cli_args(
        monkeypatch,
        str(input_video),
        str(candidates),
        str(candidates / "images"),
        "--report",
        str(tmp_path / "frame_quality.json"),
    )
    monkeypatch.setattr(
        frame_quality_select,
        "clear_stale_candidates",
        lambda _path: side_effects.append("clear"),
    )
    monkeypatch.setattr(
        frame_quality_select.subprocess,
        "run",
        lambda *_args, **_kwargs: side_effects.append("ffmpeg"),
    )

    with pytest.raises(ValueError, match="images_dir must not overlap candidates_dir"):
        frame_quality_select.main()

    assert side_effects == []
    assert not candidates.exists()


def test_main_missing_input_exits_before_extraction(tmp_path, monkeypatch):
    side_effects = []
    set_cli_args(
        monkeypatch,
        str(tmp_path / "missing.mp4"),
        str(tmp_path / "candidates"),
        str(tmp_path / "images"),
        "--report",
        str(tmp_path / "frame_quality.json"),
    )
    monkeypatch.setattr(
        frame_quality_select,
        "clear_stale_candidates",
        lambda _path: side_effects.append("clear"),
    )
    monkeypatch.setattr(
        frame_quality_select.subprocess,
        "run",
        lambda *_args, **_kwargs: side_effects.append("ffmpeg"),
    )

    with pytest.raises(SystemExit, match="input video not found"):
        frame_quality_select.main()

    assert side_effects == []


def test_main_rejects_candidate_fps_below_target_fps_before_extraction(
    tmp_path,
    monkeypatch,
):
    input_video = tmp_path / "input.mp4"
    input_video.write_bytes(b"video")
    side_effects = []
    set_cli_args(
        monkeypatch,
        str(input_video),
        str(tmp_path / "candidates"),
        str(tmp_path / "images"),
        "--report",
        str(tmp_path / "frame_quality.json"),
        "--candidate-fps",
        "2",
        "--target-fps",
        "3",
    )
    monkeypatch.setattr(
        frame_quality_select,
        "clear_stale_candidates",
        lambda _path: side_effects.append("clear"),
    )
    monkeypatch.setattr(
        frame_quality_select.subprocess,
        "run",
        lambda *_args, **_kwargs: side_effects.append("ffmpeg"),
    )

    with pytest.raises(
        SystemExit,
        match="candidate-fps must be greater than or equal to target-fps",
    ):
        frame_quality_select.main()

    assert side_effects == []


def test_main_reuse_candidates_skips_extraction_and_writes_report(
    tmp_path,
    monkeypatch,
):
    input_video = tmp_path / "input.mp4"
    input_video.write_bytes(b"video")
    candidates = tmp_path / "candidates"
    images = tmp_path / "images"
    report = tmp_path / "frame_quality.json"
    rows = []
    for index in range(1, 9):
        path = candidates / f"candidate_{index:06d}.jpg"
        write_image(path, checkerboard())
        rows.append(metric(str(path), index, (index - 1) * 0.4, float(index)))
    side_effects = []
    set_cli_args(
        monkeypatch,
        str(input_video),
        str(candidates),
        str(images),
        "--report",
        str(report),
        "--reuse-candidates",
    )
    monkeypatch.setattr(
        frame_quality_select,
        "clear_stale_candidates",
        lambda _path: side_effects.append("clear"),
    )
    monkeypatch.setattr(
        frame_quality_select.subprocess,
        "run",
        lambda *_args, **_kwargs: side_effects.append("ffmpeg"),
    )
    monkeypatch.setattr(
        frame_quality_select,
        "load_candidate_metrics",
        lambda _path, _fps: rows,
    )

    assert frame_quality_select.main() == 0

    assert side_effects == []
    assert (images / "frame_00001.jpg").is_file()
    assert json.loads(report.read_text())["selected_count"] == 8


def test_main_reuse_candidates_rejects_short_video_by_default(
    tmp_path,
    monkeypatch,
):
    input_video = tmp_path / "input.mp4"
    input_video.write_bytes(b"video")
    candidates = tmp_path / "candidates"
    images = tmp_path / "images"
    report = tmp_path / "frame_quality.json"
    rows = []
    for index in range(1, 6):
        path = candidates / f"candidate_{index:06d}.jpg"
        write_image(path, checkerboard())
        rows.append(metric(str(path), index, (index - 1) / 12.0, float(index)))
    set_cli_args(
        monkeypatch,
        str(input_video),
        str(candidates),
        str(images),
        "--report",
        str(report),
        "--reuse-candidates",
    )
    monkeypatch.setattr(
        frame_quality_select,
        "load_candidate_metrics",
        lambda _path, _fps: rows,
    )

    with pytest.raises(SystemExit, match="candidate frame count is lower than 8"):
        frame_quality_select.main()

    assert not report.exists()


def test_main_reuse_candidates_allows_short_experiment_with_relaxed_minimums(
    tmp_path,
    monkeypatch,
):
    input_video = tmp_path / "input.mp4"
    input_video.write_bytes(b"video")
    candidates = tmp_path / "candidates"
    images = tmp_path / "images"
    report = tmp_path / "frame_quality.json"
    rows = []
    for index in range(1, 6):
        path = candidates / f"candidate_{index:06d}.jpg"
        write_image(path, checkerboard())
        rows.append(metric(str(path), index, (index - 1) / 12.0, float(index)))
    set_cli_args(
        monkeypatch,
        str(input_video),
        str(candidates),
        str(images),
        "--report",
        str(report),
        "--reuse-candidates",
        "--candidate-fps",
        "12",
        "--target-fps",
        "12",
        "--min-candidates",
        "1",
        "--min-selected",
        "1",
    )
    monkeypatch.setattr(
        frame_quality_select,
        "load_candidate_metrics",
        lambda _path, _fps: rows,
    )

    assert frame_quality_select.main() == 0

    assert (images / "frame_00005.jpg").is_file()
    data = json.loads(report.read_text())
    assert data["candidate_count"] == 5
    assert data["selected_count"] == 5


def test_main_dry_run_prints_expected_ffmpeg_command(tmp_path, monkeypatch, capsys):
    input_video = tmp_path / "input.mp4"
    input_video.write_bytes(b"video")
    candidates = tmp_path / "candidates"
    set_cli_args(
        monkeypatch,
        str(input_video),
        str(candidates),
        str(tmp_path / "images"),
        "--report",
        str(tmp_path / "frame_quality.json"),
        "--candidate-fps",
        "10",
        "--width",
        "800",
        "--dry-run",
    )

    assert frame_quality_select.main() == 0

    assert capsys.readouterr().out == (
        "ffmpeg -nostdin -y -i "
        f"{input_video} -vf fps=10,scale=800:-1 -an -f image2 "
        f"{candidates / 'candidate_%06d.jpg'}\n"
    )
