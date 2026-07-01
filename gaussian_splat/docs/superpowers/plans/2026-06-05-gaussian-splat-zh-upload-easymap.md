# Gaussian Splat 中文化上傳與 Easymap 3D 定位 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完成 Gaussian Splat MVP 前後台中文化、首頁 MP4 拖放/貼上上傳、完整 placeholder、Easymap 3D 定位與方向旋轉，並用 `jpgtoglb` 範例影片建立一筆烏日 ICC 18 樓測試工作。

**Architecture:** 保留現有 PHP 頁面與資料表結構，將 UI 文案、上傳互動和定位控制集中在 `index.php`、`admin.php`、`api.php`、`map.php`。首頁改用原生 `FormData` 上傳，讓 `$include_mode = "easymap7115";` 可以專注載入圖台；Easymap 定位頁使用公開 API `panToXYZ`、`enable3D`、`panTo3D(new dgXYZ(...), { heading, pitch, roll })` 和 `map.rotate(...)`。

**Tech Stack:** PHP 7/8-style legacy pages, Easymap 7.1.15 global SDK, jQuery, Bootstrap classes, Python `pytest` static asset tests, Nerfstudio/CUDA worker scripts.

---

## File Structure

- Modify `index.php`: 首頁中文化補齊、placeholder、拖放/貼上 focus 區、原生 `FormData` 上傳、`$include_mode = "easymap7115";`。
- Modify `admin.php`: 後台標題、表格、按鈕、空狀態、錯誤提示中文化，保持 `retry`/`abort` action 值不變。
- Modify `api.php`: 使用者會看到的 `reason` 與 API fallback 訊息中文化。
- Modify `map.php`: 定位頁中文化，`$include_mode = "easymap7115";`，加入 2D/3D 定位按鈕、相機 heading/pitch/roll、圖台旋轉、方向旋轉控制。
- Modify `tests/test_php_page_assets.py`: 覆蓋首頁 placeholder、drop/paste UI、後台中文化。
- Modify `tests/test_php_api_assets.py`: 覆蓋 API 中文錯誤訊息。
- Modify `tests/test_map_page_assets.py`: 覆蓋定位頁中文化、Easymap 3D 定位、旋轉控制。
- No new permanent runtime script is required for the sample job; create it with a checked PHP one-liner during Task 4.
- Important boundary: current Gaussian Splat output is `splat.ply`, so it remains in the existing Three.js iframe preview. Easymap 3D controls position the map/camera and persist transform values; direct Cesium overlay waits for a later 3D Tiles / glTF-compatible export path.

## Constants

Use these values for the ICC office default and sample job:

```text
Title: 烏日 ICC 大樓辦公室 18 樓
Address: 台中市烏日區高鐵一路268號
Lon: 120.61022
Lat: 24.110946
Alt: 72
Scale: 1
Heading: 0
Pitch: 0
Roll: 0
Camera Alt: 180
Camera Heading: 0
Camera Pitch: -35
Camera Roll: 0
Map Rotate: 0
Sample MP4: /var/www/html/demo/php/map/3D/jpgtoglb/uploads/2/2.mp4
```

The lon/lat come from a public address lookup for the same `高鐵一路268號` building. `Alt=72` is an 18F working default for alignment, not a survey-grade elevation.

---

### Task 1: 首頁 Placeholder 與拖放/貼上上傳

**Files:**
- Modify: `tests/test_php_page_assets.py`
- Modify: `index.php`

- [ ] **Step 1: Write the failing test**

Add these assertions inside `test_index_page_has_upload_form_captcha_and_job_table()` after the existing Chinese text assertions:

```python
    assert '$include_mode = "easymap7115";' in text
    assert 'placeholder="例：烏日 ICC 大樓辦公室 18 樓"' in text
    assert 'placeholder="例：name@example.com"' in text
    assert 'placeholder="例：120.61022"' in text
    assert 'placeholder="例：24.110946"' in text
    assert 'placeholder="18 樓約 72 公尺，可依現場修正"' in text
    assert 'placeholder="輸入左側圖形驗證碼"' in text
    assert 'id="videoDropZone"' in text
    assert 'tabindex="0"' in text
    assert 'data-paste-focus="true"' in text
    assert "可拖放 MP4，或點一下此區後貼上影片" in text
    assert "function setSelectedVideoFile(file)" in text
    assert "new DataTransfer()" in text
    assert 'videoDropZone.on("dragover"' in text
    assert 'videoDropZone.on("drop"' in text
    assert 'videoDropZone.on("paste"' in text
    assert "clipboardData.items" in text
    assert "new FormData(this)" in text
    assert 'fetch("api.php?mode=upload"' in text
    assert 'contentType: false' not in text
    assert '$("#uploadForm").ajaxForm' not in text
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_php_page_assets.py::test_index_page_has_upload_form_captcha_and_job_table -q
```

