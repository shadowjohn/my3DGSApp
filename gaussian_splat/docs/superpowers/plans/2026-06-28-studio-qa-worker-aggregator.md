# Studio QA Worker Aggregator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓 Studio QA job 可以建立 OpenMVS delivery_candidate + Gaussian diagnostic engine_runs，並在兩邊 terminal 後彙整 QA report。

**Architecture:** 新增一個薄 CLI worker `/var/www/html/demo/php/map/3D/studio/qa_worker.php`。Worker 只呼叫 `studio_lib.php` adapter enqueue 既有 OpenMVS / Gaussian queues，不直接呼叫任何 engine worker script。

**Tech Stack:** PHP CLI、既有 DB helper、pytest static tests、`php -l`。

---

### Task 1: Add Worker Contract Tests

**Files:**
- Modify: `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_studio_orchestration_foundation.py`

- [ ] Add assertions that `qa_worker.php` exists.
- [ ] Assert worker uses `studio_enqueue_engine_run`.
- [ ] Assert it creates OpenMVS `delivery_candidate` and Gaussian `diagnostic`.
- [ ] Assert it writes `qa_validation_report.json`.
- [ ] Assert it does not contain `run_openmvs_pipeline.sh` or `run_mvp_pipeline.sh`.

### Task 2: Implement QA Worker

**Files:**
- Create: `/var/www/html/demo/php/map/3D/studio/qa_worker.php`

- [ ] Load `studio_lib.php`.
- [ ] Select pending/running QA `studio_jobs`.
- [ ] Ensure two engine_runs exist idempotently.
- [ ] Sync engine_run statuses.
- [ ] When both engine_runs are terminal, write `jobs/{id}/validation/qa_validation_report.json`.
- [ ] Update `studio_jobs.status` to ready, partial_failed, or failed.

### Task 3: Verify

Run:

```bash
php -l /var/www/html/demo/php/map/3D/studio/qa_worker.php
pytest -q tests/test_studio_orchestration_foundation.py
pytest -q
```

Expected: all pass.
