<?php
  require __DIR__ . "/../inc/config.php";
  require_once __DIR__ . "/job_view.php";
  $include_mode = "easymap7115";
  $listState = gs_job_list_state(15);
  $rows = $listState['rows'];
  $estimateSeconds = gs_average_completed_duration($rows);
  $hasActiveJobs = false;
  $failureReasons = [];
  foreach($rows as $row){
      if(in_array((string)($row['status'] ?? ''), ['0','1'], true)){
          $hasActiveJobs = true;
      }
  }

  require "{$base_dir}/html.php";
  require "{$base_dir}/head.php";
?>
<script src="js/function.js"></script>
<title>Focusit Studio</title>
<?php
  require "{$base_dir}/head_end.php";
  require "{$base_dir}/body.php";
  require "{$base_dir}/top.php";
?>
<style nonce="gg">
  html, html body { background:#0f1722; color:#e5edf7; }
  .gs-wrap{max-width:1180px;margin:0 auto;padding:28px 20px 42px;}
  .gs-head{display:flex;align-items:flex-end;justify-content:space-between;gap:12px;margin-bottom:16px;}
  .gs-head h2{margin:0;font-weight:700;color:#f8fafc;letter-spacing:0;}
  .gs-head .gs-muted{color:#9fb0c3;}
  .gs-admin-link{background:#1d2a3a;border-color:#3b4a5f;color:#e5edf7;}
  .gs-admin-link:hover,.gs-admin-link:focus{background:#26364a;border-color:#5a718b;color:#fff;}
  .gs-panel{border:1px solid #334155;border-radius:6px;padding:18px;margin-bottom:18px;background:#172133;box-shadow:0 12px 28px rgba(0,0,0,.26);}
  .gs-panel label{color:#dbe7f3;font-weight:600;}
  .gs-panel .form-control{background:#0f1722;color:#f8fafc;border-color:#3b4a5f;box-shadow:none;}
  .gs-panel .form-control:focus{border-color:#14b8a6;box-shadow:0 0 0 2px rgba(20,184,166,.18);}
  input[type=file].form-control{background:#0f1722;color:#e5edf7;border-color:#3b4a5f;height:auto;}
  input[type=file].form-control::file-selector-button{background:#25364a;border:0;border-right:1px solid #3b4a5f;color:#f8fafc;margin:-6px 10px -6px -12px;padding:6px 12px;}
  .gs-dropzone{margin-top:10px;border:1px dashed #5a718b;border-radius:6px;background:#111b2a;color:#dbe7f3;padding:14px;outline:none;}
  .gs-dropzone.is-active,.gs-dropzone:focus{border-color:#14b8a6;box-shadow:0 0 0 2px rgba(20,184,166,.22);}
  .gs-selected-file{margin-top:8px;color:#f8fafc;font-size:13px;}
  .gs-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;}
  .gs-captcha{display:flex;align-items:center;gap:10px;flex-wrap:wrap;}
  .gs-captcha img{cursor:pointer;border:1px solid #3b4a5f;border-radius:4px;background:#020617;}
  .gs-job-list{display:grid;gap:12px;}
  .gs-job-card{display:grid;grid-template-columns:200px minmax(0,1fr);gap:14px;border:1px solid #334155;border-radius:6px;background:#111b2a;color:#dbe7f3;padding:12px;}
  .gs-job-card:hover{background:#12363c;color:#f8fafc;}
  .gs-job-body{display:grid;grid-template-columns:minmax(220px,1.4fr) minmax(170px,1fr) minmax(150px,.9fr) minmax(90px,.55fr) minmax(140px,.75fr);gap:12px;align-items:start;min-width:0;}
  .gs-job-section{min-width:0;border-left:1px solid #29384d;padding-left:12px;}
  .gs-job-title{border-left:0;padding-left:0;}
  .gs-section-label{margin-bottom:5px;color:#9fb0c3;font-size:12px;font-weight:700;}
  .gs-job-name{font-size:15px;font-weight:700;color:#f8fafc;overflow-wrap:anywhere;}
  .gs-empty-list{border:1px solid #334155;border-radius:6px;background:#111b2a;padding:18px;text-align:center;}
  .gs-form-actions{display:flex;align-items:center;justify-content:flex-end;gap:10px;}
  .gs-list-tools{display:grid;grid-template-columns:auto minmax(240px,1fr) auto auto auto;gap:10px;align-items:center;margin:0 0 14px;padding:12px;border:1px solid #334155;border-radius:6px;background:#111b2a;}
  .gs-list-tools label{margin:0;color:#dbe7f3;font-weight:700;}
  .gs-list-tools .form-control{background:#0f1722;color:#f8fafc;border-color:#3b4a5f;box-shadow:none;}
  .gs-list-count{color:#9fb0c3;font-size:12px;white-space:nowrap;}
  .gs-pagination{display:flex;justify-content:center;align-items:center;gap:10px;margin-top:14px;color:#cbd5e1;}
  .gs-pagination .disabled{pointer-events:none;opacity:.45;}
  .gs-thumb-cell{width:200px;}
  .gs-thumb-pair{display:grid;grid-template-columns:1fr 1fr;gap:8px;width:200px;}
  .gs-thumb-item{min-width:0;}
  .gs-thumb-title{margin-bottom:5px;color:#9fb0c3;font-size:12px;font-weight:700;text-align:center;}
  .gs-thumb-link{display:block;text-decoration:none;}
  .gs-model-thumb{position:relative;width:96px;height:154px;overflow:hidden;border:1px solid rgba(45,212,191,.28);border-radius:4px;background:#07111f;box-shadow:inset 0 0 0 1px rgba(15,23,42,.82);}
  .gs-model-thumb img,.gs-model-thumb canvas{display:block;width:100%;height:100%;object-fit:cover;}
  .gs-model-thumb span{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;padding:8px;color:#5eead4;font-size:13px;line-height:1.3;text-align:center;}
  .model-thumb-empty{border-color:rgba(148,163,184,.18);background:rgba(15,23,42,.56);}
  .model-thumb-empty span{color:#64748b;}
  .model-thumb-error span{color:#fca5a5;}
  .gs-status-cell{min-width:120px;max-width:150px;}
  .gs-status-main{font-size:15px;font-weight:600;color:#f8fafc;}
  .gs-failure-inline{margin-top:5px;color:#fca5a5;font-size:12px;line-height:1.4;}
  .gs-frame-cell{min-width:108px;white-space:nowrap;font-variant-numeric:tabular-nums;}
  .gs-actions-cell{min-width:150px;white-space:nowrap;}
  .gs-actions-cell .btn{margin:2px 2px 2px 0;}
  .gs-upload-time{white-space:nowrap;}
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
  .gs-muted{color:#9fb0c3;font-size:12px;}
  .gs-wrap .btn-primary{background:#0d9488;border-color:#0d9488;color:#fff;}
  .gs-wrap .btn-primary:hover,.gs-wrap .btn-primary:focus{background:#0f766e;border-color:#0f766e;color:#fff;}
  .gs-wrap .btn-default{background:#1d2a3a;border-color:#3b4a5f;color:#e5edf7;}
  .gs-wrap .btn-default:hover,.gs-wrap .btn-default:focus{background:#26364a;border-color:#5a718b;color:#fff;}
  .gs-wrap .btn-success{background:#15803d;border-color:#15803d;color:#fff;}
  .gs-wrap .btn-info{background:#2563eb;border-color:#2563eb;color:#fff;}
  #upupdown{background:#0f1722;color:#dbe7f3;}
  #upupdown hr{border-color:#334155;}
  #upupdown #footer_design{color:#f59e0b!important;}
  #upupdown a{color:#dbe7f3!important;}
  @media (max-width: 760px){
    .gs-head{display:block;}
    .gs-grid{grid-template-columns:1fr;}
    .gs-list-tools{grid-template-columns:1fr;}
    .gs-job-card{grid-template-columns:1fr;}
    .gs-job-body{grid-template-columns:1fr;}
    .gs-job-section{border-left:0;border-top:1px solid #29384d;padding-left:0;padding-top:10px;}
    .gs-job-title{border-top:0;padding-top:0;}
    .gs-thumb-cell{width:100%;}
    .gs-thumb-pair{width:100%;grid-template-columns:1fr 1fr;}
    .gs-model-thumb{width:100%;height:150px;}
    .gs-actions-cell .btn{margin-bottom:4px;}
  }
</style>

<div class="gs-wrap" data-viewer-page="viewer_splat.php" data-has-active-jobs="<?=$hasActiveJobs ? '1' : '0';?>">
  <div class="gs-head">
    <div>
      <h2>Focusit Studio</h2>
      <div class="gs-muted">建立專案，選擇重建模式，再交給背景排程處理</div>
    </div>
    <a class="btn btn-default btn-sm gs-admin-link" href="admin.php">管理</a>
  </div>

  <form id="uploadForm" method="post" enctype="multipart/form-data" action="api.php?mode=upload" class="gs-panel">
    <div class="form-group">
      <label>專案名稱</label>
      <input class="form-control" name="title" id="title" placeholder="例：烏日 ICC 大樓辦公室 18 樓" required>
    </div>
    <div class="form-group">
      <label>電子信箱</label>
      <input class="form-control" name="email" id="email" placeholder="例：name@example.com">
    </div>
    <div class="form-group">
      <label>MP4 影片 / ZIP 圖片包</label>
      <input class="form-control" type="file" name="upfile" id="upfile" accept=".mp4,.zip" required>
      <div id="videoDropZone" class="gs-dropzone" tabindex="0" role="group" aria-label="影片或圖片 ZIP 拖放與貼上區" data-paste-focus="true" aria-describedby="videoDropHelp">
        <strong>拖放 / 貼上 MP4 或 ZIP</strong>
        <div id="videoDropHelp" class="gs-muted">可拖放 MP4，或 ZIP 圖片包；ZIP 內請放 JPG/PNG。</div>
        <div id="selectedVideoName" class="gs-selected-file">尚未選擇檔案</div>
      </div>
    </div>
    <div class="form-group">
      <label>重建模式</label>
      <select class="form-control" name="pipeline_mode" id="pipeline_mode">
        <option value="fast" selected>快速</option>
        <option value="qa">驗證</option>
        <option value="premium">進階</option>
      </select>
    </div>
    <div class="gs-grid">
      <div>
        <label>經度</label>
        <input class="form-control" name="lon" id="lon" value="120.61022" placeholder="例：120.61022">
      </div>
      <div>
        <label>緯度</label>
        <input class="form-control" name="lat" id="lat" value="24.110946" placeholder="例：24.110946">
      </div>
      <div>
        <label>高度</label>
        <input class="form-control" name="alt" id="alt" value="72" placeholder="18 樓約 72 公尺，可依現場修正">
      </div>
    </div>
    <div class="form-group" style="margin-top:12px;">
      <label>驗證碼</label>
      <div class="gs-captcha">
        <img id="captchaImage" src="/john_web/gd.php?_t=<?=time();?>" alt="驗證碼">
        <input class="form-control" style="width:160px;" maxlength="5" id="gdcode" name="gdcode" placeholder="輸入左側圖形驗證碼" required>
      </div>
    </div>
    <div class="gs-form-actions">
      <span id="uploadStatus" class="gs-muted"></span>
      <button class="btn btn-primary" type="submit">建立專案</button>
    </div>
  </form>

  <?=gs_job_search_form_html($listState);?>

  <div class="gs-job-list">
    <?php foreach($rows as $r):
        $id = (int)$r['id'];
        $fullReason = trim((string)($r['reason'] ?? ''));
        if($fullReason !== '') $failureReasons[(string)$id] = gs_json_safe_text($fullReason);
    ?>
      <article class="gs-job-card" id="job-<?=$id;?>" data-job-id="<?=$id;?>">
        <div class="gs-job-thumb gs-thumb-cell" data-refresh-cell="thumb"><?=gs_job_thumbnail_cell_html($r);?></div>
        <div class="gs-job-body">
          <div class="gs-job-section gs-job-title">
            <div class="gs-section-label">#<?=$id;?> · <?=htmlspecialchars(gs_upload_time_label($r['c_datetime'] ?? ''), ENT_QUOTES);?></div>
            <div class="gs-job-name"><?=htmlspecialchars($r['title'] ?: $r['orin_filename'], ENT_QUOTES);?></div>
            <div class="gs-muted"><?=htmlspecialchars($r['orin_filename'] ?? '', ENT_QUOTES);?></div>
          </div>
          <div class="gs-job-section gs-status-cell" data-refresh-cell="status"><?=gs_job_status_cell_html($r);?></div>
          <div class="gs-job-section" data-refresh-cell="timing"><?=gs_job_timing_cell_html($r, $estimateSeconds);?></div>
          <div class="gs-job-section gs-frame-cell" data-refresh-cell="frames"><?=gs_job_frames_cell_html($r);?></div>
          <div class="gs-job-section gs-actions-cell" data-refresh-cell="actions"><?=gs_job_actions_cell_html($r);?></div>
        </div>
      </article>
    <?php endforeach; ?>
    <?php if(empty($rows)): ?>
      <div class="gs-empty-list gs-muted">目前沒有轉檔工作。</div>
    <?php endif; ?>
  </div>
  <?=gs_job_pagination_html($listState);?>

  <div id="uploadProgressDialog" class="gs-modal" role="dialog" aria-modal="true" aria-labelledby="uploadProgressTitle" hidden>
    <div class="gs-modal-card">
      <div class="gs-modal-head">
        <h3 id="uploadProgressTitle">檔案上傳中</h3>
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
</div>

<script nonce="gg">
document.title = "Focusit Studio";
var jobFailureReasons = <?=json_encode($failureReasons, JSON_UNESCAPED_UNICODE | JSON_HEX_TAG | JSON_HEX_APOS | JSON_HEX_QUOT | JSON_HEX_AMP);?>;
var initialThumbQueue = <?=json_encode(gs_job_thumb_queue_payload($rows, 3), JSON_UNESCAPED_UNICODE);?>;

function refreshCaptchaImage() {
  $("#captchaImage").attr("src", "/john_web/gd.php?_t=" + Date.now());
}

function openReasonDialog(id) {
  var reason = jobFailureReasons[String(id)] || "這筆工作沒有失敗原因。";
  $("#jobReasonDialogBody").text(reason);
  $("#jobReasonDialog").removeAttr("hidden");
}

function closeReasonDialog() {
  $("#jobReasonDialog").attr("hidden", "hidden");
  $("#jobReasonDialogBody").text("");
}

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

var jobRefreshTimer = null;
var jobRefreshInFlight = false;

function updateJobCell($row, cell, html) {
  $row.find('[data-refresh-cell="' + cell + '"]').html(html || "");
}

function updateJobRow(row) {
  var $row = $("#job-" + row.id);
  if (!$row.length) {
    return;
  }
  updateJobCell($row, "thumb", row.thumb_html);
  updateJobCell($row, "status", row.status_html);
  updateJobCell($row, "timing", row.timing_html);
  updateJobCell($row, "frames", row.frames_html);
  updateJobCell($row, "actions", row.actions_html);
  scanMissingOutputThumbs();
}

var outputThumbQueue = [];
var outputThumbRunning = false;

function outputThumbSessionKey(id) {
  return "gs-output-thumb-" + id;
}

function outputThumbAlreadyTried(id) {
  try {
    return sessionStorage.getItem(outputThumbSessionKey(id)) === "1";
  } catch (err) {
    return false;
  }
}

function markOutputThumbTried(id) {
  try {
    sessionStorage.setItem(outputThumbSessionKey(id), "1");
  } catch (err) {
  }
}

function enqueueOutputThumbJob(id) {
  id = parseInt(id, 10);
  if (!id || outputThumbAlreadyTried(id) || outputThumbQueue.indexOf(id) !== -1) {
    return;
  }
  outputThumbQueue.push(id);
  runNextOutputThumbJob();
}

function scanMissingOutputThumbs() {
  $('[data-missing-output-thumb="1"]').slice(0, 3).each(function() {
    enqueueOutputThumbJob($(this).attr("data-job-id"));
  });
}

function runNextOutputThumbJob() {
  if (outputThumbRunning || !outputThumbQueue.length) {
    return;
  }
  var id = outputThumbQueue.shift();
  if (outputThumbAlreadyTried(id)) {
    runNextOutputThumbJob();
    return;
  }
  outputThumbRunning = true;
  var iframe = document.createElement("iframe");
  iframe.style.position = "fixed";
  iframe.style.width = "400px";
  iframe.style.height = "360px";
  iframe.style.left = "-10000px";
  iframe.style.top = "-10000px";
  iframe.style.opacity = "0";
  iframe.style.pointerEvents = "none";
  iframe.style.border = "0";
  iframe.setAttribute("aria-hidden", "true");
  iframe.src = "viewer_splat.php?id=" + encodeURIComponent(id);
  document.body.appendChild(iframe);
  setTimeout(function() {
    markOutputThumbTried(id);
    if (iframe.parentNode) {
      iframe.parentNode.removeChild(iframe);
    }
    outputThumbRunning = false;
    runNextOutputThumbJob();
  }, 13000);
}

function refreshActiveJobs() {
  if (jobRefreshInFlight) {
    return;
  }
  jobRefreshInFlight = true;
  $.getJSON("api.php?mode=jobs_delta&" + window.location.search.replace(/^\?/, ""), function(jd) {
    if (jd && jd.failure_reasons) {
      jobFailureReasons = jd.failure_reasons;
    }
    if (jd && $.isArray(jd.rows)) {
      $.each(jd.rows, function(_, row) {
        updateJobRow(row);
      });
    }
    if (jd && $.isArray(jd.thumb_queue)) {
      $.each(jd.thumb_queue, function(_, id) {
        enqueueOutputThumbJob(id);
      });
    }
    scanMissingOutputThumbs();
    var hasActiveJobs = !!(jd && jd.has_active_jobs);
    $(".gs-wrap").attr("data-has-active-jobs", hasActiveJobs ? "1" : "0");
    if (!hasActiveJobs && jobRefreshTimer) {
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
  if (jobRefreshTimer) {
    return;
  }
  jobRefreshTimer = setInterval(refreshActiveJobs, 2000);
  refreshActiveJobs();
}

var initialUploadFormState = null;

function getUploadFormState() {
  return JSON.stringify({
    title: $("#title").val() || "",
    email: $("#email").val() || "",
    lon: $("#lon").val() || "",
    lat: $("#lat").val() || "",
    alt: $("#alt").val() || "",
    gdcode: $("#gdcode").val() || "",
    file: selectedVideoFile ? getUploadFileName(selectedVideoFile) : ""
  });
}

function isUploadFormDirty() {
  if (initialUploadFormState === null) {
    initialUploadFormState = getUploadFormState();
  }
  return getUploadFormState() !== initialUploadFormState;
}

$(function() {
  initialUploadFormState = getUploadFormState();
  highlightUploadedJob();
  $.each(initialThumbQueue || [], function(_, id) {
    enqueueOutputThumbJob(id);
  });
  scanMissingOutputThumbs();
  startActiveJobRefresh();
});

$("#captchaImage").on("click", refreshCaptchaImage);

$("#closeUploadProgress").on("click", function() {
  $("#uploadProgressDialog").attr("hidden", "hidden");
});

var selectedVideoFile = null;
var fileInput = $("#upfile");
var videoDropZone = $("#videoDropZone");
var isUploading = false;

function getUploadFileName(file) {
  var name = file.name || "";
  if (/\.mp4$/i.test(name)) {
    return name;
  }
  if (/\.zip$/i.test(name)) {
    return name;
  }
  if (file.type === "video/mp4") {
    return "clipboard-video.mp4";
  }
  if (file.type === "application/zip" || file.type === "application/x-zip-compressed") {
    return "clipboard-images.zip";
  }
  return name || "clipboard-video.mp4";
}

function isUploadSourceFile(file) {
  return !!file && (
    /\.mp4$/i.test(file.name || "") ||
    /\.zip$/i.test(file.name || "") ||
    file.type === "video/mp4" ||
    file.type === "application/zip" ||
    file.type === "application/x-zip-compressed"
  );
}

function formatUploadSeconds(uploadStartedAt) {
  var seconds = Math.max(0, Math.round((Date.now() - uploadStartedAt) / 1000));
  if (seconds >= 60) {
    return Math.floor(seconds / 60) + " 分 " + (seconds % 60) + " 秒";
  }
  return seconds + " 秒";
}

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

function setUploadBusy(isBusy) {
  isUploading = isBusy;
  $("#uploadForm button[type=submit]").prop("disabled", isBusy);
}

function resetUploadBusy() {
  setUploadBusy(false);
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

function setSelectedVideoFile(file) {
  if (!file) {
    return false;
  }
  if (!isUploadSourceFile(file)) {
    $("#uploadStatus").text("請選擇 MP4 影片或 ZIP 圖片包。");
    return false;
  }
  selectedVideoFile = file;
  if (typeof DataTransfer !== "undefined") {
    try {
      var transfer = new DataTransfer();
      transfer.items.add(file);
      fileInput[0].files = transfer.files;
    } catch (err) {
      // Some browsers expose DataTransfer but disallow assigning files.
    }
  }
  $("#selectedVideoName").text(getUploadFileName(file));
  return true;
}

fileInput.on("change", function() {
  if (this.files && this.files.length > 0) {
    setSelectedVideoFile(this.files[0]);
  }
});

videoDropZone.on("click", function() {
  this.focus();
});

videoDropZone.on("dragover", function(e) {
  e.preventDefault();
  e.stopPropagation();
  videoDropZone.addClass("is-active");
});

videoDropZone.on("dragleave blur", function() {
  videoDropZone.removeClass("is-active");
});

videoDropZone.on("drop", function(e) {
  e.preventDefault();
  e.stopPropagation();
  videoDropZone.removeClass("is-active");
  var files = e.originalEvent.dataTransfer.files;
  if (files && files.length > 0) {
    setSelectedVideoFile(files[0]);
  }
});

videoDropZone.on("paste", function(e) {
  var clipboardData = e.originalEvent.clipboardData;
  if (!clipboardData || !clipboardData.items) {
    return;
  }
  for (var i = 0; i < clipboardData.items.length; i++) {
    if (clipboardData.items[i].kind === "file") {
      var file = clipboardData.items[i].getAsFile();
      if (file && setSelectedVideoFile(file)) {
        e.preventDefault();
        break;
      }
    }
  }
});

$("#uploadForm").on("submit", function(e) {
  e.preventDefault();
  if (isUploading) {
    return;
  }
  setUploadBusy(true);
  var uploadFile = selectedVideoFile;
  if (!isUploadSourceFile(uploadFile)) {
    resetUploadBusy();
    $("#uploadStatus").text("請選擇 MP4 影片或 ZIP 圖片包。");
    return;
  }
  selectedVideoFile = uploadFile;

  $("#uploadStatus").text("正在檢查驗證碼...");
  $.ajax({
    url: "api.php?mode=checkGD",
    method: "POST",
    data: { gdcode: $("#gdcode").val() },
    success: function(data) {
      if ($.trim(data) !== "OK") {
        resetUploadBusy();
        $("#uploadStatus").text("驗證碼錯誤。");
        refreshCaptchaImage();
        return;
      }

      $("#uploadStatus").text("正在上傳...");
      var uploadStartedAt = Date.now();
      var uploadTimer = null;
      try {
        var formData = new FormData(this);
        formData.set("upfile", selectedVideoFile, getUploadFileName(selectedVideoFile));
        showUploadProgressDialog(selectedVideoFile);
        uploadTimer = setInterval(function() {
          $("#uploadProgressElapsed").text(formatUploadSeconds(uploadStartedAt));
        }, 500);
      } catch (err) {
        resetUploadBusy();
        var setupReason = err && err.message ? err.message : "上傳初始化失敗";
        $("#uploadStatus").text(setupReason);
        finishUploadProgress(setupReason, true);
        refreshCaptchaImage();
        return;
      }
      uploadWithProgress(formData)
        .then(function(jd) {
          if (uploadTimer !== null) clearInterval(uploadTimer);
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
          resetUploadBusy();
          var reason = jd.reason || "上傳失敗";
          $("#uploadStatus").text(reason);
          finishUploadProgress(reason, true);
          refreshCaptchaImage();
        })
        .catch(function(err) {
          if (uploadTimer !== null) clearInterval(uploadTimer);
          resetUploadBusy();
          var reason = err && err.message ? err.message : "上傳失敗";
          $("#uploadStatus").text(reason);
          finishUploadProgress(reason, true);
          refreshCaptchaImage();
        });
    }.bind(this),
    error: function() {
      resetUploadBusy();
      $("#uploadStatus").text("驗證碼錯誤。");
      refreshCaptchaImage();
    }
  });
});
</script>
</body></html>
