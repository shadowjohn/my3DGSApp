from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_shared_frontend_js_opens_viewer_and_refreshes_logs():
    text = (ROOT / "js" / "function.js").read_text()

    assert "function openSplatViewer" in text
    assert "viewer_splat.php?id=" in text
    assert "encodeURIComponent(id)" in text
    assert "viewer_splat.html?src=" not in text
    assert "function refreshJobLog" in text
    assert "api.php?mode=get_log&id=" in text
    assert "$(targetSelector).text(jd.log || \"\")" in text


def test_index_page_has_upload_form_captcha_and_job_cards_and_thumb_queue():
    text = (ROOT / "index.php").read_text()

    assert 'require __DIR__ . "/../inc/config.php";' in text
    assert '$include_mode = "easymap7115";' in text
    assert "gs_job_list_state(15)" in text
    assert "LIMIT 50" not in text
    job_view = (ROOT / "job_view.php").read_text()
    api = (ROOT / "api.php").read_text()
    assert "GS_DEFAULT_ESTIMATE_SECONDS" in job_view
    assert "function gs_format_duration" in job_view
    assert "function gs_elapsed_seconds" in job_view
    assert "function gs_average_completed_duration" in job_view
    assert "function gs_job_timing_summary" in job_view
    assert "function gs_short_failure_reason" in job_view
    assert "function gs_upload_time_label" in job_view
    assert "function gs_pipeline_stage_map" in job_view
    assert "function gs_job_progress" in job_view
    assert "function gs_pipeline_mode_label" in job_view
    assert "'fast'=>'快速'" in job_view
    assert "'qa'=>'驗證'" in job_view
    assert "'premium'=>'進階'" in job_view
    assert "等待覆核" in job_view
    assert "candidate frame count is lower than 8" in job_view
    assert "可用影格不足" in job_view
    assert '<script src="js/function.js"></script>' in text
    assert 'action="api.php?mode=upload"' in text
    assert 'name="upfile"' in text
    assert 'accept=".mp4,.zip"' in text
    assert 'name="gdcode"' in text
    assert '/gd.php?_t=' in text
    assert 'api.php?mode=checkGD' in text
    assert "openSplatViewer" in text or "openSplatViewer" in job_view
    assert 'data-viewer-page="viewer_splat.php"' in text
    assert "viewer_splat.html?src=" not in text
    assert "openSplatViewer(<?=$id;?>)" in job_view
    assert "$isReady = (string)($row['status'] ?? '') === '2';" in job_view
    assert "splat.clean.ply" in job_view
    assert "$hasSplat = $isReady && is_file" in job_view
    assert 'href="map.php?id=' not in text
    assert "html, html body { background:#0f1722;" in text
    assert ".gs-panel{border:1px solid #334155;" in text
    assert ".gs-panel label{color:#dbe7f3;" in text
    assert "input[type=file].form-control{background:#0f1722;" in text
    assert ".gs-job-list{display:grid;" in text
    assert ".gs-job-card{display:grid;grid-template-columns:200px minmax(0,1fr);" in text
    assert ".gs-job-body{display:grid;" in text
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
    assert "<title>Focusit Studio</title>" in text
    assert "<h2>Focusit Studio</h2>" in text
    assert "建立專案，選擇重建模式，再交給背景排程處理" in text
    assert "<label>專案名稱</label>" in text
    assert "<label>電子信箱</label>" in text
    assert "<label>MP4 影片 / ZIP 圖片包</label>" in text
    assert "<label>重建模式</label>" in text
    assert 'name="pipeline_mode"' in text
    assert '<option value="fast" selected>快速</option>' in text
    assert '<option value="qa">驗證</option>' in text
    assert '<option value="premium">進階</option>' in text
    assert 'name="engine"' not in text
    assert "OpenMVS" not in text
    assert "Nerfstudio splatfacto" not in text
    assert "<label>經度</label>" in text
    assert "<label>緯度</label>" in text
    assert "<label>高度</label>" in text
    assert "<label>驗證碼</label>" in text
    assert ">更新<" not in text
    assert 'id="refreshCaptcha"' not in text
    assert '$("#captchaImage").on("click", refreshCaptchaImage);' in text
    assert ">建立專案<" in text
    assert '<div class="gs-job-list">' in text
    assert '<article class="gs-job-card" id="job-<?=$id;?>" data-job-id="<?=$id;?>">' in text
    assert 'class="gs-job-thumb gs-thumb-cell" data-refresh-cell="thumb"' in text
    assert '<div class="gs-job-section gs-job-title">' in text
    assert '<div class="gs-job-section gs-status-cell" data-refresh-cell="status">' in text
    assert '<div class="gs-job-section" data-refresh-cell="timing">' in text
    assert '<div class="gs-job-section gs-frame-cell" data-refresh-cell="frames">' in text
    assert '<div class="gs-job-section gs-actions-cell" data-refresh-cell="actions">' in text
    assert '<table class="table table-striped table-hover gs-table">' not in text
    assert 'data-refresh-cell="thumb"' in text
    assert "gs_job_thumbnail_cell_html" in text
    assert "gs-thumb-pair" in job_view
    assert "原始" in job_view
    assert "成果" in job_view
    assert "output_{$id}.png" in job_view
    assert "function gs_job_needs_output_thumb" in job_view
    needs_thumb_block = job_view[job_view.index("function gs_job_needs_output_thumb"):job_view.index("function gs_job_thumb_queue_payload")]
    assert "gs_splat_artifact_for_job($id)" in needs_thumb_block
    assert "gs_job_splat_path($id)" not in needs_thumb_block
    assert "function gs_job_thumb_queue_payload" in job_view
    assert 'data-missing-output-thumb="1"' in job_view
    assert "gs_job_thumb_queue_payload($rows, 3)" in job_view
    assert "'thumb_queue'" in job_view
    assert "case 'jobs_delta':" in api
    assert "'thumb_queue'=>$payload['thumb_queue']" in api
    assert api.count("case 'save_thumb':") == 1
    save_thumb_block = api[api.index("case 'save_thumb':"):api.index("case 'save_transform':")]
    assert "`status`" in save_thumb_block
    assert "(string)($rows[0]['status'] ?? '') !== '2'" in save_thumb_block
    assert "is_file($thumbPath)" in save_thumb_block
    assert "gs_json(['status'=>'OK','url'=>gs_job_thumb_cache_url($id)])" in save_thumb_block
    assert "gs_splat_artifact_for_job($id)" in save_thumb_block
    assert "gs_job_splat_path($id)" not in save_thumb_block
    assert "gs_delete_thumb_cache($id)" not in save_thumb_block
    assert "function initGaussianSplatThumbs" not in text
    assert "saveGaussianSplatThumb" not in text
    assert 'name="q"' in job_view
    assert 'list="gsJobSearchList"' in job_view
    assert "gs_job_search_form_html" in text
    assert "gs_job_pagination_html" in text
    assert "每頁 15 筆" in job_view
    assert "<th>Splat 檔</th>" not in text
    assert "<th>地圖</th>" not in text
    assert "目前沒有轉檔工作。" in text
    assert "粗估總長" in job_view
    assert "已花" in job_view
    assert "預估剩" in job_view
    assert "current_stage_label" in job_view
    assert "duration_seconds" in job_view
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
    assert 'role="group"' in text
    assert 'aria-label="影片或圖片 ZIP 拖放與貼上區"' in text
    assert 'data-paste-focus="true"' in text
    assert "拖放 / 貼上 MP4 或 ZIP" in text
    assert "可拖放 MP4，或 ZIP 圖片包" in text
    assert "function setSelectedVideoFile(file)" in text
    assert "function isUploadSourceFile(file)" in text
    assert 'file.type === "video/mp4"' in text
    assert 'if (/\\.mp4$/i.test(name)) {' in text
    assert 'if (/\\.zip$/i.test(name)) {' in text
    assert 'if (file.type === "video/mp4") {\n    return "clipboard-video.mp4";\n  }' in text
    assert 'if (!isUploadSourceFile(file)) {\n    $("#uploadStatus").text("請選擇 MP4 影片或 ZIP 圖片包。");\n    return false;\n  }' in text
    assert 'typeof DataTransfer !== "undefined"' in text
    assert "new DataTransfer()" in text
    assert 'videoDropZone.on("click", function() {\n  this.focus();\n});' in text
    assert 'fileInput.trigger("click")' not in text
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
    assert "function updateUploadProgress" in text
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
    assert "var jobFailureReasons = <?=json_encode($failureReasons, JSON_UNESCAPED_UNICODE | JSON_HEX_TAG | JSON_HEX_APOS | JSON_HEX_QUOT | JSON_HEX_AMP);?>;" in text
    assert "JSON_UNESCAPED_UNICODE" in text
    assert "JSON_HEX_TAG" in text
    assert "JSON_HEX_APOS" in text
    assert "JSON_HEX_QUOT" in text
    assert "JSON_HEX_AMP" in text
    assert "function openReasonDialog" in text
    assert "id=\"jobReasonDialog\"" in text
    assert "id=\"jobReasonDialogBody\"" in text
    assert ">原因<" in job_view
    assert ">檢視<" in job_view
    assert ">定位<" not in text
    assert "data-has-active-jobs" in text
    assert 'data-refresh-cell="status"' in text
    assert 'data-refresh-cell="timing"' in text
    assert 'data-refresh-cell="frames"' in text
    assert 'data-refresh-cell="actions"' in text
    assert "var initialThumbQueue =" in text
    assert "sessionStorage" in text
    assert "function scanMissingOutputThumbs" in text
    assert "function enqueueOutputThumbJob" in text
    assert "function runNextOutputThumbJob" in text
    assert "viewer_splat.php?id=" in text
    assert "document.createElement(\"iframe\")" in text
    assert 'iframe.style.display = "none"' not in text
    assert 'iframe.style.position = "fixed"' in text
    assert 'iframe.style.width = "400px"' in text
    assert 'iframe.style.height = "360px"' in text
    assert 'iframe.style.left = "-10000px"' in text
    assert 'iframe.style.opacity = "0"' in text
    assert 'iframe.style.pointerEvents = "none"' in text
    assert "setTimeout(function() {" in text
    assert "scanMissingOutputThumbs();" in text
    update_row_block = text[text.index("function updateJobRow(row)"):text.index("var outputThumbQueue")]
    assert "enqueueOutputThumbJob(row.id);" not in update_row_block
    thumb_runner_block = text[text.index("function runNextOutputThumbJob()"):text.index("function refreshActiveJobs()")]
    assert thumb_runner_block.index("document.body.appendChild(iframe);") < thumb_runner_block.index("markOutputThumbTried(id);")
    assert "function startActiveJobRefresh" in text
    assert "function refreshActiveJobs" in text
    assert "function updateJobRow" in text
    assert "function updateJobCell" in text
    assert "jobRefreshTimer" in text
    assert "jobRefreshInFlight" in text
    assert 'api.php?mode=jobs_delta' in text
    assert '$.getJSON("api.php?mode=jobs_delta&" + window.location.search.replace(/^\\?/, "")' in text
    assert 'updateJobCell($row, "status", row.status_html)' in text
    assert 'updateJobCell($row, "timing", row.timing_html)' in text
    assert 'updateJobCell($row, "frames", row.frames_html)' in text
    assert 'updateJobCell($row, "actions", row.actions_html)' in text
    assert "setInterval(refreshActiveJobs, 2000)" in text
    active_refresh_block = text[text.index("var jobRefreshTimer"):text.index("var initialUploadFormState")]
    assert "location.replace" not in active_refresh_block
    assert "location.reload" not in active_refresh_block
    assert 'document.title = "Focusit Studio";' in text


