# OpenMVS Diagnostic Summary Table Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one OpenMVS-only diagnostic summary table that counts repeated warnings/errors, keeps raw logs on disk, and shows a five-level quality light in the job list.

**Architecture:** Keep the existing `openmvs_jobs` row as the job summary and add exactly one child table, `openmvs_job_diagnostics`, with one row per `job_id` / `stage` / `pattern_id`. The cron worker writes full process output to `uploads/{id}/logs/openmvs_pipeline.log`, parses that file at the end, upserts compact counts, and never streams full stdout/stderr into MySQL.

**Tech Stack:** PHP, MySQL/MariaDB through the existing `selectSQL_SAFE` / `updateSQL_SAFE` helpers and `$pdo`, bash pipeline logs, pytest asset checks, one tiny PHP parser self-check.

---

## File Structure

- `migrate.php`: create `openmvs_job_diagnostics`; add four diagnostic summary columns to `openmvs_jobs`.
- `crontab/inc/function.php`: stop DB writes for full process output; add filesystem log helpers, OpenMVS diagnostic parser, diagnostic upsert, and job summary scoring.
- `crontab/1_run.php`: write raw output to `uploads/{id}/logs/openmvs_pipeline.log`; call diagnostic finalization on success and failure.
- `api.php`: clear diagnostics on retry/start; add `get_diagnostics` JSON endpoint for the detail modal.
- `job_view.php`: render the five-level quality light and a diagnostics action button; include the new HTML in `jobs_delta`.
- `index.php`: add the quality column and diagnostics modal.
- `js/function.js`: add `openDiagnosticsDialog()` and close helpers.
- `tests/test_openmvs_php_assets.py`: add asset checks and invoke the PHP parser self-check.
- `tests/openmvs_diagnostics_parser_test.php`: assert repeated pattern counts, stages, first/last line, and sample text.

No commit steps: this workspace is not currently a git repository.

## Tasks

### Task 1: Add Failing Tests For The Required Surface

**Files:**
- Modify: `tests/test_openmvs_php_assets.py`
- Create: `tests/openmvs_diagnostics_parser_test.php`

- [ ] **Step 1: Add migration/UI/runner asset assertions**

Append focused assertions to `tests/test_openmvs_php_assets.py`:

```python
def test_openmvs_diagnostics_summary_surface():
    migrate = read("migrate.php")
    helper = read("crontab/inc/function.php")
    runner = read("crontab/1_run.php")
    api = read("api.php")
    index = read("index.php")
    job_view = read("job_view.php")
    js = read("js/function.js")

    assert "CREATE TABLE IF NOT EXISTS `openmvs_job_diagnostics`" in migrate
    assert "UNIQUE KEY `uq_job_stage_pattern`" in migrate
    for column in [
        "diagnostic_status",
        "diagnostic_score",
        "diagnostic_summary",
        "diagnostic_log_path",
    ]:
        assert f"`{column}`" in migrate

    assert "function ovm_parse_log_diagnostics" in helper
    assert "function ovm_upsert_job_diagnostics" in helper
    assert "function ovm_finalize_job_diagnostics" in helper
    assert "openmvs.linear_solver_failure" in helper
    assert "openmvs.texture_patch_rejected" in helper
    assert "openmvs.cpu_fallback" in helper
    assert "openmvs.out_of_memory" in helper
    assert "openmvs.missing_scene" in helper
    assert "openmvs.process_timeout" in helper
    assert "openmvs.nonzero_exit" in helper

    assert 'uploads/{$id}/logs/openmvs_pipeline.log' in runner
    assert "ovm_append_log_block($id, $line)" not in runner
    assert "ovm_finalize_job_diagnostics" in runner

    assert "case 'get_diagnostics':" in api
    assert "DELETE FROM `openmvs_job_diagnostics` WHERE `job_id`=?" in api
    assert "<th>品質</th>" in index
    assert 'data-refresh-cell="quality"' in index
    assert "openDiagnosticsDialog" in index
    assert "ovm_job_quality_cell_html" in job_view
    assert "quality_html" in job_view
    assert "function openDiagnosticsDialog" in js
```

- [ ] **Step 2: Add the PHP parser self-check**

Create `tests/openmvs_diagnostics_parser_test.php`:

```php
<?php
require __DIR__ . '/../crontab/inc/function.php';

function assert_true($condition, $message){
    if(!$condition){
        fwrite(STDERR, $message . PHP_EOL);
        exit(1);
    }
}

$log = implode("\n", [
    "[timing] START openmvs_refine OpenMVS mesh refinement",
    "RefineMesh: linear solver failed to converge",
    "RefineMesh: linear solver failed to converge",
    "[env-check] RefineMesh GPU stage failed; retrying with CPU",
    "[timing] START openmvs_texture OpenMVS mesh texturing",
    "TextureMesh: rejected texture patch because no valid view",
    "TextureMesh: rejected texture patch because no valid view",
    "TextureMesh: rejected texture patch because no valid view",
    "missing scene_dense.mvs",
]) . "\n";

$diagnostics = ovm_parse_log_diagnostics($log, 'uploads/42/logs/openmvs_pipeline.log');
$byKey = [];
foreach($diagnostics as $row){
    $byKey[$row['stage'] . '|' . $row['pattern_id']] = $row;
}

assert_true($byKey['openmvs_refine|openmvs.linear_solver_failure']['pattern_count'] === 2, 'linear solver count');
assert_true($byKey['openmvs_refine|openmvs.cpu_fallback']['pattern_count'] === 1, 'cpu fallback count');
assert_true($byKey['openmvs_texture|openmvs.texture_patch_rejected']['pattern_count'] === 3, 'texture patch count');
assert_true($byKey['openmvs_texture|openmvs.missing_scene']['severity'] === 'error', 'missing scene severity');
assert_true($byKey['openmvs_texture|openmvs.missing_scene']['first_seen_line'] === 9, 'line number');
assert_true(strpos($byKey['openmvs_refine|openmvs.linear_solver_failure']['message_sample'], 'linear solver') !== false, 'sample');

echo "ok\n";
```

- [ ] **Step 3: Run tests and verify they fail**

Run:

```bash
pytest tests/test_openmvs_php_assets.py -q
php tests/openmvs_diagnostics_parser_test.php
```

Expected now: pytest fails on missing strings and PHP fails because `ovm_parse_log_diagnostics()` does not exist.

### Task 2: Add The Database Shape

**Files:**
- Modify: `migrate.php`

- [ ] **Step 1: Add the summary columns to the create-table SQL**

In `CREATE TABLE IF NOT EXISTS openmvs_jobs`, add after `texture_patch_count`:

```sql
  `diagnostic_status` varchar(16) DEFAULT NULL COMMENT 'ok warning error',
  `diagnostic_score` decimal(5,2) DEFAULT NULL COMMENT 'diagnostic quality score 0-100',
  `diagnostic_summary` text DEFAULT NULL COMMENT 'diagnostic short summary',
  `diagnostic_log_path` varchar(512) DEFAULT NULL COMMENT 'raw diagnostic log path',
```

- [ ] **Step 2: Add the same columns to `$columns`**

Add:

```php
['diagnostic_status', "varchar(16) DEFAULT NULL COMMENT 'ok warning error'", 'texture_patch_count'],
['diagnostic_score', "decimal(5,2) DEFAULT NULL COMMENT 'diagnostic quality score 0-100'", 'diagnostic_status'],
['diagnostic_summary', "text DEFAULT NULL COMMENT 'diagnostic short summary'", 'diagnostic_score'],
['diagnostic_log_path', "varchar(512) DEFAULT NULL COMMENT 'raw diagnostic log path'", 'diagnostic_summary'],
```

- [ ] **Step 3: Create the one diagnostics table**

After `openmvs_jobs` is created, execute:

```php
$diagnosticsSQL = "
CREATE TABLE IF NOT EXISTS `openmvs_job_diagnostics` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `job_id` BIGINT NOT NULL,
  `stage` VARCHAR(64) NOT NULL,
  `pattern_id` VARCHAR(128) NOT NULL,
  `severity` VARCHAR(16) NOT NULL DEFAULT 'info',
  `pattern_count` INT NOT NULL DEFAULT 0,
  `first_seen_line` INT NULL,
  `last_seen_line` INT NULL,
  `message_sample` TEXT NULL,
  `message_summary` TEXT NULL,
  `raw_log_path` VARCHAR(512) NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uq_job_stage_pattern` (`job_id`, `stage`, `pattern_id`),
  INDEX `idx_job_id` (`job_id`),
  INDEX `idx_stage` (`stage`),
  INDEX `idx_pattern_id` (`pattern_id`),
  INDEX `idx_severity` (`severity`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci";
```

Run `$pdo->exec($diagnosticsSQL);` and append `['ok', 'openmvs_job_diagnostics table ready']` or a `fail` log exactly like the existing table creation block.

- [ ] **Step 4: Run the migration syntax check**

Run:

```bash
php -l migrate.php
pytest tests/test_openmvs_php_assets.py::test_migration_defines_openmvs_job_schema -q
```

Expected: syntax OK; old migration test still passes.

### Task 3: Move Full Process Output To Filesystem Logs

**Files:**
- Modify: `crontab/inc/function.php`
- Modify: `crontab/1_run.php`
- Modify: `api.php`

- [ ] **Step 1: Add raw log path helpers**

In `crontab/inc/function.php`, after `ovm_run_cmd()`:

```php
function ovm_job_log_dir($id){
    $root = dirname(dirname(__DIR__));
    return "{$root}/uploads/" . (int)$id . "/logs";
}

function ovm_job_pipeline_log_path($id){
    return ovm_job_log_dir($id) . "/openmvs_pipeline.log";
}

function ovm_relative_openmvs_path($path){
    $root = dirname(dirname(__DIR__));
    $path = (string)$path;
    return strpos($path, $root . '/') === 0 ? substr($path, strlen($root) + 1) : $path;
}
```

- [ ] **Step 2: Make small DB log writes non-fatal**

Wrap the existing DB update inside `ovm_append_log()` with:

```php
try {
    $stmt = $pdo->prepare("UPDATE `openmvs_jobs` SET `process_log` = RIGHT(CONCAT(IFNULL(`process_log`,''), ?), 60000) WHERE `id`=?");
    $stmt->execute([$line, $id]);
} catch(Throwable $e){
    echo date('H:i:s') . " DB log skipped: " . $e->getMessage() . "\n";
}
```

- [ ] **Step 3: Stop storing process output blocks in DB**

In `ovm_append_log_block()`, keep stage parsing and `echo`, but delete the `$pdo->prepare("UPDATE openmvs_jobs SET process_log...")` block. This function is used for full command output; the raw file is the source of truth now.

- [ ] **Step 4: Write runner output to `uploads/{id}/logs/openmvs_pipeline.log`**

In `crontab/1_run.php`, replace:

```php
$logPath = "{$jobDir}/process.log";
@unlink($logPath);
```

with:

```php
$logDir = "{$jobDir}/logs";
$logPath = "{$logDir}/openmvs_pipeline.log";
if(!is_dir($logDir)) @mkdir($logDir, 0777, true);
@unlink($logPath);
```

In the start update fields, add:

```php
'diagnostic_status'=>null,
'diagnostic_score'=>null,
'diagnostic_summary'=>null,
'diagnostic_log_path'=>"uploads/{$id}/logs/openmvs_pipeline.log",
```

In the command callback, keep file writing and stage parsing, but do not append every line to DB:

```php
}, function($line) use($id, $logPath){
    @file_put_contents($logPath, $line . "\n", FILE_APPEND);
    ovm_append_log_block($id, $line);
});
```

- [ ] **Step 5: Clear filesystem logs on retry/start**

In `api.php`, add `logs` to `ovm_clear_generated_outputs()`:

```php
foreach(['images','colmap','mvs','exports','logs','.npm-cache'] as $dir){
```

Also remove old root `process.log` for backwards cleanup as the existing file loop already does.

- [ ] **Step 6: Run syntax checks**

Run:

```bash
php -l crontab/inc/function.php
php -l crontab/1_run.php
php -l api.php
```

Expected: all report `No syntax errors detected`.

### Task 4: Parse Logs And Upsert Diagnostics

**Files:**
- Modify: `crontab/inc/function.php`

- [ ] **Step 1: Add OpenMVS-only pattern definitions**

Add:

```php
function ovm_diagnostic_patterns(){
    return [
        'openmvs.linear_solver_failure' => [
            'severity' => 'error',
            'summary' => 'Linear solver failures',
            'regex' => '/linear solver|failed to converge|Cholesky|numerical/i',
        ],
        'openmvs.texture_patch_rejected' => [
            'severity' => 'warning',
            'summary' => 'Texture patches rejected',
            'regex' => '/rejected .*patch|patch .*rejected|no valid view/i',
        ],
        'openmvs.cpu_fallback' => [
            'severity' => 'warning',
            'summary' => 'GPU failed, CPU fallback used',
            'regex' => '/CPU fallback|falling back to CPU|retrying with CPU|--cuda-device -2/i',
        ],
        'openmvs.out_of_memory' => [
            'severity' => 'error',
            'summary' => 'Out of memory',
            'regex' => '/out of memory|std::bad_alloc|bad allocation|cannot allocate memory|^Killed$/i',
        ],
        'openmvs.missing_scene' => [
            'severity' => 'error',
            'summary' => 'Missing or unreadable scene file',
            'regex' => '/missing .*scene|scene.*not found|cannot load .*\\.mvs|failed .*open .*\\.mvs/i',
        ],
        'openmvs.process_timeout' => [
            'severity' => 'error',
            'summary' => 'Process timed out',
            'regex' => '/timed out|timeout|exit status 124|status 124/i',
        ],
        'openmvs.nonzero_exit' => [
            'severity' => 'error',
            'summary' => 'Process exited with a non-zero status',
            'regex' => '/non-zero|nonzero|exit code [1-9][0-9]*|failed$/i',
        ],
    ];
}
```

- [ ] **Step 2: Add the parser**

Add:

```php
function ovm_parse_log_diagnostics($text, $rawLogPath=''){
    $patterns = ovm_diagnostic_patterns();
    $stage = 'unknown';
    $rows = [];
    $lines = preg_split('/\R/u', (string)$text);

    foreach($lines as $index => $line){
        $lineNo = $index + 1;
        $trimmed = trim((string)$line);
        if($trimmed === '') continue;

        $parsedStage = ovm_parse_timing_stage_line($trimmed);
        if($parsedStage && !empty($parsedStage['key'])){
            $stage = $parsedStage['key'];
            continue;
        }

        foreach($patterns as $patternId => $pattern){
            if(!preg_match($pattern['regex'], $trimmed)) continue;
            $key = $stage . '|' . $patternId;
            if(!isset($rows[$key])){
                $sample = function_exists('mb_substr') ? mb_substr($trimmed, 0, 500, 'UTF-8') : substr($trimmed, 0, 500);
                $rows[$key] = [
                    'stage' => $stage,
                    'pattern_id' => $patternId,
                    'severity' => $pattern['severity'],
                    'pattern_count' => 0,
                    'first_seen_line' => $lineNo,
                    'last_seen_line' => $lineNo,
                    'message_sample' => $sample,
                    'message_summary' => $pattern['summary'],
                    'raw_log_path' => $rawLogPath,
                ];
            }
            $rows[$key]['pattern_count']++;
            $rows[$key]['last_seen_line'] = $lineNo;
        }
    }

    return array_values($rows);
}
```

- [ ] **Step 3: Add upsert and clear helpers**

Add:

```php
function ovm_clear_job_diagnostics($id){
    global $pdo;
    if(!isset($pdo)) return;
    $stmt = $pdo->prepare("DELETE FROM `openmvs_job_diagnostics` WHERE `job_id`=?");
    $stmt->execute([(int)$id]);
}

function ovm_upsert_job_diagnostics($id, $diagnostics){
    global $pdo;
    if(!isset($pdo)) return;
    $stmt = $pdo->prepare("
        INSERT INTO `openmvs_job_diagnostics`
            (`job_id`,`stage`,`pattern_id`,`severity`,`pattern_count`,`first_seen_line`,`last_seen_line`,`message_sample`,`message_summary`,`raw_log_path`)
        VALUES
            (?,?,?,?,?,?,?,?,?,?)
        ON DUPLICATE KEY UPDATE
            `severity`=VALUES(`severity`),
            `pattern_count`=VALUES(`pattern_count`),
            `first_seen_line`=VALUES(`first_seen_line`),
            `last_seen_line`=VALUES(`last_seen_line`),
            `message_sample`=VALUES(`message_sample`),
            `message_summary`=VALUES(`message_summary`),
            `raw_log_path`=VALUES(`raw_log_path`)
    ");
    foreach($diagnostics as $row){
        $stmt->execute([
            (int)$id,
            $row['stage'],
            $row['pattern_id'],
            $row['severity'],
            (int)$row['pattern_count'],
            $row['first_seen_line'],
            $row['last_seen_line'],
            $row['message_sample'],
            $row['message_summary'],
            $row['raw_log_path'],
        ]);
    }
}
```

- [ ] **Step 4: Run the parser self-check**

Run:

```bash
php tests/openmvs_diagnostics_parser_test.php
```

Expected: `ok`.

### Task 5: Summarize Diagnostics On Worker Finish

**Files:**
- Modify: `crontab/inc/function.php`
- Modify: `crontab/1_run.php`

- [ ] **Step 1: Add score and summary helpers**

Add:

```php
function ovm_diagnostic_summary_fields($diagnostics, $logPath, $successSummary=''){
    $errorCount = 0;
    $warningCount = 0;
    $parts = [];

    foreach($diagnostics as $row){
        $count = (int)($row['pattern_count'] ?? 0);
        if(($row['severity'] ?? '') === 'error') $errorCount += $count;
        if(($row['severity'] ?? '') === 'warning') $warningCount += $count;
        if(count($parts) < 3){
            $parts[] = ($row['message_summary'] ?? $row['pattern_id']) . " x " . $count;
        }
    }

    $status = $errorCount > 0 ? 'error' : ($warningCount > 0 ? 'warning' : 'ok');
    $score = max(0, 100 - min(100, ($errorCount * 25) + ($warningCount * 5)));
    $summary = $parts ? implode('; ', $parts) : ($successSummary !== '' ? $successSummary : 'No repeated OpenMVS diagnostics');

    return [
        'diagnostic_status' => $status,
        'diagnostic_score' => number_format((float)$score, 2, '.', ''),
        'diagnostic_summary' => $summary,
        'diagnostic_log_path' => ovm_relative_openmvs_path($logPath),
    ];
}

function ovm_success_diagnostic_summary($qa){
    if(!is_array($qa)) return '';
    $parts = [];
    if(isset($qa['input_frame_count'], $qa['registered_frame_count'])){
        $parts[] = $qa['registered_frame_count'] . '/' . $qa['input_frame_count'] . ' images registered';
    }
    if(isset($qa['texture_patch_count'])){
        $parts[] = $qa['texture_patch_count'] . ' texture patches';
    }
    if(isset($qa['glb_file_size_mb'])){
        $parts[] = 'GLB ' . $qa['glb_file_size_mb'] . ' MB';
    }
    return implode('; ', $parts);
}
```

- [ ] **Step 2: Add finalization helper**

Add:

```php
function ovm_finalize_job_diagnostics($id, $logPath, $qa=[], $extraLine=''){
    $text = is_file($logPath) ? (string)@file_get_contents($logPath) : '';
    if(trim($extraLine) !== '') $text .= "\n" . trim($extraLine) . "\n";
    $relativeLogPath = ovm_relative_openmvs_path($logPath);
    $diagnostics = ovm_parse_log_diagnostics($text, $relativeLogPath);
    ovm_clear_job_diagnostics($id);
    ovm_upsert_job_diagnostics($id, $diagnostics);
    return ovm_diagnostic_summary_fields($diagnostics, $logPath, ovm_success_diagnostic_summary($qa));
}
```

- [ ] **Step 3: Call finalization on failure before `ovm_fail()` exits**

In `crontab/1_run.php`, replace the failure branch with:

```php
if(!$ok){
    if(ovm_is_abort_requested($id)) ovm_abort($id);
    $reason = implode("\n", $out);
    $diagFields = ovm_finalize_job_diagnostics($id, $logPath, [], "openmvs.nonzero_exit failed");
    updateSQL_SAFE('openmvs_jobs', $diagFields, "`id`=?", [$id]);
    ovm_fail($id, $reason);
}
```

- [ ] **Step 4: Add finalization fields on success**

After `$qa` is loaded and `$upd` is built, before `$upd['status'] = 2;`:

```php
$upd = array_merge($upd, ovm_finalize_job_diagnostics($id, $logPath, $qa));
```

- [ ] **Step 5: Clear stale diagnostics at run start**

After the start update in `crontab/1_run.php`:

```php
ovm_clear_job_diagnostics($id);
```

- [ ] **Step 6: Run syntax checks**

Run:

```bash
php -l crontab/inc/function.php
php -l crontab/1_run.php
php tests/openmvs_diagnostics_parser_test.php
```

Expected: syntax OK and parser `ok`.

### Task 6: Show Quality Light And Diagnostics Detail

**Files:**
- Modify: `job_view.php`
- Modify: `index.php`
- Modify: `api.php`
- Modify: `js/function.js`

- [ ] **Step 1: Add quality rendering helpers**

In `job_view.php`, add:

```php
function ovm_diagnostic_quality_level($row){
    if(($row['diagnostic_status'] ?? '') === 'error') return [1, '失敗'];
    $score = is_numeric($row['diagnostic_score'] ?? null) ? (float)$row['diagnostic_score'] : null;
    if($score === null) return [3, '未知'];
    if($score >= 90) return [5, '優'];
    if($score >= 75) return [4, '良'];
    if($score >= 50) return [3, '可用'];
    if($score >= 25) return [2, '注意'];
    return [1, '失敗'];
}

function ovm_job_quality_cell_html($row){
    [$level, $label] = ovm_diagnostic_quality_level($row);
    $summary = trim((string)($row['diagnostic_summary'] ?? ''));
    ob_start();
    ?>
      <div class="ovm-quality ovm-quality-<?=$level;?>">Q<?=$level;?> <?=htmlspecialchars($label, ENT_QUOTES);?></div>
      <?php if($summary !== ''): ?>
        <div class="ovm-muted"><?=htmlspecialchars($summary, ENT_QUOTES);?></div>
      <?php endif; ?>
    <?php
    return trim(ob_get_clean());
}
```

Add `'quality_html' => ovm_job_quality_cell_html($row),` to `ovm_job_delta_payload()`.

- [ ] **Step 2: Add the quality column**

In `index.php`, add `<th>品質</th>` after status, add:

```php
<td data-refresh-cell="quality"><?=ovm_job_quality_cell_html($r);?></td>
```

after the status cell, update empty colspan from `9` to `10`, and in `updateJobRow()` add:

```javascript
updateJobCell($row, "quality", row.quality_html);
```

Add compact CSS:

```css
.ovm-quality{display:inline-block;min-width:48px;border-radius:4px;padding:2px 6px;font-size:12px;font-weight:700;text-align:center;}
.ovm-quality-5{background:#166534;color:#dcfce7;}
.ovm-quality-4{background:#0f766e;color:#ccfbf1;}
.ovm-quality-3{background:#854d0e;color:#fef3c7;}
.ovm-quality-2{background:#9a3412;color:#ffedd5;}
.ovm-quality-1{background:#991b1b;color:#fee2e2;}
```

- [ ] **Step 3: Add detail button to job actions**

In `ovm_job_actions_cell_html()`, before retry buttons:

```php
if(trim((string)($row['diagnostic_summary'] ?? '')) !== ''):
    $hasAction = true; ?>
    <button class="btn btn-xs btn-default" type="button" onclick="openDiagnosticsDialog(<?=$id;?>)">診斷</button>
<?php endif;
```

- [ ] **Step 4: Add diagnostics endpoint**

In `api.php`, add:

```php
case 'get_diagnostics':
    require "{$base_dir}/inc/checkpassword.php";
    $id = (int)($_GET['id'] ?? 0);
    $jobs = selectSQL_SAFE("SELECT `diagnostic_status`,`diagnostic_score`,`diagnostic_summary`,`diagnostic_log_path` FROM `openmvs_jobs` WHERE `id`=? LIMIT 1", [$id]);
    $items = selectSQL_SAFE("
        SELECT `stage`,`pattern_id`,`severity`,`pattern_count`,`first_seen_line`,`last_seen_line`,`message_sample`,`message_summary`,`raw_log_path`
        FROM `openmvs_job_diagnostics`
        WHERE `job_id`=?
        ORDER BY FIELD(`severity`, 'error', 'warning', 'info'), `pattern_count` DESC
    ", [$id]);
    ovm_json([
        'status' => 'OK',
        'job' => $jobs[0] ?? [],
        'items' => $items,
    ]);
```

- [ ] **Step 5: Clear diagnostics on retry/start**

In both retry and start branches, before `updateSQL_SAFE(...)`, add:

```php
global $pdo;
$stmt = $pdo->prepare("DELETE FROM `openmvs_job_diagnostics` WHERE `job_id`=?");
$stmt->execute([$id]);
```

Also add these reset fields to `ovm_queue_reset_fields()`:

```php
'diagnostic_status'=>null,
'diagnostic_score'=>null,
'diagnostic_summary'=>null,
'diagnostic_log_path'=>null,
```

- [ ] **Step 6: Add modal markup and JS**

In `index.php`, add a modal beside the reason modal:

```html
<div id="jobDiagnosticsDialog" class="ovm-modal" role="dialog" aria-modal="true" hidden>
  <div class="ovm-modal-card">
    <div class="ovm-modal-head">
      <h3>診斷摘要</h3>
      <button class="btn btn-xs btn-default" type="button" onclick="closeDiagnosticsDialog()">關閉</button>
    </div>
    <div class="ovm-modal-body">
      <div id="jobDiagnosticsSummary" class="ovm-muted"></div>
      <div id="jobDiagnosticsRows"></div>
    </div>
  </div>
</div>
```

In `js/function.js`, add:

```javascript
function closeDiagnosticsDialog() {
  $("#jobDiagnosticsDialog").attr("hidden", "hidden");
  $("#jobDiagnosticsSummary").text("");
  $("#jobDiagnosticsRows").empty();
}

function openDiagnosticsDialog(id) {
  $("#jobDiagnosticsSummary").text("讀取中...");
  $("#jobDiagnosticsRows").empty();
  $("#jobDiagnosticsDialog").removeAttr("hidden");
  $.getJSON("api.php?mode=get_diagnostics&id=" + encodeURIComponent(id), function (jd) {
    var job = (jd && jd.job) || {};
    var items = (jd && jd.items) || [];
    $("#jobDiagnosticsSummary").text((job.diagnostic_summary || "沒有診斷摘要") + (job.diagnostic_log_path ? " · " + job.diagnostic_log_path : ""));
    if (!items.length) {
      $("#jobDiagnosticsRows").html('<div class="ovm-muted">沒有重複警告或錯誤。</div>');
      return;
    }
    var html = '<table class="table table-condensed ovm-table"><thead><tr><th>Stage</th><th>Pattern</th><th>Severity</th><th>Count</th></tr></thead><tbody>';
    $.each(items, function (_, row) {
      html += '<tr><td>' + $("<div>").text(row.stage || "").html() + '</td><td>' + $("<div>").text(row.pattern_id || "").html() + '</td><td>' + $("<div>").text(row.severity || "").html() + '</td><td>' + $("<div>").text(row.pattern_count || "").html() + '</td></tr>';
    });
    html += '</tbody></table>';
    $("#jobDiagnosticsRows").html(html);
  });
}
```

- [ ] **Step 7: Run syntax and asset checks**

Run:

```bash
php -l job_view.php
php -l index.php
php -l api.php
pytest tests/test_openmvs_php_assets.py -q
```

Expected: all pass.

### Task 7: Final Verification

**Files:**
- No code changes unless verification finds a concrete bug.

- [ ] **Step 1: Run all available checks**

Run:

```bash
php -l migrate.php
php -l api.php
php -l index.php
php -l job_view.php
php -l crontab/1_run.php
php -l crontab/inc/function.php
php tests/openmvs_diagnostics_parser_test.php
pytest -q
```

Expected: PHP syntax OK, parser `ok`, pytest green.

- [ ] **Step 2: Run migration**

Run:

```bash
php migrate.php
```

Expected output includes:

```text
[OK] openmvs_jobs table ready
[OK] openmvs_job_diagnostics table ready
openmvs_jobs migration complete
```

- [ ] **Step 3: Manual smoke check**

Queue or retry one small job, then verify:

```sql
SELECT diagnostic_status, diagnostic_score, diagnostic_summary, diagnostic_log_path
FROM openmvs_jobs
WHERE id = ?;

SELECT stage, pattern_id, severity, pattern_count
FROM openmvs_job_diagnostics
WHERE job_id = ?
ORDER BY FIELD(severity, 'error', 'warning', 'info'), pattern_count DESC;
```

Expected: raw logs live under `uploads/{id}/logs/openmvs_pipeline.log`; DB contains only summary fields and compact diagnostic rows.

## Self-Review

- Spec coverage: one table, four summary fields, raw filesystem log, pattern counts, upsert uniqueness, oversized DB log avoidance, job list light, and detail modal are covered.
- Non-goals honored: no generic diagnostics framework, no COLMAP/3DGS diagnostic tables, no full stdout/stderr stored in DB.
- Ponytail simplification: stage-specific raw links use the combined pipeline log first; existing OpenMVS `mvs/*.log` files can be linked later if users need direct per-tool log download.
