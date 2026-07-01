# Studio QA Trigger API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增 Studio QA job 入口，讓 API/CLI 只建立 pending QA job，後續交給 `qa_worker.php` 處理。

**Architecture:** 在 `studio_lib.php` 增加共用 `studio_create_qa_job` 與 `studio_job_detail`。新增 `studio/api.php` 給 admin/web 呼叫，新增 `studio/create_qa_job.php` 給 CLI 使用；兩者都不直接跑 worker。

**Tech Stack:** PHP、既有 DB helper、pytest static tests、`php -l`。

---

### Task 1: Shared Helpers

**Files:**
- Modify: `/var/www/html/demo/php/map/3D/studio/studio_lib.php`
- Modify: `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_studio_orchestration_foundation.py`

- [ ] Add `studio_create_qa_job($title, $inputPath, $sourceType, $metadata)`.
- [ ] Add `studio_job_detail($studioJobId)`.
- [ ] Assert helpers exist.

### Task 2: API And CLI Entry

**Files:**
- Create: `/var/www/html/demo/php/map/3D/studio/api.php`
- Create: `/var/www/html/demo/php/map/3D/studio/create_qa_job.php`
- Modify: `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_studio_orchestration_foundation.py`

- [ ] `api.php?mode=create_qa_job` creates pending QA job and returns IDs.
- [ ] `api.php?mode=job_detail&id=...` returns job, project, engine_runs, and report path.
- [ ] `create_qa_job.php --title=... --input=...` creates pending QA job and prints JSON.
- [ ] Assert neither entry invokes `qa_worker.php` or engine worker scripts.

### Task 3: Verify

Run:

```bash
php -l /var/www/html/demo/php/map/3D/studio/api.php
php -l /var/www/html/demo/php/map/3D/studio/create_qa_job.php
pytest -q tests/test_studio_orchestration_foundation.py
pytest -q
```

Expected: all pass.