def test_job_view_exposes_waiting_override_and_confidence_gate_state():
    text = (ROOT / "job_view.php").read_text()

    assert "等待覆核" in text
    assert "function gs_confidence_gate_from_row" in text
    assert "function gs_pipeline_mode_label" in text
    assert "function gs_job_list_state" in (ROOT / "job_view.php").read_text()
    assert "GS_LIST_PER_PAGE" in (ROOT / "job_view.php").read_text()
    assert "function gs_job_search_suggestions" in (ROOT / "job_view.php").read_text()
    assert "'fast'=>'快速'" in text
    assert "'qa'=>'驗證'" in text
    assert "'premium'=>'進階'" in text
    assert "function gs_confidence_summary_from_row" in text
    assert "function gs_confidence_risk_count" in text
    assert "confidence_risk_count" in text
    assert "confidence_recommendation_count" in text
    assert "confidence_needs_override" in text
    assert "confidence_override_status" in text
    assert "confidence_updated_at" in text
    assert "trim((string)($row['confidence_updated_at'] ?? '')) !== ''" in text
    assert "function gs_job_confidence_report_url" in text
    assert "function gs_job_confidence_gate_url" in text
    assert "function gs_job_artifact_links" in text
    assert "function gs_splat_artifact_for_job" in text
    assert "function gs_splat_artifact_from_uuid" in text
    assert "function gs_splat_artifact_uuid" in text
    assert "engine_contract.json" in text
    assert "delivery_manifest.json" in text
    assert "validation/validation_report.json" in text
    assert "validation/qa_validation_report.json" in text
    assert "evidence/appearance_summary.json" in text
    assert "compare/compare_report.json" in text
    assert "confidence_gate_json" in text
    assert "confidence_score" in text
    assert "confidence_grade" in text
    assert "confidence_decision" in text
    assert "confidence_effective_decision" in text
    assert "recommendations" in text
    assert "risks" in text
    assert "confidence_gate" in text
    assert "信心" in text