Expected: FAIL on `$include_mode = "easymap7115";` or the first missing placeholder/drop-zone assertion.

- [ ] **Step 3: Write minimal implementation**

In `index.php`, change the include mode at the top:

```php
  $include_mode = "easymap7115";
```

Update the upload form fields. Preserve the existing names and IDs:

```php
<input class="form-control" name="title" id="title" placeholder="例：烏日 ICC 大樓辦公室 18 樓" required>
<input class="form-control" name="email" id="email" placeholder="例：name@example.com">
<input class="form-control" type="file" name="upfile" id="upfile" accept=".mp4" required>
<div id="videoDropZone" class="gs-dropzone" tabindex="0" role="button" data-paste-focus="true" aria-describedby="videoDropHelp">
  <strong>選擇檔案 / 拖放 / 貼上影片</strong>
  <div id="videoDropHelp" class="gs-muted">可拖放 MP4，或點一下此區後貼上影片。</div>
  <div id="selectedVideoName" class="gs-selected-file">尚未選擇影片</div>
</div>
```

Use these defaults and placeholders for location:

```php
<input class="form-control" name="lon" value="120.61022" placeholder="例：120.61022">
<input class="form-control" name="lat" value="24.110946" placeholder="例：24.110946">
<input class="form-control" name="alt" value="72" placeholder="18 樓約 72 公尺，可依現場修正">
<input class="form-control" style="width:160px;" maxlength="5" id="gdcode" name="gdcode" placeholder="輸入左側圖形驗證碼" required>
```

Add dark-theme drop-zone CSS in the existing `<style nonce="gg">`:

```css
  .gs-dropzone{margin-top:10px;border:1px dashed #5a718b;border-radius:6px;background:#111b2a;color:#dbe7f3;padding:14px;outline:none;}
  .gs-dropzone.is-active,.gs-dropzone:focus{border-color:#14b8a6;box-shadow:0 0 0 2px rgba(20,184,166,.22);}
  .gs-selected-file{margin-top:8px;color:#f8fafc;font-size:13px;}
```

Replace the current `ajaxForm` block with native `FormData` upload code:

```js
document.title = "Gaussian Splat 轉檔 MVP";

var selectedVideoFile = null;
var videoDropZone = $("#videoDropZone");
var fileInput = $("#upfile");

function refreshCaptchaImage() {
  $("#captchaImage").attr("src", "/gd.php?_t=" + Date.now());
}

function setSelectedVideoFile(file) {
  if (!file) return false;
  var name = file.name || "clipboard-video.mp4";
  var isMp4 = /\.mp4$/i.test(name) || file.type === "video/mp4";
  if (!isMp4) {
    $("#uploadStatus").text("請選擇 MP4 影片。");
    return false;
  }

  selectedVideoFile = file;
  var dt = new DataTransfer();
  dt.items.add(file);
  fileInput[0].files = dt.files;
  $("#selectedVideoName").text(name + " (" + Math.max(1, Math.round(file.size / 1024 / 1024)) + " MB)");
  return true;
}

$("#captchaImage,#refreshCaptcha").on("click", refreshCaptchaImage);

fileInput.on("change", function() {
  setSelectedVideoFile(this.files && this.files[0]);
});

videoDropZone.on("dragover", function(event) {
  event.preventDefault();
  videoDropZone.addClass("is-active");
});

videoDropZone.on("dragleave blur", function() {
  videoDropZone.removeClass("is-active");
});

videoDropZone.on("drop", function(event) {
  event.preventDefault();
  videoDropZone.removeClass("is-active");
  var files = event.originalEvent.dataTransfer && event.originalEvent.dataTransfer.files;
  setSelectedVideoFile(files && files[0]);
});

videoDropZone.on("paste", function(event) {
  var items = event.originalEvent.clipboardData && event.originalEvent.clipboardData.items;
  if (!items) return;
  for (var i = 0; i < items.length; i++) {
    if (items[i].kind === "file") {
      if (setSelectedVideoFile(items[i].getAsFile())) event.preventDefault();
      break;
    }
  }
});

videoDropZone.on("click", function() {
  videoDropZone.trigger("focus");
  fileInput.trigger("click");
});

$("#uploadForm").on("submit", function(event) {
  event.preventDefault();
  var form = this;
  var captchaOk = false;
  $("#uploadStatus").text("正在檢查驗證碼...");
  $.ajax({
    url: "api.php?mode=checkGD",
    method: "POST",
    data: { gdcode: $("#gdcode").val() },
    async: false,
    success: function(data) {
      captchaOk = $.trim(data) === "OK";
    }
  });
  if (!captchaOk) {
    $("#uploadStatus").text("驗證碼錯誤。");
    refreshCaptchaImage();
    return;
  }

  var formData = new FormData(form);
  if (selectedVideoFile) formData.set("upfile", selectedVideoFile, selectedVideoFile.name || "clipboard-video.mp4");
  $("#uploadStatus").text("正在上傳...");

  fetch("api.php?mode=upload", {
    method: "POST",
    body: formData
  }).then(function(resp) {
    return resp.json();
  }).then(function(jd) {
    if (jd.status === "OK") location.reload();
    else {
      $("#uploadStatus").text(jd.reason || "上傳失敗");
      refreshCaptchaImage();
    }
  }).catch(function() {
    $("#uploadStatus").text("上傳失敗");
    refreshCaptchaImage();
  });
});
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/test_php_page_assets.py::test_index_page_has_upload_form_captcha_and_job_table -q
php -l index.php
```

Expected: PASS and `No syntax errors detected in index.php`.

- [ ] **Step 5: Commit**

```bash
git add index.php tests/test_php_page_assets.py
git commit -m "feat: add localized drag paste video upload"
```

---

### Task 2: 後台與 API Reason 中文化

**Files:**
- Modify: `tests/test_php_page_assets.py`
- Modify: `tests/test_php_api_assets.py`
- Modify: `admin.php`
- Modify: `api.php`

- [ ] **Step 1: Write the failing tests**

In `test_admin_page_requires_auth_and_exposes_job_actions()`, add:

```python
    assert "<title>Gaussian Splat 轉檔後台</title>" in text
    assert "Gaussian Splat 轉檔後台" in text
    assert "回前台" in text
    assert "<th>編號</th>" in text
    assert "<th>標題</th>" in text
    assert "<th>狀態</th>" in text
    assert "<th>影格</th>" in text
    assert "<th>Splat MB</th>" in text
    assert "<th>品管</th>" in text
    assert "<th>操作</th>" in text
    assert ">重試<" in text
    assert ">中止<" in text
    assert ">紀錄<" in text
    assert ">檢視<" in text
    assert "目前沒有工作。" in text
    assert 'alert(jd.reason || "操作失敗");' in text
    assert 'document.title = "Gaussian Splat 轉檔後台";' in text
```

In `test_api_upload_creates_pending_mp4_job_and_stages_input()`, replace the English reason assertions and add:

```python
    assert "請輸入標題" in text
    assert "請選擇 MP4 影片" in text
    assert "目前僅支援 MP4 影片" in text
    assert "建立上傳目錄失敗" in text
    assert "上傳後找不到影片檔" in text
    assert "title is required" not in text
    assert "upload failed" not in text
    assert "only mp4 is supported in the MVP worker" not in text
```

In `test_api_log_transform_and_admin_actions()`, add:

```python
    assert "定位資料格式錯誤" in text
    assert "建立工作目錄失敗" in text
    assert "儲存定位資料失敗" in text
    assert "工作編號錯誤" in text
    assert "未知的操作" in text
    assert "未知模式" in text
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/test_php_page_assets.py::test_admin_page_requires_auth_and_exposes_job_actions tests/test_php_api_assets.py -q
```

Expected: FAIL on missing admin Chinese title and API reason strings.

- [ ] **Step 3: Write minimal implementation**

In `admin.php`, update visible text only:

```php
<title>Gaussian Splat 轉檔後台</title>
...
<h2>Gaussian Splat 轉檔後台 <small><a href="index.php">回前台</a></small></h2>
...
<th>編號</th>
<th>標題</th>
<th>狀態</th>
<th>影格</th>
<th>Splat MB</th>
<th>品管</th>
<th>操作</th>
...
<button class="btn btn-xs btn-warning" type="button" onclick="jobAction(<?=$id;?>,'retry')">重試</button>
<button class="btn btn-xs btn-danger" type="button" onclick="jobAction(<?=$id;?>,'abort')">中止</button>
<button class="btn btn-xs btn-default" type="button" onclick="refreshJobLog(<?=$id;?>, '#log')">紀錄</button>
<button class="btn btn-xs btn-success" type="button" onclick="openSplatViewer('<?=htmlspecialchars($splat, ENT_QUOTES);?>')">檢視</button>
...
<tr><td colspan="7" class="text-center">目前沒有工作。</td></tr>
```

Add this at the start of the admin script block:

```js
document.title = "Gaussian Splat 轉檔後台";
```

Change the alert fallback:

```js
alert(jd.reason || "操作失敗");
```

In `api.php`, replace user-facing reason strings:

```php
if($title === '') gs_json(['status'=>'NO','reason'=>'請輸入標題']);
if(!isset($_FILES['upfile']) || $_FILES['upfile']['error'] !== 0 || ($_FILES['upfile']['size'] ?? 0) <= 0){
    gs_json(['status'=>'NO','reason'=>'請選擇 MP4 影片']);
}
if($ext !== 'mp4') gs_json(['status'=>'NO','reason'=>'目前僅支援 MP4 影片']);
...
gs_mark_failed($id, '建立上傳目錄失敗');
gs_json(['status'=>'NO','reason'=>'建立上傳目錄失敗']);
...
gs_mark_failed($id, '上傳後找不到影片檔');
gs_json(['status'=>'NO','reason'=>'上傳後找不到影片檔']);
...
if($id <= 0 || !is_array($data)) gs_json(['status'=>'NO','reason'=>'定位資料格式錯誤']);
...
gs_json(['status'=>'NO','reason'=>'建立工作目錄失敗']);
...
gs_json(['status'=>'NO','reason'=>'儲存定位資料失敗']);
...
if($id <= 0) gs_json(['status'=>'NO','reason'=>'工作編號錯誤']);
...
gs_json(['status'=>'NO','reason'=>'未知的操作']);
...
gs_json(['status'=>'NO','reason'=>'未知模式']);
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
pytest tests/test_php_page_assets.py::test_admin_page_requires_auth_and_exposes_job_actions tests/test_php_api_assets.py -q
php -l admin.php
php -l api.php
```

Expected: PASS and no PHP syntax errors.

- [ ] **Step 5: Commit**

```bash
git add admin.php api.php tests/test_php_page_assets.py tests/test_php_api_assets.py
git commit -m "feat: localize gaussian splat admin and api messages"
```

---

### Task 3: Easymap 3D 定位、相機方向與圖台旋轉

**Files:**
- Modify: `tests/test_map_page_assets.py`
- Modify: `map.php`

- [ ] **Step 1: Write the failing test**

Update `test_map_page_requires_auth_ready_job_and_splat_file()`:

```python
    assert '$include_mode = "easymap7115";' in text
    assert '$include_mode = "easymap7115|three.js-r155";' not in text
    assert 'exit("工作不存在")' in text
    assert 'exit("工作尚未完成")' in text
    assert 'exit("找不到 splat.ply")' in text
```

Add these assertions to `test_map_page_builds_easymap_form_preview_and_save_payload()`:

```python
    assert "<title>Gaussian Splat 定位校正</title>" in text
    assert 'document.title = "Gaussian Splat 定位校正";' in text
    assert "定位校正" in text
    assert "經度" in text
    assert "緯度" in text
    assert "高度" in text
    assert "比例" in text
    assert "模型方向" in text
    assert "俯仰" in text
    assert "翻滾" in text
    assert "相機經度" in text
    assert "相機緯度" in text
    assert "相機高度" in text
    assert "相機方向" in text
    assert "相機俯仰" in text
    assert "相機翻滾" in text
    assert "圖台旋轉" in text
    assert 'id="map_rotate"' in text
    assert 'id="map_rotate_range"' in text
    assert 'id="locate2d"' in text
    assert 'id="locate3d"' in text
    assert 'id="applyMapRotate"' in text
    assert "map.panToXYZ(new dgXY" in text
    assert "map.enable3D(function" in text
    assert "map.panTo3D(new dgXYZ" in text
    assert "heading: numberOrDefault(\"#camera_heading\", numberOrDefault(\"#heading\", 0))" in text
    assert "pitch: numberOrDefault(\"#camera_pitch\", -35)" in text
    assert "roll: numberOrDefault(\"#camera_roll\", 0)" in text
    assert "map.rotate(numberOrDefault(\"#map_rotate\", 0))" in text
    assert "方向旋轉" in text
    assert "儲存定位" in text
    assert "開啟獨立檢視器" in text
    assert "正在儲存..." in text
    assert "已儲存。" in text
    assert "儲存失敗。" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_map_page_assets.py -q
```

Expected: FAIL on include mode or missing Chinese/3D controls.

- [ ] **Step 3: Write minimal implementation**

In `map.php`, use Easymap only:

```php
$include_mode = "easymap7115";
```

Localize guard messages:

```php
if(!$rows) exit("工作不存在");
if(!$isReady) exit("工作尚未完成");
if(!is_file(__DIR__ . "/{$splat}")) exit("找不到 splat.ply");
```

Use this title:

```php
<title>Gaussian Splat 定位校正</title>
```

Replace English labels in the panel:

```php
<h3>定位校正：<?=htmlspecialchars($info['title'] ?: $info['orin_filename'], ENT_QUOTES);?></h3>
<label>經度 <input id="lon" placeholder="例：120.61022" value="<?=htmlspecialchars((string)gs_value($info['lon'], 120.61022), ENT_QUOTES);?>"></label>
<label>緯度 <input id="lat" placeholder="例：24.110946" value="<?=htmlspecialchars((string)gs_value($info['lat'], 24.110946), ENT_QUOTES);?>"></label>
<label>高度 <input id="alt" placeholder="18 樓約 72 公尺" value="<?=htmlspecialchars((string)gs_value($info['alt'], 72), ENT_QUOTES);?>"></label>
<label>比例 <input id="scale" placeholder="例：1" value="<?=htmlspecialchars((string)gs_value($info['scale'], 1), ENT_QUOTES);?>"></label>
<label>模型方向 <input id="heading" placeholder="0=北，90=東，180=南，270=西" value="<?=htmlspecialchars((string)gs_value($info['heading'], 0), ENT_QUOTES);?>"></label>
<label>俯仰 <input id="pitch" placeholder="例：0" value="<?=htmlspecialchars((string)gs_value($info['pitch'], 0), ENT_QUOTES);?>"></label>
<label>翻滾 <input id="roll" placeholder="例：0" value="<?=htmlspecialchars((string)gs_value($info['roll'], 0), ENT_QUOTES);?>"></label>
```

Add synchronized rotation controls below the transform fields:

```php
<div class="field-row">
  <label>圖台旋轉 <input id="map_rotate" value="0" placeholder="0=正北，順時針角度"></label>
  <label>方向旋轉 <input id="map_rotate_range" type="range" min="0" max="360" step="1" value="0"></label>
</div>
```

Localize camera labels and default camera values:

```php
<h4>相機</h4>
<label>相機經度 <input id="camera_lon" placeholder="留空則使用經度" value="<?=htmlspecialchars((string)gs_value($info['camera_lon'], ''), ENT_QUOTES);?>"></label>
<label>相機緯度 <input id="camera_lat" placeholder="留空則使用緯度" value="<?=htmlspecialchars((string)gs_value($info['camera_lat'], ''), ENT_QUOTES);?>"></label>
<label>相機高度 <input id="camera_alt" placeholder="例：180" value="<?=htmlspecialchars((string)gs_value($info['camera_alt'], 180), ENT_QUOTES);?>"></label>
<label>相機方向 <input id="camera_heading" placeholder="0=北，90=東，180=南，270=西" value="<?=htmlspecialchars((string)gs_value($info['camera_heading'], 0), ENT_QUOTES);?>"></label>
<label>相機俯仰 <input id="camera_pitch" placeholder="例：-35" value="<?=htmlspecialchars((string)gs_value($info['camera_pitch'], -35), ENT_QUOTES);?>"></label>
<label>相機翻滾 <input id="camera_roll" placeholder="例：0" value="<?=htmlspecialchars((string)gs_value($info['camera_roll'], 0), ENT_QUOTES);?>"></label>
```

