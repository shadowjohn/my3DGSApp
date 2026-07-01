# Index Upload Progress And Compact Job Table Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve `index.php` so uploads show a lightbox progress meter, completed uploads scroll to their new row, and the job table becomes more compact with upload time, stage progress, and action buttons.

**Architecture:** Keep the feature inside the existing PHP page and its existing `api.php?mode=upload` endpoint. Use `XMLHttpRequest` for browser upload progress because `fetch()` cannot report upload progress in this code path. Show conversion progress as a stage-based approximate percentage using existing `status`, `current_stage`, and `current_stage_label` fields, with active rows auto-refreshing on a timer.

**Tech Stack:** PHP, jQuery, native `XMLHttpRequest`, Bootstrap-style buttons already used by the page, static pytest asset tests.

---

## File Structure

- Modify: `/var/www/html/demo/php/map/3D/gaussian_splat/index.php`
  - Add PHP helpers for upload time formatting and stage-based conversion progress.
  - Add upload progress lightbox markup, failure reason lightbox markup, compact table columns, row anchors, and row highlight CSS.
  - Replace `fetch("api.php?mode=upload")` with `XMLHttpRequest` upload progress handling.
  - Add active-job auto-refresh that avoids refreshing while a lightbox is open.
- Modify: `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_php_page_assets.py`
  - Update the existing `test_index_page_has_upload_form_captcha_and_job_table` assertions so the intended UI and JS behavior are locked down.
- No change: `/var/www/html/demo/php/map/3D/gaussian_splat/api.php`
  - The current upload endpoint already returns `{"status":"OK","id":...}` and is sufficient for progress completion and row highlighting.

## Progress Model

The front table will show approximate conversion progress only when a job is waiting or running. This is intentionally stage-based:

| Stage key | User label | Step | Percent |
| --- | --- | ---: | ---: |
| `worker_start` | 啟動 worker | 0 / 7 | 3 |
| `frame_select` | 挑選影格 | 1 / 7 | 12 |
| `legacy_extract` | 擷取影格 | 1 / 7 | 12 |
| `colmap` | COLMAP 相機姿態估算 | 2 / 7 | 28 |
| `frame_colmap` | 標註影格品質 | 3 / 7 | 38 |
| `enhance` | 影格增強 | 4 / 8 | 46 |
| `prepare_training_images` | 準備訓練影像 | 5 / 8 | 52 |
| `train` | Gaussian 訓練 | 4 / 7 | 76 |
| `export` | 匯出 Splat | 5 / 7 | 90 |
| `cleanup` | 清理 Splat | 6 / 7 | 96 |
| `finalize` | 產生 metadata / QA | 7 / 7 | 99 |

Completed jobs show `100%`; failed and aborted jobs show the status text plus their action button for failure reason instead of a live progress bar.

### Task 1: Update Static Test For Upload Progress And Compact Table

**Files:**
- Modify: `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_php_page_assets.py`

- [ ] **Step 1: Replace the index page assertions with the new behavior contract**

Replace the body of `test_index_page_has_upload_form_captcha_and_job_table()` with this code:

```python
def test_index_page_has_upload_form_captcha_and_job_table():
    text = (ROOT / "index.php").read_text()

    assert 'require "../../../../../inc/config.php";' in text
    assert '$include_mode = "easymap7115";' in text
    assert "SELECT * FROM `gaussian_splat_jobs` WHERE `del`='0' ORDER BY `id` DESC LIMIT 50" in text
    assert "GS_DEFAULT_ESTIMATE_SECONDS" in text
    assert "function gs_format_duration" in text
    assert "function gs_elapsed_seconds" in text
    assert "function gs_average_completed_duration" in text
    assert "function gs_job_timing_summary" in text
    assert "function gs_short_failure_reason" in text
    assert "function gs_upload_time_label" in text
    assert "function gs_pipeline_stage_map" in text
    assert "function gs_job_progress" in text
    assert "candidate frame count is lower than 8" in text
    assert "可用影格不足" in text
    assert '<script src="js/function.js"></script>' in text
    assert 'action="api.php?mode=upload"' in text
    assert 'name="upfile"' in text
    assert 'accept=".mp4"' in text
    assert 'name="gdcode"' in text
    assert '/gd.php?_t=' in text
    assert 'api.php?mode=checkGD' in text
    assert "openSplatViewer" in text
    assert "viewer_splat.html" in text
    assert "$isReady = (string)$r['status'] === '2';" in text
    assert "$hasSplat = $isReady && is_file" in text
    assert 'href="map.php?id=' in text
    assert "html, html body { background:#0f1722;" in text
    assert ".gs-panel{border:1px solid #334155;" in text
    assert ".gs-panel label{color:#dbe7f3;" in text
    assert "input[type=file].form-control{background:#0f1722;" in text
    assert ".gs-table > thead > tr > th{background:#223047;" in text
    assert ".gs-wrap .btn-primary{background:#0d9488;" in text
    assert "#upupdown{background:#0f1722;" in text
    assert ".gs-form-actions{display:flex;" in text
    assert "justify-content:flex-end" in text
    assert ".gs-frame-cell" in text
    assert "white-space:nowrap" in text
    assert ".gs-status-cell" in text
    assert ".gs-actions-cell" in text
    assert ".gs-job-highlight" in text
    assert ".gs-progress-mini" in text
    assert "<title>Gaussian Splat 轉檔 MVP</title>" in text
    assert "<h2>Gaussian Splat 轉檔 MVP</h2>" in text
    assert "MP4 影像擷取至 Nerfstudio splatfacto 匯出" in text
    assert "<label>標題</label>" in text
    assert "<label>電子信箱</label>" in text
    assert "<label>MP4 影片</label>" in text
    assert "<label>經度</label>" in text
    assert "<label>緯度</label>" in text
    assert "<label>高度</label>" in text
    assert "<label>驗證碼</label>" in text
    assert ">更新<" in text
    assert ">上傳<" in text
    assert "<th>編號</th>" in text
    assert "<th>標題</th>" in text
    assert "<th>上傳時間</th>" in text
    assert "<th>狀態</th>" in text
    assert "<th>耗時</th>" in text
    assert "<th>影格</th>" in text
    assert "<th>功能</th>" in text
    assert "<th>Splat 檔</th>" not in text
    assert "<th>地圖</th>" not in text
    assert "目前沒有轉檔工作。" in text
    assert "粗估總長" in text
    assert "已花" in text
    assert "預估剩" in text
    assert "current_stage_label" in text
    assert "duration_seconds" in text
    assert 'placeholder="例：烏日 ICC 大樓辦公室 18 樓"' in text
    assert 'placeholder="例：name@example.com"' in text
    assert 'name="lon" id="lon"' in text
    assert 'placeholder="例：120.61022"' in text
    assert 'name="lat" id="lat"' in text
    assert 'placeholder="例：24.110946"' in text
    assert 'name="alt" id="alt"' in text
    assert 'placeholder="18 樓約 72 公尺，可依現場修正"' in text
    assert 'placeholder="輸入左側圖形驗證碼"' in text
    assert 'id="videoDropZone"' in text
    assert 'tabindex="0"' in text
    assert 'data-paste-focus="true"' in text
    assert "可拖放 MP4，或點一下此區後貼上影片" in text
    assert "function setSelectedVideoFile(file)" in text
    assert "function isMp4File(file)" in text
    assert 'file.type === "video/mp4"' in text
    assert 'if (/\\.mp4$/i.test(name)) {' in text
    assert 'if (file.type === "video/mp4") {\n    return "clipboard-video.mp4";\n  }' in text
    assert 'if (!isMp4File(file)) {\n    $("#uploadStatus").text("請選擇 MP4 影片。");\n    return false;\n  }' in text
    assert 'typeof DataTransfer !== "undefined"' in text
    assert "new DataTransfer()" in text
    assert 'videoDropZone.on("dragover"' in text
    assert 'videoDropZone.on("drop"' in text
    assert 'videoDropZone.on("paste"' in text
    assert "clipboardData.items" in text
    assert "new FormData(this)" in text
    assert 'fetch("api.php?mode=upload"' not in text
    assert "new XMLHttpRequest()" in text
    assert "xhr.upload.onprogress" in text
    assert "updateUploadProgress(event.loaded, event.total)" in text
    assert "function formatUploadBytes" in text
    assert "function showUploadProgressDialog" in text
    assert "function uploadWithProgress" in text
    assert "id=\"uploadProgressDialog\"" in text
    assert "id=\"uploadProgressFill\"" in text
    assert "id=\"uploadProgressPercent\"" in text
    assert "id=\"uploadProgressBytes\"" in text
    assert "id=\"uploadProgressFileName\"" in text
    assert "正在檢查驗證碼..." in text
    assert "驗證碼錯誤。" in text
    assert "正在上傳..." in text
    assert "function formatUploadSeconds" in text
    assert "uploadStartedAt" in text
    assert "上傳完成，已入隊" in text
    assert 'location.href = "index.php?highlight_job="' in text
    assert "scrollIntoView" in text
    assert "highlightUploadedJob" in text
    assert "上傳失敗" in text
    assert "jobFailureReasons" in text
    assert "function openReasonDialog" in text
    assert "id=\"jobReasonDialog\"" in text
    assert "id=\"jobReasonDialogBody\"" in text
    assert ">原因<" in text
    assert ">檢視<" in text
    assert ">定位<" in text
    assert "data-has-active-jobs" in text
    assert "setInterval(function() {" in text
    assert "location.replace" in text
    assert 'document.title = "Gaussian Splat 轉檔 MVP";' in text
```

