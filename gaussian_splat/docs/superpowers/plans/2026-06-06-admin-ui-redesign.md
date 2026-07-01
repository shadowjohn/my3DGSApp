# Admin UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign `admin.php` so the backend table is readable, has comfortable column widths, hides invalid completed-job abort actions, confirms destructive/admin actions, and uses compact report labels.

**Architecture:** Keep the current single-file PHP admin page and existing `api.php?mode=admin_action` endpoint. Add static contract tests first, then update `admin.php` markup/CSS/JS in place: a flex header with a right-aligned back button, fixed table column classes, clearer dark table styling, compact QA link text, conditional action buttons, and confirmation before retry/abort.

**Tech Stack:** PHP 8.1, Bootstrap-style existing button/table classes, jQuery, pytest static page contract tests, `php -l`.

---

## File Structure

- Modify `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_php_page_assets.py`
  - Locks the new admin layout contract.
  - Requires readable admin CSS classes.
  - Requires compact `品管` QA link text instead of visible `qa_report.json`.
  - Requires completed/non-active jobs not to show abort controls.
  - Requires retry/abort confirmation before posting actions.

- Modify `/var/www/html/demo/php/map/3D/gaussian_splat/admin.php`
  - Owns the backend UI, table markup, action buttons, and admin JS.
  - No API behavior changes are required for this plan.

## Contract

The implementation must satisfy these user-visible requirements:

- The backend page stays dark but becomes easier to read: stronger text color, calmer table header, better spacing, and reduced cramped layout.
- The header shows `Gaussian Splat 轉檔後台` on the left and a right-aligned button-style `回前台` link.
- The duration column is wider and no longer wraps short labels like `排隊`, `轉檔`, `總計`, or their values.
- Visible `qa_report.json` link text becomes `品管`.
- Completed jobs must not show `中止`.
- Waiting/running jobs may show `中止`.
- `重試` and `中止` must ask for confirmation before posting to `api.php?mode=admin_action`.
- Existing admin detail dialog behavior remains intact.

---

### Task 1: Write Admin UI Contract Tests

**Files:**
- Modify: `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_php_page_assets.py`
- Test: `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_php_page_assets.py`

- [ ] **Step 1: Update admin test assertions**

In `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_php_page_assets.py`, inside `test_admin_page_requires_auth_and_exposes_job_actions()`, replace the current admin UI/action assertions from:

```python
    assert "qa_report.json" in text
    assert "timing_report.json" in text
    assert "jobAction" in text
    assert "api.php?mode=admin_action" in text
    assert "retry" in text
    assert "abort" in text
    assert "$isRunning = (string)$r['status'] === '1';" in text
    assert "<?php if(!$isRunning): ?>" in text
    assert "$hasSplat = $isReady && is_file" in text
```

with:

```python
    assert "qa_report.json" in text
    assert ">qa_report.json<" not in text
    assert ">品管<" in text
    assert "timing_report.json" in text
    assert "jobAction" in text
    assert "confirmAdminAction" in text
    assert "api.php?mode=admin_action" in text
    assert "retry" in text
    assert "abort" in text
    assert "$isRunning = (string)$r['status'] === '1';" in text
    assert "$canAbort = in_array((string)$r['status'], ['0','1'], true);" in text
    assert "<?php if(!$isRunning): ?>" in text
    assert "<?php if($canAbort): ?>" in text
    assert "$hasSplat = $isReady && is_file" in text
```

Then replace the current header, table, and action assertions from:

```python
    assert "回前台" in text
    assert "<th>編號</th>" in text
    assert "<th>標題</th>" in text
    assert "<th>狀態</th>" in text
    assert "<th>耗時</th>" in text
    assert "<th>階段明細</th>" in text
    assert "<th>影格</th>" in text
    assert "<th>Splat 大小 (MB)</th>" in text
    assert "<th>品管</th>" in text
    assert "<th>操作</th>" in text
    assert ">重試<" in text
    assert ">中止<" in text
    assert "onclick=\"jobAction(<?=$id;?>,'retry')\"" in text
    assert "onclick=\"jobAction(<?=$id;?>,'abort')\"" in text
```

with:

```python
    assert ".gs-admin{max-width:1480px;" in text
    assert ".gs-admin-header{display:flex;" in text
    assert "justify-content:space-between" in text
    assert ".gs-admin-back-btn" in text
    assert 'class="btn btn-default gs-admin-back-btn" href="index.php">回前台</a>' in text
    assert ".gs-admin-table{table-layout:fixed;" in text
    assert ".gs-admin-col-duration{width:190px;min-width:190px;white-space:nowrap;}" in text
    assert ".gs-admin-duration{white-space:nowrap;" in text
    assert ".gs-admin-stage-list" in text
    assert ".gs-admin-qa-link" in text
    assert '<th class="gs-admin-col-id">編號</th>' in text
    assert '<th class="gs-admin-col-title">標題</th>' in text
    assert '<th class="gs-admin-col-status">狀態</th>' in text
    assert '<th class="gs-admin-col-duration">耗時</th>' in text
    assert '<th class="gs-admin-col-stage">階段明細</th>' in text
    assert '<th class="gs-admin-col-frames">影格</th>' in text
    assert '<th class="gs-admin-col-size">Splat 大小 (MB)</th>' in text
    assert '<th class="gs-admin-col-qa">品管</th>' in text
    assert '<th class="gs-admin-col-actions">操作</th>' in text
    assert ">重試<" in text
    assert ">中止<" in text
    assert "onclick=\"confirmAdminAction(<?=$id;?>,'retry','重試')\"" in text
    assert "onclick=\"confirmAdminAction(<?=$id;?>,'abort','中止')\"" in text
    assert 'if(!confirm("確定要" + label + "工作 #" + id + "？")) return;' in text
```

Keep the existing assertions for:

```python
    assert ">詳細<" in text
    assert ">檢視<" in text
    assert "current_stage_label" in text
    assert "queue_seconds" in text
    assert "process_seconds" in text
    assert "duration_seconds" in text
    assert "timing_report.json</a>" in text
    assert "目前沒有工作。" in text
    assert 'alert(jd.reason || "操作失敗");' in text
    assert 'document.title = "Gaussian Splat 轉檔後台";' in text
```

- [ ] **Step 2: Run the admin page test and verify it fails**

Run:

```bash
cd /var/www/html/demo/php/map/3D/gaussian_splat
pytest -q tests/test_php_page_assets.py::test_admin_page_requires_auth_and_exposes_job_actions
```

Expected: FAIL because `admin.php` still uses the old heading link, old table column markup, visible `qa_report.json` label, always-visible abort button, and direct `jobAction()` calls.

- [ ] **Step 3: Commit the red test if the worktree allows a clean test-only commit**

Run:

```bash
cd /var/www/html/demo/php/map/3D/gaussian_splat
git add tests/test_php_page_assets.py
git commit -m "test(gaussian): require clearer admin table UI"
```

Expected: commit succeeds if `tests/test_php_page_assets.py` has no unrelated unstaged hunks. If the file already contains unrelated uncommitted work, do not force a mixed commit; leave the test change unstaged and record that the commit is deferred because the shared worktree is dirty.

---

### Task 2: Redesign Admin Header And Table Styling

**Files:**
- Modify: `/var/www/html/demo/php/map/3D/gaussian_splat/admin.php`
- Test: `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_php_page_assets.py`

- [ ] **Step 1: Replace the admin CSS block**

In `/var/www/html/demo/php/map/3D/gaussian_splat/admin.php`, replace the CSS rules from:

```css
  .gs-admin{max-width:1280px;margin:0 auto;padding:20px;}
  .gs-admin h2{margin-top:0;}
  .gs-admin table td,.gs-admin table th{vertical-align:middle!important;}
  .gs-admin-actions{white-space:nowrap;}
  .gs-admin-actions .btn{margin-right:4px;}
  .gs-admin-reason{margin-top:4px;font-size:13px;line-height:1.45;color:#ffb4b4;max-width:360px;}
```

with this exact CSS:

```css
  html, html body{background:#0f1722;color:#e5edf7;}
  .gs-admin{max-width:1480px;margin:0 auto;padding:22px 20px 42px;}
  .gs-admin-header{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:14px;}
  .gs-admin h2{margin:0;color:#f8fafc;font-size:28px;font-weight:700;letter-spacing:0;}
  .gs-admin-back-btn{background:#1d2a3a;border-color:#3b4a5f;color:#e5edf7;}
  .gs-admin-back-btn:hover,.gs-admin-back-btn:focus{background:#26364a;border-color:#5a718b;color:#fff;}
  .gs-admin-table{table-layout:fixed;background:#111b2a;border:1px solid #334155;margin-bottom:0;}
  .gs-admin-table > thead > tr > th{background:#223047;color:#f8fafc;border-color:#334155;font-weight:700;vertical-align:middle!important;}
  .gs-admin-table > tbody > tr > td{border-color:#29384d;color:#dbe7f3;vertical-align:middle!important;}
  .gs-admin-table.table-hover > tbody > tr:hover{background:#12363c;}
  .gs-admin-col-id{width:56px;}
  .gs-admin-col-title{width:220px;}
  .gs-admin-col-status{width:190px;}
  .gs-admin-col-duration{width:190px;min-width:190px;white-space:nowrap;}
  .gs-admin-col-stage{width:270px;}
  .gs-admin-col-frames{width:78px;}
  .gs-admin-col-size{width:110px;}
  .gs-admin-col-qa{width:82px;}
  .gs-admin-col-actions{width:210px;}
  .gs-admin-file{margin-top:4px;font-size:12px;color:#9fb0c3;line-height:1.35;word-break:break-word;}
  .gs-admin-status{font-size:16px;font-weight:700;color:#f8fafc;}
  .gs-admin-reason{margin-top:6px;font-size:13px;line-height:1.45;color:#ffb4b4;max-width:320px;}
  .gs-admin-duration{white-space:nowrap;line-height:1.7;font-variant-numeric:tabular-nums;}
  .gs-admin-duration-current{font-size:12px;color:#9fb0c3;white-space:normal;line-height:1.45;}
  .gs-admin-stage-list{font-size:12px;color:#9fb0c3;line-height:1.45;max-height:150px;overflow:auto;}
  .gs-admin-stage-list a{display:inline-block;margin-bottom:4px;color:#dbeafe;font-weight:700;text-decoration:underline;}
  .gs-admin-frame,.gs-admin-size{font-variant-numeric:tabular-nums;white-space:nowrap;}
  .gs-admin-qa-link{min-width:44px;}
  .gs-admin-actions{white-space:nowrap;}
  .gs-admin-actions .btn{margin:2px 3px 2px 0;}
  @media (max-width: 900px){
    .gs-admin{padding:18px 12px 32px;}
    .gs-admin-header{align-items:flex-start;}
    .gs-admin h2{font-size:24px;}
  }
```

Leave all existing log dialog CSS rules after `.gs-admin-actions .btn` in place.

- [ ] **Step 2: Replace the heading with a flex header**

Replace:

```php
<div class="gs-admin">
  <h2>Gaussian Splat 轉檔後台 <small><a href="index.php">回前台</a></small></h2>
```

with:

```php
<div class="gs-admin">
  <div class="gs-admin-header">
    <h2>Gaussian Splat 轉檔後台</h2>
    <a class="btn btn-default gs-admin-back-btn" href="index.php">回前台</a>
  </div>
```

- [ ] **Step 3: Add admin table and column classes**

Replace:

```php
    <table class="table table-bordered table-condensed table-hover">
```

with:

```php
    <table class="table table-bordered table-condensed table-hover gs-admin-table">
```

Then replace the current header row:

```php
          <th>編號</th>
          <th>標題</th>
          <th>狀態</th>
          <th>耗時</th>
          <th>階段明細</th>
          <th>影格</th>
          <th>Splat 大小 (MB)</th>
          <th>品管</th>
          <th>操作</th>
```

with:

```php
          <th class="gs-admin-col-id">編號</th>
          <th class="gs-admin-col-title">標題</th>
          <th class="gs-admin-col-status">狀態</th>
          <th class="gs-admin-col-duration">耗時</th>
          <th class="gs-admin-col-stage">階段明細</th>
          <th class="gs-admin-col-frames">影格</th>
          <th class="gs-admin-col-size">Splat 大小 (MB)</th>
          <th class="gs-admin-col-qa">品管</th>
          <th class="gs-admin-col-actions">操作</th>
```

- [ ] **Step 4: Run the focused test and verify partial progress**

Run:

```bash
cd /var/www/html/demo/php/map/3D/gaussian_splat
php -l admin.php
pytest -q tests/test_php_page_assets.py::test_admin_page_requires_auth_and_exposes_job_actions
```

Expected: PHP lint passes. The admin page test still fails because the row cell classes, QA link text, abort visibility, and confirmation JS are not implemented yet.

- [ ] **Step 5: Commit styling changes if the worktree allows a clean admin-only commit**

Run:

```bash
cd /var/www/html/demo/php/map/3D/gaussian_splat
git add admin.php
git commit -m "style(gaussian): improve admin table readability"
```

Expected: commit succeeds if `admin.php` has no unrelated unstaged hunks. If `admin.php` already contains unrelated uncommitted work, do not force a mixed commit; leave the change unstaged and record that the commit is deferred because the shared worktree is dirty.

---

### Task 3: Update Row Markup, QA Label, And Action Visibility

**Files:**
- Modify: `/var/www/html/demo/php/map/3D/gaussian_splat/admin.php`
- Test: `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_php_page_assets.py`

- [ ] **Step 1: Add `canAbort` row state**

Inside the `foreach($rows as $r)` setup block in `admin.php`, after:

```php
          $isRunning = (string)$r['status'] === '1';
```

add:

```php
          $canAbort = in_array((string)$r['status'], ['0','1'], true);
```

This means only waiting and running jobs show `中止`. Completed, failed, and already-aborted jobs do not show abort.

- [ ] **Step 2: Replace title, status, duration, stage, frame, size, and QA cells**

Replace the current cells from:

```php
          <td>
            <?=htmlspecialchars($r['title'] ?: $r['orin_filename'], ENT_QUOTES);?>
            <div style="font-size:12px;color:#667085;"><?=htmlspecialchars($r['orin_filename'] ?? '', ENT_QUOTES);?></div>
          </td>
          <td>
            <?=htmlspecialchars(gs_admin_status_text($r['status']), ENT_QUOTES);?>
            <?php if($shortReason !== ''): ?>
              <div class="gs-admin-reason"><?=htmlspecialchars($shortReason, ENT_QUOTES);?></div>
            <?php endif; ?>
          </td>
          <td>
            <div>排隊：<?=htmlspecialchars(gs_admin_format_duration($r['queue_seconds'] ?? null), ENT_QUOTES);?></div>
            <div>轉檔：<?=htmlspecialchars(gs_admin_format_duration($r['process_seconds'] ?? null), ENT_QUOTES);?></div>
            <div>總計：<?=htmlspecialchars(gs_admin_format_duration($r['duration_seconds'] ?? null), ENT_QUOTES);?></div>
            <?php if(!empty($r['current_stage_label'])): ?>
              <div style="font-size:12px;color:#667085;">目前：<?=htmlspecialchars($r['current_stage_label'], ENT_QUOTES);?></div>
            <?php endif; ?>
          </td>
          <td>
            <?php if(is_file(__DIR__ . "/{$timing}")): ?>
              <a href="<?=$timing;?>" target="_blank">timing_report.json</a>
            <?php endif; ?>
            <?php foreach($timingRows as $stage): ?>
              <div style="font-size:12px;color:#667085;">
                <?=htmlspecialchars($stage['label'], ENT_QUOTES);?>
                /
                <?=htmlspecialchars($stage['status'], ENT_QUOTES);?>
                /
                <?=htmlspecialchars(gs_admin_format_duration($stage['duration']), ENT_QUOTES);?>
              </div>
            <?php endforeach; ?>
          </td>
          <td><?=htmlspecialchars((string)($r['frame_count'] ?? ''), ENT_QUOTES);?> / <?=htmlspecialchars((string)($r['registered_frame_count'] ?? ''), ENT_QUOTES);?></td>
          <td><?=htmlspecialchars((string)($r['splat_file_size_mb'] ?? ''), ENT_QUOTES);?></td>
          <td><?php if(is_file(__DIR__ . "/{$qa}")): ?><a href="<?=$qa;?>" target="_blank">qa_report.json</a><?php endif; ?></td>
```

with:

```php
          <td>
            <?=htmlspecialchars($r['title'] ?: $r['orin_filename'], ENT_QUOTES);?>
            <div class="gs-admin-file"><?=htmlspecialchars($r['orin_filename'] ?? '', ENT_QUOTES);?></div>
          </td>
          <td>
            <div class="gs-admin-status"><?=htmlspecialchars(gs_admin_status_text($r['status']), ENT_QUOTES);?></div>
            <?php if($shortReason !== ''): ?>
              <div class="gs-admin-reason"><?=htmlspecialchars($shortReason, ENT_QUOTES);?></div>
            <?php endif; ?>
          </td>
          <td class="gs-admin-duration">
            <div>排隊：<?=htmlspecialchars(gs_admin_format_duration($r['queue_seconds'] ?? null), ENT_QUOTES);?></div>
            <div>轉檔：<?=htmlspecialchars(gs_admin_format_duration($r['process_seconds'] ?? null), ENT_QUOTES);?></div>
            <div>總計：<?=htmlspecialchars(gs_admin_format_duration($r['duration_seconds'] ?? null), ENT_QUOTES);?></div>
            <?php if(!empty($r['current_stage_label'])): ?>
              <div class="gs-admin-duration-current">目前：<?=htmlspecialchars($r['current_stage_label'], ENT_QUOTES);?></div>
            <?php endif; ?>
          </td>
          <td>
            <div class="gs-admin-stage-list">
              <?php if(is_file(__DIR__ . "/{$timing}")): ?>
                <a href="<?=$timing;?>" target="_blank">timing_report.json</a>
              <?php endif; ?>
              <?php foreach($timingRows as $stage): ?>
                <div>
                  <?=htmlspecialchars($stage['label'], ENT_QUOTES);?>
                  /
                  <?=htmlspecialchars($stage['status'], ENT_QUOTES);?>
                  /
                  <?=htmlspecialchars(gs_admin_format_duration($stage['duration']), ENT_QUOTES);?>
                </div>
              <?php endforeach; ?>
            </div>
          </td>
          <td class="gs-admin-frame"><?=htmlspecialchars((string)($r['frame_count'] ?? ''), ENT_QUOTES);?> / <?=htmlspecialchars((string)($r['registered_frame_count'] ?? ''), ENT_QUOTES);?></td>
          <td class="gs-admin-size"><?=htmlspecialchars((string)($r['splat_file_size_mb'] ?? ''), ENT_QUOTES);?></td>
          <td><?php if(is_file(__DIR__ . "/{$qa}")): ?><a class="btn btn-xs btn-info gs-admin-qa-link" href="<?=$qa;?>" target="_blank">品管</a><?php endif; ?></td>
```

- [ ] **Step 3: Replace action buttons**

Replace:

```php
            <?php if(!$isRunning): ?>
              <button class="btn btn-xs btn-warning" type="button" onclick="jobAction(<?=$id;?>,'retry')">重試</button>
            <?php endif; ?>
            <button class="btn btn-xs btn-danger" type="button" onclick="jobAction(<?=$id;?>,'abort')">中止</button>
            <button class="btn btn-xs btn-default" type="button" onclick="openJobDetail(<?=$id;?>)">詳細</button>
```

with:

```php
            <?php if(!$isRunning): ?>
              <button class="btn btn-xs btn-warning" type="button" onclick="confirmAdminAction(<?=$id;?>,'retry','重試')">重試</button>
            <?php endif; ?>
            <?php if($canAbort): ?>
              <button class="btn btn-xs btn-danger" type="button" onclick="confirmAdminAction(<?=$id;?>,'abort','中止')">中止</button>
            <?php endif; ?>
            <button class="btn btn-xs btn-default" type="button" onclick="openJobDetail(<?=$id;?>)">詳細</button>
```

- [ ] **Step 4: Run syntax and focused admin test**

Run:

```bash
cd /var/www/html/demo/php/map/3D/gaussian_splat
php -l admin.php
pytest -q tests/test_php_page_assets.py::test_admin_page_requires_auth_and_exposes_job_actions
```

Expected: PHP lint passes. The test still fails because `confirmAdminAction()` is not implemented yet.

- [ ] **Step 5: Commit markup/action visibility changes if the worktree allows a clean admin-only commit**

Run:

```bash
cd /var/www/html/demo/php/map/3D/gaussian_splat
git add admin.php
git commit -m "feat(gaussian): simplify admin job actions"
```

Expected: commit succeeds if `admin.php` has no unrelated unstaged hunks. If the worktree is dirty in the same file from prior work, leave the change uncommitted and note that commit is deferred.

---

### Task 4: Add Retry/Abort Confirmation

**Files:**
- Modify: `/var/www/html/demo/php/map/3D/gaussian_splat/admin.php`
- Test: `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_php_page_assets.py`

- [ ] **Step 1: Add `confirmAdminAction()` before `jobAction()`**

In `admin.php`, immediately before the existing:

```javascript
function jobAction(id, action) {
```

insert:

```javascript
function confirmAdminAction(id, action, label) {
  if(!confirm("確定要" + label + "工作 #" + id + "？")) return;
  jobAction(id, action);
}
```