def test_admin_page_requires_auth_and_exposes_job_actions():
    text = (ROOT / "admin.php").read_text()

    assert 'require __DIR__ . "/../inc/config.php";' in text
    assert 'require "{$base_dir}/inc/checkpassword.php";' in text
    assert 'gs_job_list_state(15, "{$orderBy} {$sortDir}, `id` DESC")' in text
    assert "gs_job_search_form_html" in text
    assert "gs_job_pagination_html" in text
    assert "function gs_admin_format_duration" in text
    assert "function gs_admin_short_failure_reason" in text
    assert "function gs_admin_timing_rows" in text
    assert '<script src="js/function.js"></script>' in text
    assert "qa_report.json" in text
    assert ">qa_report.json<" not in text
    assert ">品管<" in text
    assert "timing_report.json" in text
    assert "confirmAdminAction" in text
    assert "openReconvertDialog" in text
    assert "closeReconvertDialog" in text
    assert "submitReconvert" in text
    assert "reconvertDialog" in text
    assert "jobAction" in text
    assert "api.php?mode=admin_action" in text
    assert "reconvert" in text
    assert "confidence_override" in text
    assert "abort" in text
    assert "$sortMap" in text
    assert "confidence_score" in text
    assert "confidence_grade" in text
    assert "confidence_decision" in text
    assert "confidence_needs_override" in text
    assert "confidence_override_status" in text
    assert "function gs_admin_status_class" in text
    assert "gs-admin-list" in text
    assert "gs-admin-job" in text
    assert "gs-admin-job-head" in text
    assert "gs-admin-job-body" in text
    assert "gs-admin-section-title" in text
    assert "工作列表" in text
    assert "排序：" in text
    assert '<span class="gs-admin-mode">' in text
    assert "建議執行" in text
    assert "可執行有風險" in text
    assert "不建議重建" in text
    assert "風險" in text
    assert "建議" in text
    assert "gs_admin_sort_link" in text
    assert "gs-admin-confidence-cell" in text
    assert "gs_admin_confidence_summary_from_row" in text
    assert "openSplatViewer(<?=$id;?>)" in text
    assert "viewer_splat.html?src=" not in text
    assert "信心" in text
    assert "等級" in text
    assert "決策" in text
    assert "覆核" in text
    assert "覆核狀態" in text
    assert "Confidence Preview" in text
    assert "renderConfidencePreview" in text
    assert "gs-confidence-panel" in text
    assert "gs-confidence-badge-run" in text
    assert "gs-confidence-badge-warn" in text
    assert "gs-confidence-badge-hold" in text
    assert "gs-confidence-badge-reject" in text
    assert "建議執行" in text
    assert "可執行但有風險" in text
    assert "等待覆核" in text
    assert "不建議重建" in text
    assert "Risks" in text
    assert "Recommendations" in text
    assert "confidence_report.json" in text
    assert "confidence_gate.json" in text
    assert "artifactPreviewPanel" in text
    assert "renderArtifactPreview" in text
    assert "Project Detail" in text
    assert "Pipeline / Engine Runs / Artifacts / Validation / Delivery" in text
    assert "escapeHtml" in text
    assert "$isRunning = (string)$r['status'] === '1';" in text
    assert "$isHeld = (string)$r['status'] === '5';" in text
    assert "$canAbort = in_array((string)$r['status'], ['0','1'], true);" in text
    assert "$canReconvert = in_array((string)$r['status'], ['2','3','4','5'], true);" in text
    assert "<?php if($canReconvert): ?>" in text
    assert "覆核啟動" in text
    assert "function openReconvertDialog" in text
    assert "function submitReconvert" in text
    assert "<?php if($canAbort): ?>" in text
    assert "$hasSplat = $isReady && is_file" in text
    assert "$progress = gs_job_progress($r);" in text
    assert "<?php if($progress['active']): ?>" in text
    assert ".gs-admin-progress" in text
    assert "$progress['label']" in text
    assert "<?=htmlspecialchars((string)($progress['percent'] ?? 0), ENT_QUOTES);?>%" in text
    assert "style=\"width:<?=min(100, max(0, (int)$progress['percent']));?>%;\"" in text
    assert "splat.clean.ply" in text
    assert "openJobDetail" in text
    assert "jobLogDialog" in text
    assert "jobLogDialogBody" in text
    assert "artifact_links" in (ROOT / "api.php").read_text()
    assert "JOB_LOG_REFRESH_MS = 2000" in text
    assert "jobLogRefreshTimer" in text
    assert "setInterval(function() {" in text
    assert "clearInterval(jobLogRefreshTimer)" in text
    assert "refreshJobDetail(id, false)" in text
    assert "isJobLogPinnedToBottom" in text
    assert 'parts.push("模式：" + (jd.pipeline_mode_label || "快速"));' in text
    assert "body.scrollTop = body.scrollHeight" in text
    assert ".gs-log-terminal" in text
    assert ".gs-log-dialog-panel{width:min(980px,calc(100vw - 32px));max-height:calc(100vh - 48px);display:flex;flex-direction:column;" in text
    assert ".gs-log-dialog-head{flex:0 0 auto;" in text
    assert ".gs-confidence-panel{flex:0 0 auto;" in text
    assert "flex:1 1 auto;min-height:0;max-height:none;overflow:auto" in text
    assert "background:#020617" in text
    assert "color:#3cff71" in text
    assert "white-space:pre-wrap" in text
    assert "font-size:14px" in text
    assert "詳細紀錄" in text
    assert "$shortReason = gs_admin_short_failure_reason" in text
    assert "htmlspecialchars($shortReason" in text
    assert "<title>Gaussian Splat 轉檔後台</title>" in text
    assert "Gaussian Splat 轉檔後台" in text
    assert "回前台" in text
    assert ".gs-admin{--panel:#111b2a;" in text
    assert "max-width:1440px;" in text
    assert ".gs-admin-header{display:flex;" in text
    assert "justify-content:space-between" in text
    assert ".gs-admin-back-btn" in text
    assert 'class="btn btn-default gs-admin-back-btn" href="index.php">回前台</a>' in text
    assert ".gs-admin-toolbar{display:flex;" in text
    assert ".gs-admin-actions{display:flex;flex-wrap:wrap;" in text
    assert ".gs-admin-job-body{display:grid;" in text
    assert ".gs-admin-metrics{display:grid;" in text
    assert ".gs-admin-stage-row{display:grid;" in text
    assert ".gs-admin-duration{line-height:1.7;" in text
    assert ".gs-admin-stage-list" in text
    assert ".gs-admin-qa-link" in text
    assert '<article class="gs-admin-job gs-admin-job-<?=$statusClass;?>">' in text
    assert '<div class="gs-admin-section-title">狀態</div>' in text
    assert '<div class="gs-admin-section-title">信心</div>' in text
    assert '<div class="gs-admin-section-title">耗時與輸出</div>' in text
    assert '<div class="gs-admin-section-title">階段明細</div>' in text
    assert "Splat MB" in text
    assert ">重轉<" in text
    assert ">中止<" in text
    assert "onclick=\"openReconvertDialog(<?=$id;?>" in text
    assert "onclick=\"confirmAdminAction(<?=$id;?>,'abort','中止')\"" in text
    assert 'payload.pipeline_mode = mode;' in text
    assert 'if (!/^(fast|qa|premium)$/.test(mode))' in text
    assert "重轉設定" in text
    assert "來源影片" in text
    assert "重轉方式" in text
    assert "同編號重轉" in text
    assert "新建編號重轉" in text
    assert "開始重轉" in text
    assert 'payload.reconvert_target = target;' in text
    assert 'jobAction(reconvertJobId, "reconvert", null, mode, target);' in text
    assert 'if(!confirm("確定要" + label + "工作 #" + id + "？")) return;' in text
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
