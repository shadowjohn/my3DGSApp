# Golden Benchmark Pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Phase G1.5: a repeatable Golden Benchmark Pack for `uploads/3` that compares old results, new selected-30k results, official-viewer evidence, custom-viewer evidence, capture diagnosis, and fixed human scorecards.

**Architecture:** Add a focused Python report builder that reads existing job artifacts and writes a benchmark folder without copying large artifacts by default. Keep pipeline execution separate: the benchmark tool records artifact mapping and reports, while `scripts/run_mvp_pipeline.sh` still performs reconstruction. Use tests to lock the JSON schema, fixed scorecard fields, viewer separation, and non-portable artifact policy.

**Tech Stack:** Python 3, pytest, Markdown, JSON, existing Gaussian Splat job folders, existing `scripts/run_mvp_pipeline.sh`, existing `viewer_splat.html`.

---

## Scope

This plan implements the design in:

```text
docs/superpowers/specs/2026-06-15-golden-benchmark-pack-design.md
```

In scope:

- `uploads/3` as the first benchmark source.
- `uploads/benchmark-uploads-3/` as the first benchmark bundle.
- Artifact mapping in `benchmark.json`.
- `artifactPolicy.portableMode = false`.
- Fixed scorecard fields:
  - `Geometry`
  - `Recognizability`
  - `Floaters`
  - `Registration`
  - `Viewer Quality`
  - `Overall`
- `capture_diagnosis.md`.
- Separate `official-viewer/` and `custom-viewer/` evidence folders.
- `benchmark.md` for human review.
- Commands for re-running current selected-30k into `uploads/benchmark-uploads-3/new-selected-30k`.

Out of scope:

- Mesh Extraction.
- GLB Export.
- 3D Tiles.
- MapLibre.
- Cesium.
- GIS Integration.
- Real-ESRGAN.
- Automated visual scoring.
- Fully automated external third-party benchmark capture.

## File Structure

- Create `scripts/build_golden_benchmark_pack.py`
  - Reads an old job directory and an optional new job directory.
  - Writes `benchmark.json`, `benchmark.md`, `scorecard.md`, `capture_diagnosis.md`, viewer notes, and artifact folders.
  - References large files by path when `portableMode` is false.
- Create `tests/test_golden_benchmark_pack.py`
  - Unit tests for artifact mapping, scorecard template, capture diagnosis, viewer separation, and Markdown output.
- Modify `docs/frame-quality-runbook.md`
  - Add a G1.5 section with commands to run `uploads/3` benchmark.
- Modify `history.md`
  - Add a short note that G1.5 planning started and points to the plan/spec.
- Use existing `scripts/run_mvp_pipeline.sh`
  - Do not modify it for G1.5.
- Use existing `scripts/build_ab_evidence_report.py`
  - Optional helper after the new selected-30k run; do not modify unless implementation discovers a strict need.

---

### Task 1: Benchmark Pack Schema Tests

**Files:**
- Create: `tests/test_golden_benchmark_pack.py`
- Create later: `scripts/build_golden_benchmark_pack.py`

- [ ] **Step 1: Write failing tests for artifact mapping and directory structure**

Create `tests/test_golden_benchmark_pack.py` with:

```python
import json
from pathlib import Path

from scripts.build_golden_benchmark_pack import build_benchmark_pack


def write_ply(path: Path, vertices: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "ply\n"
        "format binary_little_endian 1.0\n"
        f"element vertex {vertices}\n"
        "property float x\n"
        "end_header\n",
        encoding="utf-8",
    )


def make_old_job(tmp_path: Path) -> Path:
    job = tmp_path / "uploads" / "3"
    (job / "input").mkdir(parents=True)
    (job / "input" / "input.mp4").write_bytes(b"mp4")
    (job / "qa_report.json").write_text(
        json.dumps(
            {
                "job_id": "3",
                "frame_count": 32,
                "registered_frame_count": 25,
                "registered_ratio": 0.78,
                "warnings": ["registered_ratio lower than 0.8"],
            }
        ),
        encoding="utf-8",
    )
    (job / "transform.json").write_text(json.dumps({"job_id": "3"}), encoding="utf-8")
    write_ply(job / "exports" / "splat.ply", 1234)
    write_ply(job / "exports" / "splat.core-20260605-1100.ply", 1000)
    (job / "exports" / "splat.core-20260605-1100.viewer.json").write_text(
        json.dumps({"viewer": {"rx": 0, "ry": 0, "rz": 0, "upMode": "view"}}),
        encoding="utf-8",
    )
    return job


def test_build_benchmark_pack_writes_artifact_mapping_and_viewer_folders(tmp_path):
    old_job = make_old_job(tmp_path)
    output_dir = tmp_path / "uploads" / "benchmark-uploads-3"

    report = build_benchmark_pack(
        benchmark_id="benchmark-uploads-3",
        source_job=old_job,
        output_dir=output_dir,
        project_root=tmp_path,
        viewer_base_url="https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_splat.html",
        new_job=None,
        portable_mode=False,
    )

    assert report["benchmarkId"] == "benchmark-uploads-3"
    assert report["sourceJob"].endswith("uploads/3")
    assert report["artifactPolicy"] == {"portableMode": False}
    assert report["cases"]["old"]["rawSplat"].endswith("uploads/3/exports/splat.ply")
    assert report["cases"]["old"]["coreSplat"].endswith("uploads/3/exports/splat.core-20260605-1100.ply")
    assert report["cases"]["reference"]["externalDemo"].endswith("references/external-demo")
    assert (output_dir / "benchmark.json").is_file()
    assert (output_dir / "benchmark.md").is_file()
    assert (output_dir / "scorecard.md").is_file()
    assert (output_dir / "capture_diagnosis.md").is_file()
    assert (output_dir / "new-selected-30k" / "official-viewer" / "screenshots").is_dir()
    assert (output_dir / "new-selected-30k" / "custom-viewer" / "screenshots").is_dir()
```