- [ ] **Step 2: Run the updated test and confirm it fails before implementation**

Run:

```bash
pytest -q tests/test_php_page_assets.py::test_index_page_has_upload_form_captcha_and_job_table
```

Expected: fail on the first missing new contract, likely `function gs_upload_time_label`.

- [ ] **Step 3: Commit the test contract**

Run:

```bash
git add tests/test_php_page_assets.py
git commit -m "test(gaussian): cover upload progress and compact job table"
```

### Task 2: Add PHP Helpers For Upload Time And Conversion Progress

**Files:**
- Modify: `/var/www/html/demo/php/map/3D/gaussian_splat/index.php`

- [ ] **Step 1: Add upload time and progress helper functions**

Insert this block after `gs_short_failure_reason()`:

```php
  function gs_upload_time_label($datetime){
      $datetime = trim((string)$datetime);
      if($datetime === '') return '未記錄';
      $ts = strtotime($datetime);
      if($ts === false) return $datetime;
      return date('Y-m-d H:i', $ts);
  }

  function gs_pipeline_stage_map(){
      return [
          'worker_start' => ['percent'=>3, 'step'=>'啟動中', 'label'=>'啟動 worker'],
          'frame_select' => ['percent'=>12, 'step'=>'1 / 7', 'label'=>'挑選影格'],
          'legacy_extract' => ['percent'=>12, 'step'=>'1 / 7', 'label'=>'擷取影格'],
          'colmap' => ['percent'=>28, 'step'=>'2 / 7', 'label'=>'COLMAP 相機姿態估算'],
          'frame_colmap' => ['percent'=>38, 'step'=>'3 / 7', 'label'=>'標註影格品質'],
          'enhance' => ['percent'=>46, 'step'=>'4 / 8', 'label'=>'影格增強'],
          'prepare_training_images' => ['percent'=>52, 'step'=>'5 / 8', 'label'=>'準備訓練影像'],
          'train' => ['percent'=>76, 'step'=>'4 / 7', 'label'=>'Gaussian 訓練'],
          'export' => ['percent'=>90, 'step'=>'5 / 7', 'label'=>'匯出 Splat'],
          'cleanup' => ['percent'=>96, 'step'=>'6 / 7', 'label'=>'清理 Splat'],
          'finalize' => ['percent'=>99, 'step'=>'7 / 7', 'label'=>'產生 metadata / QA'],
      ];
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
```

- [ ] **Step 2: Add page-level active job and reason containers**

Insert this block after `$estimateSeconds = gs_average_completed_duration($rows);`:

```php
  $hasActiveJobs = false;
  $failureReasons = [];
  foreach($rows as $row){
      if(in_array((string)($row['status'] ?? ''), ['0','1'], true)){
          $hasActiveJobs = true;
      }
  }
```

- [ ] **Step 3: Run PHP lint**

Run:

```bash
php -l index.php
```

Expected: `No syntax errors detected in index.php`.

