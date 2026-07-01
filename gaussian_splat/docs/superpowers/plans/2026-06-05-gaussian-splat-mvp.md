# Gaussian Splat MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a first working Gaussian Splat pipeline in `/var/www/html/demo/php/map/3D/gaussian_splat`: sample MP4 input -> frames -> Nerfstudio `splatfacto` -> exported `splat.ply` -> browser viewer -> PHP job shell with log/status.

**Architecture:** Start with small command-line tools that can be tested without GPU training, then wrap them in the same PHP queue/cron pattern used by `jpgtoglb`. The browser MVP uses GaussianSplats3D for standalone `.ply` viewing first; Easymap/Cesium alignment is added after the `.ply` viewer is stable.

**Tech Stack:** PHP with existing `/inc/config.php` helpers, Bash, Python 3.10, pytest, ffmpeg, COLMAP through Nerfstudio, PyTorch CUDA `cu128`, Nerfstudio, gsplat, Three.js r155, `@mkkellogg/gaussian-splats-3d@0.4.7`, Easymap 7.

---

## Context

Current working directory:

```text
/var/www/html/demo/php/map/3D/gaussian_splat
```

Existing roadmap:

```text
/var/www/html/demo/php/map/3D/gaussian_splat/docs/plan.md
```

Reusable examples from the sibling project:

```text
/var/www/html/demo/php/map/3D/jpgtoglb/index.php
/var/www/html/demo/php/map/3D/jpgtoglb/api.php
/var/www/html/demo/php/map/3D/jpgtoglb/admin.php
/var/www/html/demo/php/map/3D/jpgtoglb/map.php
/var/www/html/demo/php/map/3D/jpgtoglb/js/function.js
/var/www/html/demo/php/map/3D/jpgtoglb/crontab/1_run.php
/var/www/html/demo/php/map/3D/jpgtoglb/crontab/inc/function.php
/var/www/html/demo/php/map/3D/jpgtoglb/migrate.php
```

Reusable sample inputs:

```text
/var/www/html/demo/php/map/3D/jpgtoglb/uploads/2/2.mp4
/var/www/html/demo/php/map/3D/jpgtoglb/uploads/7/7.mp4
/var/www/html/demo/php/map/3D/jpgtoglb/uploads/1/1.zip
/var/www/html/demo/php/map/3D/jpgtoglb/uploads/3/3.zip
```

Important constraints:

```text
CUDA stack: use cu128
Conda env path: /park/conda_vm/gs_scene
First output format: splat.ply
First browser renderer: GaussianSplats3D
Current folder is not a git repository at planning time
```

Official references used by this plan:

```text
PyTorch cu128 wheel index: https://pytorch.org/get-started/previous-versions/
Nerfstudio install flow: https://docs.nerf.studio/quickstart/installation.html
gsplat install flow: https://docs.gsplat.studio/main/index.html
GaussianSplats3D viewer API: https://github.com/mkkellogg/GaussianSplats3D
```

## Target File Structure

```text
/var/www/html/demo/php/map/3D/gaussian_splat/
  README.md
  .gitignore
  pytest.ini
  requirements-dev.txt
  migrate.php
  index.php
  api.php
  admin.php
  map.php
  viewer_splat.html
  crontab/
    1min.sh
    1_run.php
    inc/
      function.php
  js/
    gaussian_splat_viewer.js
    function.js
  scripts/
    install_gs_env.sh
    extract_frames.py
    write_default_transform.py
    build_qa_report.py
    process_nerfstudio.sh
    train_splat.sh
    export_splat.sh
    run_mvp_pipeline.sh
  tests/
    conftest.py
    test_fixture_sources.py
    test_install_gs_env.py
    test_extract_frames.py
    test_default_transform.py
    test_qa_report.py
    test_nerfstudio_scripts.py
    test_viewer_assets.py
  uploads/
    .gitkeep
```

Job directory shape:

```text
uploads/{id}/
  input/
    input.mp4
  images/
    frame_00001.jpg
  processed/
    transforms.json
  outputs/
  exports/
    splat.ply
  transform.json
  qa_report.json
  process.log
```

Status values:

```text
0 waiting
1 running
2 ready
3 failed
4 aborted
```

---

### Task 1: Bootstrap Project Tracking And Test Harness

**Files:**
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/README.md`
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/.gitignore`
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/pytest.ini`
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/requirements-dev.txt`
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/tests/conftest.py`
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_fixture_sources.py`
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/uploads/.gitkeep`

- [ ] **Step 1: Verify repository tracking state**

Run:

```bash
git rev-parse --show-toplevel
```

Expected in the current folder at planning time:

```text
fatal: not a git repository (or any of the parent directories): .git
```

- [ ] **Step 2: Initialize local git only when tracking is absent**

Run:

```bash
if ! git rev-parse --show-toplevel >/dev/null 2>&1; then git init; fi
git status --short --branch
```

Expected after initialization:

```text
## No commits yet on main
?? docs/
```

- [ ] **Step 3: Write pytest configuration**

Create `/var/www/html/demo/php/map/3D/gaussian_splat/pytest.ini`:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
addopts = -q
```

- [ ] **Step 4: Write development requirements**

Create `/var/www/html/demo/php/map/3D/gaussian_splat/requirements-dev.txt`:

```text
pytest
```

- [ ] **Step 4A: Write generated-artifact ignore rules**

Create `/var/www/html/demo/php/map/3D/gaussian_splat/.gitignore`:

```text
.pytest_cache/
__pycache__/
*.py[cod]
```

- [ ] **Step 5: Write shared test paths**

Create `/var/www/html/demo/php/map/3D/gaussian_splat/tests/conftest.py`:

```python
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SIBLING_JPGTOGLB = PROJECT_ROOT.parent / "jpgtoglb"
SAMPLE_MP4 = SIBLING_JPGTOGLB / "uploads" / "2" / "2.mp4"
SAMPLE_MP4_ALT = SIBLING_JPGTOGLB / "uploads" / "7" / "7.mp4"
SAMPLE_ZIP = SIBLING_JPGTOGLB / "uploads" / "1" / "1.zip"
```

- [ ] **Step 6: Write failing fixture-source test**

Create `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_fixture_sources.py`:

```python
from conftest import SAMPLE_MP4, SAMPLE_MP4_ALT, SAMPLE_ZIP


def test_jpgtoglb_sample_inputs_exist():
    assert SAMPLE_MP4.is_file()
    assert SAMPLE_MP4_ALT.is_file()
    assert SAMPLE_ZIP.is_file()
    assert SAMPLE_MP4.stat().st_size > 0
    assert SAMPLE_MP4_ALT.stat().st_size > 0
    assert SAMPLE_ZIP.stat().st_size > 0
```

- [ ] **Step 7: Run fixture test**

Run:

```bash
python3 -m pip install -r requirements-dev.txt
pytest tests/test_fixture_sources.py
```

Expected:

```text
1 passed
```

- [ ] **Step 8: Write README runbook**

Create `/var/www/html/demo/php/map/3D/gaussian_splat/README.md`:

````markdown
# Gaussian Splat MVP

This prototype converts MP4 captures into a Nerfstudio Gaussian Splat export and displays the exported `splat.ply` in a browser viewer.

## Local Paths

- Project: `/var/www/html/demo/php/map/3D/gaussian_splat`
- CUDA/Python environment: `/park/conda_vm/gs_scene`
- Sample MP4: `/var/www/html/demo/php/map/3D/jpgtoglb/uploads/2/2.mp4`
- Alternate sample MP4: `/var/www/html/demo/php/map/3D/jpgtoglb/uploads/7/7.mp4`

## First Smoke Test

The following commands become runnable after the environment, pipeline scripts, and viewer are created in later tasks.

```bash
bash scripts/install_gs_env.sh
bash scripts/run_mvp_pipeline.sh /var/www/html/demo/php/map/3D/jpgtoglb/uploads/2/2.mp4 uploads/local-smoke
```

Open:

```text
http://localhost/demo/php/map/3D/gaussian_splat/viewer_splat.html?src=uploads/local-smoke/exports/splat.ply
```
````

- [ ] **Step 9: Create upload placeholder**

Run:

```bash
mkdir -p uploads
touch uploads/.gitkeep
```

Expected:

```text
uploads/.gitkeep exists
```

- [ ] **Step 10: Commit bootstrap**

Run:

```bash
git add README.md .gitignore pytest.ini requirements-dev.txt tests/conftest.py tests/test_fixture_sources.py uploads/.gitkeep docs/superpowers/plans/2026-06-05-gaussian-splat-mvp.md
git commit -m "chore: bootstrap gaussian splat mvp project"
```

Expected:

```text
[main
```

---

### Task 2: CUDA cu128 Environment Installer

**Files:**
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/scripts/install_gs_env.sh`
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_install_gs_env.py`

- [ ] **Step 1: Write failing test for cu128 installer**

Create `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_install_gs_env.py`:

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "install_gs_env.sh"


def test_installer_uses_requested_cu128_stack():
    text = SCRIPT.read_text()
    assert "ENV_PATH=/park/conda_vm/gs_scene" in text
    assert "python=3.10" in text
    assert "https://download.pytorch.org/whl/cu128" in text
    assert "torch==2.10.0" in text
    assert "torchvision==0.25.0" in text
    assert "torchaudio==2.10.0" in text
    assert "cuda-toolkit=12.8.0" in text
    assert "setuptools==80.10.2" in text
    assert "--no-build-isolation" in text
    assert "CUDA_HOME=\"$ENV_PATH\"" in text
    assert "CC=\"$ENV_PATH/bin/x86_64-conda-linux-gnu-gcc\"" in text
    assert "CXX=\"$ENV_PATH/bin/x86_64-conda-linux-gnu-g++\"" in text
    assert "install nerfstudio" in text
    assert "install gsplat" in text
    assert "torch.cuda.is_available()" in text


def test_installer_is_strict_bash():
    text = SCRIPT.read_text()
    assert text.startswith("#!/usr/bin/env bash")
    assert "set -euo pipefail" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_install_gs_env.py