Localize links and buttons:

```php
<p><a target="_blank" rel="noopener" href="<?=htmlspecialchars($viewerSrc, ENT_QUOTES);?>">開啟獨立檢視器</a></p>
<button class="btn btn-default" id="locate2d" type="button">2D 定位</button>
<button class="btn btn-default" id="locate3d" type="button">3D 定位</button>
<button class="btn btn-default" id="applyMapRotate" type="button">套用圖台旋轉</button>
<button class="btn btn-primary" id="save" type="button">儲存定位</button>
```

Use this JS block structure:

```js
document.title = "Gaussian Splat 定位校正";

var map = new Easymap("map");
map.panToXYZ(new dgXY(parseFloat($("#lon").val()), parseFloat($("#lat").val())), 19);

function numberOrNull(selector) {
  var value = parseFloat($(selector).val());
  return Number.isFinite(value) ? value : null;
}

function numberOrDefault(selector, defaultValue) {
  var value = numberOrNull(selector);
  return value === null ? defaultValue : value;
}

function targetLon() {
  return numberOrDefault("#lon", 120.61022);
}

function targetLat() {
  return numberOrDefault("#lat", 24.110946);
}

function targetAlt() {
  return numberOrDefault("#alt", 72);
}

function syncRotateInputs(source) {
  var value = numberOrDefault(source, 0);
  $("#map_rotate").val(value);
  $("#map_rotate_range").val(value);
}

function applyMapRotate() {
  map.rotate(numberOrDefault("#map_rotate", 0));
}

function locate2d() {
  map.panToXYZ(new dgXY(targetLon(), targetLat()), 19);
  applyMapRotate();
}

function locate3d() {
  map.enable3D(function() {
    map.panTo3D(new dgXYZ(targetLon(), targetLat(), targetAlt()), {
      heading: numberOrDefault("#camera_heading", numberOrDefault("#heading", 0)),
      pitch: numberOrDefault("#camera_pitch", -35),
      roll: numberOrDefault("#camera_roll", 0)
    });
  });
}

$("#map_rotate,#map_rotate_range").on("input change", function() {
  syncRotateInputs("#" + this.id);
  applyMapRotate();
});

$("#applyMapRotate").on("click", applyMapRotate);
$("#locate2d").on("click", locate2d);
$("#locate3d").on("click", locate3d);
```

Keep the existing `payload()` but include map rotation if it is not added to the database:

```js
map_rotate: numberOrNull("#map_rotate")
```

If the database has no `map_rotate` column, keep it in `transform.json` only and do not add it to the API field allow-list. The existing DB columns already cover model heading/pitch/roll and camera heading/pitch/roll.

Change save messages:

```js
$("#saveStatus").text("正在儲存...");
if(jd.status === "OK") $("#saveStatus").text("已儲存。");
else $("#saveStatus").text(jd.reason || "儲存失敗。");
...
$("#saveStatus").text("儲存失敗。");
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest tests/test_map_page_assets.py -q
php -l map.php
```

Expected: PASS and no PHP syntax errors.

- [ ] **Step 5: Commit**

```bash
git add map.php tests/test_map_page_assets.py
git commit -m "feat: add easymap 3d alignment controls"
```

---

### Task 4: 建立並試跑烏日 ICC 18F 範例工作

**Files:**
- No source files modified.
- Generated runtime files under `uploads/<job-id>/` are ignored artifacts and must not be committed.

- [ ] **Step 1: Verify the sample MP4 exists**

Run:

```bash
ls -lh /var/www/html/demo/php/map/3D/jpgtoglb/uploads/2/2.mp4
ffprobe -v error -show_entries format=duration,size -of default=nw=1:nk=1 /var/www/html/demo/php/map/3D/jpgtoglb/uploads/2/2.mp4
```

Expected: file exists, about `4.0M`, duration about `16.000000`.

- [ ] **Step 2: Create a pending job directly through existing DB helpers**

