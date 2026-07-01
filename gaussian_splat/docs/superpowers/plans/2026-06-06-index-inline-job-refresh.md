# Inline Job Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the front page active-job full page reload with an AJAX poll that updates only the existing job row cells, preserving partially filled forms and scroll position.

**Architecture:** Move front-page job row presentation into a shared PHP helper so `index.php` and `api.php?mode=jobs_delta` render the same escaped cell HTML. The browser polls the delta endpoint while visible rows are waiting/running, updates only `td[data-refresh-cell]` content for rows already present in the table, and stops polling when no active visible jobs remain.

**Tech Stack:** PHP 8.1, existing 3WA SQL helpers (`selectSQL_SAFE`), jQuery, pytest static contract tests, `php -l`.

---

## File Structure

- Modify `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_php_page_assets.py`
  - Locks the no-full-reload requirement.
  - Requires `data-refresh-cell` hooks and AJAX refresh functions.
  - Ensures `location.replace` is no longer used for active job polling.

- Modify `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_php_api_assets.py`
  - Locks the new public `api.php?mode=jobs_delta` endpoint.
  - Requires the endpoint to use the same list query as `index.php`.
  - Requires `job_view.php` shared renderer and `gs_job_delta_payload()`.

- Create `/var/www/html/demo/php/map/3D/gaussian_splat/job_view.php`
  - Owns all front-page job-list presentation helpers that must be shared by the HTML page and JSON endpoint.
  - Produces escaped HTML snippets for `status`, `timing`, `frames`, and `actions` cells.
  - Produces failure-reason strings for the existing reason dialog.

- Modify `/var/www/html/demo/php/map/3D/gaussian_splat/index.php`
  - Includes `job_view.php`.
  - Uses renderer helpers for the initial table cells.
  - Adds `data-refresh-cell` attributes.
  - Replaces full-page active-job polling with `api.php?mode=jobs_delta` polling.

- Modify `/var/www/html/demo/php/map/3D/gaussian_splat/api.php`
  - Includes `job_view.php` for `jobs_delta`.
  - Returns cell HTML payload for the same latest 50 rows that the front page initially renders.

## Contract

The implementation must satisfy these user-visible requirements:

- While a job is waiting or running, the page must not call `location.replace`, `location.reload`, or assign `location.href` for routine progress updates.
- Polling must update only existing rows already rendered on the page. It must not prepend, remove, or reorder rows during a routine poll.
- Form contents, selected pasted/dragged file state, captcha text, modals, and scroll position must be left alone during polling.
- The table cells that may update are `status`, `timing`, `frames`, and `actions`.
- When a job finishes, the existing row should update from running to completed and show the `檢視` button if the splat file exists.
- When a job fails, the existing row should update to failed and show the `原因` button, and `openReasonDialog(id)` should display the latest short/full reason data.
- Upload success can still redirect to `index.php?highlight_job=...#job-...`; that is not routine active-job polling.

---

### Task 1: Write Static Tests For Inline Refresh

**Files:**
- Modify: `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_php_page_assets.py`
- Test: `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_php_page_assets.py`

- [ ] **Step 1: Replace the old full-page refresh assertions**

In `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_php_page_assets.py`, inside `test_index_page_has_upload_form_captcha_and_job_table()`, replace the existing active refresh assertions near the bottom:

```python
    assert "data-has-active-jobs" in text
    assert "setInterval(function() {" in text
    assert '!$("#uploadProgressDialog").is("[hidden]")' in text
    assert '!$("#jobReasonDialog").is("[hidden]")' in text
    assert 'if (!$("#uploadProgressDialog").is("[hidden]") || !$("#jobReasonDialog").is("[hidden]")) {\n      return;\n    }\n    location.replace' in text
    assert "location.replace" in text
```

with this stricter contract:

```python
    assert "data-has-active-jobs" in text
    assert 'data-refresh-cell="status"' in text
    assert 'data-refresh-cell="timing"' in text
    assert 'data-refresh-cell="frames"' in text
    assert 'data-refresh-cell="actions"' in text
    assert "function startActiveJobRefresh" in text
    assert "function refreshActiveJobs" in text
    assert "function updateJobRow" in text
    assert "function updateJobCell" in text
    assert "jobRefreshTimer" in text
    assert "jobRefreshInFlight" in text
    assert 'api.php?mode=jobs_delta' in text
    assert "$.getJSON(\"api.php?mode=jobs_delta\"" in text
    assert 'updateJobCell($row, "status", row.status_html)' in text
    assert 'updateJobCell($row, "timing", row.timing_html)' in text
    assert 'updateJobCell($row, "frames", row.frames_html)' in text
    assert 'updateJobCell($row, "actions", row.actions_html)' in text
    active_refresh_block = text[text.index("var jobRefreshTimer"):text.index("var initialUploadFormState")]
    assert "location.replace" not in active_refresh_block
    assert "location.reload" not in active_refresh_block
```