```

Expected:

```text
FAILED
No such file or directory
```

- [ ] **Step 3: Write installer implementation**

Create `/var/www/html/demo/php/map/3D/gaussian_splat/scripts/install_gs_env.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

CONDA=${CONDA:-/opt/miniconda3/bin/conda}
ENV_PATH=/park/conda_vm/gs_scene

if [ ! -x "$CONDA" ]; then
  echo "conda not found at $CONDA" >&2
  exit 1
fi

if [ ! -d "$ENV_PATH" ]; then
  "$CONDA" create -y -p "$ENV_PATH" python=3.10
fi

if ! "$ENV_PATH/bin/nvcc" --version 2>/dev/null | grep -q "release 12.8"; then
  "$CONDA" install -y -p "$ENV_PATH" -c nvidia/label/cuda-12.8.0 cuda-toolkit=12.8.0
fi

export CUDA_HOME="$ENV_PATH"
export PATH="$ENV_PATH/bin:$PATH"
export LD_LIBRARY_PATH="$ENV_PATH/lib:${LD_LIBRARY_PATH:-}"
export CC="$ENV_PATH/bin/x86_64-conda-linux-gnu-gcc"
export CXX="$ENV_PATH/bin/x86_64-conda-linux-gnu-g++"
export CUDAHOSTCXX="$CXX"

"$ENV_PATH/bin/python" -m pip install --upgrade pip wheel
"$ENV_PATH/bin/pip" install setuptools==80.10.2

"$ENV_PATH/bin/pip" install \
  torch==2.10.0 \
  torchvision==0.25.0 \
  torchaudio==2.10.0 \
  --index-url https://download.pytorch.org/whl/cu128

"$ENV_PATH/bin/pip" install ninja

CUDA_ARCH="$("$ENV_PATH/bin/python" - <<'PY'
import torch
if torch.cuda.is_available():
    major, minor = torch.cuda.get_device_capability(0)
    print(f"{major}{minor}")
PY
)"

if [ -n "$CUDA_ARCH" ]; then
  export TCNN_CUDA_ARCHITECTURES="$CUDA_ARCH"
fi

"$ENV_PATH/bin/nvcc" --version
"$ENV_PATH/bin/pip" install --no-build-isolation git+https://github.com/NVlabs/tiny-cuda-nn/#subdirectory=bindings/torch
"$ENV_PATH/bin/pip" install nerfstudio
"$ENV_PATH/bin/pip" install gsplat

"$ENV_PATH/bin/python" - <<'PY'
import torch
print("torch", torch.__version__)
print("cuda available", torch.cuda.is_available())
print("torch cuda", torch.version.cuda)
if not torch.cuda.is_available():
    raise SystemExit("CUDA is not available to PyTorch")
PY

"$ENV_PATH/bin/ns-train" --help >/dev/null
"$ENV_PATH/bin/ns-process-data" --help >/dev/null
"$ENV_PATH/bin/ns-export" --help >/dev/null

