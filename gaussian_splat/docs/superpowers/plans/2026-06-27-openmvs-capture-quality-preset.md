# OpenMVS Capture Quality Preset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add OpenMVS-first `capture_*` summary fields and engine-agnostic diagnostic aliases for capture quality analytics.

**Architecture:** Keep the change inside `/var/www/html/demo/php/map/3D/openmvs`. Add nullable DB columns, fill them from existing upload metadata and `qa_report.json`, then show a small Chinese summary in the existing quality cell. Do not touch Gaussian Splat runtime code.

**Tech Stack:** PHP, MySQL migration text, existing OpenMVS cron worker, existing asset-style Python/PHP tests.

---

## Repository Note

`/var/www/html/demo/php/map/3D/openmvs` is outside the `gaussian_splat` git repository. Implement OpenMVS file edits directly and report changed paths. Do not commit OpenMVS changes from this task.

## Task 1: OpenMVS Capture Quality Summary

**Files:**
- Modify: `/var/www/html/demo/php/map/3D/openmvs/migrate.php`
- Modify: `/var/www/html/demo/php/map/3D/openmvs/api.php`
- Modify: `/var/www/html/demo/php/map/3D/openmvs/crontab/inc/function.php`
- Modify: `/var/www/html/demo/php/map/3D/openmvs/crontab/1_run.php`
- Modify: `/var/www/html/demo/php/map/3D/openmvs/job_view.php`
- Modify: `/var/www/html/demo/php/map/3D/openmvs/tests/test_openmvs_php_assets.py`
- Modify: `/var/www/html/demo/php/map/3D/openmvs/tests/openmvs_diagnostics_parser_test.php`

- [ ] **Step 1: Add failing schema and worker asset assertions**

In `/var/www/html/demo/php/map/3D/openmvs/tests/test_openmvs_php_assets.py`, extend existing tests instead of creating a new test file.

Add these expected job columns to `test_migration_defines_openmvs_job_schema`:

```python
        "capture_source_type",
        "capture_preset",
        "capture_quality_score",
        "capture_quality_grade",
        "capture_quality_decision",
        "capture_mask_status",
        "capture_frame_count",
        "capture_selected_frame_count",
        "capture_aligned_camera_count",
        "capture_registered_ratio",
        "capture_warning_count",
        "capture_updated_at",
```

Add these expected diagnostic columns to `test_openmvs_diagnostics_summary_surface`:

```python
        "diagnostic_category",
        "diagnostic_code",
        "diagnostic_severity",
        "diagnostic_count",
        "diagnostic_value",
        "diagnostic_message",
        "diagnostic_source",
```

Add assertions in `test_cron_worker_runs_pipeline_and_updates_metrics`:

```python
    assert "ovm_capture_source_type" in helper
    assert "ovm_capture_summary_fields" in helper
    assert "capture_registered_ratio" in runner
    assert "capture_quality_decision" in runner
```

Add assertions in `test_index_job_view_and_js_wire_glb_viewer_actions`:

```python
    assert "拍攝模式" in job_view
    assert "註冊比例" in job_view
    assert "capture_quality_decision" in job_view
```

- [ ] **Step 2: Run focused tests and verify they fail**

```bash
cd /var/www/html/demo/php/map/3D/openmvs
pytest -q tests/test_openmvs_php_assets.py
```

Expected: FAIL because new fields/helpers are not implemented yet.

- [ ] **Step 3: Add nullable `capture_*` columns in migration**

In `/var/www/html/demo/php/map/3D/openmvs/migrate.php`, add the `capture_*` fields to both `CREATE TABLE IF NOT EXISTS openmvs_jobs` and the `$columns` migration list after `mask_mode` or near existing quality metrics.

Use these definitions:

```php
`capture_source_type` varchar(30) DEFAULT NULL COMMENT 'capture source type images video 360_video',
`capture_preset` varchar(40) DEFAULT 'normal_orbit' COMMENT 'capture preset',
`capture_quality_score` decimal(5,2) DEFAULT NULL COMMENT 'capture quality score 0-100',
`capture_quality_grade` varchar(8) DEFAULT NULL COMMENT 'capture quality grade',
`capture_quality_decision` varchar(32) DEFAULT NULL COMMENT 'run warn hold reject',
`capture_mask_status` varchar(32) DEFAULT NULL COMMENT 'capture mask status',
`capture_frame_count` int(11) DEFAULT NULL COMMENT 'capture frame count',
`capture_selected_frame_count` int(11) DEFAULT NULL COMMENT 'selected frame count',
`capture_aligned_camera_count` int(11) DEFAULT NULL COMMENT 'aligned camera count',
`capture_registered_ratio` decimal(6,4) DEFAULT NULL COMMENT 'aligned camera ratio',
`capture_warning_count` int(11) NOT NULL DEFAULT 0 COMMENT 'capture warning count',
`capture_updated_at` datetime DEFAULT NULL COMMENT 'capture summary updated time',
```

Add diagnostic alias columns to `openmvs_job_diagnostics`:

```php
`diagnostic_category` varchar(64) DEFAULT NULL,
`diagnostic_code` varchar(128) DEFAULT NULL,
`diagnostic_severity` varchar(16) DEFAULT NULL,
`diagnostic_count` int(11) NOT NULL DEFAULT 0,
`diagnostic_value` varchar(128) DEFAULT NULL,
`diagnostic_message` text DEFAULT NULL,
`diagnostic_source` varchar(512) DEFAULT NULL,
```

Keep existing diagnostic columns for compatibility.

- [ ] **Step 4: Add capture summary helpers**

In `/var/www/html/demo/php/map/3D/openmvs/crontab/inc/function.php`, add small helpers near existing diagnostics helpers:

```php
function ovm_capture_source_type($kind){
    $kind = strtolower(trim((string)$kind));
    if($kind === 'zip') return 'images';
    if($kind === 'mp4') return 'video';
    return null;
}

function ovm_capture_quality_from_ratio($ratio, $warningCount){
    if(!is_numeric($ratio)) return [null, null, null];
    $score = max(0, min(100, (float)$ratio * 100 - ((int)$warningCount * 5)));
    if($score >= 90) return [$score, 'A', 'run'];
    if($score >= 75) return [$score, 'B', 'run'];
    if($score >= 60) return [$score, 'C', 'warn'];
    if($score >= 40) return [$score, 'D', 'hold'];
    return [$score, 'F', 'reject'];
}

function ovm_capture_summary_fields($row, $qa, $diagnostics){
    $frameCount = is_array($qa) ? ($qa['input_frame_count'] ?? null) : null;
    $alignedCount = is_array($qa) ? ($qa['registered_frame_count'] ?? null) : null;
    $ratio = (is_numeric($frameCount) && (int)$frameCount > 0 && is_numeric($alignedCount))
        ? ((float)$alignedCount / (float)$frameCount)
        : null;
    $warningCount = 0;
    foreach($diagnostics as $diag){
        if(($diag['severity'] ?? '') === 'warning') $warningCount += (int)($diag['pattern_count'] ?? 0);
    }
    [$score, $grade, $decision] = ovm_capture_quality_from_ratio($ratio, $warningCount);
    return [
        'capture_source_type' => ovm_capture_source_type($row['kind'] ?? ''),
        'capture_preset' => trim((string)($row['capture_preset'] ?? '')) !== '' ? $row['capture_preset'] : 'normal_orbit',
        'capture_quality_score' => is_numeric($score) ? number_format((float)$score, 2, '.', '') : null,
        'capture_quality_grade' => $grade,
        'capture_quality_decision' => $decision,
        'capture_mask_status' => trim((string)($row['mask_mode'] ?? 'none')) ?: 'none',
        'capture_frame_count' => $frameCount,
        'capture_selected_frame_count' => $frameCount,
        'capture_aligned_camera_count' => $alignedCount,
        'capture_registered_ratio' => is_numeric($ratio) ? number_format((float)$ratio, 4, '.', '') : null,
        'capture_warning_count' => $warningCount,
        'capture_updated_at' => date('Y-m-d H:i:s'),
    ];
}
```