Leave the existing `jobAction()` body intact:

```javascript
function jobAction(id, action) {
  $.post("api.php?mode=admin_action", { id: id, action: action }, function(jd) {
    if (jd.status === "OK") {
      location.reload();
    } else {
      alert(jd.reason || "操作失敗");
    }
  }, "json");
}
```

- [ ] **Step 2: Run the focused admin test**

Run:

```bash
cd /var/www/html/demo/php/map/3D/gaussian_splat
php -l admin.php
pytest -q tests/test_php_page_assets.py::test_admin_page_requires_auth_and_exposes_job_actions
```

Expected: PHP lint passes and the focused admin test passes.

- [ ] **Step 3: Commit confirmation behavior if the worktree allows a clean admin-only commit**

Run:

```bash
cd /var/www/html/demo/php/map/3D/gaussian_splat
git add admin.php
git commit -m "feat(gaussian): confirm admin retry and abort actions"
```

Expected: commit succeeds if `admin.php` has no unrelated unstaged hunks. If the worktree is dirty in the same file from prior work, leave the change uncommitted and note that commit is deferred.

---

### Task 5: Verification And Visual Check

**Files:**
- Verify: `/var/www/html/demo/php/map/3D/gaussian_splat/admin.php`
- Verify: `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_php_page_assets.py`

- [ ] **Step 1: Run syntax and related tests**

Run:

```bash
cd /var/www/html/demo/php/map/3D/gaussian_splat
php -l admin.php
pytest -q tests/test_php_page_assets.py::test_admin_page_requires_auth_and_exposes_job_actions
pytest -q tests/test_php_page_assets.py
```

Expected:

```text
No syntax errors detected in admin.php
```

and all selected pytest tests pass with exit code `0`.

- [ ] **Step 2: Confirm key source strings**

Run:

```bash
cd /var/www/html/demo/php/map/3D/gaussian_splat
python3 - <<'PY'
from pathlib import Path
text = Path("admin.php").read_text()
assert 'class="btn btn-default gs-admin-back-btn" href="index.php">回前台</a>' in text
assert '>qa_report.json<' not in text
assert '>品管<' in text
assert "$canAbort = in_array((string)$r['status'], ['0','1'], true);" in text
assert 'onclick="confirmAdminAction(<?=$id;?>,\\'abort\\',\\'中止\\')"' in text
assert 'if(!confirm("確定要" + label + "工作 #" + id + "？")) return;' in text
print("admin UI contract source check passed")
PY
```

Expected:

```text
admin UI contract source check passed
```

- [ ] **Step 3: Browser smoke check**

Open:

```text
https://3wa.tw/demo/php/map/3D/gaussian_splat/admin.php
```

Manual verification:

1. Header title is left aligned and `回前台` is a button on the right.
2. Text is readable on the dark background.
3. The table no longer feels cramped at desktop width.
4. `耗時` values do not break into awkward single-character lines.
5. Completed rows do not show `中止`.
6. Waiting/running rows still show `中止`.
7. `重試` asks for confirmation.
8. `中止` asks for confirmation.
9. QA report link displays `品管`, not `qa_report.json`.
10. `詳細` still opens the log dialog.
11. `檢視` still opens the splat viewer for completed jobs with splat files.

---

## Self-Review

**Spec coverage:**

- Backend UI readability and layout width are covered by Task 2 CSS/table changes.
- Completed-item abort removal is covered by Task 3 `$canAbort = in_array((string)$r['status'], ['0','1'], true);`.
- Retry/abort confirmation is covered by Task 4 `confirmAdminAction()`.
- `qa_report.json` visible text becoming `品管` is covered by Task 3 QA cell replacement.
- Wider no-wrap duration column is covered by `.gs-admin-col-duration` and `.gs-admin-duration`.
- `回前台` button on the right is covered by `.gs-admin-header` and `.gs-admin-back-btn`.

**Placeholder scan:**

- Every task names exact files.
- Every implementation step includes the exact code to insert or replace.
- Every verification step includes commands and expected outcomes.

**Type and name consistency:**

- CSS classes use the `gs-admin-*` prefix consistently.
- Confirmation wrapper is consistently named `confirmAdminAction(id, action, label)`.
- Existing `jobAction(id, action)` remains the function that posts to `api.php?mode=admin_action`.
- Existing `openJobDetail(id)` and `openSplatViewer(url)` calls remain unchanged.
