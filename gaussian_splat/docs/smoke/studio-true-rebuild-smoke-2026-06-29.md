# Studio True Rebuild Smoke - 2026-06-29

Latest Result: `full_pass`

## Studio QA Full-pass Baseline Freeze

Baseline: `studio-qa-full-pass-2026-06-29`

- Studio job: `#10`
- OpenMVS external job: `#23`
- Gaussian external job: `#15`
- Manifest: `studio/jobs/10/delivery_manifest.json`
- Compare viewer: `https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_compare_splat_mesh.html?studio_job_id=10`
- Delivery page: `https://3wa.tw/demo/php/map/3D/studio/delivery.php?job_id=10`
- Gaussian cap: `GS_QA_TRAIN_MAX_ITERATIONS=10`, Nerfstudio `max_num_iterations=10`
- Verification: `pytest -q` => 275 passed, `php -l` OK, `bash -n` OK
- Environment notes: `www-data` can read `scripts/`, write `/var/www/.triton`, write `/var/www/.cache`; cron was restored after controlled smoke.

## 10D-2B Capped Gaussian True Rebuild Smoke

Result: `full_pass`

This was a controlled QA true rebuild smoke. OpenMVS and Gaussian cron runners were temporarily paused to avoid queue races, then restored after the smoke. No schema, UI, manifest, hard gate, public token, or artifact-delete behavior was changed.

本次為 controlled QA 真重建 smoke。測試期間暫停 OpenMVS / Gaussian cron runner 避免 queue race，完成後已恢復。沒有修改 schema、UI、manifest、hard gate、public token 或 artifact delete 行為。

### Input

- Source: `/var/www/html/demo/php/map/3D/gaussian_splat/uploads/5/input/input.mp4`
- Size: 3.1 MB
- Mode: `qa`
- Studio job: `#10`
- Studio project: `#10`
- OpenMVS external job: `#23`
- Gaussian external job: `#15`

### Commands

```bash
sudo -u www-data php /var/www/html/demo/php/map/3D/studio/create_qa_job.php \
  --title='Capped Gaussian True Rebuild Smoke QA 2026-06-29 controlled-full-pass' \
  --input=/var/www/html/demo/php/map/3D/gaussian_splat/uploads/5/input/input.mp4 \
  --source-type=video

sudo -u www-data php /var/www/html/demo/php/map/3D/studio/qa_worker.php --job-id=10

sudo -u www-data env \
  OVM_FRAME_FPS=12 \
  OVM_MAX_FRAMES=12 \
  OVM_MIN_FRAMES=5 \
  OVM_FRAME_WIDTH=800 \
  php /var/www/html/demo/php/map/3D/openmvs/crontab/1_run.php

sudo -u www-data env \
  GS_QA_TRAIN_MAX_ITERATIONS=10 \
  GS_FRAME_MAX_FRAMES=8 \
  GS_FRAME_WIDTH=800 \
  php /var/www/html/demo/php/map/3D/gaussian_splat/crontab/1_run.php

sudo -u www-data php /var/www/html/demo/php/map/3D/studio/qa_worker.php --job-id=10
```

### Results

- Studio job `#10`: `completed`
- OpenMVS engine_run `#19`: `completed`
- Gaussian engine_run `#20`: `completed`
- QA validation: `studio/jobs/10/validation/qa_validation_report.json`
- Delivery manifest: `studio/jobs/10/delivery_manifest.json`
- Compare viewer: `viewer_compare_splat_mesh.html?studio_job_id=10`

OpenMVS true rebuild:

- selected frames: 5
- registered frames: 5
- Densify: success
- Reconstruct: success
- Refine: success
- Texture: success
- GLB export: success
- artifact: `openmvs/uploads/23/exports/model.glb`

Gaussian diagnostic:

- `GS_QA_TRAIN_MAX_ITERATIONS=10` was passed from PHP worker.
- `run_mvp_pipeline.sh` logged `[config] GS_TRAIN_MAX_ITERATIONS=10`.
- Nerfstudio config logged `max_num_iterations=10`.
- Training finished at step 9 and exported from `step-000000009.ckpt`.
- artifact: `gaussian_splat/uploads/15/exports/splat.clean.ply`

Delivery tracks:

- `mesh/openmvs`
  - role: `delivery_candidate`
  - delivery_capable: `true`
  - artifact: `../../../openmvs/uploads/23/exports/model.glb`