Keep the existing assertion:

```python
    assert 'location.href = "index.php?highlight_job="' in text
```

because upload success intentionally navigates to the newly queued job once.

- [ ] **Step 2: Run the page test and verify it fails**

Run:

```bash
cd /var/www/html/demo/php/map/3D/gaussian_splat
pytest -q tests/test_php_page_assets.py::test_index_page_has_upload_form_captcha_and_job_table
```

Expected: FAIL because `index.php` still contains `location.replace` inside `startActiveJobRefresh()` and does not contain `api.php?mode=jobs_delta`, `refreshActiveJobs`, or `data-refresh-cell` hooks.

- [ ] **Step 3: Add API endpoint contract assertions**

In `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_php_api_assets.py`, inside `test_api_log_transform_and_admin_actions()`, add these assertions after the existing `get_log` assertions and before `save_transform` assertions:

```python
    assert "case 'jobs_delta':" in text
    assert 'require_once __DIR__ . "/job_view.php";' in text
    assert "SELECT * FROM `gaussian_splat_jobs` WHERE `del`='0' ORDER BY `id` DESC LIMIT 50" in text
    assert "gs_job_delta_payload($rows)" in text
    assert "'has_active_jobs'=>$payload['has_active_jobs']" in text
    assert "'rows'=>$payload['rows']" in text
    assert "'failure_reasons'=>$payload['failure_reasons']" in text
```

- [ ] **Step 4: Run the API test and verify it fails**

Run:

```bash
cd /var/www/html/demo/php/map/3D/gaussian_splat
pytest -q tests/test_php_api_assets.py::test_api_log_transform_and_admin_actions
```

Expected: FAIL because `api.php` does not yet have `case 'jobs_delta':` or `gs_job_delta_payload($rows)`.

- [ ] **Step 5: Commit the red tests**

Run:

```bash
cd /var/www/html/demo/php/map/3D/gaussian_splat
git add tests/test_php_page_assets.py tests/test_php_api_assets.py
git commit -m "test(gaussian): require inline job progress refresh"
```

Expected: commit succeeds. If the worktree contains unrelated dirty files, commit only the two test files listed above.

---

### Task 2: Extract Shared Job Row Rendering

**Files:**
- Create: `/var/www/html/demo/php/map/3D/gaussian_splat/job_view.php`
- Modify: `/var/www/html/demo/php/map/3D/gaussian_splat/index.php`
- Test: `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_php_page_assets.py`

- [ ] **Step 1: Create `job_view.php`**

Create `/var/www/html/demo/php/map/3D/gaussian_splat/job_view.php` with this complete content:

```php
<?php
if(!defined('GS_DEFAULT_ESTIMATE_SECONDS')){
    define('GS_DEFAULT_ESTIMATE_SECONDS', 1800);
}

function gs_status_text($status){
    switch((string)$status){
        case '0': return '等待轉檔';
        case '1': return '轉檔中';
        case '2': return '已完成';
        case '3': return '失敗';
        case '4': return '已中止';
    }
    return '未知';
}

function gs_format_duration($seconds){
    if(!is_numeric($seconds)) return '尚未開始';
    $seconds = max(0, (int)round((float)$seconds));
    $hours = intdiv($seconds, 3600);
    $minutes = intdiv($seconds % 3600, 60);
    $remainSeconds = $seconds % 60;
    if($hours > 0) return "{$hours} 小時 {$minutes} 分";
    if($minutes > 0) return "{$minutes} 分 {$remainSeconds} 秒";
    return "{$remainSeconds} 秒";
}

function gs_elapsed_seconds($row){
    if(is_numeric($row['duration_seconds'] ?? null)){
        return (int)$row['duration_seconds'];
    }
    $start = $row['c_datetime'] ?? null;
    if(empty($start)) return null;
    $startTs = strtotime((string)$start);
    if($startTs === false) return null;
    $endTs = time();
    if(in_array((string)($row['status'] ?? ''), ['2','3','4'], true) && !empty($row['work_et_datetime'])){
        $endTs = strtotime((string)$row['work_et_datetime']);
    }
    if($endTs === false) return null;
    return max(0, $endTs - $startTs);
}

function gs_average_completed_duration($rows){
    $durations = [];
    foreach($rows as $row){
        if((string)($row['status'] ?? '') === '2' && is_numeric($row['duration_seconds'] ?? null) && (int)$row['duration_seconds'] > 0){
            $durations[] = (int)$row['duration_seconds'];
        }
    }
    if(!$durations) return GS_DEFAULT_ESTIMATE_SECONDS;
    return (int)round(array_sum($durations) / count($durations));
}

function gs_job_timing_summary($row, $estimateSeconds){
    $elapsed = gs_elapsed_seconds($row);
    $status = (string)($row['status'] ?? '');
    $stage = trim((string)($row['current_stage_label'] ?? ''));
    $summary = [];
    if($status === '2'){
        $summary[] = '總耗時 ' . gs_format_duration($elapsed);
    } else {
        $summary[] = '已花 ' . gs_format_duration($elapsed);
        $summary[] = '粗估總長 ' . gs_format_duration($estimateSeconds);
        if(in_array($status, ['0','1'], true) && is_numeric($elapsed)){
            $summary[] = '預估剩 ' . gs_format_duration(max(0, (int)$estimateSeconds - (int)$elapsed));
        }
    }
    if($stage !== '') $summary[] = '目前：' . $stage;
    return $summary;
}

function gs_short_failure_reason($reason){
    $reason = trim((string)$reason);
    if($reason === '') return '';

    if(strpos($reason, '影片太短') !== false){
        if(preg_match('/影片太短[^。]*。/u', $reason, $m)) return $m[0];
        return '影片太短。';
    }
    if(strpos($reason, 'candidate frame count is lower than 8') !== false || strpos($reason, 'selected frame count is lower than 8') !== false){
        return '可用影格不足，影片可能太短。';
    }
    if(strpos($reason, 'input file missing') !== false){
        return '找不到上傳影片。';
    }
    if(stripos($reason, 'failed') !== false || stripos($reason, 'error') !== false){
        return '轉檔失敗，請聯絡管理員查看詳細紀錄。';
    }

    $lines = preg_split('/\R/u', $reason);
    $shortReason = trim((string)($lines[0] ?? $reason));
    if(function_exists('mb_strlen') && mb_strlen($shortReason, 'UTF-8') > 80){
        return mb_substr($shortReason, 0, 80, 'UTF-8') . '...';
    }
    return strlen($shortReason) > 160 ? substr($shortReason, 0, 160) . '...' : $shortReason;
}

function gs_json_safe_text($value){
    $value = (string)$value;
    if($value === '') return '';
    if(function_exists('mb_convert_encoding')){
        return mb_convert_encoding($value, 'UTF-8', 'UTF-8');
    }
    return preg_replace('/[\x00-\x08\x0B\x0C\x0E-\x1F]/', '', $value);
}

function gs_upload_time_label($datetime){
    $datetime = trim((string)$datetime);
    if($datetime === '') return '未記錄';
    if(preg_match('/^0{4}-0{2}-0{2}/', $datetime)) return '未記錄';

    foreach(['Y-m-d H:i:s', 'Y-m-d H:i'] as $format){
        $dt = DateTime::createFromFormat('!' . $format, $datetime);
        $errors = DateTime::getLastErrors();
        $hasErrors = is_array($errors) && ((int)$errors['warning_count'] > 0 || (int)$errors['error_count'] > 0);
        if($dt instanceof DateTime && !$hasErrors && $dt->format($format) === $datetime){
            return $dt->format('Y-m-d H:i');
        }
    }
    return $datetime;
}

function gs_pipeline_stage_map(){
    static $stageMap = null;
    if($stageMap !== null) return $stageMap;

    $stageMap = [
        'worker_start' => ['percent'=>3, 'step'=>'啟動中', 'label'=>'啟動 worker'],
        'frame_select' => ['percent'=>12, 'step'=>'1 / 7', 'label'=>'挑選影格'],
        'legacy_extract' => ['percent'=>12, 'step'=>'1 / 7', 'label'=>'擷取影格'],
        'colmap' => ['percent'=>28, 'step'=>'2 / 7', 'label'=>'COLMAP 相機姿態估算'],
        'frame_colmap' => ['percent'=>38, 'step'=>'3 / 7', 'label'=>'標註影格品質'],
        'enhance' => ['percent'=>46, 'step'=>'選用前處理', 'label'=>'影格增強'],
        'prepare_training_images' => ['percent'=>52, 'step'=>'選用前處理', 'label'=>'準備訓練影像'],
        'train' => ['percent'=>76, 'step'=>'4 / 7', 'label'=>'Gaussian 訓練'],
        'export' => ['percent'=>90, 'step'=>'5 / 7', 'label'=>'匯出 Splat'],
        'cleanup' => ['percent'=>96, 'step'=>'6 / 7', 'label'=>'清理 Splat'],
        'finalize' => ['percent'=>99, 'step'=>'7 / 7', 'label'=>'產生 metadata / QA'],
    ];
    return $stageMap;
}

function gs_job_progress($row){
    $status = (string)($row['status'] ?? '');
    if($status === '2'){
        return ['percent'=>100, 'step'=>'完成', 'label'=>'完成', 'active'=>false];
    }
    if($status === '0'){
        return ['percent'=>0, 'step'=>'等待中', 'label'=>'等待轉檔', 'active'=>true];
    }
    if($status !== '1'){
        return ['percent'=>0, 'step'=>'已停止', 'label'=>gs_status_text($status), 'active'=>false];
    }

    $stageKey = trim((string)($row['current_stage'] ?? ''));
    $stageLabel = trim((string)($row['current_stage_label'] ?? ''));
    $stageMap = gs_pipeline_stage_map();
    if(isset($stageMap[$stageKey])){
        $progress = $stageMap[$stageKey];
        if($stageLabel !== '') $progress['label'] = $stageLabel;
        $progress['active'] = true;
        return $progress;
    }
    return ['percent'=>5, 'step'=>'處理中', 'label'=>$stageLabel !== '' ? $stageLabel : '轉檔中', 'active'=>true];
}

function gs_job_splat_path($row){
    $id = (int)($row['id'] ?? 0);
    $cleanSplat = "uploads/{$id}/exports/splat.clean.ply";
    $rawSplat = "uploads/{$id}/exports/splat.ply";
    return is_file(__DIR__ . "/{$cleanSplat}") ? $cleanSplat : $rawSplat;
}

function gs_job_has_splat($row, $splat){
    return (string)($row['status'] ?? '') === '2' && is_file(__DIR__ . "/{$splat}");
}

function gs_render_job_status_cell($row){
    $progress = gs_job_progress($row);
    ob_start();
    ?>
    <div class="gs-status-main"><?=htmlspecialchars(gs_status_text($row['status'] ?? ''), ENT_QUOTES);?></div>
    <?php if($progress['active']): ?>
      <div class="gs-muted"><?=htmlspecialchars((string)($progress['percent'] ?? 0), ENT_QUOTES);?>% · <?=htmlspecialchars((string)($progress['step'] ?? ''), ENT_QUOTES);?> · <?=htmlspecialchars((string)($progress['label'] ?? ''), ENT_QUOTES);?></div>
      <div class="gs-progress-mini"><span style="width:<?=min(100, max(0, (int)$progress['percent']));?>%;"></span></div>
    <?php else: ?>
      <div class="gs-muted"><?=htmlspecialchars((string)($progress['step'] ?? ''), ENT_QUOTES);?> · <?=htmlspecialchars((string)($progress['label'] ?? ''), ENT_QUOTES);?></div>
    <?php endif; ?>
    <?php
    return trim(ob_get_clean());
}

function gs_render_job_timing_cell($row, $estimateSeconds){
    $timingSummary = gs_job_timing_summary($row, $estimateSeconds);
    ob_start();
    foreach($timingSummary as $timingLine): ?>
      <div class="gs-muted"><?=htmlspecialchars($timingLine, ENT_QUOTES);?></div>
    <?php endforeach;
    return trim(ob_get_clean());
}

function gs_render_job_frame_cell($row){
    return htmlspecialchars((string)($row['frame_count'] ?? ''), ENT_QUOTES) . ' / ' . htmlspecialchars((string)($row['registered_frame_count'] ?? ''), ENT_QUOTES);
}

function gs_render_job_actions_cell($row, &$failureReasons){
    $id = (int)($row['id'] ?? 0);
    $splat = gs_job_splat_path($row);
    $hasSplat = gs_job_has_splat($row, $splat);
    $shortReason = gs_short_failure_reason($row['reason'] ?? '');
    $fullReason = trim((string)($row['reason'] ?? ''));
    if($fullReason !== ''){
        $failureReasons[(string)$id] = gs_json_safe_text($fullReason);
    }

    ob_start();
    $hasAction = false;
    if($hasSplat):
        $hasAction = true; ?>
        <button class="btn btn-xs btn-success" type="button" onclick="openSplatViewer('<?=htmlspecialchars($splat, ENT_QUOTES);?>')">檢視</button>
    <?php endif;
    if($shortReason !== ''):
        $hasAction = true; ?>
        <button class="btn btn-xs btn-default" type="button" onclick="openReasonDialog(<?=$id;?>)">原因</button>
    <?php endif;
    if(!$hasAction): ?>
        <span class="gs-muted">-</span>
    <?php endif;
    return trim(ob_get_clean());
}

function gs_has_active_jobs($rows){
    foreach($rows as $row){
        if(in_array((string)($row['status'] ?? ''), ['0','1'], true)){
            return true;
        }
    }
    return false;
}

function gs_job_delta_payload($rows){
    $estimateSeconds = gs_average_completed_duration($rows);
    $failureReasons = [];
    $payloadRows = [];

    foreach($rows as $row){
        $id = (int)($row['id'] ?? 0);
        $rowFailureReasons = [];
        $actionsHtml = gs_render_job_actions_cell($row, $rowFailureReasons);
        foreach($rowFailureReasons as $reasonId => $reasonText){
            $failureReasons[$reasonId] = $reasonText;
        }

        $payloadRows[] = [
            'id' => $id,
            'status' => (string)($row['status'] ?? ''),
            'active' => in_array((string)($row['status'] ?? ''), ['0','1'], true),
            'status_html' => gs_render_job_status_cell($row),
            'timing_html' => gs_render_job_timing_cell($row, $estimateSeconds),
            'frames_html' => gs_render_job_frame_cell($row),
            'actions_html' => $actionsHtml,
            'failure_reason' => $failureReasons[(string)$id] ?? '',
        ];
    }

    return [
        'has_active_jobs' => gs_has_active_jobs($rows),
        'rows' => $payloadRows,
        'failure_reasons' => $failureReasons,
    ];
}
```