- [ ] **Step 2: Run the new test and verify it fails**

Run:

```bash
pytest -q tests/test_golden_benchmark_pack.py::test_build_benchmark_pack_writes_artifact_mapping_and_viewer_folders
```

Expected:

```text
ModuleNotFoundError: No module named 'scripts.build_golden_benchmark_pack'
```

- [ ] **Step 3: Commit the failing test**

```bash
git add tests/test_golden_benchmark_pack.py
git commit -m "test: define golden benchmark pack schema"
```

---

### Task 2: Minimal Benchmark Builder

**Files:**
- Create: `scripts/build_golden_benchmark_pack.py`
- Modify: `tests/test_golden_benchmark_pack.py`

- [ ] **Step 1: Implement minimal builder to pass Task 1**

Create `scripts/build_golden_benchmark_pack.py`:

```python
#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any
from urllib.parse import quote


DEFAULT_VIEWER_BASE_URL = "https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_splat.html"


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def relative_path(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def viewer_url(path: Path, project_root: Path, viewer_base_url: str, meta: Path | None = None) -> str:
    url = viewer_base_url + "?src=" + quote(relative_path(path, project_root), safe="/")
    if meta is not None and meta.is_file():
        url += "&meta=" + quote(relative_path(meta, project_root), safe="/")
    return url + "&rx=0&ry=0&rz=0&up=view"


def ensure_viewer_dirs(output_dir: Path) -> None:
    for viewer_kind in ["official-viewer", "custom-viewer"]:
        base = output_dir / "new-selected-30k" / viewer_kind
        (base / "screenshots").mkdir(parents=True, exist_ok=True)
        notes = base / "notes.md"
        if not notes.exists():
            notes.write_text(f"# {viewer_kind} Notes\n\n", encoding="utf-8")


def old_case(source_job: Path, project_root: Path, viewer_base_url: str) -> dict[str, Any]:
    raw = source_job / "exports" / "splat.ply"
    core = source_job / "exports" / "splat.core-20260605-1100.ply"
    core_meta = source_job / "exports" / "splat.core-20260605-1100.viewer.json"
    return {
        "jobDir": relative_path(source_job, project_root),
        "rawSplat": relative_path(raw, project_root),
        "coreSplat": relative_path(core, project_root),
        "qaReport": relative_path(source_job / "qa_report.json", project_root),
        "transform": relative_path(source_job / "transform.json", project_root),
        "viewerUrls": {
            "raw": viewer_url(raw, project_root, viewer_base_url),
            "core": viewer_url(core, project_root, viewer_base_url, core_meta),
        },
    }


def new_case(output_dir: Path, project_root: Path, new_job: Path | None, viewer_base_url: str) -> dict[str, Any]:
    job = new_job if new_job is not None else output_dir / "new-selected-30k"
    clean = job / "exports" / "splat.clean.ply"
    clean_meta = job / "exports" / "splat.clean.viewer.json"
    return {
        "jobDir": relative_path(job, project_root),
        "rawSplat": relative_path(job / "exports" / "splat.ply", project_root),
        "cleanSplat": relative_path(clean, project_root),
        "cleanViewerMeta": relative_path(clean_meta, project_root),
        "qaReport": relative_path(job / "qa_report.json", project_root),
        "frameReport": relative_path(job / "frame_quality_report.json", project_root),
        "timingReport": relative_path(job / "timing_report.json", project_root),
        "officialViewer": relative_path(output_dir / "new-selected-30k" / "official-viewer", project_root),
        "customViewer": relative_path(output_dir / "new-selected-30k" / "custom-viewer", project_root),
        "viewerUrls": {
            "raw": viewer_url(job / "exports" / "splat.ply", project_root, viewer_base_url),
            "clean": viewer_url(clean, project_root, viewer_base_url, clean_meta),
        },
    }


def build_benchmark_pack(
    benchmark_id: str,
    source_job: Path,
    output_dir: Path,
    project_root: Path,
    viewer_base_url: str = DEFAULT_VIEWER_BASE_URL,
    new_job: Path | None = None,
    portable_mode: bool = False,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "old").mkdir(parents=True, exist_ok=True)
    (output_dir / "references" / "external-demo" / "screenshots").mkdir(parents=True, exist_ok=True)
    ensure_viewer_dirs(output_dir)

    report = {
        "benchmarkId": benchmark_id,
        "sourceJob": relative_path(source_job, project_root),
        "artifactPolicy": {"portableMode": portable_mode},
        "cases": {
            "old": old_case(source_job, project_root, viewer_base_url),
            "newSelected30k": new_case(output_dir, project_root, new_job, viewer_base_url),
            "reference": {
                "externalDemo": relative_path(output_dir / "references" / "external-demo", project_root)
            },
        },
    }
    write_json(output_dir / "benchmark.json", report)
    write_markdown_files(output_dir, report)
    return report
```