- [ ] **Step 4: Commit helper changes**

Run:

```bash
git add index.php
git commit -m "feat(gaussian): add front page job progress helpers"
```

### Task 3: Rework Table Columns, Actions, Failure Reason Lightbox, And Row Highlight

**Files:**
- Modify: `/var/www/html/demo/php/map/3D/gaussian_splat/index.php`

- [ ] **Step 1: Add compact table, progress, modal, and form action CSS**

In the `<style nonce="gg">` block, replace the existing `.gs-actions{white-space:nowrap;}` line with this block:

```css
  .gs-form-actions{display:flex;align-items:center;justify-content:flex-end;gap:10px;}
  .gs-status-cell{min-width:120px;max-width:150px;}
  .gs-status-main{font-size:15px;font-weight:600;color:#f8fafc;}
  .gs-frame-cell{min-width:108px;white-space:nowrap;font-variant-numeric:tabular-nums;}
  .gs-actions-cell{min-width:150px;white-space:nowrap;}
  .gs-actions-cell .btn{margin:2px 2px 2px 0;}
  .gs-upload-time{min-width:128px;white-space:nowrap;}
  .gs-progress-mini{height:7px;border-radius:999px;background:#0b1220;border:1px solid #334155;overflow:hidden;margin-top:7px;}
  .gs-progress-mini span{display:block;height:100%;background:#14b8a6;}
  .gs-job-highlight{animation:gsPulseRow 2.4s ease-out 1;background:#12363c!important;}
  @keyframes gsPulseRow{0%{box-shadow:inset 0 0 0 2px #f59e0b;}100%{box-shadow:inset 0 0 0 0 rgba(245,158,11,0);}}
  .gs-modal[hidden]{display:none;}
  .gs-modal{position:fixed;z-index:10000;inset:0;background:rgba(2,6,23,.72);display:flex;align-items:center;justify-content:center;padding:20px;}
  .gs-modal-card{width:min(620px,calc(100vw - 32px));border:1px solid #334155;border-radius:6px;background:#111b2a;color:#e5edf7;box-shadow:0 24px 80px rgba(0,0,0,.45);}
  .gs-modal-head{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px 16px;border-bottom:1px solid #26364a;}
  .gs-modal-head h3{margin:0;font-size:18px;color:#f8fafc;}
  .gs-modal-body{padding:16px;}
  .gs-upload-bar{height:16px;border:1px solid #334155;background:#020617;border-radius:999px;overflow:hidden;}
  .gs-upload-bar span{display:block;height:100%;width:0;background:#14b8a6;transition:width .18s linear;}
  .gs-upload-meta{display:grid;grid-template-columns:110px 1fr;gap:7px 10px;margin-top:14px;font-size:14px;}
  .gs-reason-body{max-height:58vh;overflow:auto;background:#020617;color:#3cff71;border:1px solid #334155;border-radius:4px;padding:14px;font-size:14px;line-height:1.55;white-space:pre-wrap;}
```

- [ ] **Step 2: Right-align the upload button**

Replace the current upload button and status span:

```php
    <button class="btn btn-primary" type="submit">上傳</button>
    <span id="uploadStatus" class="gs-muted" style="margin-left:10px;"></span>
```

with:

```php
    <div class="gs-form-actions">
      <span id="uploadStatus" class="gs-muted"></span>
      <button class="btn btn-primary" type="submit">上傳</button>
    </div>
```

- [ ] **Step 3: Add active-job state to the wrapper**

Replace:

```php
<div class="gs-wrap" data-viewer-page="viewer_splat.html">
```

with:

```php
<div class="gs-wrap" data-viewer-page="viewer_splat.html" data-has-active-jobs="<?=$hasActiveJobs ? '1' : '0';?>">
```

- [ ] **Step 4: Replace the table header**

Replace the `<thead>` row with:

```php
        <tr>
          <th>編號</th>
          <th>標題</th>
          <th>上傳時間</th>
          <th>狀態</th>
          <th>耗時</th>
          <th>影格</th>
          <th>功能</th>
        </tr>
```

- [ ] **Step 5: Replace the row rendering with compact status and actions**

Inside the `foreach($rows as $r)` loop, replace the variable setup and `<tr>...</tr>` block with:

```php
      <?php foreach($rows as $r):
          $id = (int)$r['id'];
          $splat = "uploads/{$id}/exports/splat.ply";
          $isReady = (string)$r['status'] === '2';
          $hasSplat = $isReady && is_file(__DIR__ . "/{$splat}");
          $timingSummary = gs_job_timing_summary($r, $estimateSeconds);
          $shortReason = gs_short_failure_reason($r['reason'] ?? '');
          $fullReason = trim((string)($r['reason'] ?? ''));
          if($fullReason !== '') $failureReasons[(string)$id] = $fullReason;
          $progress = gs_job_progress($r);
      ?>
        <tr id="job-<?=$id;?>" data-job-id="<?=$id;?>">
          <td><?=$id;?></td>
          <td>
            <?=htmlspecialchars($r['title'] ?: $r['orin_filename'], ENT_QUOTES);?>
            <div class="gs-muted"><?=htmlspecialchars($r['orin_filename'] ?? '', ENT_QUOTES);?></div>
          </td>
          <td class="gs-upload-time"><?=htmlspecialchars(gs_upload_time_label($r['c_datetime'] ?? ''), ENT_QUOTES);?></td>
          <td class="gs-status-cell">
            <div class="gs-status-main"><?=htmlspecialchars(gs_status_text($r['status']), ENT_QUOTES);?></div>
            <?php if($progress['active']): ?>
              <div class="gs-progress-mini" aria-label="轉檔進度 <?=$progress['percent'];?>%">
                <span style="width:<?=$progress['percent'];?>%"></span>
              </div>
              <div class="gs-muted"><?=$progress['percent'];?>% · <?=htmlspecialchars($progress['step'], ENT_QUOTES);?> · <?=htmlspecialchars($progress['label'], ENT_QUOTES);?></div>
            <?php endif; ?>
          </td>
          <td>
            <?php foreach($timingSummary as $timingLine): ?>
              <div class="gs-muted"><?=htmlspecialchars($timingLine, ENT_QUOTES);?></div>
            <?php endforeach; ?>
          </td>
          <td class="gs-frame-cell"><?=htmlspecialchars((string)($r['frame_count'] ?? ''), ENT_QUOTES);?> / <?=htmlspecialchars((string)($r['registered_frame_count'] ?? ''), ENT_QUOTES);?></td>
          <td class="gs-actions-cell">
            <?php if($hasSplat): ?>
              <button class="btn btn-xs btn-success" type="button" onclick="openSplatViewer('<?=htmlspecialchars($splat, ENT_QUOTES);?>')">檢視</button>
              <a class="btn btn-xs btn-info" href="map.php?id=<?=$id;?>">定位</a>
            <?php endif; ?>
            <?php if($shortReason !== ''): ?>
              <button class="btn btn-xs btn-warning" type="button" onclick="openReasonDialog(<?=$id;?>)">原因</button>
            <?php endif; ?>
            <?php if(!$hasSplat && $shortReason === ''): ?>
              <span class="gs-muted">-</span>
            <?php endif; ?>
          </td>
        </tr>
      <?php endforeach; ?>
```

- [ ] **Step 6: Keep the empty table row aligned**

Confirm the empty state remains:

```php
        <tr><td colspan="7" class="text-center gs-muted">目前沒有轉檔工作。</td></tr>
```

- [ ] **Step 7: Add upload progress and failure reason lightboxes after the table**

Insert this block after the closing `</div>` for `.table-responsive` and before the closing `</div>` for `.gs-wrap`:

```php
  <div id="uploadProgressDialog" class="gs-modal" role="dialog" aria-modal="true" aria-labelledby="uploadProgressTitle" hidden>
    <div class="gs-modal-card">
      <div class="gs-modal-head">
        <h3 id="uploadProgressTitle">影片上傳中</h3>
        <button class="btn btn-xs btn-default" type="button" id="closeUploadProgress" hidden>關閉</button>
      </div>
      <div class="gs-modal-body">
        <div class="gs-upload-bar" aria-label="上傳進度">
          <span id="uploadProgressFill"></span>
        </div>
        <div class="gs-upload-meta">
          <div>進度</div><div id="uploadProgressPercent">0%</div>
          <div>檔案</div><div id="uploadProgressFileName">-</div>
          <div>大小</div><div id="uploadProgressBytes">0 B / 0 B</div>
          <div>耗時</div><div id="uploadProgressElapsed">0 秒</div>
          <div>狀態</div><div id="uploadProgressMessage">正在上傳...</div>
        </div>
      </div>
    </div>
  </div>

  <div id="jobReasonDialog" class="gs-modal" role="dialog" aria-modal="true" aria-labelledby="jobReasonTitle" hidden>
    <div class="gs-modal-card">
      <div class="gs-modal-head">
        <h3 id="jobReasonTitle">失敗原因</h3>
        <button class="btn btn-xs btn-default" type="button" onclick="closeReasonDialog()">關閉</button>
      </div>
      <div class="gs-modal-body">
        <pre id="jobReasonDialogBody" class="gs-reason-body"></pre>
      </div>
    </div>
  </div>
```

- [ ] **Step 8: Add the failure reason data object at the top of the script**

At the beginning of `<script nonce="gg">`, immediately after `document.title = "Gaussian Splat 轉檔 MVP";`, add:

```php
var jobFailureReasons = <?=json_encode($failureReasons, JSON_UNESCAPED_UNICODE | JSON_HEX_TAG | JSON_HEX_APOS | JSON_HEX_QUOT | JSON_HEX_AMP);?>;
```

- [ ] **Step 9: Add reason dialog functions**

Add these JavaScript functions after `refreshCaptchaImage()`:

```javascript
function openReasonDialog(id) {
  var reason = jobFailureReasons[String(id)] || "這筆工作沒有失敗原因。";
  $("#jobReasonDialogBody").text(reason);
  $("#jobReasonDialog").removeAttr("hidden");
}

function closeReasonDialog() {
  $("#jobReasonDialog").attr("hidden", "hidden");
  $("#jobReasonDialogBody").text("");
}
```

- [ ] **Step 10: Add row highlight and active job auto-refresh**

Add these JavaScript functions after the reason dialog functions:

```javascript
function highlightUploadedJob() {
  var params = new URLSearchParams(window.location.search);
  var highlightId = params.get("highlight_job");
  if (!highlightId && window.location.hash.indexOf("#job-") === 0) {
    highlightId = window.location.hash.replace("#job-", "");
  }
  if (!highlightId) {
    return;
  }
  var row = document.getElementById("job-" + highlightId);
  if (!row) {
    return;
  }
  row.scrollIntoView({ behavior: "smooth", block: "center" });
  row.classList.add("gs-job-highlight");
}

function startActiveJobRefresh() {
  if ($(".gs-wrap").attr("data-has-active-jobs") !== "1") {
    return;
  }
  setInterval(function() {
    if (!$("#uploadProgressDialog").is("[hidden]") || !$("#jobReasonDialog").is("[hidden]")) {
      return;
    }
    location.replace(location.pathname + location.search + location.hash);
  }, 20000);
}

$(function() {
  highlightUploadedJob();
  startActiveJobRefresh();
});
```

- [ ] **Step 11: Run lint and static page test**

Run:

```bash
php -l index.php
pytest -q tests/test_php_page_assets.py::test_index_page_has_upload_form_captcha_and_job_table
```

Expected: PHP lint passes. The pytest may still fail on upload progress JavaScript until Task 4.

- [ ] **Step 12: Commit table and lightbox changes**

Run:

```bash
git add index.php
git commit -m "feat(gaussian): compact front job table actions"
```

### Task 4: Replace Upload Fetch With XHR Progress Lightbox

**Files:**
- Modify: `/var/www/html/demo/php/map/3D/gaussian_splat/index.php`

- [ ] **Step 1: Add upload progress JavaScript helpers**

Insert this block after `formatUploadSeconds(uploadStartedAt)`:

```javascript
function formatUploadBytes(bytes) {
  bytes = Math.max(0, Number(bytes) || 0);
  if (bytes >= 1024 * 1024 * 1024) {
    return (bytes / 1024 / 1024 / 1024).toFixed(2) + " GB";
  }
  if (bytes >= 1024 * 1024) {
    return (bytes / 1024 / 1024).toFixed(2) + " MB";
  }
  if (bytes >= 1024) {
    return (bytes / 1024).toFixed(1) + " KB";
  }
  return bytes + " B";
}

function showUploadProgressDialog(file) {
  $("#closeUploadProgress").attr("hidden", "hidden");
  $("#uploadProgressFill").css("width", "0%");
  $("#uploadProgressPercent").text("0%");
  $("#uploadProgressFileName").text(getUploadFileName(file));
  $("#uploadProgressBytes").text("0 B / " + formatUploadBytes(file.size || 0));
  $("#uploadProgressElapsed").text("0 秒");
  $("#uploadProgressMessage").text("正在上傳...");
  $("#uploadProgressDialog").removeAttr("hidden");
}

function updateUploadProgress(loaded, total) {
  loaded = Math.max(0, Number(loaded) || 0);
  total = Math.max(0, Number(total) || 0);
  var percent = total > 0 ? Math.min(100, Math.round((loaded / total) * 100)) : 0;
  $("#uploadProgressFill").css("width", percent + "%");
  $("#uploadProgressPercent").text(percent + "%");
  $("#uploadProgressBytes").text(formatUploadBytes(loaded) + " / " + (total > 0 ? formatUploadBytes(total) : "未知大小"));
}

function finishUploadProgress(message, canClose) {
  $("#uploadProgressMessage").text(message);
  if (canClose) {
    $("#closeUploadProgress").removeAttr("hidden");
  }
}

function uploadWithProgress(formData) {
  return new Promise(function(resolve, reject) {
    var xhr = new XMLHttpRequest();
    xhr.open("POST", "api.php?mode=upload");
    xhr.upload.onprogress = function(event) {
      updateUploadProgress(event.loaded, event.total);
    };
    xhr.onreadystatechange = function() {
      if (xhr.readyState !== 4) {
        return;
      }
      var payload = null;
      try {
        payload = JSON.parse(xhr.responseText);
      } catch (err) {
        reject(new Error("上傳回應格式錯誤"));
        return;
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(payload);
        return;
      }
      reject(new Error(payload.reason || "上傳失敗"));
    };
    xhr.onerror = function() {
      reject(new Error("上傳連線失敗"));
    };
    xhr.send(formData);
  });
}
```

- [ ] **Step 2: Add close handler for the upload progress lightbox**

Add this after `$("#captchaImage,#refreshCaptcha").on("click", refreshCaptchaImage);`:

```javascript
$("#closeUploadProgress").on("click", function() {
  $("#uploadProgressDialog").attr("hidden", "hidden");
});
```

- [ ] **Step 3: Replace the `fetch()` upload branch**

Inside the `success` callback for `api.php?mode=checkGD`, replace:

```javascript
      $("#uploadStatus").text("正在上傳...");
      var uploadStartedAt = Date.now();
      var formData = new FormData(this);
      formData.set("upfile", selectedVideoFile, getUploadFileName(selectedVideoFile));
      fetch("api.php?mode=upload", { method: "POST", body: formData })
        .then(function(response) {
          return response.json();
        })
        .then(function(jd) {
          if (jd.status === "OK") {
            $("#uploadStatus").text("上傳完成，已入隊 #" + jd.id + "，上傳耗時 " + formatUploadSeconds(uploadStartedAt) + "。");
            setTimeout(function() { location.reload(); }, 1200);
          } else {
            $("#uploadStatus").text(jd.reason || "上傳失敗");
            refreshCaptchaImage();
          }
        })
        .catch(function() {
          $("#uploadStatus").text("上傳失敗");
          refreshCaptchaImage();
        });
```

with:

```javascript
      $("#uploadStatus").text("正在上傳...");
      var uploadStartedAt = Date.now();
      var uploadTimer = setInterval(function() {
        $("#uploadProgressElapsed").text(formatUploadSeconds(uploadStartedAt));
      }, 500);
      var formData = new FormData(this);
      formData.set("upfile", selectedVideoFile, getUploadFileName(selectedVideoFile));
      showUploadProgressDialog(selectedVideoFile);
      uploadWithProgress(formData)
        .then(function(jd) {
          clearInterval(uploadTimer);
          if (jd.status === "OK") {
            updateUploadProgress(selectedVideoFile.size || 0, selectedVideoFile.size || 0);
            var doneText = "上傳完成，已入隊 #" + jd.id + "，上傳耗時 " + formatUploadSeconds(uploadStartedAt) + "。";
            $("#uploadStatus").text(doneText);
            finishUploadProgress(doneText, false);
            setTimeout(function() {
              location.href = "index.php?highlight_job=" + encodeURIComponent(jd.id) + "#job-" + encodeURIComponent(jd.id);
            }, 800);
            return;
          }
          var reason = jd.reason || "上傳失敗";
          $("#uploadStatus").text(reason);
          finishUploadProgress(reason, true);
          refreshCaptchaImage();
        })
        .catch(function(err) {
          clearInterval(uploadTimer);
          var reason = err && err.message ? err.message : "上傳失敗";
          $("#uploadStatus").text(reason);
          finishUploadProgress(reason, true);
          refreshCaptchaImage();
        });
```

- [ ] **Step 4: Run lint and the focused index test**

Run:

```bash
php -l index.php
pytest -q tests/test_php_page_assets.py::test_index_page_has_upload_form_captcha_and_job_table
```

Expected:

```text
No syntax errors detected in index.php
1 passed
```

- [ ] **Step 5: Commit upload progress**

Run:

```bash
git add index.php tests/test_php_page_assets.py
git commit -m "feat(gaussian): show upload progress dialog"
```

### Task 5: Verify Front Page And Asset Tests

**Files:**
- Verify: `/var/www/html/demo/php/map/3D/gaussian_splat/index.php`
- Verify: `/var/www/html/demo/php/map/3D/gaussian_splat/tests/test_php_page_assets.py`

- [ ] **Step 1: Run PHP lint**

Run:

```bash
php -l index.php
```

Expected:

```text
No syntax errors detected in index.php
```

- [ ] **Step 2: Run page asset tests**

Run:

```bash
pytest -q tests/test_php_page_assets.py
```

Expected: all tests in `tests/test_php_page_assets.py` pass.

- [ ] **Step 3: Run related PHP asset tests**

Run:

```bash
pytest -q tests/test_php_page_assets.py tests/test_php_api_assets.py tests/test_cron_worker_assets.py
```

Expected: these related static tests pass.

- [ ] **Step 4: Manual browser check**

Open:

```text
https://3wa.tw/demo/php/map/3D/gaussian_splat/index.php
```

Check these visible behaviors:

- Upload button is aligned right.
- Selecting, dragging, or pasting an MP4 still sets the selected file name.
- Submitting opens the upload lightbox with filename, size, elapsed time, and percent.
- After upload completes, the page navigates to `index.php?highlight_job=<id>#job-<id>`, scrolls to that row, and highlights it.
- Table columns are `編號 / 標題 / 上傳時間 / 狀態 / 耗時 / 影格 / 功能`.
- The `影格` column does not wrap.
- `檢視`, `定位`, and `原因` are in the `功能` column.
- Clicking `原因` opens a readable lightbox with the failure reason.
- Running jobs show a compact progress bar and percentage.

- [ ] **Step 5: Inspect the final diff before handing back**

Run:

```bash
git diff -- index.php tests/test_php_page_assets.py
```

Expected: diff only contains the planned front page and test changes.

## Self-Review

- Spec coverage:
  - Upload progress lightbox: Task 4.
  - Percent, file size, elapsed upload display: Task 4.
  - Scroll to uploaded row after upload: Task 3 and Task 4.
  - Upload button aligned right: Task 3.
  - Wider non-wrapping frame column: Task 3.
  - Shorter status column: Task 3.
  - New function/action column containing view, map, and failure reason: Task 3.
  - Failure reason button opens lightbox: Task 3.
  - Upload time visible: Task 3.
  - Conversion progress during running jobs: Progress Model, Task 2, Task 3.
- Placeholder scan: no unspecified implementation steps remain; every code step contains exact code or an exact command.
- Type and name consistency:
  - PHP helper names used by tests match implementation snippets: `gs_upload_time_label`, `gs_pipeline_stage_map`, `gs_job_progress`.
  - JavaScript names used by tests match implementation snippets: `formatUploadBytes`, `showUploadProgressDialog`, `uploadWithProgress`, `openReasonDialog`, `highlightUploadedJob`.
