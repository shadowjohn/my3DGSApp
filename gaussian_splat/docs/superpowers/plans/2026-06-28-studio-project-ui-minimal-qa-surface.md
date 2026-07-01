# Studio Project UI Minimal QA Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增最小 Studio QA UI，讓使用者建立 QA job 並查看 studio job / engine_runs / QA report path。

**Architecture:** 新增 `/var/www/html/demo/php/map/3D/studio/index.php`。頁面只呼叫 `studio/api.php?mode=create_qa_job` 與 `studio/api.php?mode=job_detail`，不執行 worker、不做 dashboard。

**Tech Stack:** PHP auth gate、vanilla JavaScript、Studio API、pytest static tests、`php -l`。

---

### Task 1: UI Contract Test

**Files:**
- Modify: `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_studio_orchestration_foundation.py`

- [ ] Assert `studio/index.php` exists.
- [ ] Assert it posts to `api.php?mode=create_qa_job`.
- [ ] Assert it reads `api.php?mode=job_detail`.
- [ ] Assert it displays engine runs, `delivery_candidate`, `diagnostic`, and `qa_validation_report.json`.
- [ ] Assert it does not mention Premium / Compare Viewer.

### Task 2: Minimal QA UI

**Files:**
- Create: `/var/www/html/demo/php/map/3D/studio/index.php`

- [ ] Require existing admin password check.
- [ ] Add form fields: title, input path, source type.
- [ ] On submit, call create API and show `studio_job_id`.
- [ ] Add detail lookup by studio job id.
- [ ] Render mode/status, engine_runs, and QA report path.

### Task 3: Verify

Run:

```bash
php -l /var/www/html/demo/php/map/3D/studio/index.php
pytest -q tests/test_studio_orchestration_foundation.py
pytest -q
```

Expected: all pass.
