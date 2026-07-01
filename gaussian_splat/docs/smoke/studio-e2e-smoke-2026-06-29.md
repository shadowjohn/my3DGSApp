# Studio E2E Smoke - 2026-06-29

Task: 10A-2 Controlled Real QA / Premium E2E Smoke Execution.

This smoke did not start COLMAP, OpenMVS, Gaussian training, `qa_worker` engine workers, or `premium_worker` engine workers. It created Studio jobs and reused existing completed engine outputs:

- OpenMVS external job: `openmvs_jobs#15` (`status=2`, `exports/model.glb`)
- Gaussian external job: `gaussian_splat_jobs#8` (`status=2`, `exports/splat.clean.ply`)

## QA Smoke

Command:

```bash
php /var/www/html/demo/php/map/3D/studio/create_qa_job.php \
  --title='Smoke QA existing outputs 2026-06-29' \
  --input=/var/www/html/demo/php/map/3D/gaussian_splat/uploads/8/input/input.mp4 \
  --source-type=video
```

Studio job:

- `studio_job_id`: `1`
- mode: `qa`
- preflight: `confidence_score=0.941`, `confidence_level=high`
- gate decision: `pass`
- engine runs:
  - `openmvs`, role `delivery_candidate`, external `openmvs_jobs#15`, status `2`
  - `gaussian_splat`, role `diagnostic`, external `gaussian_splat_jobs#8`, status `2`

Aggregation:

```bash
php /var/www/html/demo/php/map/3D/studio/qa_worker.php --job-id=1
```

Result:

- worker output: `studio_job 1: completed`
- delivery manifest: `/var/www/html/demo/php/map/3D/studio/jobs/1/delivery_manifest.json`
- validation report: `/var/www/html/demo/php/map/3D/studio/jobs/1/validation/qa_validation_report.json`
- viewer: `https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_compare_splat_mesh.html?studio_job_id=1`
- evidence status: `not_available` because these legacy outputs do not include `evidence_manifest_path`

Smoke harness result:

```json
{
  "status": "ok",
  "studio_job_id": 1,
  "mode": "qa",
  "viewer_link": "viewer_compare_splat_mesh.html?studio_job_id=1"
}
```

## Premium Smoke

Command:

```bash
php /var/www/html/demo/php/map/3D/studio/create_premium_job.php \
  --title='Smoke Premium existing outputs 2026-06-29' \
  --input=/var/www/html/demo/php/map/3D/gaussian_splat/uploads/8/input/input.mp4 \
  --source-type=video
```

Studio job:

- `studio_job_id`: `2`
- mode: `premium`
- preflight: `confidence_score=0.941`, `confidence_level=high`
- gate decision: `pass`
- engine runs:
  - `openmvs`, role `delivery_capable`, external `openmvs_jobs#15`, status `2`
  - `gaussian_splat`, role `delivery_capable`, external `gaussian_splat_jobs#8`, status `2`

Aggregation:

```bash
php /var/www/html/demo/php/map/3D/studio/premium_worker.php --job-id=2
```

Result:

- worker output: `studio_job 2: completed`
- delivery manifest: `/var/www/html/demo/php/map/3D/studio/jobs/2/delivery_manifest.json`
- viewer: `https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_compare_splat_mesh.html?studio_job_id=2`
- evidence status: `not_available` because these legacy outputs do not include `evidence_manifest_path`

Smoke harness result:

```json
{
  "status": "ok",
  "studio_job_id": 2,
  "mode": "premium",
  "viewer_link": "viewer_compare_splat_mesh.html?studio_job_id=2"
}
```

## HTTP Checks

- QA manifest: `https://3wa.tw/demo/php/map/3D/studio/jobs/1/delivery_manifest.json` -> `HTTP 200`
- Premium manifest: `https://3wa.tw/demo/php/map/3D/studio/jobs/2/delivery_manifest.json` -> `HTTP 200`
- OpenMVS GLB: `https://3wa.tw/demo/php/map/3D/openmvs/uploads/15/exports/model.glb` -> `HTTP 200`
- Gaussian splat: `https://3wa.tw/demo/php/map/3D/gaussian_splat/uploads/8/exports/splat.clean.ply` -> `HTTP 200`
- Compare viewer: `https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_compare_splat_mesh.html?studio_job_id=1` -> `HTTP 200`
- Compare viewer: `https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_compare_splat_mesh.html?studio_job_id=2` -> `HTTP 200`

`studio/api.php` requires login through `checkpassword.php`; anonymous curl receives the login page. Browser smoke should be done while logged in.

## Recheck After Delivery Page MVP

Time: `2026-06-29 11:41:56 CST`

No reconstruction workers were started. The recheck reused the same completed Studio jobs:

- QA Studio job: `1`
- Premium Studio job: `2`

Fresh smoke harness checks:

```bash
python3 scripts/studio_e2e_smoke.py --job-id=1
python3 scripts/studio_e2e_smoke.py --job-id=2
php -r 'require "/var/www/html/demo/php/map/3D/studio/studio_lib.php"; echo json_encode(studio_job_detail(1), JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES|JSON_PRETTY_PRINT), "\n";' > /tmp/studio_job_1.json
python3 scripts/studio_e2e_smoke.py --job-detail-json=/tmp/studio_job_1.json
php -r 'require "/var/www/html/demo/php/map/3D/studio/studio_lib.php"; echo json_encode(studio_job_detail(2), JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES|JSON_PRETTY_PRINT), "\n";' > /tmp/studio_job_2.json
python3 scripts/studio_e2e_smoke.py --job-detail-json=/tmp/studio_job_2.json
```

Results:

- QA job `1`: `status=ok`, mode `qa`, engine runs `openmvs` + `gaussian_splat`, preflight `ok`, gate `pass`, validation `ok`, delivery manifest `ok`, evidence `not_available`
- Premium job `2`: `status=ok`, mode `premium`, engine runs `openmvs` + `gaussian_splat`, preflight `ok`, gate `pass`, delivery manifest `ok`, evidence `not_available`
- Premium validation remains `not_available` in this existing-output smoke because this run is not a full Premium rebuild.

Delivery page checks:

- `https://3wa.tw/demo/php/map/3D/studio/delivery.php?job_id=1` -> `HTTP 302` to login
- `https://3wa.tw/demo/php/map/3D/studio/delivery.php?job_id=2` -> `HTTP 302` to login

Viewer / artifact checks:

- `https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_compare_splat_mesh.html?studio_job_id=1` -> `HTTP 200`
- `https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_compare_splat_mesh.html?studio_job_id=2` -> `HTTP 200`
- `https://3wa.tw/demo/php/map/3D/openmvs/uploads/15/exports/model.glb` -> `HTTP 200`
- `https://3wa.tw/demo/php/map/3D/gaussian_splat/uploads/8/exports/splat.clean.ply` -> `HTTP 200`

## Notes

- This is a real Studio orchestration smoke over existing completed engine outputs.
- This is not a full rebuild smoke.
- Evidence is correctly reported as unavailable for these legacy outputs.
- `studio/` and `studio/jobs/*` directory permissions needed `755` for web smoke, and Studio PHP files needed `644`.
