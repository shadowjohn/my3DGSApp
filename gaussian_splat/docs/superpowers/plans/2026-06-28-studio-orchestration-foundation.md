# Studio Orchestration Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立 Studio 共用 project / job / engine_runs foundation，讓 OpenMVS 與 Gaussian Splat 仍由各自 queue / DB / lock 執行。

**Architecture:** 新增 `/var/www/html/demo/php/map/3D/studio` 作為薄 orchestration 層。Studio 只建立 project/job/engine_run records，adapter 只把輸入排進 OpenMVS 或 Gaussian 既有 uploads + DB queue，不直接呼叫兩邊 worker script。

**Tech Stack:** PHP 既有 `inc/config.php`、`insertSQL`、`selectSQL_SAFE`、`updateSQL_SAFE`、MySQL/MariaDB、pytest static asset tests。

---

### Task 1: Studio Tables

**Files:**
- Create: `/var/www/html/demo/php/map/3D/studio/migrate.php`
- Test: `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_studio_orchestration_foundation.py`

- [ ] **Step 1: Write static migration expectations**

Run: `pytest -q tests/test_studio_orchestration_foundation.py`

Expected: fail until `studio/migrate.php` exists and defines `studio_projects`, `studio_jobs`, `studio_engine_runs`.

- [ ] **Step 2: Create migration**

Create `studio/migrate.php` with `CREATE TABLE IF NOT EXISTS` for:

- `studio_projects`
- `studio_jobs`
- `studio_engine_runs`

- [ ] **Step 3: Validate syntax**

Run: `php -l /var/www/html/demo/php/map/3D/studio/migrate.php`

Expected: `No syntax errors detected`.

### Task 2: Engine Adapter Library

**Files:**
- Create: `/var/www/html/demo/php/map/3D/studio/studio_lib.php`
- Test: `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_studio_orchestration_foundation.py`

- [ ] **Step 1: Write adapter expectations**

Assert `studio_lib.php` exposes:

- `studio_create_project`
- `studio_create_job`
- `studio_enqueue_engine_run`
- `studio_refresh_engine_run_status`

Assert it contains no direct worker invocation:

- `run_openmvs_pipeline.sh`
- `run_mvp_pipeline.sh`

- [ ] **Step 2: Implement minimal adapter functions**

Adapters insert into existing engine queues:

- OpenMVS: `openmvs_jobs`, `/var/www/html/demo/php/map/3D/openmvs/uploads/{id}/input/input.{ext}`
- Gaussian: `gaussian_splat_jobs`, `/var/www/html/demo/php/map/3D/gaussian_splat/uploads/{id}/input/input.mp4`

- [ ] **Step 3: Validate syntax and tests**

Run:

```bash
php -l /var/www/html/demo/php/map/3D/studio/studio_lib.php
pytest -q tests/test_studio_orchestration_foundation.py
```

Expected: all pass.

### Task 3: TODO Boundary Note

**Files:**
- Modify: `/var/www/html/demo/php/map/3D/gaussian_splat/docs/todo.md`

- [ ] **Step 1: Add Studio foundation checklist**

Add a checked item for Studio orchestration foundation.

- [ ] **Step 2: Keep QA orchestration unchecked**

Add note:

`Blocked until Studio-level project / engine_runs orchestration exists. Do not invoke OpenMVS directly from Gaussian worker because OpenMVS runner owns its upload path, DB, and lock semantics.`

- [ ] **Step 3: Run focused checks**

Run:

```bash
pytest -q tests/test_studio_orchestration_foundation.py
php -l /var/www/html/demo/php/map/3D/studio/migrate.php
php -l /var/www/html/demo/php/map/3D/studio/studio_lib.php
```

Expected: all pass.