Run this from `/var/www/html/demo/php/map/3D/gaussian_splat`; it records the generated ID in ignored `output/last_icc_job_id.txt`:

```bash
JOB_ID=$(php <<'PHP'
<?php
require "/var/www/html/inc/config.php";

$root = "/var/www/html/demo/php/map/3D/gaussian_splat";
$src = "/var/www/html/demo/php/map/3D/jpgtoglb/uploads/2/2.mp4";
if(!is_file($src)){
    fwrite(STDERR, "sample mp4 missing\n");
    exit(1);
}

$m = [
    'title' => '烏日 ICC 大樓辦公室 18 樓',
    'email' => '',
    'orin_filename' => 'jpgtoglb-uploads-2-2.mp4',
    'c_datetime' => date('Y-m-d H:i:s'),
    'IP' => '127.0.0.1',
    'status' => 0,
    'reason' => '',
    'kind' => 'mp4',
    'del' => 0,
    'lon' => 120.61022,
    'lat' => 24.110946,
    'alt' => 72,
    'heading' => 0,
    'pitch' => 0,
    'roll' => 0,
    'scale' => 1,
    'camera_alt' => 180,
    'camera_heading' => 0,
    'camera_pitch' => -35,
    'camera_roll' => 0,
];

$id = (int)insertSQL('gaussian_splat_jobs', $m);
$inputDir = "{$root}/uploads/{$id}/input";
if(!is_dir($inputDir) && !mkdir($inputDir, 0777, true)){
    fwrite(STDERR, "failed to create {$inputDir}\n");
    exit(1);
}
if(!copy($src, "{$inputDir}/input.mp4")){
    fwrite(STDERR, "failed to copy sample mp4\n");
    exit(1);
}
@chmod("{$root}/uploads/{$id}", 0755);
@chmod($inputDir, 0755);
@chmod("{$inputDir}/input.mp4", 0644);
echo $id . PHP_EOL;
PHP
)
mkdir -p output
printf '%s\n' "$JOB_ID" > output/last_icc_job_id.txt
echo "Created job ${JOB_ID}"
test -n "$JOB_ID"
```

Expected: prints `Created job N`, where `N` is numeric.

- [ ] **Step 3: Run the worker with a short training smoke limit**

Run:

```bash
GS_TRAIN_MAX_ITERATIONS=25 php crontab/1_run.php
```

Expected: exits `0` and prints `Done.`. It may take around 2 minutes on the CUDA machine.

- [ ] **Step 4: Verify the job output**

```bash
JOB_ID=$(cat output/last_icc_job_id.txt)
test -f "uploads/${JOB_ID}/exports/splat.ply"
test -f "uploads/${JOB_ID}/qa_report.json"
JOB_ID="$JOB_ID" php <<'PHP'
<?php
require "/var/www/html/inc/config.php";
$id = (int)getenv("JOB_ID");
$rows = selectSQL_SAFE("SELECT `id`,`title`,`status`,`lon`,`lat`,`alt`,`frame_count`,`registered_frame_count`,`splat_file_size_mb` FROM `gaussian_splat_jobs` WHERE `id`=? LIMIT 1", [$id]);
print_r($rows[0] ?? []);
PHP
```

Expected: `status` is `2`, title is `烏日 ICC 大樓辦公室 18 樓`, lon/lat/alt match the constants, and `splat_file_size_mb` is non-empty.

- [ ] **Step 5: No commit**

Do not commit generated files under the job directory named by `$(cat output/last_icc_job_id.txt)`. Confirm:

```bash
git status --short --ignored
```

Expected: source tree has no unstaged source changes from this task. Generated uploads remain ignored.

---

### Task 5: Browser Verification And Final Commit Check

**Files:**
- No planned source edits.
- Screenshot artifact: `output/playwright/gaussian-index-zh-upload.png` and `output/playwright/gaussian-map-3d-controls.png` are ignored and must not be committed.

- [ ] **Step 1: Run full static verification**

Run:

```bash
pytest
php -l index.php
php -l admin.php
php -l api.php
php -l map.php
git diff --check
```

Expected: all tests pass, all PHP lint commands report no syntax errors, and `git diff --check` exits `0`.

- [ ] **Step 2: Browser-check homepage text and upload UI**

