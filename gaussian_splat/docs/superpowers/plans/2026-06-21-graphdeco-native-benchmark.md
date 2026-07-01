# Graphdeco Native Benchmark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the official Graphdeco INRIA `gaussian-splatting` pipeline once from a clean official checkout, then publish web-viewable benchmark artifacts for comparison with the current Nerfstudio pipeline.

**Architecture:** Keep the official repository isolated under `external/graphdeco-gaussian-splatting` and do not mix it into the PHP/Nerfstudio application code. Reuse the already downloaded official dataset under `data/official_graphdeco/tandt_db`, write all published artifacts under `uploads/3/official-graphdeco-native`, and document exact commands/results for repeatability.

**Tech Stack:** Graphdeco INRIA `gaussian-splatting`, CUDA/PyTorch, official COLMAP-format dataset, existing `viewer_splat.html` for website inspection.

---

### Task 1: Official Checkout

**Files:**
- Create: `external/graphdeco-gaussian-splatting/`
- Create: `uploads/3/official-graphdeco-native/`

- [ ] Clone `https://github.com/graphdeco-inria/gaussian-splatting.git` with submodules into `external/graphdeco-gaussian-splatting`.
- [ ] Record the commit hash used for the benchmark.
- [ ] Confirm official scripts exist: `train.py`, `render.py`, `full_eval.py`, `environment.yml`.

### Task 2: Native Environment Probe

**Files:**
- Read: `external/graphdeco-gaussian-splatting/environment.yml`
- Read: `external/graphdeco-gaussian-splatting/README.md`

- [ ] Check available CUDA/PyTorch environment.
- [ ] Prefer the official environment when possible.
- [ ] If conda is unavailable in shell PATH, use `/park/conda_vm/gs_scene/bin/python` as the CUDA/PyTorch base and install official submodules there only if needed.
- [ ] Verify `python train.py -h` can import the official package.

### Task 3: First Native Training Run

**Files:**
- Read: `data/official_graphdeco/tandt_db/tandt/train`
- Create: `uploads/3/official-graphdeco-native/train-7k/`

- [ ] Run official `train.py` on the official `tandt/train` scene.
- [ ] Start with a bounded iteration count, e.g. `--iterations 7000`, to validate the official path before committing to 30k.
- [ ] Keep output under `uploads/3/official-graphdeco-native/train-7k/model`.
- [ ] Capture stdout/stderr to `uploads/3/official-graphdeco-native/train-7k/train.log`.

### Task 4: Publish Viewer Artifact

**Files:**
- Create: `uploads/3/official-graphdeco-native/train-7k/point_cloud/iteration_7000/point_cloud.ply`

- [ ] Confirm official PLY exists after training.
- [ ] If `viewer_splat.html` can load the official PLY directly, publish that URL.
- [ ] If the PLY format differs from our viewer expectations, inspect the header and add a minimal conversion/export step in a later task instead of mutating the official output.

### Task 5: Benchmark Notes

**Files:**
- Create: `uploads/3/official-graphdeco-native/benchmark-notes.md`
- Modify: `history.md`

- [ ] Record dataset, official commit, command, runtime, output paths, and whether our viewer can display the official PLY.
- [ ] Compare visually against Nerfstudio `train-7k-ds2-round` and note whether fragmentation is mostly training/export/viewer-related.

---

### Initial Acceptance Criteria

- Official repo checkout exists and has a recorded commit.
- At least one official scene training run completes or fails with a documented blocker.
- The result is inspectable from the 3wa website, or the exact format blocker is documented.
- Existing PHP/Nerfstudio app code is not changed for this probe.
