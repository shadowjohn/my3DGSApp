# Studio E2E Smoke Runbook

This runbook checks existing QA / Premium outputs only. It does not create jobs, run workers, or start reconstruction.

## Quick Checks

No job id, scan existing completed Studio manifests:

```bash
python3 scripts/studio_e2e_smoke.py
```

Specific Studio job id:

```bash
python3 scripts/studio_e2e_smoke.py --job-id=123
```

Captured Studio API detail:

```bash
curl 'https://3wa.tw/demo/php/map/3D/studio/api.php?mode=job_detail&id=123' > /tmp/studio_job_123.json
python3 scripts/studio_e2e_smoke.py --job-detail-json=/tmp/studio_job_123.json
```

Direct manifest smoke:

```bash
python3 scripts/studio_e2e_smoke.py --manifest=/var/www/html/demo/php/map/3D/studio/jobs/123/delivery_manifest.json
```

## Expected Output

The smoke report should include:

- `studio_job_id`
- `viewer_link`
- `checks.engine_runs`
- `checks.preflight`
- `checks.gate_decision`
- `checks.validation`
- `checks.delivery_manifest`
- `checks.evidence`

If there is no completed Studio job, the script returns:

```json
{
  "status": "missing_completed_job"
}
```

That is a clean smoke-harness state, not a reconstruction failure.

## Viewer Smoke

Open the emitted `viewer_link`, usually:

```text
viewer_compare_splat_mesh.html?studio_job_id=123
```

The viewer should not blank if evidence is missing. It should show pending / not available states for missing evidence assets.

## Boundaries

- Do not run `qa_worker.php`.
- Do not run `premium_worker.php`.
- Do not create QA / Premium jobs.
- Do not change schemas.
- Do not start COLMAP / OpenMVS / Gaussian reconstruction.