- [ ] **Step 2: Include the helper in `index.php` and remove duplicate functions**

In `/var/www/html/demo/php/map/3D/gaussian_splat/index.php`, directly after:

```php
  require "../../../../../inc/config.php";
  $include_mode = "easymap7115";
  $rows = selectSQL_SAFE("SELECT * FROM `gaussian_splat_jobs` WHERE `del`='0' ORDER BY `id` DESC LIMIT 50", []);
```

add:

```php
  require_once __DIR__ . "/job_view.php";
```

Then remove the local definitions of these functions and constant from `index.php` because `job_view.php` now owns them:

```php
function gs_status_text($status)
define('GS_DEFAULT_ESTIMATE_SECONDS', 1800)
function gs_format_duration($seconds)
function gs_elapsed_seconds($row)
function gs_average_completed_duration($rows)
function gs_job_timing_summary($row, $estimateSeconds)
function gs_short_failure_reason($reason)
function gs_json_safe_text($value)
function gs_upload_time_label($datetime)
function gs_pipeline_stage_map()
function gs_job_progress($row)
```

Keep this page-level context setup in `index.php` after the removed helper block:

```php
  $estimateSeconds = gs_average_completed_duration($rows);
  $hasActiveJobs = gs_has_active_jobs($rows);
  $failureReasons = [];
```

