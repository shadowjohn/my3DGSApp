# OpenMVS Upload Conversion Viewer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an OpenMVS upload queue that accepts MP4/ZIP input, converts jobs in the background with COLMAP + OpenMVS, and opens completed GLB models in a browser viewer.

**Architecture:** Mirror the existing Gaussian Splat app with a PHP upload API, MySQL job table, one-at-a-time cron worker, shell pipeline, Python helper scripts, and a three.js GLB viewer. Keep OpenMVS tooling configurable through environment variables and make missing binaries a visible job failure.

**Tech Stack:** PHP, MySQL helper functions from global `config.php`, bash, Python 3 standard library, COLMAP CLI, OpenMVS CLI, ffmpeg/ffprobe, three.js from CDN.

---

## File Structure

- `migrate.php`: create and repair the `openmvs_jobs` table.
- `api.php`: handle captcha, uploads, job delta polling, admin retry/abort, and transform saving.
- `index.php`: upload form, job table, progress polling, and action buttons.
- `job_view.php`: shared rendering helpers for status, timing, artifact links, and `jobs_delta`.
- `crontab/inc/function.php`: command execution, logging, abort, stage parsing, and failure helpers.
- `crontab/1_run.php`: lock, claim one pending job, run the pipeline, and persist final metrics.
- `crontab/1min.sh`: cron entrypoint.
- `scripts/run_openmvs_pipeline.sh`: COLMAP/OpenMVS conversion pipeline.
- `scripts/prepare_images.py`: safe MP4 frame extraction and ZIP image staging.
- `scripts/build_qa_report.py`: summarize artifacts into JSON.
- `scripts/write_default_transform.py`: write basic model geolocation transform JSON.
- `scripts/install_openmvs_env.sh`: create `/park/conda_vm/openmvs` and document OpenMVS build/install steps.
- `viewer_mesh.html`: three.js GLB viewer.
- `js/function.js`: viewer opening and log refresh helpers.
- `tests/`: TDD guard tests for the above assets and helpers.

## Tasks

### Task 1: Test the Required Surface

- [x] Write tests that fail while the OpenMVS app is empty.
- [x] Verify the test suite fails because files/functions are missing.

### Task 2: Implement PHP Queue Surface

- [ ] Create migration, API, index, job view, JS helper, cron helper, cron runner, and cron shell wrapper.
- [ ] Use `openmvs_jobs`, `uploads/{id}/input/input.{mp4|zip}`, `uploads/{id}/exports/model.glb`, and `viewer_mesh.html?src=...`.
- [ ] Run PHP syntax checks and PHP asset tests.

### Task 3: Implement Pipeline Helpers

- [ ] Create `prepare_images.py` with safe ZIP extraction and ffmpeg MP4 extraction.
- [ ] Create `build_qa_report.py` and `write_default_transform.py`.
- [ ] Create `run_openmvs_pipeline.sh` with COLMAP stages, OpenMVS stages, GLB export, and clear missing-tool errors.
- [ ] Run Python unit tests and static pipeline tests.

### Task 4: Add Viewer And Environment Helper

- [ ] Add the three.js GLB viewer adapted from the existing mesh viewer.
- [ ] Add `install_openmvs_env.sh` targeting `/park/conda_vm/openmvs` without embedding sudo credentials.
- [ ] Run shell syntax checks.

### Task 5: Verify Integration

- [ ] Run all tests in `/var/www/html/demo/php/map/3D/openmvs`.
- [ ] Run `php -l` on PHP files.
- [ ] Run `bash -n` on shell scripts.
- [ ] If OpenMVS binaries are absent, verify the pipeline fails with a clear missing-binary message.