- [ ] **Step 2: Add placeholder writers with fixed content**

Append to `scripts/build_golden_benchmark_pack.py`:

```python
SCORECARD_FIELDS = [
    "Geometry",
    "Recognizability",
    "Floaters",
    "Registration",
    "Viewer Quality",
    "Overall",
]


def write_markdown_files(output_dir: Path, report: dict[str, Any]) -> None:
    write_benchmark_md(output_dir / "benchmark.md", report)
    write_scorecard_md(output_dir / "scorecard.md")
    write_capture_diagnosis_md(output_dir / "capture_diagnosis.md")


def write_benchmark_md(path: Path, report: dict[str, Any]) -> None:
    old_urls = report["cases"]["old"]["viewerUrls"]
    new_urls = report["cases"]["newSelected30k"]["viewerUrls"]
    lines = [
        "# Golden Benchmark Pack",
        "",
        "## Conclusion",
        "",
        "Recommended Variant:",
        "Reason:",
        "Known Issues:",
        "Next Action:",
        "Route Confidence:",
        "",
        "## Artifact Policy",
        "",
        f"portableMode: `{str(report['artifactPolicy']['portableMode']).lower()}`",
        "",
        "## Viewer Links",
        "",
        f"- Old raw: {old_urls['raw']}",
        f"- Old core: {old_urls['core']}",
        f"- New raw: {new_urls['raw']}",
        f"- New clean: {new_urls['clean']}",
        "",
        "## Scorecard Summary",
        "",
        "Fill `scorecard.md` after visual review.",
    ]
    path.write_text("\\n".join(lines).rstrip() + "\\n", encoding="utf-8")


def write_scorecard_md(path: Path) -> None:
    variants = ["old_uploads_3_raw", "old_uploads_3_core", "new_selected_30k_raw", "new_selected_30k_clean"]
    lines = [
        "# Golden Benchmark Scorecard",
        "",
        "Scores are fixed from 1 to 5. Higher is better.",
        "",
        "| Variant | Geometry | Recognizability | Floaters | Registration | Viewer Quality | Overall | Notes |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for variant in variants:
        lines.append(f"| {variant} |  |  |  |  |  |  |  |")
    path.write_text("\\n".join(lines).rstrip() + "\\n", encoding="utf-8")


def write_capture_diagnosis_md(path: Path) -> None:
    lines = [
        "# Capture Diagnosis",
        "",
        "## Scene Conditions",
        "",
        "- Reflective surfaces:",
        "- Moving people / moving objects:",
        "- Low-texture walls or floors:",
        "- Repeated patterns:",
        "- Thin structures:",
        "- Transparent or glossy objects:",
        "- Background clutter:",
        "",
        "## Camera Conditions",
        "",
        "- Camera path:",
        "- Approximate overlap:",
        "- Motion speed:",
        "- Shake:",
        "- Focus stability:",
        "- Exposure stability:",
        "- Lighting level:",
        "- Rolling shutter risk:",
        "",
        "## Diagnosis",
        "",
        "Capture Risk: low / medium / high",
        "Primary Capture Issues:",
        "Expected Pipeline Impact:",
        "Retake Recommendation:",
    ]
    path.write_text("\\n".join(lines).rstrip() + "\\n", encoding="utf-8")
```

- [ ] **Step 3: Add CLI entrypoint**

Append to `scripts/build_golden_benchmark_pack.py`:

```python
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a Golden Benchmark Pack.")
    parser.add_argument("--benchmark-id", required=True)
    parser.add_argument("--source-job", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--viewer-base-url", default=DEFAULT_VIEWER_BASE_URL)
    parser.add_argument("--new-job", type=Path)
    parser.add_argument("--portable-mode", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    build_benchmark_pack(
        benchmark_id=args.benchmark_id,
        source_job=args.source_job,
        output_dir=args.output_dir,
        project_root=args.project_root,
        viewer_base_url=args.viewer_base_url,
        new_job=args.new_job,
        portable_mode=args.portable_mode,
    )
    print(args.output_dir / "benchmark.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run Task 1 test and verify it passes**

Run:

```bash
pytest -q tests/test_golden_benchmark_pack.py::test_build_benchmark_pack_writes_artifact_mapping_and_viewer_folders
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Commit minimal builder**

```bash
git add scripts/build_golden_benchmark_pack.py tests/test_golden_benchmark_pack.py
git commit -m "feat: add golden benchmark pack builder"
```

---

### Task 3: Markdown and Scorecard Contract Tests

**Files:**
- Modify: `tests/test_golden_benchmark_pack.py`
- Modify: `scripts/build_golden_benchmark_pack.py`

- [ ] **Step 1: Add failing tests for fixed scorecard, capture diagnosis, and benchmark Markdown**

Append to `tests/test_golden_benchmark_pack.py`:

```python
def test_benchmark_pack_writes_fixed_scorecard_and_capture_diagnosis(tmp_path):
    old_job = make_old_job(tmp_path)
    output_dir = tmp_path / "uploads" / "benchmark-uploads-3"

    build_benchmark_pack(
        benchmark_id="benchmark-uploads-3",
        source_job=old_job,
        output_dir=output_dir,
        project_root=tmp_path,
        viewer_base_url="https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_splat.html",
        new_job=None,
        portable_mode=False,
    )

    scorecard = (output_dir / "scorecard.md").read_text(encoding="utf-8")
    assert "| Variant | Geometry | Recognizability | Floaters | Registration | Viewer Quality | Overall | Notes |" in scorecard
    assert "old_uploads_3_raw" in scorecard
    assert "new_selected_30k_clean" in scorecard

    capture = (output_dir / "capture_diagnosis.md").read_text(encoding="utf-8")
    assert "Reflective surfaces:" in capture
    assert "Moving people / moving objects:" in capture
    assert "Capture Risk: low / medium / high" in capture

    benchmark = (output_dir / "benchmark.md").read_text(encoding="utf-8")
    assert "Route Confidence:" in benchmark
    assert "portableMode: `false`" in benchmark
    assert "Old raw:" in benchmark
    assert "New clean:" in benchmark
```

- [ ] **Step 2: Run test and verify it fails if Task 2 did not include exact content**

Run:

```bash
pytest -q tests/test_golden_benchmark_pack.py::test_benchmark_pack_writes_fixed_scorecard_and_capture_diagnosis
```

Expected if Task 2 is incomplete:

```text
FAILED
```

If it already passes because Task 2 included the exact content, continue to Step 4.

- [ ] **Step 3: Adjust Markdown writers to pass the contract**

Ensure `scripts/build_golden_benchmark_pack.py` writes exactly these required strings:

```python
"| Variant | Geometry | Recognizability | Floaters | Registration | Viewer Quality | Overall | Notes |"
"Reflective surfaces:"
"Moving people / moving objects:"
"Capture Risk: low / medium / high"
"Route Confidence:"
"portableMode: `false`"
```

- [ ] **Step 4: Run test and verify it passes**

Run:

```bash
pytest -q tests/test_golden_benchmark_pack.py::test_benchmark_pack_writes_fixed_scorecard_and_capture_diagnosis
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Commit Markdown contract**

```bash
git add scripts/build_golden_benchmark_pack.py tests/test_golden_benchmark_pack.py
git commit -m "test: lock golden benchmark markdown templates"
```

---

### Task 4: New Selected-30k Case Integration

**Files:**
- Modify: `tests/test_golden_benchmark_pack.py`
- Modify: `scripts/build_golden_benchmark_pack.py`

- [ ] **Step 1: Add failing test for a completed new selected-30k job**

Append to `tests/test_golden_benchmark_pack.py`:

```python
def make_new_job(tmp_path: Path) -> Path:
    job = tmp_path / "uploads" / "benchmark-uploads-3" / "new-selected-30k"
    (job / "images").mkdir(parents=True)
    for index in range(5):
        (job / "images" / f"frame_{index + 1:05d}.jpg").write_bytes(b"jpg")
    (job / "processed").mkdir()
    (job / "processed" / "transforms.json").write_text(
        json.dumps({"frames": [{"file_path": "images/frame_00001.jpg"} for _ in range(4)]}),
        encoding="utf-8",
    )
    (job / "qa_report.json").write_text(
        json.dumps({"quality_grade": "B", "registered_ratio": 0.8, "warnings": []}),
        encoding="utf-8",
    )
    (job / "frame_quality_report.json").write_text(
        json.dumps({"selected": [{"output_name": "frame_00001.jpg"}]}),
        encoding="utf-8",
    )
    (job / "timing_report.json").write_text(
        json.dumps({"duration_seconds": 100.0, "stages": [{"key": "train", "duration_seconds": 80.0}]}),
        encoding="utf-8",
    )
    write_ply(job / "exports" / "splat.ply", 2000)
    write_ply(job / "exports" / "splat.clean.ply", 1800)
    (job / "exports" / "splat.clean.viewer.json").write_text(
        json.dumps({"cleanup": {"kept_ratio": 0.9}}),
        encoding="utf-8",
    )
    return job