- `splat/gaussian_splat`
  - role: `diagnostic`
  - delivery_capable: `false`
  - artifact: `../../../gaussian_splat/uploads/15/exports/splat.clean.ply`

HTTP smoke:

```text
200 https://3wa.tw/demo/php/map/3D/studio/jobs/10/delivery_manifest.json
200 https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_compare_splat_mesh.html?studio_job_id=10
200 https://3wa.tw/demo/php/map/3D/openmvs/uploads/23/exports/model.glb
200 https://3wa.tw/demo/php/map/3D/gaussian_splat/uploads/15/exports/splat.clean.ply
302 https://3wa.tw/demo/php/map/3D/studio/delivery.php?job_id=10
```

`delivery.php` returning 302 is expected because it is protected/internal.

Smoke script:

```bash
sudo python3 /var/www/html/demo/php/map/3D/gaussian_splat/scripts/studio_e2e_smoke.py --job-id=10
```

Result:

- status: `ok`
- delivery_manifest: `ok`
- validation: `ok`
- evidence: `not_available`
- viewer_link: `viewer_compare_splat_mesh.html?studio_job_id=10`

### Findings During 10D-2B

- First `gsplat_cuda` run on cu128 compiled torch extensions under `/var/www/.cache/torch_extensions/py310_cu128/gsplat_cuda`; this took much longer than the 10-iteration training itself.
- `gaussian_splat/scripts/` must be readable/executable by `www-data`.
- `/var/www/.triton` and `/var/www/.cache` must be writable by `www-data`.
- If system cron picks a QA Gaussian job without an explicit override, the guard still caps it with default `GS_QA_TRAIN_MAX_ITERATIONS=1000`; for smoke, temporarily pause cron and run the worker with a smaller explicit cap.

No residual `run_mvp_pipeline.sh`, `splatfacto`, `ns-train`, `ns-export`, or OpenMVS heavy process remained after the pass.

## Previous 10D Controlled Smoke

Result: `partial_pass`

This was a controlled true rebuild smoke. It created a real Studio QA job, ran the Studio worker, ran the OpenMVS engine worker, and produced a Studio delivery manifest. Gaussian diagnostic was intentionally aborted after detecting it had started full training without the intended iteration cap.

This smoke is marked as partial_pass. OpenMVS true rebuild, Studio aggregation, delivery manifest, HTTP artifact checks, and Compare Viewer integration passed. Gaussian diagnostic was intentionally stopped because the training cap was not enforced, preventing uncontrolled compute usage. Studio job #4 correctly ended as partial_failed.

本次 smoke 標記為 partial_pass。OpenMVS 真重建、Studio 聚合、delivery manifest、HTTP artifact 檢查與 Compare Viewer 串接皆通過。Gaussian diagnostic 因訓練 cap 未確實生效，為避免無限制燒算力而刻意中止，Studio job #4 正確進入 partial_failed。

## Input

- Source: `/var/www/html/demo/php/map/3D/gaussian_splat/uploads/5/input/input.mp4`
- Size: 3.1 MB
- Mode: `qa`
- Studio job: `#4`
- Studio project: `#4`

## Create Job

```bash
sudo -u www-data php /var/www/html/demo/php/map/3D/studio/create_qa_job.php \
  --title='True Rebuild Smoke QA 2026-06-29 www-data' \
  --input=/var/www/html/demo/php/map/3D/gaussian_splat/uploads/5/input/input.mp4 \
  --source-type=video
```

Created:

- `studio_job_id`: 4
- `preflight_report_path`: `studio/jobs/4/preflight/preflight_report.json`
- Initial gate: `warn`

## Environment Fixes Found

The smoke found two deployment issues before the engine rebuild could run:

1. `gaussian_splat_jobs.pipeline_mode` was missing.
   - Fixed by running existing migration: `php /var/www/html/demo/php/map/3D/gaussian_splat/migrate.php`

2. Runtime directories were not writable/readable by the worker user.
   - `openmvs/uploads` is owned by `www-data`, so Studio worker must run as `www-data`.
   - `studio/jobs` needed to be writable by `www-data`.
   - `gaussian_splat/crontab` was `700 john`, so `www-data` could not read the worker.

These were environment/deploy problems, not schema or orchestration design changes.

## Studio Worker

```bash
sudo -u www-data php /var/www/html/demo/php/map/3D/studio/qa_worker.php --job-id=4
```

Engine runs created:

- OpenMVS engine_run `#7`
  - external job: `openmvs_jobs#17`
  - role: `delivery_candidate`

- Gaussian engine_run `#8`
  - external job: `gaussian_splat_jobs#9`
  - role: `diagnostic`

## OpenMVS True Rebuild

First attempt used too few frames:

- `OVM_FRAME_FPS=1`
- selected 1 image
- failed: `no usable images: selected 1 image(s), require at least 8`

Second attempt:

```bash
sudo -u www-data env \
  OVM_FRAME_FPS=12 \
  OVM_MAX_FRAMES=12 \
  OVM_MIN_FRAMES=5 \
  OVM_FRAME_WIDTH=800 \
  php /var/www/html/demo/php/map/3D/openmvs/crontab/1_run.php
```

Result: `pass`

- selected frames: 5
- registered frames: 5
- OpenMVS Densify: success
- OpenMVS Reconstruct: success
- OpenMVS Refine: success
- OpenMVS Texture: success
- GLB export: success
- `openmvs/uploads/17/exports/model.glb`
- `openmvs/uploads/17/engine_contract.json`
- `openmvs/uploads/17/validation/validation_report.json`
- `openmvs/uploads/17/delivery_manifest.json`

## Gaussian Diagnostic

Gaussian job `#9` started, but the intended `GS_TRAIN_MAX_ITERATIONS=10` cap was not applied because the worker had already started under the crontab process environment.

The process was aborted to avoid burning compute:

- `gaussian_splat_jobs#9`
- final status: `4`
- reason: `使用者中止`
- stage: `splatfacto training`

This means the QA smoke is not a full dual-engine pass. It is a true OpenMVS rebuild pass plus a Studio partial-failure aggregation pass.

## Studio Aggregation

Final Studio job:

- `studio_job_id`: 4
- status: `partial_failed`
- reason: `partial_failed`
- delivery manifest: `studio/jobs/4/delivery_manifest.json`
- validation report: `studio/jobs/4/validation/qa_validation_report.json`

QA validation summary:

- `mesh_issue`: none
- `splat_issue`: `Gaussian diagnostic run did not complete.`
- decision: `review_needed`

## Delivery Manifest

`studio/jobs/4/delivery_manifest.json`

Tracks:

- `mesh/openmvs`
  - role: `delivery_candidate`
  - delivery_capable: `true`
  - artifact: `../../../openmvs/uploads/17/exports/model.glb`

- `splat/gaussian_splat`
  - role: `diagnostic`
  - delivery_capable: `false`
  - artifact path present in manifest, but artifact was not produced because Gaussian was aborted.

## HTTP Smoke

```text
200 /demo/php/map/3D/studio/jobs/4/delivery_manifest.json
200 /demo/php/map/3D/gaussian_splat/viewer_compare_splat_mesh.html?studio_job_id=4
200 /demo/php/map/3D/openmvs/uploads/17/exports/model.glb
302 /demo/php/map/3D/studio/delivery.php?job_id=4
```

`delivery.php` returning 302 is expected because it is protected/internal.

## Smoke Script

```bash
sudo python3 /var/www/html/demo/php/map/3D/gaussian_splat/scripts/studio_e2e_smoke.py --job-id=4
```

Result:

- status: `ok`
- validation: `ok`
- delivery_manifest: `ok`
- evidence: `not_available`
- viewer_link: `viewer_compare_splat_mesh.html?studio_job_id=4`

The script reported `job_detail` as `not_checked` because it read the manifest path directly in this local protected environment.

## Known Limitations

- This is not a full QA dual-engine pass.
- Gaussian diagnostic true rebuild still needs a small, capped worker smoke where `GS_TRAIN_MAX_ITERATIONS` is guaranteed before worker start.
- Premium true rebuild was not run.
- Evidence is `not_available`, which is acceptable for this smoke.

## Follow-up

Minimal next check:

```bash
sudo -u www-data env \
  GS_QA_TRAIN_MAX_ITERATIONS=10 \
  GS_FRAME_MAX_FRAMES=8 \
  GS_FRAME_MIN_FRAMES=5 \
  GS_FRAME_TARGET_FPS=12 \
  GS_FRAME_CANDIDATE_FPS=12 \
  GS_FRAME_WIDTH=800 \
  php /var/www/html/demo/php/map/3D/gaussian_splat/crontab/1_run.php
```

Run only after confirming no existing Gaussian worker is active and the job is freshly queued.