Keep this heuristic intentionally simple. It is a summary, not a new analyzer.

- [ ] **Step 5: Fill diagnostic aliases during upsert**

In `ovm_upsert_job_diagnostics`, include the new diagnostic alias fields in the INSERT and execute values:

```php
$category = explode('.', (string)$row['pattern_id'], 2)[0] ?: 'openmvs';
$code = $row['pattern_id'];
$severity = $row['severity'];
$count = (int)$row['pattern_count'];
$message = $row['message_summary'];
$source = $row['raw_log_path'];
```

Set aliases to the same normalized values:

```text
diagnostic_category = category
diagnostic_code = pattern_id
diagnostic_severity = severity
diagnostic_count = pattern_count
diagnostic_value = null
diagnostic_message = message_summary
diagnostic_source = raw_log_path
```

- [ ] **Step 6: Make finalize return diagnostics for capture summary**

Change `ovm_finalize_job_diagnostics` to optionally expose parsed diagnostics without a second log parse:

```php
function ovm_finalize_job_diagnostics($id, $logPath, $qa=[], $extraLine='', &$diagnosticsOut=null){
    ...
    $diagnostics = ovm_parse_log_diagnostics($text, $relativeLogPath);
    if($diagnosticsOut !== null) $diagnosticsOut = $diagnostics;
    ...
}
```

Update existing callers without behavior change.

- [ ] **Step 7: Persist capture summary in worker**

In `/var/www/html/demo/php/map/3D/openmvs/crontab/1_run.php`, initialize capture fields when a job starts:

```php
'capture_source_type'=>ovm_capture_source_type($kind),
'capture_mask_status'=>$maskMode,
'capture_updated_at'=>$workStart,
```

On success, after reading `qa_report.json`, collect diagnostics and merge capture fields:

```php
$diagnostics = [];
$diagFields = ovm_finalize_job_diagnostics($id, $logPath, $qa, '', $diagnostics);
$upd = array_merge($upd, $diagFields, ovm_capture_summary_fields($row, $qa, $diagnostics));
```

On nonzero failure, keep diagnostics behavior and add capture fields with empty QA:

```php
$diagnostics = [];
$diagFields = ovm_finalize_job_diagnostics($id, $logPath, [], "openmvs.nonzero_exit failed", $diagnostics);
$captureFields = ovm_capture_summary_fields($row, [], $diagnostics);
updateSQL_SAFE('openmvs_jobs', array_merge($diagFields, $captureFields), "`id`=?", [$id]);
```

- [ ] **Step 8: Show small Chinese capture summary**

In `/var/www/html/demo/php/map/3D/openmvs/job_view.php`, add helper labels:

```php
function ovm_capture_decision_label($decision){
    switch((string)$decision){
        case 'run': return '建議執行';
        case 'warn': return '可執行但有風險';
        case 'hold': return '等待覆核';
        case 'reject': return '不建議重建';
    }
    return '';
}
```

In `ovm_job_quality_cell_html`, keep the existing Q badge and append compact lines only when fields exist:

```php
$decision = ovm_capture_decision_label($row['capture_quality_decision'] ?? '');
$ratio = ovm_percent_label($row['capture_registered_ratio'] ?? null);
```

Render lines:

```text
拍攝模式 normal_orbit
註冊比例 91.7%
品質決策 建議執行
```

Use `htmlspecialchars`.

- [ ] **Step 9: Run verification**

```bash
cd /var/www/html/demo/php/map/3D/openmvs
pytest -q tests/test_openmvs_php_assets.py
php tests/openmvs_diagnostics_parser_test.php
php -l migrate.php
php -l crontab/1_run.php
php -l crontab/inc/function.php
php -l job_view.php
```

Expected: all pass / no syntax errors.

- [ ] **Step 10: Report changed paths**

Because OpenMVS is not in the current git repo, do not commit these file edits. Report changed files and test results to the controller.