def test_benchmark_pack_maps_completed_new_selected_30k_job(tmp_path):
    old_job = make_old_job(tmp_path)
    new_job = make_new_job(tmp_path)
    output_dir = tmp_path / "uploads" / "benchmark-uploads-3"

    report = build_benchmark_pack(
        benchmark_id="benchmark-uploads-3",
        source_job=old_job,
        output_dir=output_dir,
        project_root=tmp_path,
        viewer_base_url="https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_splat.html",
        new_job=new_job,
        portable_mode=False,
    )

    new_case = report["cases"]["newSelected30k"]
    assert new_case["rawSplat"].endswith("new-selected-30k/exports/splat.ply")
    assert new_case["cleanSplat"].endswith("new-selected-30k/exports/splat.clean.ply")
    assert new_case["cleanViewerMeta"].endswith("new-selected-30k/exports/splat.clean.viewer.json")
    assert new_case["qaReport"].endswith("new-selected-30k/qa_report.json")
    assert "splat.clean.viewer.json" in new_case["viewerUrls"]["clean"]
```

- [ ] **Step 2: Run test and verify it passes**

Run:

```bash
pytest -q tests/test_golden_benchmark_pack.py::test_benchmark_pack_maps_completed_new_selected_30k_job
```

Expected:

```text
1 passed
```

- [ ] **Step 3: Add metric summary to benchmark JSON**

Add these helpers to `scripts/build_golden_benchmark_pack.py`:

```python
def count_images(images_dir: Path) -> int:
    if not images_dir.is_dir():
        return 0
    return sum(1 for path in images_dir.iterdir() if path.suffix.lower() in {".jpg", ".jpeg", ".png"})


def registered_count(processed_dir: Path) -> int:
    data = load_json(processed_dir / "transforms.json")
    frames = data.get("frames", [])
    return len(frames) if isinstance(frames, list) else 0


def metric_summary(job: Path) -> dict[str, Any]:
    qa = load_json(job / "qa_report.json")
    timing = load_json(job / "timing_report.json")
    frame_count = count_images(job / "images")
    registered = qa.get("registered_count") or qa.get("registered_frame_count") or registered_count(job / "processed")
    return {
        "frameCount": frame_count or qa.get("frame_count"),
        "registeredCount": registered,
        "registeredRatio": qa.get("registered_ratio"),
        "qualityGrade": qa.get("quality_grade"),
        "warnings": qa.get("warnings", []),
        "durationSeconds": timing.get("duration_seconds"),
    }
```

Then add `"metrics": metric_summary(source_job)` to `old_case()` and `"metrics": metric_summary(job)` to `new_case()`.

- [ ] **Step 4: Add and run metric summary test**

Append to `tests/test_golden_benchmark_pack.py`:

```python
def test_benchmark_pack_includes_machine_metrics(tmp_path):
    old_job = make_old_job(tmp_path)
    new_job = make_new_job(tmp_path)
    output_dir = tmp_path / "uploads" / "benchmark-uploads-3"

    report = build_benchmark_pack(
        benchmark_id="benchmark-uploads-3",
        source_job=old_job,
        output_dir=output_dir,
        project_root=tmp_path,
        viewer_base_url="https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_splat.html",
        new_job=new_job,
        portable_mode=False,
    )

    assert report["cases"]["old"]["metrics"]["frameCount"] == 32
    assert report["cases"]["old"]["metrics"]["registeredCount"] == 25
    assert report["cases"]["newSelected30k"]["metrics"]["frameCount"] == 5
    assert report["cases"]["newSelected30k"]["metrics"]["registeredCount"] == 4
    assert report["cases"]["newSelected30k"]["metrics"]["durationSeconds"] == 100.0
```

Run:

```bash
pytest -q tests/test_golden_benchmark_pack.py::test_benchmark_pack_includes_machine_metrics
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Commit new case integration**

```bash
git add scripts/build_golden_benchmark_pack.py tests/test_golden_benchmark_pack.py
git commit -m "feat: map new selected 30k benchmark artifacts"
```

---

### Task 5: CLI Smoke Test and First Pack Without Re-run