- [ ] **Step 3: Run syntax and page tests**

Run:

```bash
cd /var/www/html/demo/php/map/3D/gaussian_splat
php -l job_view.php
php -l index.php
pytest -q tests/test_php_page_assets.py::test_index_page_has_upload_form_captcha_and_job_table
```

Expected: PHP lint passes. The page test still fails because `data-refresh-cell` and AJAX polling are not implemented yet.

- [ ] **Step 4: Commit the shared helper extraction**

Run:

```bash
cd /var/www/html/demo/php/map/3D/gaussian_splat
git add job_view.php index.php
git commit -m "refactor(gaussian): share job row presentation helpers"
```

Expected: commit succeeds. If unrelated files are dirty, commit only `job_view.php` and `index.php`.

---

### Task 3: Render Initial Table Cells Through Shared Helpers

**Files:**
- Modify: `/var/www/html/demo/php/map/3D/gaussian_splat/index.php`
- Test: `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_php_page_assets.py`

- [ ] **Step 1: Replace per-row PHP variables**

In the `foreach($rows as $r)` block in `index.php`, replace:

```php
          $cleanSplat = "uploads/{$id}/exports/splat.clean.ply";
          $rawSplat = "uploads/{$id}/exports/splat.ply";
          $splat = is_file(__DIR__ . "/{$cleanSplat}") ? $cleanSplat : $rawSplat;
          $isReady = (string)$r['status'] === '2';
          $hasSplat = $isReady && is_file(__DIR__ . "/{$splat}");
          $timingSummary = gs_job_timing_summary($r, $estimateSeconds);
          $shortReason = gs_short_failure_reason($r['reason'] ?? '');
          $fullReason = trim((string)($r['reason'] ?? ''));
          if($fullReason !== '') $failureReasons[(string)$id] = gs_json_safe_text($fullReason);
          $progress = gs_job_progress($r);
```

