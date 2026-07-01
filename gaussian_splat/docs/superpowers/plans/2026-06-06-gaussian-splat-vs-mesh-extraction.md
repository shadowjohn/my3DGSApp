# Gaussian Splat vs Mesh Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a first-pass pipeline and viewers that compare an existing Gaussian Splat output with an extracted Mesh/GLB output from the same job.

**Architecture:** Add small Python CLI scripts for Splat PLY to colored point cloud, point cloud to mesh, mesh to GLB cleanup, and compare-bundle creation. Add standalone Three.js viewers for GLB and side-by-side Splat/Mesh comparison, with static contract tests and lightweight script unit tests. The first production run targets `uploads/7`, while code remains job/path agnostic.

**Tech Stack:** Python 3.10+, NumPy, Trimesh, optional Open3D, optional Blender, Three.js/GLTFLoader/OrbitControls, pytest, existing Gaussian Splat viewer.

---

## File Structure

- Create `/var/www/html/demo/php/map/3D/gaussian_splat/scripts/splat_to_pointcloud.py`
  - Reads binary little-endian Nerfstudio Gaussian Splat PLY.
  - Filters by opacity and scale.
  - Converts `f_dc_0..2` or `red/green/blue` to RGB.
  - Writes a standard colored point-cloud PLY with `x y z red green blue`.

- Create `/var/www/html/demo/php/map/3D/gaussian_splat/scripts/pointcloud_to_mesh.py`
  - Reads colored point cloud.
  - Uses Open3D Poisson reconstruction when Open3D is installed.
  - Falls back to Trimesh convex hull for preview when Open3D is unavailable.
  - Writes mesh PLY and `mesh_report.json`.

- Create `/var/www/html/demo/php/map/3D/gaussian_splat/scripts/blender_mesh_cleanup.py`
  - Blender script for importing mesh PLY, removing loose geometry, decimating, smoothing, and exporting GLB.

- Create `/var/www/html/demo/php/map/3D/gaussian_splat/scripts/build_compare_bundle.py`
  - Creates `uploads/<id>/compare/`.
  - Copies Splat baseline files.
  - Runs point-cloud extraction, mesh reconstruction, GLB export fallback, and verdict template creation.
  - Writes `compare_report.json`.

- Create `/var/www/html/demo/php/map/3D/gaussian_splat/viewer_mesh.html`
  - Loads GLB with Three.js GLTFLoader.
  - Shows file size, vertex/triangle counts, wireframe toggle, and opacity control.

- Create `/var/www/html/demo/php/map/3D/gaussian_splat/viewer_compare_splat_mesh.html`
  - Embeds Splat and Mesh viewers side by side with fixed query parameters.
  - Displays links and notes for the two outputs.

- Create `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_mesh_extraction_scripts.py`
  - Unit tests for PLY parsing, SH color conversion, filtering, point-cloud writing, mesh fallback, and compare report helpers.

- Create `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_mesh_viewer_assets.py`
  - Static tests for the two viewers and their required controls/imports.

---

### Task 1: Contract And Script Tests

**Files:**
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_mesh_extraction_scripts.py`
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_mesh_viewer_assets.py`

- [ ] **Step 1: Add script behavior tests**

Create tests that:

```python
from pathlib import Path
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def write_tiny_splat(path: Path):
    header = "\n".join([
        "ply",
        "format binary_little_endian 1.0",
        "element vertex 3",
        "property float x",
        "property float y",
        "property float z",
        "property float f_dc_0",
        "property float f_dc_1",
        "property float f_dc_2",
        "property float opacity",
        "property float scale_0",
        "property float scale_1",
        "property float scale_2",
        "end_header",
        "",
    ]).encode("ascii")
    rows = [
        (0, 0, 0, 0.8, 0.0, 0.0, 4.0, -2.0, -2.0, -2.0),
        (1, 0, 0, 0.0, 0.8, 0.0, 4.0, -2.0, -2.0, -2.0),
        (0, 1, 0, 0.0, 0.0, 0.8, -8.0, -2.0, -2.0, -2.0),
    ]
    path.write_bytes(header + b"".join(struct.pack("<10f", *row) for row in rows))
```

Assertions:

```python
def test_splat_to_pointcloud_filters_and_writes_rgb(tmp_path):
    source = tmp_path / "splat.clean.ply"
    output = tmp_path / "point_cloud.ply"
    report = tmp_path / "point_cloud_report.json"
    write_tiny_splat(source)

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "splat_to_pointcloud.py"),
            "--input", str(source),
            "--output", str(output),
            "--report", str(report),
            "--min-opacity", "0.2",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    text = output.read_text()
    assert "property uchar red" in text
    assert "element vertex 2" in text
    assert report.is_file()
```

```python
def test_pointcloud_to_mesh_preview_fallback_writes_report(tmp_path):
    point_cloud = tmp_path / "point_cloud.ply"
    mesh = tmp_path / "raw_mesh.ply"
    report = tmp_path / "mesh_report.json"
    point_cloud.write_text(
        "ply\nformat ascii 1.0\nelement vertex 4\n"
        "property float x\nproperty float y\nproperty float z\n"
        "property uchar red\nproperty uchar green\nproperty uchar blue\n"
        "end_header\n"
        "0 0 0 255 0 0\n1 0 0 0 255 0\n0 1 0 0 0 255\n0 0 1 255 255 255\n"
    )

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "pointcloud_to_mesh.py"),
            "--input", str(point_cloud),
            "--output", str(mesh),
            "--report", str(report),
            "--method", "convex_hull",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert mesh.is_file()
    assert report.is_file()
```

- [ ] **Step 2: Add viewer static tests**

Create tests that assert:

```python
def test_mesh_viewer_loads_glb_and_controls():
    text = (ROOT / "viewer_mesh.html").read_text()
    assert "GLTFLoader" in text
    assert "OrbitControls" in text
    assert "wireframe" in text
    assert "opacity" in text
    assert "triangle" in text
    assert "file size" in text.lower()
    assert "src=uploads/7/compare/mesh/cleaned_mesh.glb" in text

def test_compare_viewer_embeds_splat_and_mesh_viewers():
    text = (ROOT / "viewer_compare_splat_mesh.html").read_text()
    assert "viewer_splat.html" in text
    assert "viewer_mesh.html" in text
    assert "splat.clean.ply" in text
    assert "cleaned_mesh.glb" in text
    assert "Gaussian Splat" in text
    assert "Mesh GLB" in text
```

- [ ] **Step 3: Run tests and verify red**

Run:

```bash
pytest -q tests/test_mesh_extraction_scripts.py tests/test_mesh_viewer_assets.py
```

Expected: FAIL because scripts/viewers do not exist yet.

---

### Task 2: Mesh Extraction Scripts

**Files:**
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/scripts/splat_to_pointcloud.py`
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/scripts/pointcloud_to_mesh.py`
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/scripts/blender_mesh_cleanup.py`
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/scripts/build_compare_bundle.py`
- Test: `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_mesh_extraction_scripts.py`

- [ ] **Step 1: Implement Splat PLY to point cloud**

Implement a CLI with:

```bash
python3 scripts/splat_to_pointcloud.py \
  --input uploads/7/exports/splat.clean.ply \
  --output uploads/7/compare/mesh/point_cloud.ply \
  --report uploads/7/compare/mesh/point_cloud_report.json
```

Required behavior:
- Supports binary little-endian float/double Gaussian PLY.
- Requires `x`, `y`, `z`, `opacity`, `scale_0`, `scale_1`, `scale_2`.
- Uses RGB properties when present, otherwise converts `f_dc_0..2` with `rgb = clamp((f_dc * 0.28209479177387814 + 0.5) * 255)`.
- Applies sigmoid opacity threshold.
- Applies exp(max scale) threshold or a quantile-based automatic threshold.
- Writes ASCII point-cloud PLY with `property uchar red/green/blue`.
- Writes report JSON with input count, kept count, removed count, min opacity, max scale, bbox, and output path.

- [ ] **Step 2: Implement point cloud to mesh**

Implement a CLI with:

```bash
python3 scripts/pointcloud_to_mesh.py \
  --input uploads/7/compare/mesh/point_cloud.ply \
  --output uploads/7/compare/mesh/raw_mesh.ply \
  --report uploads/7/compare/mesh/mesh_report.json \
  --depth 9
```

Required behavior:
- `--method auto|open3d|convex_hull`, default `auto`.
- If Open3D is available and method is `auto` or `open3d`, estimate normals, run Poisson reconstruction, crop to bbox, remove low-density vertices, and write mesh.
- If Open3D is unavailable and method is `auto`, use Trimesh convex hull as preview fallback.
- If method is `open3d` and Open3D is unavailable, exit non-zero with a clear message.
- Writes JSON report with method, vertex count, face count, output path, depth, and fallback reason when used.