**Files:**
- Modify: `tests/test_golden_benchmark_pack.py`
- Use: `scripts/build_golden_benchmark_pack.py`

- [ ] **Step 1: Add CLI smoke test**

Append to `tests/test_golden_benchmark_pack.py`:

```python
def test_cli_writes_pack(tmp_path):
    old_job = make_old_job(tmp_path)
    output_dir = tmp_path / "uploads" / "benchmark-uploads-3"
    script = Path(__file__).resolve().parents[1] / "scripts" / "build_golden_benchmark_pack.py"

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--benchmark-id",
            "benchmark-uploads-3",
            "--source-job",
            str(old_job),
            "--output-dir",
            str(output_dir),
            "--project-root",
            str(tmp_path),
            "--viewer-base-url",
            "https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_splat.html",
        ],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    assert (output_dir / "benchmark.json").is_file()
    assert "benchmark.json" in result.stdout
```

Also add imports at the top if missing:

```python
import subprocess
import sys
```

- [ ] **Step 2: Run CLI smoke test**

Run:

```bash
pytest -q tests/test_golden_benchmark_pack.py::test_cli_writes_pack
```

Expected:

```text
1 passed
```

- [ ] **Step 3: Build first benchmark shell without re-run**

Run:

```bash
python3 scripts/build_golden_benchmark_pack.py \
  --benchmark-id benchmark-uploads-3 \
  --source-job uploads/3 \
  --output-dir uploads/benchmark-uploads-3 \
  --project-root /var/www/html/demo/php/map/3D/gaussian_splat \
  --viewer-base-url https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_splat.html
```

Expected:

```text
uploads/benchmark-uploads-3/benchmark.json
```

- [ ] **Step 4: Inspect generated files**

Run:

```bash
find uploads/benchmark-uploads-3 -maxdepth 3 -type f -o -type d | sort | sed -n '1,120p'
sed -n '1,180p' uploads/benchmark-uploads-3/benchmark.md
jq . uploads/benchmark-uploads-3/benchmark.json
```

Expected:

- `benchmark.json` exists.
- `benchmark.md` exists.
- `scorecard.md` exists.
- `capture_diagnosis.md` exists.
- `new-selected-30k/official-viewer/notes.md` exists.
- `new-selected-30k/custom-viewer/notes.md` exists.
- `artifactPolicy.portableMode` is `false`.

- [ ] **Step 5: Commit CLI smoke and first shell output if desired**

Commit code and tests. Do not commit generated benchmark artifacts unless project policy says generated evidence belongs in git.

```bash
git add scripts/build_golden_benchmark_pack.py tests/test_golden_benchmark_pack.py
git commit -m "test: add golden benchmark CLI smoke test"
```

---

### Task 6: Run New Selected-30k Variant for uploads/3

**Files:**
- Generated: `uploads/benchmark-uploads-3/new-selected-30k/**`
- Use: `scripts/run_mvp_pipeline.sh`
- Use: `scripts/build_golden_benchmark_pack.py`

- [ ] **Step 1: Start the selected-30k benchmark run**

Run:

```bash
GS_FRAME_CANDIDATE_FPS=12 GS_FRAME_TARGET_FPS=3 GS_FRAME_MAX_FRAMES=180 GS_TRAIN_MAX_ITERATIONS=30000 \
  bash scripts/run_mvp_pipeline.sh uploads/3/input/input.mp4 uploads/benchmark-uploads-3/new-selected-30k
```

Expected:

- Pipeline runs frame selection.
- Pipeline runs COLMAP.
- Pipeline runs 30k splatfacto training.
- Pipeline exports `splat.ply`.
- Pipeline writes `splat.clean.ply`.
- Pipeline writes QA/timing metadata.

- [ ] **Step 2: Verify new run outputs**

Run:

```bash
test -f uploads/benchmark-uploads-3/new-selected-30k/qa_report.json
test -f uploads/benchmark-uploads-3/new-selected-30k/frame_quality_report.json
test -f uploads/benchmark-uploads-3/new-selected-30k/timing_report.json
test -f uploads/benchmark-uploads-3/new-selected-30k/exports/splat.ply
test -f uploads/benchmark-uploads-3/new-selected-30k/exports/splat.clean.ply
test -f uploads/benchmark-uploads-3/new-selected-30k/exports/splat.clean.viewer.json
jq . uploads/benchmark-uploads-3/new-selected-30k/qa_report.json
jq . uploads/benchmark-uploads-3/new-selected-30k/timing_report.json
```

Expected:

- All `test -f` checks pass with exit code 0.
- QA report prints valid JSON.
- Timing report prints valid JSON.

- [ ] **Step 3: Rebuild benchmark pack with new job attached**

Run:

```bash
python3 scripts/build_golden_benchmark_pack.py \
  --benchmark-id benchmark-uploads-3 \
  --source-job uploads/3 \
  --new-job uploads/benchmark-uploads-3/new-selected-30k \
  --output-dir uploads/benchmark-uploads-3 \
  --project-root /var/www/html/demo/php/map/3D/gaussian_splat \
  --viewer-base-url https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_splat.html
```

Expected:

```text
uploads/benchmark-uploads-3/benchmark.json
```

- [ ] **Step 4: Generate A/B evidence for old/new if useful**

Run:

```bash
python3 scripts/build_ab_evidence_report.py \
  --variant old_uploads_3=uploads/3 \
  --variant new_selected_30k=uploads/benchmark-uploads-3/new-selected-30k \
  --output uploads/benchmark-uploads-3/ab_evidence.json \
  --markdown uploads/benchmark-uploads-3/ab_evidence.md \
  --viewer-base-url https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_splat.html \
  --project-root /var/www/html/demo/php/map/3D/gaussian_splat
```

Expected:

- `uploads/benchmark-uploads-3/ab_evidence.json` exists.
- `uploads/benchmark-uploads-3/ab_evidence.md` exists.

- [ ] **Step 5: Record run summary in benchmark notes**

Append a short manual note to `uploads/benchmark-uploads-3/benchmark.md` after reviewing reports:

```markdown
## Run Notes

- New selected-30k completed:
- Registered ratio:
- Clean kept ratio:
- Total duration:
- Immediate visual impression:
```

Do not fill visual impression until the viewer is opened.

---

### Task 7: Official vs Custom Viewer Evidence

**Files:**
- Generated/modify: `uploads/benchmark-uploads-3/new-selected-30k/official-viewer/notes.md`
- Generated/modify: `uploads/benchmark-uploads-3/new-selected-30k/custom-viewer/notes.md`
- Use: `viewer_splat.html`
- Use: `/park/conda_vm/gs_scene/bin/ns-viewer`

- [ ] **Step 1: Write custom-viewer links into notes**

Edit `uploads/benchmark-uploads-3/new-selected-30k/custom-viewer/notes.md`:

```markdown
# Custom Viewer Notes

## Links

Raw:
https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_splat.html?src=uploads%2Fbenchmark-uploads-3%2Fnew-selected-30k%2Fexports%2Fsplat.ply&rx=0&ry=0&rz=0&up=view

Clean:
https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_splat.html?src=uploads%2Fbenchmark-uploads-3%2Fnew-selected-30k%2Fexports%2Fsplat.clean.ply&meta=uploads%2Fbenchmark-uploads-3%2Fnew-selected-30k%2Fexports%2Fsplat.clean.viewer.json&rx=0&ry=0&rz=0&up=view

## Review

- Geometry:
- Recognizability:
- Floaters:
- Registration feel:
- Viewer-specific issues:
```

- [ ] **Step 2: Try official viewer**

Find config:

```bash
find uploads/benchmark-uploads-3/new-selected-30k/outputs -path '*/splatfacto/*/config.yml' -type f | sort | tail -n 1
```

Run with the found config path:

```bash
TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1 /park/conda_vm/gs_scene/bin/ns-viewer \
  --load-config uploads/benchmark-uploads-3/new-selected-30k/outputs/processed/splatfacto/<DATE>/config.yml \
  --viewer.websocket-port 7007 \
  --viewer.websocket-host 0.0.0.0
```

Expected:

- The checkpoint loads.
- The viewer prints a viser HTTP/WebSocket endpoint.

- [ ] **Step 3: Record official viewer result**

Edit `uploads/benchmark-uploads-3/new-selected-30k/official-viewer/notes.md`:

```markdown
# Official Viewer Notes

## Command

```bash
TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1 /park/conda_vm/gs_scene/bin/ns-viewer --load-config <CONFIG> --viewer.websocket-port 7007 --viewer.websocket-host 0.0.0.0
```

## Connectivity

- Checkpoint loaded:
- HTTP reachable:
- Port:
- Issues:

## Review

- Geometry:
- Recognizability:
- Floaters:
- Registration feel:
- Difference from custom viewer:
```

- [ ] **Step 4: If official viewer hangs or times out, stop it and record the failure**

Find and stop only the official viewer process started for this benchmark:

```bash
ps -ef | rg 'ns-viewer.*benchmark-uploads-3'
```

If needed:

```bash
pkill -f 'ns-viewer.*benchmark-uploads-3/new-selected-30k'
```

Record the timeout in `official-viewer/notes.md`. Do not call official viewer evidence available unless HTTP actually opens.

---

### Task 8: Documentation and History

**Files:**
- Modify: `docs/frame-quality-runbook.md`
- Modify: `history.md`

- [ ] **Step 1: Add G1.5 commands to runbook**

Add this section to `docs/frame-quality-runbook.md`:

```markdown
## Phase G1.5: Golden Benchmark Pack

First benchmark source:

```text
uploads/3
```

Build the initial benchmark shell:

```bash
python3 scripts/build_golden_benchmark_pack.py \
  --benchmark-id benchmark-uploads-3 \
  --source-job uploads/3 \
  --output-dir uploads/benchmark-uploads-3 \
  --project-root /var/www/html/demo/php/map/3D/gaussian_splat \
  --viewer-base-url https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_splat.html
```

Run the current selected 30k route:

```bash
GS_FRAME_CANDIDATE_FPS=12 GS_FRAME_TARGET_FPS=3 GS_FRAME_MAX_FRAMES=180 GS_TRAIN_MAX_ITERATIONS=30000 \
  bash scripts/run_mvp_pipeline.sh uploads/3/input/input.mp4 uploads/benchmark-uploads-3/new-selected-30k
```

Rebuild the benchmark after the new run:

```bash
python3 scripts/build_golden_benchmark_pack.py \
  --benchmark-id benchmark-uploads-3 \
  --source-job uploads/3 \
  --new-job uploads/benchmark-uploads-3/new-selected-30k \
  --output-dir uploads/benchmark-uploads-3 \
  --project-root /var/www/html/demo/php/map/3D/gaussian_splat \
  --viewer-base-url https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_splat.html
```
```

- [ ] **Step 2: Add history note**

Append to `history.md`:

```markdown
## 2026-06-15 Golden Benchmark Pack

Decision:

- Start Phase G1.5.
- Use `uploads/3` as the first Golden Benchmark source.
- Compare old `uploads/3` output against a new selected-30k run from the same input video.
- Separate official-viewer and custom-viewer evidence.
- Keep `portableMode: false` to avoid copying large artifacts by default.

Deferred:

- Mesh Extraction
- GLB Export
- 3D Tiles
- MapLibre
- Cesium
- GIS Integration
```

- [ ] **Step 3: Run docs grep**

Run:

```bash
rg -n "G1.5|Golden Benchmark|benchmark-uploads-3|portableMode" docs/frame-quality-runbook.md history.md
```

Expected:

- Matches in both files.

- [ ] **Step 4: Commit docs**

```bash
git add docs/frame-quality-runbook.md history.md
git commit -m "docs: document golden benchmark workflow"
```

---

### Task 9: Final Verification

**Files:**
- Verify only.

- [ ] **Step 1: Run unit tests**

Run:

```bash
pytest -q tests/test_golden_benchmark_pack.py
```

Expected:

```text
all tests pass
```

- [ ] **Step 2: Run full test suite**

Run:

```bash
pytest -q
```

Expected:

```text
all tests pass
```

- [ ] **Step 3: Run Python compile checks**

Run:

```bash
python3 -m py_compile scripts/build_golden_benchmark_pack.py scripts/build_ab_evidence_report.py scripts/pipeline_timing.py
```

Expected:

- Exit code 0.
- No output.

- [ ] **Step 4: Inspect generated benchmark pack**

Run:

```bash
jq . uploads/benchmark-uploads-3/benchmark.json
sed -n '1,220p' uploads/benchmark-uploads-3/benchmark.md
sed -n '1,160p' uploads/benchmark-uploads-3/scorecard.md
sed -n '1,180p' uploads/benchmark-uploads-3/capture_diagnosis.md
```

Expected:

- `benchmark.json` has `benchmarkId`, `sourceJob`, `artifactPolicy`, and `cases`.
- `benchmark.md` has conclusion placeholders and viewer links.
- `scorecard.md` uses the fixed fields.
- `capture_diagnosis.md` has scene and camera diagnosis sections.

- [ ] **Step 5: Record final status**

Append final execution status to `uploads/benchmark-uploads-3/benchmark.md`:

```markdown
## Execution Status

- Unit tests:
- Full tests:
- Py compile:
- New selected-30k run:
- Official viewer:
- Custom viewer:
- Route confidence:
```

Fill each line with observed evidence.

---

## Self-Review

- Spec coverage: The plan covers artifact mapping, `portableMode: false`, fixed scorecard, `capture_diagnosis.md`, official/custom viewer separation, G1.5 roadmap position, and `uploads/3` as the first benchmark.
- Scope check: The plan does not implement Mesh Extraction, GLB, 3D Tiles, MapLibre, Cesium, GIS integration, Real-ESRGAN, or automated visual scoring.
- Placeholder scan: The plan intentionally includes human-fill review fields in generated Markdown templates, but no implementation step uses incomplete-work marker language.
- Type consistency: The JSON shape consistently uses `benchmarkId`, `sourceJob`, `artifactPolicy.portableMode`, `cases.old`, `cases.newSelected30k`, and `cases.reference`.
- Testability: Tasks 1 through 5 can be verified without running Nerfstudio; Task 6 is the long-running selected-30k reconstruction step; Tasks 7 through 9 verify visual evidence and final reports.