Run a Playwright script using the cached module path already verified in this workspace:

```bash
NODE_PATH=/home/john/.npm/_npx/31e32ef8478fbf80/node_modules node <<'NODE'
const fs = require('fs');
const { chromium } = require('playwright');
(async () => {
  fs.mkdirSync('output/playwright', { recursive: true });
  const browser = await chromium.launch({ headless: true, executablePath: '/usr/bin/chromium-browser' });
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, ignoreHTTPSErrors: true });
  const errors = [];
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  await page.goto('https://3wa.tw/demo/php/map/3D/gaussian_splat/index.php?_verify=' + Date.now(), { waitUntil: 'networkidle' });
  const info = await page.evaluate(() => ({
    title: document.title,
    h2: document.querySelector('.gs-head h2')?.textContent.trim(),
    dropText: document.querySelector('#videoDropZone')?.textContent.trim(),
    titlePlaceholder: document.querySelector('#title')?.getAttribute('placeholder'),
    lon: document.querySelector('input[name="lon"]')?.value,
    lat: document.querySelector('input[name="lat"]')?.value,
    alt: document.querySelector('input[name="alt"]')?.value,
    tableHeadings: Array.from(document.querySelectorAll('.gs-table th')).map(el => el.textContent.trim()),
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth
  }));
  await page.screenshot({ path: 'output/playwright/gaussian-index-zh-upload.png', fullPage: true });
  await browser.close();
  console.log(JSON.stringify({ info, errorCount: errors.length, errors }, null, 2));
})();
NODE
```

Expected: `title` and `h2` are `Gaussian Splat 轉檔 MVP`, `dropText` contains `貼上影片`, lon/lat/alt are `120.61022`, `24.110946`, `72`, `errorCount` is `0`, and `scrollWidth === clientWidth`.

- [ ] **Step 3: Browser-check map page if the sample job completed**

```bash
JOB_ID=$(cat output/last_icc_job_id.txt)
NODE_PATH=/home/john/.npm/_npx/31e32ef8478fbf80/node_modules node <<'NODE'
const fs = require('fs');
const { chromium } = require('playwright');
(async () => {
  const id = process.env.JOB_ID;
  fs.mkdirSync('output/playwright', { recursive: true });
  const browser = await chromium.launch({ headless: true, executablePath: '/usr/bin/chromium-browser' });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, ignoreHTTPSErrors: true });
  const errors = [];
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  await page.goto(`https://3wa.tw/demo/php/map/3D/gaussian_splat/map.php?id=${encodeURIComponent(id)}&_verify=${Date.now()}`, { waitUntil: 'networkidle' });
  const info = await page.evaluate(() => ({
    title: document.title,
    h3: document.querySelector('#panel h3')?.textContent.trim(),
    rotate: document.querySelector('#map_rotate')?.value,
    hasLocate3d: !!document.querySelector('#locate3d'),
    hasMap: !!document.querySelector('#map'),
    hasPreview: !!document.querySelector('#preview'),
    saveText: document.querySelector('#save')?.textContent.trim(),
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth
  }));
  await page.screenshot({ path: 'output/playwright/gaussian-map-3d-controls.png', fullPage: true });
  await browser.close();
  console.log(JSON.stringify({ info, errorCount: errors.length, errors }, null, 2));
})();
NODE
```

Expected: `title` is `Gaussian Splat 定位校正`, `hasLocate3d` is `true`, `hasMap` is `true`, `hasPreview` is `true`, `errorCount` is `0`.

- [ ] **Step 4: Final status**

Run:

```bash
git status --short --branch --ignored
git log --oneline -5
```

Expected: only `docs/plan.md` remains untracked plus ignored generated artifacts. The latest commits should include Tasks 1-3.

---

## Self-Review

- Spec coverage: front/back UI text, buttons, titles, placeholders, upload drag/drop/paste focus area, Easymap include mode, 3D positioning, rotation controls, and sample video job are each covered by a task.
- No placeholder gaps: every task has concrete tests, code snippets, commands, expected output, and commit messages.
- Type/name consistency: field IDs are stable across tests and implementation (`upfile`, `videoDropZone`, `map_rotate`, `locate3d`, `camera_heading`). API DB fields remain limited to existing schema; extra `map_rotate` is stored only in `transform.json`.