- [ ] **Step 3: Implement Blender cleanup**

Implement a Blender Python script invoked as:

```bash
blender -b --python scripts/blender_mesh_cleanup.py -- \
  --input uploads/7/compare/mesh/raw_mesh.ply \
  --output uploads/7/compare/mesh/cleaned_mesh.glb \
  --target_faces 100000
```

Required behavior:
- Parses args after `--`.
- Imports PLY or OBJ.
- Deletes loose geometry where available.
- Applies decimate if face count is above target.
- Sets smooth shading.
- Exports GLB.

- [ ] **Step 4: Implement compare bundle builder**

Implement:

```bash
python3 scripts/build_compare_bundle.py --job-dir uploads/7
```

Required behavior:
- Creates `compare/splat`, `compare/mesh`, `compare/screenshots`.
- Copies `exports/splat.ply`, `exports/splat.clean.ply`, and `exports/splat.clean.viewer.json` when present.
- Writes `compare/splat/viewer.json` with the fixed viewer parameters from the source plan.
- Runs Splat-to-pointcloud and pointcloud-to-mesh.
- Exports `cleaned_mesh.glb` with Trimesh when Blender is not requested or not available.
- Writes `compare/verdict.md` from the template in `docs/gaussian-splat-vs-mesh-extraction-plan.md`.
- Writes `compare/compare_report.json` with viewer URLs and artifact paths.

- [ ] **Step 5: Verify**

Run:

```bash
python3 -m py_compile scripts/splat_to_pointcloud.py scripts/pointcloud_to_mesh.py scripts/blender_mesh_cleanup.py scripts/build_compare_bundle.py
pytest -q tests/test_mesh_extraction_scripts.py
```

Expected: PASS.

---

### Task 3: Mesh And Comparison Viewers

**Files:**
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/viewer_mesh.html`
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/viewer_compare_splat_mesh.html`
- Test: `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_mesh_viewer_assets.py`

- [ ] **Step 1: Implement Mesh Viewer**

Create a first-screen tool, not a landing page:
- Full-bleed dark viewer canvas.
- `?src=` query with default `uploads/7/compare/mesh/cleaned_mesh.glb`.
- Imports Three.js, GLTFLoader, OrbitControls from jsDelivr.
- Shows status text with file size, vertex count, triangle count.
- Adds wireframe checkbox and opacity range.
- Uses OrbitControls and fixed initial camera.

- [ ] **Step 2: Implement Compare Viewer**

Create a two-column comparison page:
- Left iframe: `viewer_splat.html?src=uploads/7/exports/splat.clean.ply&rx=0&ry=0&rz=0&up=view&distance=12&alpha=40&splatScale=0.35`
- Right iframe: `viewer_mesh.html?src=uploads/7/compare/mesh/cleaned_mesh.glb`
- Query params `job`, `splat`, and `mesh` override defaults.
- Header includes concise metrics/links, not marketing copy.

- [ ] **Step 3: Verify**

Run:

```bash
pytest -q tests/test_mesh_viewer_assets.py
```

Expected: PASS.

---

### Task 4: uploads/7 Comparison Bundle Smoke Run

**Files:**
- Generated: `/var/www/html/demo/php/map/3D/gaussian_splat/uploads/7/compare/**`

- [ ] **Step 1: Build the comparison bundle**

Run:

```bash
python3 scripts/build_compare_bundle.py --job-dir uploads/7 --mesh-method auto
```

Expected:
- `uploads/7/compare/splat/viewer.json`
- `uploads/7/compare/mesh/point_cloud.ply`
- `uploads/7/compare/mesh/raw_mesh.ply`
- `uploads/7/compare/mesh/cleaned_mesh.glb`
- `uploads/7/compare/mesh/mesh_report.json`
- `uploads/7/compare/compare_report.json`
- `uploads/7/compare/verdict.md`

- [ ] **Step 2: Final verification**

Run:

```bash
pytest -q tests/test_mesh_extraction_scripts.py tests/test_mesh_viewer_assets.py
python3 -m py_compile scripts/splat_to_pointcloud.py scripts/pointcloud_to_mesh.py scripts/blender_mesh_cleanup.py scripts/build_compare_bundle.py
test -f uploads/7/compare/mesh/cleaned_mesh.glb
```

Expected: PASS and GLB exists.
