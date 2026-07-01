# Baseline Behavior Snapshot

Date: 2026-06-28

This file records the current behavior before the Photogrammetry Studio refactor goes deeper. It is intentionally factual and short.

## Gaussian Splat

Upload:

- `index.php` uploads MP4 only through `api.php?mode=upload`.
- Upload validates captcha, title, MP4 extension, and minimum 3 second video length.
- New jobs are inserted into `gaussian_splat_jobs` with `status=0`.
- `pipeline_mode` accepts `fast`, `qa`, or `premium`; empty mode defaults to `fast`.

Worker:

- `crontab/1_run.php` processes one queued job at a time using `1_run.lock`.
- Status values are: `0` queued, `1` running, `2` completed, `3` failed, `4` aborted, `5` waiting review.
- Worker runs `scripts/confidence_gate.py` before the heavy pipeline.
- `hold` moves the job to waiting review.
- `reject` fails the job before training.
- `run`, `warn`, and `run_with_override` continue into `scripts/run_mvp_pipeline.sh`.
- `scripts/run_mvp_pipeline.sh` extracts/chooses frames, runs Nerfstudio/COLMAP processing, trains splatfacto, exports PLY, cleans PLY, writes metadata, and builds `qa_report.json`.

Viewer:

- `viewer_splat.html` loads `js/gaussian_splat_viewer.js`.
- Viewer accepts splat URLs through query params and keeps rotation controls (`rx`, `ry`, `rz`, `up`) on screen.

QA / diagnostics:

- `qa_report.json` is the current Gaussian Splat job summary.
- Confidence artifacts are `confidence_report.json` and `confidence_gate.json`.
- Validation/contract artifacts are being added alongside existing outputs; legacy viewer URLs remain valid.

## OpenMVS

Upload:

- `/var/www/html/demo/php/map/3D/openmvs/index.php` uploads MP4 or image ZIP through `api.php?mode=upload`.
- Upload validates captcha, title, allowed extension, MP4 duration, and ZIP image contents.
- Mask mode accepts `none`, `provided`, or `auto`.
- New jobs are inserted into `openmvs_jobs` with `status=0`.

Worker:

- `/var/www/html/demo/php/map/3D/openmvs/crontab/1_run.php` processes one queued job at a time using `1_run.lock`.
- Worker defaults to `openmvs_native` pipeline mode unless `input/pipeline_mode.txt` overrides it.
- Worker calls `scripts/run_openmvs_pipeline.sh` with `OVM_MASK_MODE` and `OVM_PIPELINE_MODE`.
- On success, worker writes standard artifacts:
  - `engine_contract.json`
  - `validation/validation_report.json`
  - `delivery_manifest.json`
- On failure, failure path writes standard failure artifacts through existing failure helpers.

Viewer:

- `viewer_mesh.html` loads GLB from `src` query param, defaulting to `uploads/1/exports/model.glb`.
- Viewer uses Three.js `GLTFLoader` and `OrbitControls`.
- Current mouse behavior: left rotate, middle rotate, right pan, wheel zoom.
- Existing direct `viewer_mesh.html?src=...` URLs remain the compatibility path.

QA / diagnostics:

- `qa_report.json` stores OpenMVS frame, registration, texture, GLB, and mesh summary fields.
- `openmvs_job_diagnostics` stores compact diagnostics; raw logs remain under `uploads/{id}/logs/openmvs_pipeline.log`.
- The job list shows status, quality, timing, frames, artifacts, and guarded actions.

## Baseline Checks

Run on 2026-06-28:

- Gaussian asset URL check passed:
  - `viewer_splat.html?src=uploads%2F8%2Fexports%2Fsplat.clean.ply...` returned HTTP 200.
  - `uploads/8/exports/splat.clean.ply` returned HTTP 200.
- OpenMVS asset URL check passed:
  - `viewer_mesh.html?src=uploads%2F8%2Fexports%2Fmodel.glb` returned HTTP 200.
  - `uploads/8/exports/model.glb` returned HTTP 200.
- OpenMVS headless render smoke passed with small existing GLB:
  - `viewer_mesh.html?src=uploads%2Fwiki-sceaux-colmap-20260625-131955%2Fexports%2Fmodel.glb`
  - Chromium screenshot reached `Loaded GLB with OrbitControls` and displayed the mesh.
- Gaussian headless render smoke was inconclusive:
  - `viewer_splat.html?src=uploads%2Flocal-smoke%2Fexports%2Fsplat.ply...`
  - Chromium screenshot reached `Processing splats...`, but did not reach a drawn splat before screenshot.
  - Keep the TODO render confirmation unchecked until a real-browser or better automated viewer check verifies an existing splat visually.