with:

```php
          $rowFailureReasons = [];
          $statusHtml = gs_render_job_status_cell($r);
          $timingHtml = gs_render_job_timing_cell($r, $estimateSeconds);
          $framesHtml = gs_render_job_frame_cell($r);
          $actionsHtml = gs_render_job_actions_cell($r, $rowFailureReasons);
          foreach($rowFailureReasons as $reasonId => $reasonText){
              $failureReasons[$reasonId] = $reasonText;
          }
```

- [ ] **Step 2: Add refresh hooks to table cells**

In the same row template, replace the status, timing, frames, and actions cells with this markup:

```php
          <td class="gs-status-cell" data-refresh-cell="status"><?=$statusHtml;?></td>
          <td data-refresh-cell="timing"><?=$timingHtml;?></td>
          <td class="gs-frame-cell" data-refresh-cell="frames"><?=$framesHtml;?></td>
          <td class="gs-actions-cell" data-refresh-cell="actions"><?=$actionsHtml;?></td>
```

The full row body should still start with:

```php
        <tr id="job-<?=$id;?>" data-job-id="<?=$id;?>">
          <td><?=$id;?></td>
          <td>
            <?=htmlspecialchars($r['title'] ?: $r['orin_filename'], ENT_QUOTES);?>
            <div class="gs-muted"><?=htmlspecialchars($r['orin_filename'] ?? '', ENT_QUOTES);?></div>
          </td>
          <td class="gs-upload-time"><?=htmlspecialchars(gs_upload_time_label($r['c_datetime'] ?? ''), ENT_QUOTES);?></td>
```

- [ ] **Step 3: Run syntax and focused page test**

Run:

```bash
cd /var/www/html/demo/php/map/3D/gaussian_splat
php -l index.php
pytest -q tests/test_php_page_assets.py::test_index_page_has_upload_form_captcha_and_job_table
```

Expected: PHP lint passes. The page test still fails only on AJAX polling assertions such as `refreshActiveJobs`, `api.php?mode=jobs_delta`, and `location.replace`.

- [ ] **Step 4: Commit initial table rendering hooks**

Run:

```bash
cd /var/www/html/demo/php/map/3D/gaussian_splat
git add index.php
git commit -m "refactor(gaussian): mark job table cells for inline refresh"
```

Expected: commit succeeds. If unrelated files are dirty, commit only `index.php`.

---

### Task 4: Add `jobs_delta` API Endpoint

**Files:**
- Modify: `/var/www/html/demo/php/map/3D/gaussian_splat/api.php`
- Test: `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_php_api_assets.py`

- [ ] **Step 1: Add the endpoint before `save_transform`**

In `/var/www/html/demo/php/map/3D/gaussian_splat/api.php`, insert this switch case after the existing `case 'get_log':` block and before `case 'save_transform':`

```php
      case 'jobs_delta':
          require_once __DIR__ . "/job_view.php";
          $rows = selectSQL_SAFE("SELECT * FROM `gaussian_splat_jobs` WHERE `del`='0' ORDER BY `id` DESC LIMIT 50", []);
          $payload = gs_job_delta_payload($rows);
          gs_json([
              'status'=>'OK',
              'has_active_jobs'=>$payload['has_active_jobs'],
              'rows'=>$payload['rows'],
              'failure_reasons'=>$payload['failure_reasons'],
          ]);
```

This endpoint is public because `index.php` already publicly renders the same latest 50 job list. It must not expose `process_log`; detailed logs remain behind admin/detail flows.

- [ ] **Step 2: Run syntax and API test**

Run:

```bash
cd /var/www/html/demo/php/map/3D/gaussian_splat
php -l api.php
pytest -q tests/test_php_api_assets.py::test_api_log_transform_and_admin_actions
```

Expected: PHP lint passes. The API test passes because `case 'jobs_delta':`, `require_once __DIR__ . "/job_view.php";`, the exact latest-50 query, and the payload keys are present.

- [ ] **Step 3: Smoke test endpoint manually**

Run:

```bash
cd /var/www/html/demo/php/map/3D/gaussian_splat
php -r '$_GET["mode"]="jobs_delta"; include "api.php";' | head -c 600
```

Expected: output starts with JSON like:

```json
{"status":"OK","has_active_jobs":
```

If the local CLI include cannot connect to the application DB because the shared config expects web server globals, use:

```bash
curl -sS "https://3wa.tw/demo/php/map/3D/gaussian_splat/api.php?mode=jobs_delta" | head -c 600
```

Expected: output starts with the same JSON prefix and does not include `process_log`.

- [ ] **Step 4: Commit API endpoint**

Run:

```bash
cd /var/www/html/demo/php/map/3D/gaussian_splat
git add api.php
git commit -m "feat(gaussian): expose job row delta endpoint"
```

Expected: commit succeeds. If unrelated files are dirty, commit only `api.php`.

---

### Task 5: Replace Full-Page Refresh With Cell Updates

**Files:**
- Modify: `/var/www/html/demo/php/map/3D/gaussian_splat/index.php`
- Test: `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_php_page_assets.py`

- [ ] **Step 1: Replace `startActiveJobRefresh()` and add update helpers**

In `/var/www/html/demo/php/map/3D/gaussian_splat/index.php`, replace the current `startActiveJobRefresh()` function:

```javascript
function startActiveJobRefresh() {
  if ($(".gs-wrap").attr("data-has-active-jobs") !== "1") {
    return;
  }
  setInterval(function() {
    if (isUploadFormDirty()) {
      return;
    }
    if (!$("#uploadProgressDialog").is("[hidden]") || !$("#jobReasonDialog").is("[hidden]")) {
      return;
    }
    location.replace(location.pathname + location.search + location.hash);
  }, 20000);
}
```

with this complete block:

```javascript
var jobRefreshTimer = null;
var jobRefreshInFlight = false;

function updateJobCell($row, cellName, html) {
  $row.find('[data-refresh-cell="' + cellName + '"]').html(html || "");
}

function updateJobRow(row) {
  if (!row || typeof row.id === "undefined") {
    return;
  }
  var $row = $("#job-" + row.id);
  if (!$row.length) {
    return;
  }

  updateJobCell($row, "status", row.status_html);
  updateJobCell($row, "timing", row.timing_html);
  updateJobCell($row, "frames", row.frames_html);
  updateJobCell($row, "actions", row.actions_html);

  if (row.failure_reason) {
    jobFailureReasons[String(row.id)] = row.failure_reason;
  } else {
    delete jobFailureReasons[String(row.id)];
  }
}

function refreshActiveJobs() {
  if (jobRefreshInFlight) {
    return;
  }
  jobRefreshInFlight = true;
  $.getJSON("api.php?mode=jobs_delta", function(jd) {
    if (!jd || jd.status !== "OK") {
      return;
    }

    (jd.rows || []).forEach(updateJobRow);
    $(".gs-wrap").attr("data-has-active-jobs", jd.has_active_jobs ? "1" : "0");

    if (!jd.has_active_jobs && jobRefreshTimer !== null) {
      clearInterval(jobRefreshTimer);
      jobRefreshTimer = null;
    }
  }).always(function() {
    jobRefreshInFlight = false;
  });
}

function startActiveJobRefresh() {
  if ($(".gs-wrap").attr("data-has-active-jobs") !== "1") {
    return;
  }
  refreshActiveJobs();
  jobRefreshTimer = setInterval(refreshActiveJobs, 5000);
}
```

Important behavior:

- No `location.replace`.
- No `isUploadFormDirty()` check is needed because the poll does not reload or touch the form.
- New jobs from other users are ignored until manual reload because `updateJobRow()` only updates rows already present in the DOM.
- The interval is `5000` ms so the running progress feels alive without hammering the server.

- [ ] **Step 2: Run focused page test**

Run:

```bash
cd /var/www/html/demo/php/map/3D/gaussian_splat
php -l index.php
pytest -q tests/test_php_page_assets.py::test_index_page_has_upload_form_captcha_and_job_table
```