echo "Gaussian Splat environment ready: $ENV_PATH"
```

- [ ] **Step 4: Make installer executable**

Run:

```bash
chmod +x scripts/install_gs_env.sh
```

Expected:

```text
scripts/install_gs_env.sh is executable
```

- [ ] **Step 5: Run unit test**

Run:

```bash
pytest tests/test_install_gs_env.py
```

Expected:

```text
2 passed
```

- [ ] **Step 6: Run installer smoke test on GPU machine**

Run:

```bash
bash scripts/install_gs_env.sh
```

Expected:

```text
cuda available True
Gaussian Splat environment ready: /park/conda_vm/gs_scene
```

- [ ] **Step 7: Commit installer**

Run:

```bash
git add scripts/install_gs_env.sh tests/test_install_gs_env.py
git commit -m "chore: add cu128 gaussian splat environment installer"
```

Expected:

```text
[main
```

---

### Task 3: Frame Extraction CLI

**Files:**
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/scripts/extract_frames.py`
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_extract_frames.py`

- [ ] **Step 1: Write failing tests**

Create `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_extract_frames.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
pytest tests/test_extract_frames.py
```

Expected:

```text
FAILED
ModuleNotFoundError
```

- [ ] **Step 3: Write extraction implementation**

Create `/var/www/html/demo/php/map/3D/gaussian_splat/scripts/extract_frames.py`:

```python
#!/usr/bin/env python3
import argparse
import subprocess
from pathlib import Path


def build_ffmpeg_command(input_video: Path, output_dir: Path, fps: int, max_frames: int, width: int) -> list[str]:
    return [
        "ffmpeg",
        "-y",
        "-i",
        str(input_video),
        "-vf",
        f"fps={fps},scale={width}:-1",
        "-frames:v",
        str(max_frames),
        "-an",
        "-f",
        "image2",
        str(output_dir / "frame_%05d.jpg"),
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract frames for Gaussian Splat reconstruction.")
    parser.add_argument("input_video", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--fps", type=int, default=2)
    parser.add_argument("--max-frames", type=int, default=120)
    parser.add_argument("--width", type=int, default=1600)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.input_video.is_file():
        raise SystemExit(f"input video not found: {args.input_video}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    cmd = build_ffmpeg_command(args.input_video, args.output_dir, args.fps, args.max_frames, args.width)
    if args.dry_run:
        print(" ".join(cmd))
        return 0
    subprocess.run(cmd, check=True)
    frame_count = len(list(args.output_dir.glob("frame_*.jpg")))
    print(f"frames={frame_count}")
    if frame_count < 8:
        raise SystemExit("frame count is lower than 8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Make script executable**

Run:

```bash
chmod +x scripts/extract_frames.py
```

Expected:

```text
scripts/extract_frames.py is executable
```

- [ ] **Step 5: Run unit tests**

Run:

```bash
pytest tests/test_extract_frames.py
```

Expected:

```text
2 passed
```

- [ ] **Step 6: Run dry-run against sample MP4**

Run:

```bash
python3 scripts/extract_frames.py /var/www/html/demo/php/map/3D/jpgtoglb/uploads/2/2.mp4 uploads/dry-run/images --dry-run
```

Expected:

```text
ffmpeg -y -i /var/www/html/demo/php/map/3D/jpgtoglb/uploads/2/2.mp4 -vf fps=2,scale=1600:-1 -frames:v 120 -an -f image2 uploads/dry-run/images/frame_%05d.jpg
```

- [ ] **Step 7: Run real extraction against sample MP4**

Run:

```bash
rm -rf uploads/frame-smoke
python3 scripts/extract_frames.py /var/www/html/demo/php/map/3D/jpgtoglb/uploads/2/2.mp4 uploads/frame-smoke/images
find uploads/frame-smoke/images -name 'frame_*.jpg' | wc -l
```

Expected:

```text
8 or more
```

- [ ] **Step 8: Commit frame extractor**

Run:

```bash
git add scripts/extract_frames.py tests/test_extract_frames.py uploads/.gitkeep
git commit -m "feat: add gaussian splat frame extraction cli"
```

Expected:

```text
[main
```

---

### Task 4: Default Transform JSON Writer

**Files:**
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/scripts/write_default_transform.py`
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_default_transform.py`

- [ ] **Step 1: Write failing tests**

Create `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_default_transform.py`:

```python
import json
from scripts.write_default_transform import build_transform


def test_build_transform_matches_alignment_schema():
    data = build_transform("site001", 121.456, 25.123, 12.5)
    assert data["job_id"] == "site001"
    assert data["source_type"] == "gaussian_splat"
    assert data["origin"] == {"lng": 121.456, "lat": 25.123, "height": 12.5}
    assert data["transform"] == {"heading": 0.0, "pitch": 0.0, "roll": 0.0, "scale": 1.0}
    assert data["camera"] == {
        "lng": None,
        "lat": None,
        "height": None,
        "heading": None,
        "pitch": None,
        "roll": None,
    }


def test_transform_is_json_serializable():
    encoded = json.dumps(build_transform("abc", 120.0, 24.0, 0.0), ensure_ascii=False)
    assert '"source_type": "gaussian_splat"' in encoded
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
pytest tests/test_default_transform.py
```

Expected:

```text
FAILED
ModuleNotFoundError
```

- [ ] **Step 3: Write transform writer**

Create `/var/www/html/demo/php/map/3D/gaussian_splat/scripts/write_default_transform.py`:

```python
#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any


def build_transform(job_id: str, lng: float, lat: float, height: float) -> dict[str, Any]:
    return {
        "job_id": job_id,
        "source_type": "gaussian_splat",
        "origin": {
            "lng": lng,
            "lat": lat,
            "height": height,
        },
        "transform": {
            "heading": 0.0,
            "pitch": 0.0,
            "roll": 0.0,
            "scale": 1.0,
        },
        "camera": {
            "lng": None,
            "lat": None,
            "height": None,
            "heading": None,
            "pitch": None,
            "roll": None,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write default transform.json for a Gaussian Splat job.")
    parser.add_argument("job_id")
    parser.add_argument("output", type=Path)
    parser.add_argument("--lng", type=float, default=120.6647066)
    parser.add_argument("--lat", type=float, default=24.1504731)
    parser.add_argument("--height", type=float, default=0.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data = build_transform(args.job_id, args.lng, args.lat, args.height)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests**

Run:

```bash
pytest tests/test_default_transform.py
```

Expected:

```text
2 passed
```

- [ ] **Step 5: Write a smoke transform**

Run:

```bash
python3 scripts/write_default_transform.py local-smoke uploads/local-smoke/transform.json --lng 120.6647066 --lat 24.1504731 --height 0
python3 -m json.tool uploads/local-smoke/transform.json >/dev/null
```

Expected:

```text
uploads/local-smoke/transform.json
```

- [ ] **Step 6: Commit transform writer**

Run:

```bash
git add scripts/write_default_transform.py tests/test_default_transform.py
git commit -m "feat: add gaussian splat transform writer"
```

Expected:

```text
[main
```

---

### Task 5: Nerfstudio Pipeline Wrapper Scripts

**Files:**
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/scripts/process_nerfstudio.sh`
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/scripts/train_splat.sh`
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/scripts/export_splat.sh`
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_nerfstudio_scripts.py`

- [ ] **Step 1: Write failing wrapper tests**

Create `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_nerfstudio_scripts.py`:

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_script(name: str) -> str:
    return (ROOT / "scripts" / name).read_text()


def test_process_script_uses_ns_process_data_images():
    text = read_script("process_nerfstudio.sh")
    assert "ENV_PATH=/park/conda_vm/gs_scene" in text
    assert '"$ENV_PATH/bin/ns-process-data" images' in text
    assert "--data" in text
    assert "--output-dir" in text


def test_train_script_uses_splatfacto():
    text = read_script("train_splat.sh")
    assert '"$ENV_PATH/bin/ns-train" splatfacto' in text
    assert "--data" in text
    assert "--output-dir" in text


def test_export_script_exports_gaussian_splat_ply():
    text = read_script("export_splat.sh")
    assert '"$ENV_PATH/bin/ns-export" gaussian-splat' in text
    assert "--load-config" in text
    assert "--output-dir" in text
    assert "splat.ply" in text
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
pytest tests/test_nerfstudio_scripts.py
```

Expected:

```text
FAILED
No such file or directory
```

- [ ] **Step 3: Write process wrapper**

Create `/var/www/html/demo/php/map/3D/gaussian_splat/scripts/process_nerfstudio.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

ENV_PATH=/park/conda_vm/gs_scene
IMAGES_DIR=${1:?usage: process_nerfstudio.sh images_dir processed_dir}
PROCESSED_DIR=${2:?usage: process_nerfstudio.sh images_dir processed_dir}

if [ ! -x "$ENV_PATH/bin/ns-process-data" ]; then
  echo "ns-process-data not found. Run scripts/install_gs_env.sh first." >&2
  exit 1
fi

mkdir -p "$PROCESSED_DIR"

"$ENV_PATH/bin/ns-process-data" images \
  --data "$IMAGES_DIR" \
  --output-dir "$PROCESSED_DIR"

test -f "$PROCESSED_DIR/transforms.json"
echo "$PROCESSED_DIR/transforms.json"
```

- [ ] **Step 4: Write train wrapper**

Create `/var/www/html/demo/php/map/3D/gaussian_splat/scripts/train_splat.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

ENV_PATH=/park/conda_vm/gs_scene
PROCESSED_DIR=${1:?usage: train_splat.sh processed_dir outputs_dir}
OUTPUTS_DIR=${2:?usage: train_splat.sh processed_dir outputs_dir}

if [ ! -x "$ENV_PATH/bin/ns-train" ]; then
  echo "ns-train not found. Run scripts/install_gs_env.sh first." >&2
  exit 1
fi

mkdir -p "$OUTPUTS_DIR"

"$ENV_PATH/bin/ns-train" splatfacto \
  --data "$PROCESSED_DIR" \
  --output-dir "$OUTPUTS_DIR"

CONFIG_PATH="$(find "$OUTPUTS_DIR" -path '*/splatfacto/*/config.yml' -type f | sort | tail -n 1)"
test -f "$CONFIG_PATH"
echo "$CONFIG_PATH"
```

- [ ] **Step 5: Write export wrapper**

Create `/var/www/html/demo/php/map/3D/gaussian_splat/scripts/export_splat.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

ENV_PATH=/park/conda_vm/gs_scene
CONFIG_PATH=${1:?usage: export_splat.sh config_yml exports_dir}
EXPORTS_DIR=${2:?usage: export_splat.sh config_yml exports_dir}

if [ ! -x "$ENV_PATH/bin/ns-export" ]; then
  echo "ns-export not found. Run scripts/install_gs_env.sh first." >&2
  exit 1
fi

mkdir -p "$EXPORTS_DIR"

"$ENV_PATH/bin/ns-export" gaussian-splat \
  --load-config "$CONFIG_PATH" \
  --output-dir "$EXPORTS_DIR"

test -f "$EXPORTS_DIR/splat.ply"
echo "$EXPORTS_DIR/splat.ply"
```

- [ ] **Step 6: Make wrappers executable**

Run:

```bash
chmod +x scripts/process_nerfstudio.sh scripts/train_splat.sh scripts/export_splat.sh
```

Expected:

```text
all three wrapper scripts are executable
```

- [ ] **Step 7: Run wrapper tests**

Run:

```bash
pytest tests/test_nerfstudio_scripts.py
```

Expected:

```text
3 passed
```

- [ ] **Step 8: Commit wrappers**

Run:

```bash
git add scripts/process_nerfstudio.sh scripts/train_splat.sh scripts/export_splat.sh tests/test_nerfstudio_scripts.py
git commit -m "feat: add nerfstudio gaussian splat wrappers"
```

Expected:

```text
[main
```

---

### Task 6: QA Report Builder

**Files:**
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/scripts/build_qa_report.py`
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_qa_report.py`

- [ ] **Step 1: Write failing QA tests**

Create `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_qa_report.py`:

```python
import json
import subprocess
import sys
from pathlib import Path
from scripts.build_qa_report import build_report


def test_build_report_flags_low_registration(tmp_path):
    images = tmp_path / "images"
    processed = tmp_path / "processed"
    exports = tmp_path / "exports"
    images.mkdir()
    processed.mkdir()
    exports.mkdir()
    for i in range(10):
        (images / f"frame_{i:05d}.jpg").write_bytes(b"jpg")
    transforms = {
        "frames": [{"file_path": f"images/frame_{i:05d}.jpg"} for i in range(6)]
    }
    (processed / "transforms.json").write_text(json.dumps(transforms))
    (exports / "splat.ply").write_bytes(b"x" * 1024)

    report = build_report("site001", images, processed, exports, has_transform=True)
    assert report["frame_count"] == 10
    assert report["registered_frame_count"] == 6
    assert report["registered_ratio"] == 0.6
    assert report["viewer_ready"] is True
    assert "registered_ratio lower than 0.8" in report["warnings"]


def test_build_report_marks_missing_splat_not_ready(tmp_path):
    images = tmp_path / "images"
    processed = tmp_path / "processed"
    exports = tmp_path / "exports"
    images.mkdir()
    processed.mkdir()
    exports.mkdir()
    (processed / "transforms.json").write_text('{"frames": []}')

    report = build_report("site002", images, processed, exports, has_transform=False)
    assert report["viewer_ready"] is False
    assert "splat.ply missing" in report["warnings"]
    assert "transform.json missing" in report["warnings"]


def test_build_report_handles_malformed_transforms_json(tmp_path):
    images = tmp_path / "images"
    processed = tmp_path / "processed"
    exports = tmp_path / "exports"
    images.mkdir()
    processed.mkdir()
    exports.mkdir()
    (images / "frame_00000.jpg").write_bytes(b"jpg")
    (processed / "transforms.json").write_text("{")
    (exports / "splat.ply").write_bytes(b"x")

    report = build_report("site003", images, processed, exports, has_transform=True)
    assert report["registered_frame_count"] == 0
    assert "transforms.json invalid" in report["warnings"]


def test_build_report_flags_non_list_frames_invalid(tmp_path):
    images = tmp_path / "images"
    processed = tmp_path / "processed"
    exports = tmp_path / "exports"
    images.mkdir()
    processed.mkdir()
    exports.mkdir()
    (processed / "transforms.json").write_text(json.dumps({"frames": {"bad": True}}))

    report = build_report("site004", images, processed, exports, has_transform=True)
    assert report["registered_frame_count"] == 0
    assert "transforms.json invalid" in report["warnings"]


def test_build_report_flags_non_object_transforms_invalid(tmp_path):
    images = tmp_path / "images"
    processed = tmp_path / "processed"
    exports = tmp_path / "exports"
    images.mkdir()
    processed.mkdir()
    exports.mkdir()
    (processed / "transforms.json").write_text("[]")

    report = build_report("site005", images, processed, exports, has_transform=True)
    assert report["registered_frame_count"] == 0
    assert "transforms.json invalid" in report["warnings"]


def test_build_report_viewer_ready_only_requires_splat(tmp_path):
    images = tmp_path / "images"
    processed = tmp_path / "processed"
    exports = tmp_path / "exports"
    images.mkdir()
    processed.mkdir()
    exports.mkdir()
    (processed / "transforms.json").write_text('{"frames": []}')
    (exports / "splat.ply").write_bytes(b"x")

    report = build_report("site006", images, processed, exports, has_transform=False)
    assert report["viewer_ready"] is True
    assert "transform.json missing" in report["warnings"]


def test_cli_writes_qa_report_and_prints_output_path(tmp_path):
    job_dir = tmp_path / "job"
    images = job_dir / "images"
    processed = job_dir / "processed"
    exports = job_dir / "exports"
    images.mkdir(parents=True)
    processed.mkdir()
    exports.mkdir()
    (images / "frame_00000.jpg").write_bytes(b"jpg")
    (processed / "transforms.json").write_text('{"frames": []}')
    (exports / "splat.ply").write_bytes(b"x")

    script = Path(__file__).resolve().parents[1] / "scripts" / "build_qa_report.py"
    result = subprocess.run(
        [sys.executable, str(script), "site007", str(job_dir)],
        check=True,
        capture_output=True,
        text=True,
    )

    output = job_dir / "qa_report.json"
    assert output.is_file()
    assert str(output) in result.stdout
    report = json.loads(output.read_text())
    assert report["job_id"] == "site007"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
pytest tests/test_qa_report.py
```

Expected:

```text
FAILED
ModuleNotFoundError
```

- [ ] **Step 3: Write QA implementation**

Create `/var/www/html/demo/php/map/3D/gaussian_splat/scripts/build_qa_report.py`:

```python
#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any, NamedTuple


class RegisteredFrames(NamedTuple):
    count: int
    invalid: bool


def count_registered_frames(transforms_json: Path) -> RegisteredFrames:
    if not transforms_json.is_file():
        return RegisteredFrames(0, False)
    try:
        data = json.loads(transforms_json.read_text())
    except json.JSONDecodeError:
        return RegisteredFrames(0, True)
    if not isinstance(data, dict):
        return RegisteredFrames(0, True)
    frames = data.get("frames", [])
    if not isinstance(frames, list):
        return RegisteredFrames(0, True)
    return RegisteredFrames(len(frames), False)


def build_report(job_id: str, images_dir: Path, processed_dir: Path, exports_dir: Path, has_transform: bool) -> dict[str, Any]:
    frame_count = len(list(images_dir.glob("*.jpg"))) + len(list(images_dir.glob("*.png")))
    registered_frames = count_registered_frames(processed_dir / "transforms.json")
    registered_count = registered_frames.count
    ratio = round(registered_count / frame_count, 2) if frame_count else 0.0
    splat_path = exports_dir / "splat.ply"
    splat_size_mb = round(splat_path.stat().st_size / 1024 / 1024, 2) if splat_path.is_file() else 0.0

    warnings: list[str] = []
    if frame_count < 8:
        warnings.append("frame_count lower than 8")
    if ratio < 0.8:
        warnings.append("registered_ratio lower than 0.8")
    if not splat_path.is_file():
        warnings.append("splat.ply missing")
    if splat_size_mb > 300:
        warnings.append("splat file larger than 300MB")
    if not has_transform:
        warnings.append("transform.json missing")
    if registered_frames.invalid:
        warnings.append("transforms.json invalid")

    return {
        "job_id": job_id,
        "frame_count": frame_count,
        "registered_frame_count": registered_count,
        "registered_ratio": ratio,
        "splat_file_size_mb": splat_size_mb,
        "has_transform": has_transform,
        "viewer_ready": splat_path.is_file(),
        "warnings": warnings,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Gaussian Splat QA report.")
    parser.add_argument("job_id")
    parser.add_argument("job_dir", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(
        args.job_id,
        args.job_dir / "images",
        args.job_dir / "processed",
        args.job_dir / "exports",
        (args.job_dir / "transform.json").is_file(),
    )
    output = args.job_dir / "qa_report.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run QA tests**

Run:

```bash
pytest tests/test_qa_report.py
```

Expected:

```text
2 passed
```

- [ ] **Step 5: Commit QA builder**

Run:

```bash
git add scripts/build_qa_report.py tests/test_qa_report.py
git commit -m "feat: add gaussian splat qa report builder"
```

Expected:

```text
[main
```

---

### Task 7: End-to-End MVP Pipeline Script

**Files:**
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/scripts/run_mvp_pipeline.sh`
- Modify: `/var/www/html/demo/php/map/3D/gaussian_splat/scripts/process_nerfstudio.sh`
- Modify: `/var/www/html/demo/php/map/3D/gaussian_splat/scripts/train_splat.sh`
- Modify: `/var/www/html/demo/php/map/3D/gaussian_splat/scripts/export_splat.sh`
- Modify: `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_nerfstudio_scripts.py`

- [x] **Step 1: Extend wrapper tests**

Append this test to `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_nerfstudio_scripts.py`:

```python
def test_run_pipeline_wires_all_steps_in_order():
    text = read_script("run_mvp_pipeline.sh")
    assert "scripts/extract_frames.py" in text
    assert "scripts/process_nerfstudio.sh" in text
    assert "scripts/train_splat.sh" in text
    assert "scripts/export_splat.sh" in text
    assert "scripts/write_default_transform.py" in text
    assert "scripts/build_qa_report.py" in text
    assert 'TRANSFORMS_PATH="$(bash "$PROJECT_ROOT/scripts/process_nerfstudio.sh"' in text
    assert 'CONFIG_PATH="$(bash "$PROJECT_ROOT/scripts/train_splat.sh"' in text
    assert 'SPLAT_PATH="$(bash "$PROJECT_ROOT/scripts/export_splat.sh"' in text
    assert 'echo "$SPLAT_PATH"' in text
```

- [x] **Step 2: Run test to verify failure**

Run:

```bash
pytest tests/test_nerfstudio_scripts.py::test_run_pipeline_wires_all_steps_in_order
```

Expected:

```text
FAILED
No such file or directory
```

- [x] **Step 3: Write pipeline implementation**

Create `/var/www/html/demo/php/map/3D/gaussian_splat/scripts/run_mvp_pipeline.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

INPUT_VIDEO=${1:?usage: run_mvp_pipeline.sh input_video job_dir}
JOB_DIR=${2:?usage: run_mvp_pipeline.sh input_video job_dir}
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAGED_INPUT="$JOB_DIR/input/input.mp4"
UPLOADS_DIR="$PROJECT_ROOT/uploads"
JOB_PARENT="$(dirname "$JOB_DIR")"
UPLOADS_REAL="$(realpath "$UPLOADS_DIR")"
JOB_PARENT_REAL="$(realpath -m "$JOB_PARENT")"
JOB_DIR_REAL="$(realpath -m "$JOB_DIR")"

case "$JOB_PARENT_REAL" in
  "$UPLOADS_REAL"|"$UPLOADS_REAL"/*) ;;
  *)
    echo "job_dir must be under $UPLOADS_DIR: $JOB_DIR" >&2
    exit 1
    ;;
esac

case "$JOB_DIR_REAL" in
  "$UPLOADS_REAL"/*) ;;
  *)
    echo "job_dir must be under $UPLOADS_DIR: $JOB_DIR" >&2
    exit 1
    ;;
esac

mkdir -p "$JOB_DIR/input" "$JOB_DIR/images" "$JOB_DIR/processed" "$JOB_DIR/outputs" "$JOB_DIR/exports"
chmod a+rx "$JOB_PARENT"
chmod a+rx "$JOB_DIR" "$JOB_DIR/exports"
if [ ! -e "$STAGED_INPUT" ] || [ "$(realpath "$INPUT_VIDEO")" != "$(realpath "$STAGED_INPUT")" ]; then
  cp "$INPUT_VIDEO" "$STAGED_INPUT"
fi

python3 "$PROJECT_ROOT/scripts/extract_frames.py" "$STAGED_INPUT" "$JOB_DIR/images" >&2
TRANSFORMS_PATH="$(bash "$PROJECT_ROOT/scripts/process_nerfstudio.sh" "$JOB_DIR/images" "$JOB_DIR/processed")"
test -f "$TRANSFORMS_PATH"
CONFIG_PATH="$(bash "$PROJECT_ROOT/scripts/train_splat.sh" "$JOB_DIR/processed" "$JOB_DIR/outputs")"
SPLAT_PATH="$(bash "$PROJECT_ROOT/scripts/export_splat.sh" "$CONFIG_PATH" "$JOB_DIR/exports")"
python3 "$PROJECT_ROOT/scripts/write_default_transform.py" "$(basename "$JOB_DIR")" "$JOB_DIR/transform.json" >&2
python3 "$PROJECT_ROOT/scripts/build_qa_report.py" "$(basename "$JOB_DIR")" "$JOB_DIR" >&2
chmod a+r "$SPLAT_PATH" "$JOB_DIR/transform.json" "$JOB_DIR/qa_report.json"

echo "$SPLAT_PATH"
```

- [x] **Step 4: Make pipeline executable**

Run:

```bash
chmod +x scripts/run_mvp_pipeline.sh
```

Expected:

```text
scripts/run_mvp_pipeline.sh is executable
```

- [x] **Step 5: Run tests**

Run:

```bash
pytest tests/test_nerfstudio_scripts.py
```

Expected:

```text
5 passed
```

- [x] **Step 6: Run pipeline smoke test**

Run:

```bash
GS_TRAIN_MAX_ITERATIONS=25 timeout 900 bash scripts/run_mvp_pipeline.sh /var/www/html/demo/php/map/3D/jpgtoglb/uploads/2/2.mp4 uploads/local-smoke
```

Expected:

```text
uploads/local-smoke/exports/splat.ply
```

Actual notes:
- First cu128 `gsplat_cuda` build for this GPU took longer than 900 seconds, so it was prewarmed once with a longer timeout.
- `scripts/train_splat.sh` now caps torch extension build parallelism with `MAX_JOBS="${GS_TORCH_EXT_MAX_JOBS:-${MAX_JOBS:-2}}"`.
- `scripts/train_splat.sh` passes `--viewer.quit-on-train-completion True` so pipeline jobs do not hang after training.
- `scripts/export_splat.sh` exports `TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1` for Nerfstudio checkpoint compatibility with PyTorch 2.6+.
- `scripts/run_mvp_pipeline.sh` skips copying when the input is already `$JOB_DIR/input/input.mp4`, matching the future worker call shape.
- `scripts/run_mvp_pipeline.sh` redirects helper progress output to stderr, leaving stdout as the final `splat.ply` path only.
- `scripts/run_mvp_pipeline.sh` only opens permissions for job dirs under `$PROJECT_ROOT/uploads`, rejects symlink escapes, then makes generated viewer artifacts web-readable.
- `.gitignore` ignores generated `uploads/*` artifacts while preserving `uploads/.gitkeep`.
- Final clean cached same-input smoke completed in 108.56 seconds and printed only `uploads/local-smoke/exports/splat.ply` on stdout.

- [x] **Step 7: Verify smoke outputs**

Run:

```bash
test -f uploads/local-smoke/processed/transforms.json
test -f "$(find uploads/local-smoke/outputs -path '*/splatfacto/*/config.yml' -type f | sort | tail -n 1)"
test -f uploads/local-smoke/exports/splat.ply
python3 -m json.tool uploads/local-smoke/transform.json >/dev/null
python3 -m json.tool uploads/local-smoke/qa_report.json >/dev/null
```

Expected:

```text
all commands exit 0
```

Actual:

```text
viewer_ready=True
registered_frame_count=25
warnings=['registered_ratio lower than 0.8']
splat_bytes=824455
pytest: 19 passed
```

- [x] **Step 8: Commit pipeline**

Run:

```bash
git add scripts/run_mvp_pipeline.sh scripts/process_nerfstudio.sh scripts/train_splat.sh scripts/export_splat.sh tests/test_nerfstudio_scripts.py docs/superpowers/plans/2026-06-05-gaussian-splat-mvp.md
git commit -m "feat: add gaussian splat mvp pipeline script"
```

Expected:

```text
[main
```

---

### Task 8: Standalone Gaussian Splat Viewer

**Files:**
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/viewer_splat.html`
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/js/gaussian_splat_viewer.js`
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_viewer_assets.py`

- [x] **Step 1: Write failing viewer asset tests**

Create `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_viewer_assets.py`:

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_viewer_html_loads_module_script_and_canvas_root():
    text = (ROOT / "viewer_splat.html").read_text()
    assert '<div id="viewer-root">' in text
    assert 'js/gaussian_splat_viewer.js' in text
    assert '@mkkellogg/gaussian-splats-3d@0.4.7' in text
    assert 'three@0.155.0' in text
    assert "right: 12px" in text
    assert "max-width: calc(100vw - 24px)" in text
    assert "overflow-wrap: anywhere" in text


def test_viewer_js_uses_add_splat_scene_and_query_src():
    text = (ROOT / "js" / "gaussian_splat_viewer.js").read_text()
    assert "new GaussianSplats3D.Viewer" in text
    assert "addSplatScene" in text
    assert "URLSearchParams" in text
    assert "sharedMemoryForWorkers: false" in text
    assert "splatAlphaRemovalThreshold" in text
    assert 'if (!src)' in text
    assert "return" in text
    assert "uploads/local-smoke/exports/splat.ply" not in text
```

- [x] **Step 2: Run tests to verify failure**

Run:

```bash
pytest tests/test_viewer_assets.py
```

Expected:

```text
FAILED
No such file or directory
```

- [x] **Step 3: Write viewer HTML**

Create `/var/www/html/demo/php/map/3D/gaussian_splat/viewer_splat.html`:

```html
<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Gaussian Splat Viewer</title>
  <style>
    html, body, #viewer-root {
      margin: 0;
      width: 100%;
      height: 100%;
      overflow: hidden;
      background: #101820;
      color: #f4f7fb;
      font-family: Arial, "Noto Sans TC", sans-serif;
    }
    #status {
      position: fixed;
      left: 12px;
      right: 12px;
      top: 12px;
      z-index: 10;
      max-width: calc(100vw - 24px);
      padding: 8px 10px;
      border: 1px solid rgba(255,255,255,.2);
      border-radius: 6px;
      background: rgba(16,24,32,.82);
      font-size: 13px;
      line-height: 1.5;
      overflow-wrap: anywhere;
    }
  </style>
  <script type="importmap">
    {
      "imports": {
        "three": "https://cdn.jsdelivr.net/npm/three@0.155.0/build/three.module.js",
        "@mkkellogg/gaussian-splats-3d": "https://cdn.jsdelivr.net/npm/@mkkellogg/gaussian-splats-3d@0.4.7/build/gaussian-splats-3d.module.min.js"
      }
    }
  </script>
</head>
<body>
  <div id="viewer-root"></div>
  <div id="status">Loading</div>
  <script type="module" src="js/gaussian_splat_viewer.js"></script>
</body>
</html>
```

- [x] **Step 4: Write viewer JS**

Create `/var/www/html/demo/php/map/3D/gaussian_splat/js/gaussian_splat_viewer.js`:

```javascript
import * as GaussianSplats3D from "@mkkellogg/gaussian-splats-3d";

const params = new URLSearchParams(window.location.search);
const src = params.get("src");
const statusEl = document.getElementById("status");

function setStatus(message) {
  statusEl.textContent = message;
}

function main() {
  if (!src) {
    setStatus("Provide a splat file with ?src=path/to/splat.ply");
    return;
  }

  const viewer = new GaussianSplats3D.Viewer({
    rootElement: document.getElementById("viewer-root"),
    cameraUp: [0, -1, -0.6],
    initialCameraPosition: [-1, -4, 6],
    initialCameraLookAt: [0, 0, 0],
    sharedMemoryForWorkers: false,
    gpuAcceleratedSort: false,
    halfPrecisionCovariancesOnGPU: true,
    ignoreDevicePixelRatio: false,
    sphericalHarmonicsDegree: 0,
  });

  setStatus(`Loading ${src}`);

  viewer.addSplatScene(src, {
    splatAlphaRemovalThreshold: 5,
    showLoadingUI: true,
    position: [0, 0, 0],
    rotation: [0, 0, 0, 1],
    scale: [1, 1, 1],
  })
    .then(() => {
      viewer.start();
      setStatus(`Ready: ${src}`);
    })
    .catch((error) => {
      console.error(error);
      setStatus(`Load failed: ${error.message}`);
    });
}

main();
```

- [x] **Step 5: Run viewer asset tests**

Run:

```bash
pytest tests/test_viewer_assets.py
```

Expected:

```text
2 passed
```

- [x] **Step 6: Browser smoke test**

Run:

```bash
test -f uploads/local-smoke/exports/splat.ply
```

Open:

```text
http://localhost/demo/php/map/3D/gaussian_splat/viewer_splat.html?src=uploads/local-smoke/exports/splat.ply
```

Expected:

```text
Status text changes from Loading to Ready and the splat scene is visible.
```

Actual:

```text
HTTP 200 for viewer_splat.html, js/gaussian_splat_viewer.js, and uploads/local-smoke/exports/splat.ply
Status: Ready: uploads/local-smoke/exports/splat.ply
Console errors: 0
Desktop canvas: 1280x720, nonblank pixel check passed
Mobile canvas: 390x844, nonblank pixel check passed
Drag interaction changed 364245 pixels
Opening without ?src= shows an explicit "Provide a splat file" status instead of assuming an ignored smoke artifact.
Pipeline re-run after permission guard completed in 108.56 seconds, printed only uploads/local-smoke/exports/splat.ply, and generated an HTTP 200 splat.ply.
```

- [x] **Step 7: Commit viewer**

Run:

```bash
git add viewer_splat.html js/gaussian_splat_viewer.js tests/test_viewer_assets.py
git commit -m "feat: add standalone gaussian splat viewer"
```

Expected:

```text
[main
```

---

### Task 9: Database Migration And Upload API

**Files:**
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/migrate.php`
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/api.php`
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_php_api_assets.py`

- [x] **Step 1: Write migration file**

Create `/var/www/html/demo/php/map/3D/gaussian_splat/migrate.php` by adapting the `jpgtoglb` migration style:

```php
<?php
  require __DIR__ . "/../../../../../inc/config.php";
  if(php_sapi_name() !== 'cli'){
      require "{$base_dir}/inc/checkpassword.php";
  }

  $createSQL = "
CREATE TABLE IF NOT EXISTS `gaussian_splat_jobs` (
  `id` int(11) NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `title` varchar(255) DEFAULT NULL COMMENT '名稱',
  `orin_filename` varchar(255) DEFAULT NULL COMMENT '原檔名',
  `c_datetime` datetime DEFAULT NULL COMMENT '上傳時間',
  `IP` varchar(30) DEFAULT NULL COMMENT '上傳者 IP',
  `status` int(11) DEFAULT 0 COMMENT '0 waiting 1 running 2 ready 3 failed 4 aborted',
  `reason` text DEFAULT NULL COMMENT '失敗原因',
  `work_st_datetime` datetime DEFAULT NULL COMMENT '轉檔開始時間',
  `work_et_datetime` datetime DEFAULT NULL COMMENT '轉檔結束時間',
  `lon` double DEFAULT NULL COMMENT '坐標 lon',
  `lat` double DEFAULT NULL COMMENT '坐標 lat',
  `alt` double DEFAULT NULL COMMENT '坐標高度',
  `heading` double DEFAULT NULL COMMENT 'heading',
  `pitch` double DEFAULT NULL COMMENT 'pitch',
  `roll` double DEFAULT NULL COMMENT 'roll',
  `scale` double DEFAULT 1 COMMENT 'scale',
  `camera_lon` double DEFAULT NULL COMMENT '預設相機 lon',
  `camera_lat` double DEFAULT NULL COMMENT '預設相機 lat',
  `camera_alt` double DEFAULT NULL COMMENT '預設相機高度',
  `camera_heading` double DEFAULT NULL COMMENT '預設相機 heading',
  `camera_pitch` double DEFAULT NULL COMMENT '預設相機 pitch',
  `camera_roll` double DEFAULT NULL COMMENT '預設相機 roll',
  `kind` varchar(30) DEFAULT NULL COMMENT 'mp4',
  `email` varchar(512) DEFAULT NULL COMMENT '通知 email',
  `del` int(11) NOT NULL DEFAULT 0 COMMENT '0 active 1 deleted',
  `process_log` text DEFAULT NULL COMMENT '執行 log',
  `frame_count` int(11) DEFAULT NULL COMMENT '抽幀數',
  `registered_frame_count` int(11) DEFAULT NULL COMMENT 'COLMAP registered frames',
  `splat_file_size_mb` double DEFAULT NULL COMMENT 'splat.ply MB',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Gaussian Splat jobs';
  ";

  $pdo->exec($createSQL);
  echo "gaussian_splat_jobs migration complete\n";
```

- [x] **Step 2: Run migration**

Run:

```bash
php migrate.php
```

Expected:

```text
gaussian_splat_jobs migration complete
```

- [x] **Step 3: Write upload API**

Create `/var/www/html/demo/php/map/3D/gaussian_splat/api.php`:

```php
<?php
  require "../../../../../inc/config.php";

  function gs_json($data){
      header('Content-Type: application/json; charset=utf-8');
      echo json_encode($data, JSON_UNESCAPED_UNICODE);
      exit();
  }

  function gs_ext($name){
      return strtolower(pathinfo($name, PATHINFO_EXTENSION));
  }

  $mode = $_GET['mode'] ?? '';

  switch($mode){
      case 'upload':
          $title = trim($_POST['title'] ?? '');
          $email = trim($_POST['email'] ?? '');
          $lon = is_numeric($_POST['lon'] ?? null) ? (float)$_POST['lon'] : null;
          $lat = is_numeric($_POST['lat'] ?? null) ? (float)$_POST['lat'] : null;
          $alt = is_numeric($_POST['alt'] ?? null) ? (float)$_POST['alt'] : 0.0;
          if($title === '') gs_json(['status'=>'NO','reason'=>'title is required']);
          if(!isset($_FILES['upfile']) || $_FILES['upfile']['error'] !== 0) gs_json(['status'=>'NO','reason'=>'upload failed']);
          $ext = gs_ext($_FILES['upfile']['name']);
          if($ext !== 'mp4') gs_json(['status'=>'NO','reason'=>'only mp4 is supported in the MVP worker']);

          $m = [
              'title' => $title,
              'email' => $email,
              'orin_filename' => basename($_FILES['upfile']['name']),
              'c_datetime' => date('Y-m-d H:i:s'),
              'IP' => function_exists('ip') ? ip() : ($_SERVER['REMOTE_ADDR'] ?? ''),
              'status' => 0,
              'reason' => '',
              'kind' => $ext,
              'del' => 0,
              'lon' => $lon,
              'lat' => $lat,
              'alt' => $alt,
              'scale' => 1,
          ];
          $id = insertSQL('gaussian_splat_jobs', $m);
          $root = __DIR__ . "/uploads/{$id}";
          $inputDir = "{$root}/input";
          if(!is_dir($inputDir)) mkdir($inputDir, 0777, true);
          $dest = "{$inputDir}/input.{$ext}";
          move_uploaded_file($_FILES['upfile']['tmp_name'], $dest);
          if(!is_file($dest)) gs_json(['status'=>'NO','reason'=>'uploaded file missing after move']);
          gs_json(['status'=>'OK','id'=>$id]);

      case 'get_log':
          $id = (int)($_GET['id'] ?? 0);
          $rows = selectSQL_SAFE("SELECT `process_log` FROM `gaussian_splat_jobs` WHERE `id`=? LIMIT 1", [$id]);
          gs_json(['status'=>'OK','log'=>$rows[0]['process_log'] ?? '']);

      case 'save_transform':
          require "{$base_dir}/inc/checkpassword.php";
          $id = (int)($_POST['id'] ?? 0);
          $data = json_decode(base64_decode($_POST['data'] ?? ''), true);
          if($id <= 0 || !is_array($data)) gs_json(['status'=>'NO','reason'=>'invalid transform payload']);
          $fields = [];
          foreach(['lon','lat','alt','heading','pitch','roll','scale','camera_lon','camera_lat','camera_alt','camera_heading','camera_pitch','camera_roll'] as $key){
              if(isset($data[$key]) && is_numeric($data[$key])) $fields[$key] = (float)$data[$key];
          }
          if($fields) updateSQL_SAFE('gaussian_splat_jobs', $fields, "`id`=?", [$id]);
          file_put_contents(__DIR__ . "/uploads/{$id}/transform.json", json_encode($data, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT) . "\n");
          gs_json(['status'=>'OK']);

      case 'admin_action':
          require "{$base_dir}/inc/checkpassword.php";
          $id = (int)($_POST['id'] ?? 0);
          $action = $_POST['action'] ?? '';
          if($id <= 0) gs_json(['status'=>'NO','reason'=>'invalid id']);
          if($action === 'retry'){
              updateSQL_SAFE('gaussian_splat_jobs', ['status'=>0,'reason'=>'','process_log'=>'','work_st_datetime'=>null,'work_et_datetime'=>null], "`id`=?", [$id]);
              gs_json(['status'=>'OK']);
          }
          if($action === 'abort'){
              $dir = __DIR__ . "/uploads/{$id}";
              if(is_dir($dir)) file_put_contents("{$dir}/.abort", date('Y-m-d H:i:s'));
              updateSQL_SAFE('gaussian_splat_jobs', ['status'=>4,'reason'=>'使用者中止','work_et_datetime'=>date('Y-m-d H:i:s')], "`id`=?", [$id]);
              gs_json(['status'=>'OK']);
          }
          gs_json(['status'=>'NO','reason'=>'unknown action']);
  }

  gs_json(['status'=>'NO','reason'=>'unknown mode']);
```

- [x] **Step 4: PHP syntax checks**

Run:

```bash
php -l migrate.php
php -l api.php
```

Expected:

```text
No syntax errors detected in migrate.php
No syntax errors detected in api.php
```

Actual notes:

```text
pytest tests/test_php_api_assets.py: 3 passed
php -l migrate.php: No syntax errors detected in migrate.php
php -l api.php: No syntax errors detected in api.php
php migrate.php: gaussian_splat_jobs migration complete
```

- Migration was made idempotent like `jpgtoglb`: it creates the table, then `SHOW COLUMNS` and `ALTER TABLE ... ADD COLUMN` repairs partial tables.
- Upload API now ports the `jpgtoglb` captcha gate: `checkGD` is available and `upload` requires one-time `gdcode` before inserting a GPU worker job.
- Upload API marks the job failed if the upload directory or moved file is missing after insert.
- `save_transform` now creates the job directory if needed and checks `file_put_contents`.

- [x] **Step 5: Commit migration and API**

Run:

```bash
git add migrate.php api.php
git commit -m "feat: add gaussian splat job migration and api"
```

Expected:

```text
[main
```

---

### Task 10: Cron Worker Integration

**Files:**
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/crontab/1min.sh`
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/crontab/1_run.php`
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/crontab/inc/function.php`
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_cron_worker_assets.py`

- [x] **Step 1: Write cron helper functions**

Create `/var/www/html/demo/php/map/3D/gaussian_splat/crontab/inc/function.php`:

```php
<?php
  function gs_run_cmd($cmd, &$out=null, $timeout=86400){
      $out = [];
      $ret = 0;
      exec("timeout {$timeout} " . $cmd . " 2>&1", $out, $ret);
      return $ret === 0;
  }

  function gs_append_log($id, $msg){
      global $pdo;
      $line = date('H:i:s') . " " . $msg . "\n";
      echo $line;
      if(isset($pdo)){
          $stmt = $pdo->prepare("UPDATE `gaussian_splat_jobs` SET `process_log` = CONCAT(IFNULL(`process_log`,''), ?) WHERE `id`=?");
          $stmt->execute([$line, $id]);
      }
      gs_check_abort($id);
  }

  function gs_check_abort($id){
      $root = dirname(dirname(__DIR__));
      $flag = "{$root}/uploads/{$id}/.abort";
      if(is_file($flag)){
          updateSQL_SAFE('gaussian_splat_jobs', ['status'=>4,'reason'=>'使用者中止','work_et_datetime'=>date('Y-m-d H:i:s')], "`id`=?", [$id]);
          @unlink($flag);
          exit(0);
      }
  }

  function gs_fail($id, $reason){
      updateSQL_SAFE('gaussian_splat_jobs', ['status'=>3,'reason'=>$reason,'work_et_datetime'=>date('Y-m-d H:i:s')], "`id`=?", [$id]);
      exit(1);
  }
```

- [x] **Step 2: Write cron runner**

Create `/var/www/html/demo/php/map/3D/gaussian_splat/crontab/1_run.php`:

```php
<?php
  require "../../../../../../inc/config.php";
  require __DIR__ . "/inc/function.php";

  $root = dirname(__DIR__);
  $lockFile = __DIR__ . "/1_run.lock";
  $lockFp = fopen($lockFile, 'w');
  if(!$lockFp || !flock($lockFp, LOCK_EX | LOCK_NB)){
      echo "已有 Gaussian Splat 轉檔程序在執行中，略過本次。\n";
      exit(0);
  }
  fwrite($lockFp, getmypid());
  register_shutdown_function(function() use($lockFp){
      flock($lockFp, LOCK_UN);
      fclose($lockFp);
  });

  $rows = selectSQL_SAFE("SELECT * FROM `gaussian_splat_jobs` WHERE `del`='0' AND `status`='0' ORDER BY `id` ASC LIMIT 1", []);
  foreach($rows as $row){
      $id = (int)$row['id'];
      $kind = strtolower($row['kind']);
      $jobDir = "{$root}/uploads/{$id}";
      $input = "{$jobDir}/input/input.{$kind}";
      $logPath = "{$jobDir}/process.log";
      @unlink("{$jobDir}/.abort");

      updateSQL_SAFE('gaussian_splat_jobs', ['status'=>1,'work_st_datetime'=>date('Y-m-d H:i:s'),'process_log'=>''], "`id`=?", [$id]);
      gs_append_log($id, "開始 Gaussian Splat pipeline");
      if(!is_file($input)) gs_fail($id, "input file missing");
      if($kind !== 'mp4') gs_fail($id, "MVP cron worker currently accepts mp4 input");

      $cmd = escapeshellarg("{$root}/scripts/run_mvp_pipeline.sh") . " " . escapeshellarg($input) . " " . escapeshellarg($jobDir);
      gs_append_log($id, "執行: {$cmd}");
      $out = [];
      $ok = gs_run_cmd($cmd, $out, 86400);
      file_put_contents($logPath, implode("\n", $out) . "\n", FILE_APPEND);
      if(!$ok) gs_fail($id, implode("\n", $out));

      $qa = json_decode(@file_get_contents("{$jobDir}/qa_report.json"), true);
      $upd = ['status'=>2,'work_et_datetime'=>date('Y-m-d H:i:s')];
      if(is_array($qa)){
          $upd['frame_count'] = $qa['frame_count'] ?? null;
          $upd['registered_frame_count'] = $qa['registered_frame_count'] ?? null;
          $upd['splat_file_size_mb'] = $qa['splat_file_size_mb'] ?? null;
      }
      updateSQL_SAFE('gaussian_splat_jobs', $upd, "`id`=?", [$id]);
      gs_append_log($id, "Gaussian Splat pipeline 完成");
  }

  echo "Done.\n";
```

- [x] **Step 3: Write one-minute shell wrapper**

Create `/var/www/html/demo/php/map/3D/gaussian_splat/crontab/1min.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
php 1_run.php
```

- [x] **Step 4: Make shell wrapper executable**

Run:

```bash
chmod +x crontab/1min.sh
```

Expected:

```text
crontab/1min.sh is executable
```

- [x] **Step 5: PHP syntax checks**

Run:

```bash
php -l crontab/inc/function.php
php -l crontab/1_run.php
```

Expected:

```text
No syntax errors detected in crontab/inc/function.php
No syntax errors detected in crontab/1_run.php
```

- [x] **Step 6: Run cron dry smoke with no jobs**

Run:

```bash
php crontab/1_run.php
```

Expected:

```text
Done.
```

Actual notes:

```text
pytest tests/test_cron_worker_assets.py: 4 passed
php -l crontab/inc/function.php: No syntax errors detected in crontab/inc/function.php
php -l crontab/1_run.php: No syntax errors detected in crontab/1_run.php
php crontab/1_run.php: Done.
test -x crontab/1min.sh: crontab/1min.sh is executable
gs_run_cmd printf smoke: OK, hello
gs_run_cmd abort callback smoke: NO, aborted by user, returned in about 0.015s
```

- `crontab/1_run.php` uses an `__DIR__`-anchored config include, so the planned root-directory dry smoke works.
- `gs_run_cmd` streams command output with `proc_open`, checks abort while long training/export commands run, and terminates the process tree on abort.
- `process.log` receives full command output; DB `process_log` is capped with `RIGHT(..., 60000)` to avoid growing beyond the table field.
- Completion is logged before status changes from running to ready, avoiding a false abort on the final log checkpoint.
- `.gitignore` excludes runtime `crontab/*.lock` files.

- [x] **Step 7: Commit cron worker**

Run:

```bash
git add crontab/1min.sh crontab/1_run.php crontab/inc/function.php
git commit -m "feat: add gaussian splat cron worker"
```

Expected:

```text
[main
```

---

### Task 11: Front Page And Admin Page

**Files:**
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/index.php`
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/admin.php`
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/js/function.js`
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_php_page_assets.py`

- [x] **Step 1: Write minimal shared JS**

Create `/var/www/html/demo/php/map/3D/gaussian_splat/js/function.js`:

```javascript
function openSplatViewer(url) {
  window.open("viewer_splat.html?src=" + encodeURIComponent(url), "_blank", "noopener");
}

function refreshJobLog(id, targetSelector) {
  $.getJSON("api.php?mode=get_log&id=" + encodeURIComponent(id), function (jd) {
    if (jd.status === "OK") {
      $(targetSelector).text(jd.log || "");
    }
  });
}
```

- [x] **Step 2: Write front page**

Create `/var/www/html/demo/php/map/3D/gaussian_splat/index.php`:

```php
<?php
  require "../../../../../inc/config.php";
  $include_mode = "jquery-form|three.js-r155|easymap7115";
  $rows = selectSQL_SAFE("SELECT * FROM `gaussian_splat_jobs` WHERE `del`='0' ORDER BY `id` DESC LIMIT 50", []);
  require "{$base_dir}/html.php";
  require "{$base_dir}/head.php";
?>
<script src="js/function.js"></script>
<title>Gaussian Splat MVP</title>
<?php require "{$base_dir}/head_end.php"; require "{$base_dir}/body.php"; require "{$base_dir}/top.php"; ?>
<div class="container" style="max-width:1180px;padding:20px;">
  <h2>Gaussian Splat MVP</h2>
  <form id="uploadForm" method="post" enctype="multipart/form-data" action="api.php?mode=upload" class="panel panel-default" style="padding:16px;">
    <div class="form-group"><label>Title</label><input class="form-control" name="title" required></div>
    <div class="form-group"><label>Email</label><input class="form-control" name="email"></div>
    <div class="form-group"><label>MP4</label><input class="form-control" type="file" name="upfile" accept=".mp4" required></div>
    <div class="row">
      <div class="col-sm-4"><label>Lon</label><input class="form-control" name="lon" value="120.6647066"></div>
      <div class="col-sm-4"><label>Lat</label><input class="form-control" name="lat" value="24.1504731"></div>
      <div class="col-sm-4"><label>Alt</label><input class="form-control" name="alt" value="0"></div>
    </div>
    <div style="margin-top:12px;"><button class="btn btn-primary" type="submit">Upload</button></div>
  </form>
  <table class="table table-striped">
    <thead><tr><th>ID</th><th>Title</th><th>Status</th><th>Frames</th><th>Splat</th><th>Map</th></tr></thead>
    <tbody>
      <?php foreach($rows as $r): $splat = "uploads/{$r['id']}/exports/splat.ply"; ?>
      <tr>
        <td><?=$r['id'];?></td>
        <td><?=htmlspecialchars($r['title'] ?: $r['orin_filename']);?></td>
        <td><?=$r['status'];?> <?=htmlspecialchars($r['reason'] ?? '');?></td>
        <td><?=htmlspecialchars((string)($r['frame_count'] ?? ''));?> / <?=htmlspecialchars((string)($r['registered_frame_count'] ?? ''));?></td>
        <td><?php if(is_file($splat)): ?><button class="btn btn-xs btn-success" onclick="openSplatViewer('<?=$splat;?>')">Viewer</button><?php endif; ?></td>
        <td><?php if(is_file($splat)): ?><a class="btn btn-xs btn-info" href="map.php?id=<?=$r['id'];?>">Align</a><?php endif; ?></td>
      </tr>
      <?php endforeach; ?>
    </tbody>
  </table>
</div>
<script>
$("#uploadForm").ajaxForm({
  dataType: "json",
  success: function(jd) {
    if (jd.status === "OK") location.reload();
    else alert(jd.reason || "upload failed");
  }
});
</script>
</body></html>
```

- [x] **Step 3: Write admin page**

Create `/var/www/html/demo/php/map/3D/gaussian_splat/admin.php`:

```php
<?php
  require "../../../../../inc/config.php";
  require "{$base_dir}/inc/checkpassword.php";
  $rows = selectSQL_SAFE("SELECT * FROM `gaussian_splat_jobs` WHERE `del`='0' ORDER BY `id` DESC LIMIT 100", []);
  require "{$base_dir}/html.php";
  require "{$base_dir}/head.php";
?>
<script src="js/function.js"></script>
<title>Gaussian Splat Admin</title>
<?php require "{$base_dir}/head_end.php"; require "{$base_dir}/body.php"; require "{$base_dir}/top.php"; ?>
<div class="container" style="max-width:1280px;padding:20px;">
  <h2>Gaussian Splat Admin</h2>
  <table class="table table-bordered table-condensed">
    <thead><tr><th>ID</th><th>Title</th><th>Status</th><th>QA</th><th>Action</th></tr></thead>
    <tbody>
      <?php foreach($rows as $r): $qa = "uploads/{$r['id']}/qa_report.json"; ?>
      <tr>
        <td><?=$r['id'];?></td>
        <td><?=htmlspecialchars($r['title'] ?: $r['orin_filename']);?></td>
        <td><?=$r['status'];?> <?=htmlspecialchars($r['reason'] ?? '');?></td>
        <td><?php if(is_file($qa)): ?><a href="<?=$qa;?>" target="_blank">qa_report.json</a><?php endif; ?></td>
        <td>
          <button class="btn btn-xs btn-warning" onclick="jobAction(<?=$r['id'];?>,'retry')">Retry</button>
          <button class="btn btn-xs btn-danger" onclick="jobAction(<?=$r['id'];?>,'abort')">Abort</button>
          <button class="btn btn-xs btn-default" onclick="refreshJobLog(<?=$r['id'];?>, '#log')">Log</button>
        </td>
      </tr>
      <?php endforeach; ?>
    </tbody>
  </table>
  <pre id="log" style="min-height:220px;background:#111827;color:#e5e7eb;padding:12px;"></pre>
</div>
<script>
function jobAction(id, action) {
  $.post("api.php?mode=admin_action", { id: id, action: action }, function(jd) {
    if (jd.status === "OK") location.reload();
    else alert(jd.reason || "action failed");
  }, "json");
}
</script>
</body></html>
```

- [x] **Step 4: PHP syntax checks**

Run:

```bash
php -l index.php
php -l admin.php
```

Expected:

```text
No syntax errors detected in index.php
No syntax errors detected in admin.php
```

Actual notes:

```text
pytest tests/test_php_page_assets.py: 3 passed
php -l index.php: No syntax errors detected in index.php
php -l admin.php: No syntax errors detected in admin.php
curl index.php: HTTP 200
desktop browser smoke: form/captcha/table present, console errors 0
mobile browser smoke: form/captcha/table present, console errors 0
```

- Front page includes the `jpgtoglb`-style captcha image and `api.php?mode=checkGD` precheck required by the Task 9 upload gate.
- Completed jobs open `viewer_splat.html` through `openSplatViewer()` using `uploads/{id}/exports/splat.ply`.
- Admin page is authenticated and wires retry, abort, log refresh, QA links, and viewer launch.

- [x] **Step 5: Commit front/admin pages**

Run:

```bash
git add index.php admin.php js/function.js
git commit -m "feat: add gaussian splat job pages"
```

Expected:

```text
[main
```

---

### Task 12: Easymap Alignment Page

**Files:**
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/map.php`
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_map_page_assets.py`

- [x] **Step 1: Write alignment page**

Create `/var/www/html/demo/php/map/3D/gaussian_splat/map.php`:

```php
<?php
  require "../../../../../inc/config.php";
  require "{$base_dir}/inc/checkpassword.php";
  $include_mode = "easymap7115|three.js-r155";
  $id = (int)($_GET['id'] ?? 0);
  $rows = selectSQL_SAFE("SELECT * FROM `gaussian_splat_jobs` WHERE `id`=? AND `del`='0' LIMIT 1", [$id]);
  if(!$rows) exit("job not found");
  $info = $rows[0];
  $splat = "uploads/{$id}/exports/splat.ply";
  if(!is_file(__DIR__ . "/{$splat}")) exit("splat.ply not found");
  require "{$base_dir}/html.php";
  require "{$base_dir}/head.php";
?>
<title>Gaussian Splat Alignment</title>
<?php require "{$base_dir}/head_end.php"; require "{$base_dir}/body.php"; require "{$base_dir}/top.php"; ?>
<style nonce="gg">
  #layout{display:grid;grid-template-columns:1fr 360px;gap:12px;padding:12px;}
  #map{height:720px;border:1px solid #bbb;}
  #panel{border:1px solid #bbb;padding:12px;background:#fff;}
  #panel label{display:block;margin-top:10px;}
  #panel input{width:100%;}
  #preview{width:100%;height:280px;border:1px solid #bbb;margin-top:12px;}
</style>
<div id="layout">
  <div id="map"></div>
  <div id="panel">
    <h3><?=htmlspecialchars($info['title'] ?: $info['orin_filename']);?></h3>
    <label>Lon <input id="lon" value="<?=htmlspecialchars((string)($info['lon'] ?: 120.6647066));?>"></label>
    <label>Lat <input id="lat" value="<?=htmlspecialchars((string)($info['lat'] ?: 24.1504731));?>"></label>
    <label>Height <input id="alt" value="<?=htmlspecialchars((string)($info['alt'] ?: 0));?>"></label>
    <label>Heading <input id="heading" value="<?=htmlspecialchars((string)($info['heading'] ?: 0));?>"></label>
    <label>Pitch <input id="pitch" value="<?=htmlspecialchars((string)($info['pitch'] ?: 0));?>"></label>
    <label>Roll <input id="roll" value="<?=htmlspecialchars((string)($info['roll'] ?: 0));?>"></label>
    <label>Scale <input id="scale" value="<?=htmlspecialchars((string)($info['scale'] ?: 1));?>"></label>
    <p><a target="_blank" href="viewer_splat.html?src=<?=$splat;?>">Open standalone viewer</a></p>
    <iframe id="preview" src="viewer_splat.html?src=<?=$splat;?>"></iframe>
    <button class="btn btn-primary" id="save">Save Transform</button>
  </div>
</div>
<script nonce="gg">
  var map = new Easymap("map");
  map.zoomToXY(new dgXY(parseFloat($("#lon").val()), parseFloat($("#lat").val())), 18);

  function payload() {
    return {
      lon: parseFloat($("#lon").val()),
      lat: parseFloat($("#lat").val()),
      alt: parseFloat($("#alt").val()),
      heading: parseFloat($("#heading").val()),
      pitch: parseFloat($("#pitch").val()),
      roll: parseFloat($("#roll").val()),
      scale: parseFloat($("#scale").val())
    };
  }

  map.attachEvent("onclick", function(evt, dgxy) {
    $("#lon").val(dgxy.x.toFixed(7));
    $("#lat").val(dgxy.y.toFixed(7));
  });

  $("#save").on("click", function() {
    $.post("api.php?mode=save_transform", {
      id: <?=$id;?>,
      data: base64_encode(JSON.stringify(payload()))
    }, function(jd) {
      if(jd.status === "OK") alert("saved");
      else alert(jd.reason || "save failed");
    }, "json");
  });
</script>
</body></html>
```

- [x] **Step 2: PHP syntax check**

Run:

```bash
php -l map.php
```

Expected:

```text
No syntax errors detected in map.php
```

- [x] **Step 3: Browser smoke test**

Open:

```text
http://localhost/demo/php/map/3D/gaussian_splat/map.php?id=1
```

Expected when job 1 has `exports/splat.ply`:

```text
Easymap opens, the right-side transform form is visible, and the embedded splat preview loads the .ply viewer.
```

Actual notes:

```text
pytest tests/test_map_page_assets.py: 2 passed
php -l map.php: No syntax errors detected in map.php
curl map.php?id=1 without login: HTTP 302 login redirect
```

- Map page requires auth, selects one job, requires `status=2`, and checks `uploads/{id}/exports/splat.ply` before showing alignment controls.
- Easymap is initialized through the global SDK with `new Easymap("map")`, and map click updates lon/lat inputs.
- The right panel embeds `viewer_splat.html?src=...` for the exported splat and saves transform/camera fields through `api.php?mode=save_transform`.
- Full visual Easymap smoke requires an authenticated browser session and a ready job; unauthenticated smoke confirmed the expected login gate.

- [x] **Step 4: Commit alignment page**

Run:

```bash
git add map.php tests/test_map_page_assets.py docs/superpowers/plans/2026-06-05-gaussian-splat-mvp.md
git commit -m "feat: add easymap gaussian splat alignment page"
```

Expected:

```text
[main
```

---

### Task 13: Final MVP Verification

**Files:**
- Modify: `/var/www/html/demo/php/map/3D/gaussian_splat/README.md`
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_readme_runbook.py`

- [x] **Step 1: Run all non-GPU tests**

Run:

```bash
pytest
php -l migrate.php
php -l api.php
php -l index.php
php -l admin.php
php -l map.php
php -l crontab/1_run.php
php -l crontab/inc/function.php
```

Expected:

```text
all pytest tests pass
No syntax errors detected
```

Actual:

```text
pytest: 35 passed
php -l migrate.php api.php index.php admin.php map.php crontab/1_run.php crontab/inc/function.php: No syntax errors detected
```

- [x] **Step 2: Run GPU environment check**

Run:

```bash
/park/conda_vm/gs_scene/bin/python - <<'PY'
import torch
print(torch.__version__)
print(torch.version.cuda)
print(torch.cuda.is_available())
PY
```

Expected:

```text
2.10.0+cu128
12.8
True
```

Actual:

```text
2.10.0+cu128
12.8
True
```

- [x] **Step 3: Run full sample pipeline**

Run:

```bash
rm -rf uploads/final-smoke
bash scripts/run_mvp_pipeline.sh /var/www/html/demo/php/map/3D/jpgtoglb/uploads/2/2.mp4 uploads/final-smoke
test -f uploads/final-smoke/exports/splat.ply
python3 -m json.tool uploads/final-smoke/qa_report.json >/dev/null
```

Expected:

```text
uploads/final-smoke/exports/splat.ply exists and qa_report.json is valid JSON
```

Actual:

```text
stdout: uploads/final-smoke/exports/splat.ply
DURATION_SECONDS=114.08
frame_count=32
registered_frame_count=25
registered_ratio=0.78
splat_file_size_mb=0.79
viewer_ready=True
warnings=['registered_ratio lower than 0.8']
uploads/final-smoke/exports/splat.ply: 644, HTTP 200
```

- [x] **Step 4: Verify viewer URL**

Open:

```text
http://localhost/demo/php/map/3D/gaussian_splat/viewer_splat.html?src=uploads/final-smoke/exports/splat.ply
```

Expected:

```text
The page status says Ready and the exported splat renders.
```

Actual:

```text
Status: Ready: uploads/final-smoke/exports/splat.ply
Canvas: 1280x720
Console errors: 0
Screenshot nonblack pixels: 921600
```

- [x] **Step 5: Add crontab note to README**

Append to `/var/www/html/demo/php/map/3D/gaussian_splat/README.md`:

````markdown
## Cron

Run one queued job:

```bash
php crontab/1_run.php
```

Install one-minute cron:

```bash
*/1 * * * * cd /var/www/html/demo/php/map/3D/gaussian_splat/crontab && ./1min.sh
```
````

- [x] **Step 6: Commit final verification docs**

Run:

```bash
git add README.md tests/test_readme_runbook.py docs/superpowers/plans/2026-06-05-gaussian-splat-mvp.md
git commit -m "docs: add gaussian splat mvp verification notes"
```

Expected:

```text
[main
```

- [x] **Step 7: Final review**

Run:

```bash
git status --short
git log --oneline --max-count=13
```

Expected:

```text
git status --short has no output
git log shows the task commits from this plan
```

Actual:

```text
git status --short --branch:
## main
?? docs/plan.md

git log --oneline --max-count=13 shows Task 1 through Task 13 commits.
Ignored runtime artifacts remain under .pytest_cache, .playwright-cli, output, crontab/1_run.lock, uploads/local-smoke, and uploads/final-smoke.
```

---

## Spec Coverage Self-Review

The original roadmap requirements covered by this MVP plan:

```text
手機影片輸入: Task 3 and Task 9 support MP4; ZIP samples are retained as reference assets for a later photo-package worker
影片抽幀: Task 3
COLMAP/Nerfstudio processing: Task 5 and Task 7
cu128 environment: Task 2
splatfacto training: Task 5 and Task 7
export splat.ply: Task 5 and Task 7
Three.js viewer MVP: Task 8
FPS/file size/camera display: Task 8 status display and Task 6 QA file size; live FPS can be added after first render smoke passes
transparent background: Task 8 uses page-level dark background; transparent renderer mode is deferred until overlay integration
GLB same-scene display: not included in MVP because GaussianSplats3D first render must be verified before mixed-scene depth behavior
Easymap side-by-side alignment: Task 12
transform.json: Task 4 and Task 12
PHP job flow: Task 9, Task 10, Task 11
QA report: Task 6
sample reuse from jpgtoglb: Task 1, Task 3, Task 7, Task 13
```

Intentional MVP boundaries:

```text
Cesium + Three.js synchronized overlay is not implemented in this plan.
MapLibre custom layer is not implemented in this plan.
A true Easymap map overlay for Gaussian Splat rendering is not implemented in this plan; Task 12 provides map coordinate picking plus an embedded splat preview.
.splat, .ksplat, and .spz conversion are not implemented in this plan.
3D Tiles Gaussian Splat is not implemented in this plan.
BIM/GLB same-scene comparison is not implemented in this plan.
```

Type and naming consistency:

```text
DB table: gaussian_splat_jobs
Export file: exports/splat.ply
Transform file: transform.json
QA file: qa_report.json
Main pipeline script: scripts/run_mvp_pipeline.sh
Viewer URL param: src
Status values: 0 waiting, 1 running, 2 ready, 3 failed, 4 aborted
```
