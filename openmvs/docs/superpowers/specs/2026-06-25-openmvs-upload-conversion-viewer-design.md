# OpenMVS Upload Conversion Viewer Design

## Goal

Build `/var/www/html/demo/php/map/3D/openmvs` as a PHP job queue that mirrors the existing Gaussian Splat upload flow, but converts MP4 videos or image ZIP packages through COLMAP + OpenMVS and exposes a browser GLB viewer.

## Approved Scope

- Upload MP4 or ZIP image packages.
- Store each upload as a queued job in `openmvs_jobs`.
- Run conversion in the background through a cron-driven worker.
- Produce `uploads/{id}/exports/model.glb` as the primary viewer artifact.
- Keep useful intermediate artifacts such as COLMAP workspace, `.mvs`, `.ply`, textured mesh files, logs, and JSON reports for diagnosis.
- Use `/park/conda_vm/openmvs` as the preferred local environment path.
- Do not store sudo credentials in scripts, logs, PHP, or docs.

## Architecture

The app follows the existing Gaussian Splat shape: `api.php` validates uploads and inserts pending jobs, `crontab/1_run.php` claims one pending job under a lock, `scripts/run_openmvs_pipeline.sh` performs the conversion, and `index.php` polls `api.php?mode=jobs_delta` to update progress. Viewer actions open `viewer_mesh.html?src=uploads/{id}/exports/model.glb`.

Pipeline stages are:

1. Prepare input images from MP4 or safe ZIP extraction.
2. Run COLMAP feature extraction, matching, mapping, and image undistortion.
3. Import the COLMAP dense workspace into OpenMVS with `InterfaceCOLMAP`.
4. Run `DensifyPointCloud`, `ReconstructMesh`, optional `RefineMesh`, and `TextureMesh`.
5. Export GLB with `TransformScene --convert 1 --export-type glb`.
6. Write `qa_report.json`, `transform.json`, and readable artifacts.

## Environment

The runner searches these paths in order:

- `OPENMVS_BIN_DIR` if provided.
- `/park/conda_vm/openmvs/bin`.
- `PATH`.

`OPENMVS_CONDA_ENV` defaults to `/park/conda_vm/openmvs`. The install helper creates this conda path and can compile OpenMVS, but the app must fail jobs clearly if OpenMVS binaries are missing.

## Failure Handling

Upload validation rejects unsupported extensions, empty files, unsafe ZIPs, ZIPs with no usable images, and MP4 files whose duration cannot be read or is shorter than three seconds. Worker failures update `status=3`, store `reason`, append `process_log`, and leave intermediate files in place.

## Verification

Automated tests cover static PHP assets, cron worker wiring, shell pipeline commands, safe ZIP extraction, and QA report generation. A full photogrammetry run depends on installed OpenMVS binaries and should be smoke-tested separately after environment setup.