Expected: PHP lint passes and the page test passes.

- [ ] **Step 3: Commit inline refresh implementation**

Run:

```bash
cd /var/www/html/demo/php/map/3D/gaussian_splat
git add index.php
git commit -m "feat(gaussian): refresh active job rows inline"
```

Expected: commit succeeds. If unrelated files are dirty, commit only `index.php`.

---

### Task 6: End-To-End Verification

**Files:**
- Verify: `/var/www/html/demo/php/map/3D/gaussian_splat/index.php`
- Verify: `/var/www/html/demo/php/map/3D/gaussian_splat/api.php`
- Verify: `/var/www/html/demo/php/map/3D/gaussian_splat/job_view.php`
- Verify: `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_php_page_assets.py`
- Verify: `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_php_api_assets.py`

- [ ] **Step 1: Run PHP lint**

Run:

```bash
cd /var/www/html/demo/php/map/3D/gaussian_splat
php -l index.php
php -l api.php
php -l job_view.php
```

Expected:

```text
No syntax errors detected in index.php
No syntax errors detected in api.php
No syntax errors detected in job_view.php
```

- [ ] **Step 2: Run related static tests**

Run:

```bash
cd /var/www/html/demo/php/map/3D/gaussian_splat
pytest -q tests/test_php_page_assets.py tests/test_php_api_assets.py tests/test_map_page_assets.py
```

Expected: all selected tests pass with exit code `0`.

- [ ] **Step 3: Confirm the active refresh code has no reload path**

Run:

```bash
cd /var/www/html/demo/php/map/3D/gaussian_splat
python3 - <<'PY'
from pathlib import Path
text = Path("index.php").read_text()
active_block = text[text.index("function startActiveJobRefresh"):text.index("var initialUploadFormState")]
for bad in ["location.replace", "location.reload"]:
    assert bad not in active_block, bad
assert '$.getJSON("api.php?mode=jobs_delta"' in active_block
assert "updateJobCell($row, \"status\", row.status_html)" in active_block
print("active refresh updates cells without full-page reload")
PY
```

Expected:

```text
active refresh updates cells without full-page reload
```

- [ ] **Step 4: Browser smoke test with the live page**

Open:

```text
https://3wa.tw/demo/php/map/3D/gaussian_splat/index.php
```

Manual verification:

1. Start typing in `標題`, `電子信箱`, `經度`, `緯度`, `高度`, and `驗證碼`.
2. Scroll the table so a running job is visible.
3. Wait at least 10 seconds.
4. Confirm DevTools Network shows `api.php?mode=jobs_delta` requests.
5. Confirm only the running row cells change.
6. Confirm the typed form values remain unchanged.
7. Confirm the scroll position does not jump.
8. Confirm no document navigation occurs during the poll.

- [ ] **Step 5: Commit verification note if desired by project practice**

If the team records handoff notes in `history.md`, add one short line:

```markdown
- 2026-06-06: Front page active job refresh now polls `api.php?mode=jobs_delta` and updates existing row cells without full-page reload.
```

Then run:

```bash
cd /var/www/html/demo/php/map/3D/gaussian_splat
git add history.md
git commit -m "docs(gaussian): note inline job refresh behavior"
```

Expected: commit succeeds only if `history.md` was changed. If no docs note is needed, skip this step and leave `history.md` untouched.

---

## Self-Review

**Spec coverage:**

- User requirement: "轉檔中的更新不能 reload 整個畫面" is covered by Task 1 test assertions and Task 5 replacing `location.replace`.
- User requirement: "只能更新該 tr 甚至 td 裡的內容" is covered by Task 3 `data-refresh-cell` hooks and Task 5 `updateJobCell()`.
- User requirement: "表單填到一半不能跑掉" is covered by Task 5 not touching form state and Task 6 manual browser smoke test.
- User requirement: "捲軸不能跑掉" is covered by Task 5 updating existing rows only and Task 6 manual browser smoke test.

**Placeholder scan:**

- The plan contains exact files, snippets, commands, and expected outcomes for every task.
- Optional docs history is explicitly bounded and can be skipped without affecting the feature.

**Type and name consistency:**

- PHP endpoint name is consistently `jobs_delta`.
- Shared PHP renderer name is consistently `job_view.php`.
- Payload keys are consistently `status_html`, `timing_html`, `frames_html`, `actions_html`, and `failure_reason`.
- DOM hooks are consistently `data-refresh-cell="status|timing|frames|actions"`.
