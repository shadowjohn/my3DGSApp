<?php
  require __DIR__ . "/../inc/config.php";
  require_once __DIR__ . "/job_view.php";

  $isLoggedIn = !empty($_SESSION["login_user"]);
  $listState = ovm_job_list_state(15);
  $rows = $listState['rows'];
  $estimateSeconds = ovm_average_completed_duration($rows);
  $hasActiveJobs = false;
  $failureReasons = [];
  foreach($rows as $row){
      if(in_array((string)($row['status'] ?? ''), ['0','1'], true) || ovm_job_has_active_products($row['id'] ?? 0)) $hasActiveJobs = true;
      $fullReason = trim((string)($row['reason'] ?? ''));
      if($fullReason !== '') $failureReasons[(string)$row['id']] = ovm_json_safe_text($fullReason);
  }

  $include_mode = "easymap7115|threejs155";
  require "{$base_dir}/html.php";
  require "{$base_dir}/head.php";
?>
<script src="js/function.js"></script>
<script type="module">
  import * as THREE from "three";
  import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
  import { DRACOLoader } from "three/addons/loaders/DRACOLoader.js";
  import { KTX2Loader } from "three/addons/loaders/KTX2Loader.js";
  import { MeshoptDecoder } from "three/addons/libs/meshopt_decoder.module.js";
  window.THREE = { ...THREE, GLTFLoader, DRACOLoader, KTX2Loader, MeshoptDecoder };
</script>
<title>OpenMVS 轉檔</title>
<?php
  require "{$base_dir}/head_end.php";
  require "{$base_dir}/body.php";
  require "{$base_dir}/top.php";
?>
<style nonce="ovm">
  html, html body { background:#111827; color:#e5edf7; }
  .ovm-wrap{max-width:1420px;margin:0 auto;padding:28px 20px 42px;}
  .ovm-head{display:flex;align-items:flex-end;justify-content:space-between;gap:12px;margin-bottom:16px;}
  .ovm-head h2{margin:0;font-weight:700;color:#f8fafc;letter-spacing:0;}
  .ovm-muted{color:#9fb0c3;font-size:12px;}
  .ovm-panel{border:1px solid #344255;border-radius:6px;padding:18px;margin-bottom:18px;background:#182233;box-shadow:0 12px 28px rgba(0,0,0,.26);}
  .ovm-panel label{color:#dbe7f3;font-weight:600;}
  .ovm-panel .form-control{background:#0f1722;color:#f8fafc;border-color:#3b4a5f;box-shadow:none;}
  .ovm-panel .form-control:focus{border-color:#38bdf8;box-shadow:0 0 0 2px rgba(56,189,248,.18);}
  input[type=file].form-control{background:#0f1722;color:#e5edf7;border-color:#3b4a5f;height:auto;}
  input[type=file].form-control::file-selector-button{background:#25364a;border:0;border-right:1px solid #3b4a5f;color:#f8fafc;margin:-6px 10px -6px -12px;padding:6px 12px;}
  .ovm-dropzone{margin-top:10px;border:1px dashed #5a718b;border-radius:6px;background:#111b2a;color:#dbe7f3;padding:14px;outline:none;}
  .ovm-dropzone.is-active,.ovm-dropzone:focus{border-color:#38bdf8;box-shadow:0 0 0 2px rgba(56,189,248,.22);}
  .ovm-selected-file{margin-top:8px;color:#f8fafc;font-size:13px;}
  .ovm-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;}
  .ovm-captcha{display:flex;align-items:center;gap:10px;flex-wrap:wrap;}
  .ovm-captcha img{cursor:pointer;border:1px solid #3b4a5f;border-radius:4px;background:#020617;}
  .ovm-table{background:#111b2a;border:1px solid #334155;}
  .ovm-table td,.ovm-table th{vertical-align:middle!important;}
  .ovm-table > thead > tr > th{background:#223047;color:#f8fafc;border-color:#223047;font-weight:600;}
  .ovm-table > tbody > tr > td{border-color:#29384d;color:#dbe7f3;}
  .ovm-table.table-striped > tbody > tr:nth-of-type(odd){background:#162235;}
  .ovm-table.table-hover > tbody > tr:hover{background:#12344a;}
  .ovm-form-actions{display:flex;align-items:center;justify-content:flex-end;gap:10px;}
	  .ovm-status-main{font-size:15px;font-weight:600;color:#f8fafc;}
	  .ovm-quality{display:inline-block;min-width:48px;border-radius:4px;padding:2px 6px;font-size:12px;font-weight:700;text-align:center;}
	  .ovm-quality-5{background:#166534;color:#dcfce7;}
	  .ovm-quality-4{background:#0f766e;color:#ccfbf1;}
	  .ovm-quality-3{background:#854d0e;color:#fef3c7;}
	  .ovm-quality-2{background:#9a3412;color:#ffedd5;}
	  .ovm-quality-1{background:#991b1b;color:#fee2e2;}
	  .ovm-progress-mini{height:7px;border-radius:999px;background:#0b1220;border:1px solid #334155;overflow:hidden;margin-top:7px;}
  .ovm-progress-mini span{display:block;height:100%;background:#38bdf8;}
  .ovm-actions-cell{min-width:150px;white-space:nowrap;}
  .ovm-actions-cell .btn{margin:2px 2px 2px 0;}
  .ovm-actions-cell .btn[disabled]{opacity:.55;cursor:not-allowed;}
  .ovm-list-tools{display:grid;grid-template-columns:auto minmax(240px,1fr) auto auto auto;gap:10px;align-items:center;margin:0 0 14px;padding:12px;border:1px solid #334155;border-radius:6px;background:#111b2a;}
  .ovm-list-tools label{margin:0;color:#dbe7f3;font-weight:700;}
  .ovm-list-tools .form-control{background:#0f1722;color:#f8fafc;border-color:#3b4a5f;box-shadow:none;}
  .ovm-list-count{color:#9fb0c3;font-size:12px;white-space:nowrap;}
  .ovm-pagination{display:flex;justify-content:center;align-items:center;gap:10px;margin-top:14px;color:#cbd5e1;}
  .ovm-pagination .disabled{pointer-events:none;opacity:.45;}
  .ovm-job-list{display:grid;gap:12px;}
  .ovm-job-card{border:1px solid #334155;border-radius:6px;background:#111b2a;overflow:hidden;}
  .ovm-job-card-head{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:14px;align-items:start;padding:14px 16px;background:#18263b;border-bottom:1px solid #29384d;}
  .ovm-job-main{display:grid;grid-template-columns:200px minmax(0,1fr);gap:16px;align-items:start;min-width:0;}
  .ovm-job-title-row{display:flex;align-items:center;gap:10px;min-width:0;}
  .ovm-job-id{flex:0 0 auto;color:#bfdbfe;font-weight:700;font-variant-numeric:tabular-nums;}
  .ovm-job-title{margin:0;color:#f8fafc;font-size:19px;line-height:1.35;font-weight:700;text-align:left;overflow-wrap:anywhere;}
  .ovm-job-card-body{display:grid;grid-template-columns:minmax(180px,.85fr) minmax(220px,1fr) minmax(190px,.85fr) minmax(220px,1fr);gap:16px;padding:14px 16px;}
  .ovm-job-section{min-width:0;}
  .ovm-job-section-title{margin-bottom:7px;color:#cbd5e1;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;}
  .ovm-job-section [data-refresh-cell]{overflow-wrap:anywhere;}
  .ovm-job-actions{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:6px;max-width:420px;}
  .ovm-job-actions .btn{margin:0;white-space:nowrap;}
  .ovm-job-output{display:grid;gap:8px;}
  .ovm-product-list{display:grid;gap:6px;}
  .ovm-product-row{display:flex;align-items:center;gap:6px;flex-wrap:wrap;}
  .ovm-product-size{min-width:70px;color:#f8fafc;font-size:12px;font-weight:700;}
  .ovm-job-metric-label{display:block;color:#9fb0c3;font-size:12px;}
  .ovm-job-metric-value{display:block;color:#f8fafc;font-size:15px;font-variant-numeric:tabular-nums;overflow-wrap:anywhere;}
  .ovm-job-empty{padding:28px;text-align:center;color:#9fb0c3;border:1px solid #334155;border-radius:6px;background:#111b2a;}
  .ovm-quality-summary{max-width:360px;overflow-wrap:anywhere;}
  .ovm-thumb-cell{width:200px;}
  .ovm-thumb-pair{display:grid;grid-template-columns:1fr 1fr;gap:8px;width:200px;}
  .ovm-thumb-item{min-width:0;}
  .ovm-thumb-title{margin-bottom:5px;color:#9fb0c3;font-size:12px;font-weight:700;text-align:center;}
  .ovm-thumb-link{display:block;text-decoration:none;}
  .ovm-model-thumb{position:relative;width:96px;height:154px;overflow:hidden;border:1px solid rgba(125,211,252,.28);border-radius:4px;background:#07111f;box-shadow:inset 0 0 0 1px rgba(15,23,42,.82);}
  .ovm-model-thumb img,.ovm-model-thumb canvas{display:block;width:100%;height:100%;object-fit:cover;}
  .ovm-model-thumb span{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;padding:8px;color:#7dd3fc;font-size:13px;line-height:1.3;text-align:center;}
  .model-thumb-empty{border-color:rgba(148,163,184,.18);background:rgba(15,23,42,.56);}
  .model-thumb-empty span{color:#64748b;}
  .model-thumb-error span{color:#fca5a5;}
  .ovm-modal[hidden]{display:none;}
  .ovm-modal{position:fixed;z-index:10000;inset:0;background:rgba(2,6,23,.72);display:flex;align-items:center;justify-content:center;padding:20px;}
  .ovm-modal-card{width:min(620px,calc(100vw - 32px));border:1px solid #334155;border-radius:6px;background:#111b2a;color:#e5edf7;box-shadow:0 24px 80px rgba(0,0,0,.45);}
  .ovm-modal-head{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px 16px;border-bottom:1px solid #26364a;}
  .ovm-modal-head h3{margin:0;font-size:18px;color:#f8fafc;}
  .ovm-modal-body{padding:16px;}
  .ovm-diagnostics-body{max-height:72vh;overflow:auto;}
  .ovm-diagnostics-summary{max-height:24vh;overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere;margin-bottom:12px;}
  .ovm-diagnostics-body .ovm-table{margin-bottom:0;background:#0f1722;color:#dbe7f3;}
  .ovm-diagnostics-body .ovm-table > thead > tr > th{background:#223047!important;color:#f8fafc!important;border-color:#334155!important;}
  .ovm-diagnostics-body .ovm-table > tbody > tr > td{background:#0f1722!important;color:#dbe7f3!important;border-color:#29384d!important;}
  .ovm-diagnostics-body .ovm-table > tbody > tr:nth-of-type(odd) > td{background:#142033!important;}
  .ovm-upload-bar{height:16px;border:1px solid #334155;background:#020617;border-radius:999px;overflow:hidden;}
  .ovm-upload-bar span{display:block;height:100%;width:0;background:#38bdf8;transition:width .18s linear;}
  .ovm-upload-meta{display:grid;grid-template-columns:110px 1fr;gap:7px 10px;margin-top:14px;font-size:14px;}
  .ovm-reason-body{max-height:58vh;overflow:auto;background:#020617;color:#3cff71;border:1px solid #334155;border-radius:4px;padding:14px;font-size:14px;line-height:1.55;white-space:pre-wrap;}
  .ovm-wrap .btn-primary{background:#2563eb;border-color:#2563eb;color:#fff;}
  .ovm-wrap .btn-primary:hover,.ovm-wrap .btn-primary:focus{background:#1d4ed8;border-color:#1d4ed8;color:#fff;}
  .ovm-wrap .btn-default{background:#1d2a3a;border-color:#3b4a5f;color:#e5edf7;}
  .ovm-wrap .btn-default:hover,.ovm-wrap .btn-default:focus{background:#26364a;border-color:#5a718b;color:#fff;}
  .ovm-wrap .btn-success{background:#15803d;border-color:#15803d;color:#fff;}
  .ovm-wrap .btn-warning{background:#b45309;border-color:#b45309;color:#fff;}
  .ovm-wrap .btn-warning:hover,.ovm-wrap .btn-warning:focus{background:#92400e;border-color:#92400e;color:#fff;}
  .ovm-wrap .btn-danger{background:#b91c1c;border-color:#b91c1c;color:#fff;}
  .ovm-wrap .btn-danger:hover,.ovm-wrap .btn-danger:focus{background:#991b1b;border-color:#991b1b;color:#fff;}
  @media (max-width: 760px){
    .ovm-head{display:block;}
    .ovm-grid{grid-template-columns:1fr;}
    .ovm-job-card-head{display:block;}
    .ovm-list-tools{grid-template-columns:1fr;}
    .ovm-job-main{grid-template-columns:1fr;}
    .ovm-thumb-cell{width:100%;}
    .ovm-thumb-pair{width:100%;grid-template-columns:1fr 1fr;}
    .ovm-model-thumb{width:100%;height:150px;}
    .ovm-job-title-row{display:block;}
    .ovm-job-id{display:block;margin-bottom:3px;}
    .ovm-job-title{font-size:17px;text-align:left;}
    .ovm-job-actions{justify-content:flex-start;margin-top:12px;max-width:none;}
    .ovm-job-card-body{grid-template-columns:1fr;}
  }
  @media (min-width: 761px) and (max-width: 1080px){
    .ovm-job-card-body{grid-template-columns:repeat(2,minmax(0,1fr));}
  }
</style>

<div class="ovm-wrap" data-viewer-page="viewer_mesh.php" data-has-active-jobs="<?=$hasActiveJobs ? '1' : '0';?>">
  <div class="ovm-head">
    <div>
      <h2>OpenMVS 轉檔</h2>
      <div class="ovm-muted">MP4 影片或圖片 ZIP → COLMAP + OpenMVS → GLB 檢視</div>
    </div>
    <a class="btn btn-default" href="admin.php">後台</a>
  </div>

  <form id="uploadForm" method="post" enctype="multipart/form-data" action="api.php?mode=upload" class="ovm-panel">
    <div class="form-group">
      <label>標題</label>
      <input class="form-control" name="title" id="title" placeholder="例：辦公室物件掃描" required>
    </div>
    <div class="form-group">
      <label>電子信箱</label>
      <input class="form-control" name="email" id="email" placeholder="例：name@example.com">
    </div>
    <div class="form-group">
      <label>MP4 影片或圖片 ZIP</label>
      <input class="form-control" type="file" name="upfile" id="upfile" accept=".mp4,.zip" required>
      <div id="fileDropZone" class="ovm-dropzone" tabindex="0" role="group" aria-label="檔案拖放與貼上區">
        <strong>拖放 / 貼上檔案</strong>
        <div class="ovm-muted">可上傳 MP4，或包含 JPG/PNG/TIF 的 ZIP 圖片包。</div>
        <div id="selectedFileName" class="ovm-selected-file">尚未選擇檔案</div>
      </div>
    </div>
    <input type="hidden" name="mask_mode" id="mask_mode" value="none">
    <div class="form-group">
      <label>產出品質</label>
      <select class="form-control" name="quality_preset" id="quality_preset">
        <option value="fast">快速 fast</option>
        <option value="normal" selected>標準 normal（預設）</option>
        <option value="high">高品質 high</option>
      </select>
      <div class="ovm-muted">normal 是目前預設；fast 較快，high 會花較久時間。</div>
    </div>
    <div class="ovm-grid">
      <div>
        <label>經度</label>
        <input class="form-control" name="lon" id="lon" value="120.61022">
      </div>
      <div>
        <label>緯度</label>
        <input class="form-control" name="lat" id="lat" value="24.110946">
      </div>
      <div>
        <label>高度</label>
        <input class="form-control" name="alt" id="alt" value="72">
      </div>
    </div>
    <div class="form-group" style="margin-top:12px;">
      <label>驗證碼</label>
      <div class="ovm-captcha">
        <img id="captchaImage" src="/john_web/gd.php?_t=<?=time();?>" alt="驗證碼">
        <input class="form-control" style="width:160px;" maxlength="5" id="gdcode" name="gdcode" placeholder="輸入驗證碼" required>
      </div>
    </div>
    <div class="ovm-form-actions">
      <span id="uploadStatus" class="ovm-muted"></span>
      <button class="btn btn-primary" type="submit">上傳</button>
    </div>
  </form>

  <?=ovm_job_search_form_html($listState);?>

  <div class="ovm-job-list">
    <?php foreach($rows as $r):
        $id = (int)$r['id'];
        $timingSummary = ovm_job_timing_summary($r, $estimateSeconds);
        $progress = ovm_job_progress($r);
    ?>
      <article class="ovm-job-card" id="job-<?=$id;?>" data-job-id="<?=$id;?>">
        <header class="ovm-job-card-head">
          <div class="ovm-job-main">
            <div class="ovm-thumb-cell" data-refresh-cell="thumb"><?=ovm_job_thumbnail_cell_html($r);?></div>
            <div>
              <div class="ovm-job-title-row">
                <span class="ovm-job-id">#<?=$id;?></span>
                <h3 class="ovm-job-title"><?=htmlspecialchars($r['title'] ?: $r['orin_filename'], ENT_QUOTES);?></h3>
              </div>
              <div class="ovm-muted"><?=htmlspecialchars($r['orin_filename'] ?? '', ENT_QUOTES);?> · <?=htmlspecialchars(ovm_upload_time_label($r['c_datetime'] ?? ''), ENT_QUOTES);?></div>
            </div>
          </div>
          <div class="ovm-job-actions" data-refresh-cell="actions"><?=ovm_job_actions_cell_html($r);?></div>
        </header>
        <div class="ovm-job-card-body">
          <section class="ovm-job-section">
            <div class="ovm-job-section-title">狀態</div>
            <div data-refresh-cell="status">
              <div class="ovm-status-main"><?=htmlspecialchars(ovm_status_text($r['status']), ENT_QUOTES);?></div>
              <?php if($progress['active']): ?>
                <div class="ovm-muted"><?=htmlspecialchars((string)($progress['percent'] ?? 0), ENT_QUOTES);?>% · <?=htmlspecialchars((string)($progress['step'] ?? ''), ENT_QUOTES);?> · <?=htmlspecialchars((string)($progress['label'] ?? ''), ENT_QUOTES);?></div>
                <div class="ovm-progress-mini"><span style="width:<?=min(100, max(0, (int)$progress['percent']));?>%;"></span></div>
              <?php else: ?>
                <div class="ovm-muted"><?=htmlspecialchars((string)($progress['step'] ?? ''), ENT_QUOTES);?> · <?=htmlspecialchars((string)($progress['label'] ?? ''), ENT_QUOTES);?></div>
              <?php endif; ?>
            </div>
          </section>
          <section class="ovm-job-section">
            <div class="ovm-job-section-title">品質</div>
            <div data-refresh-cell="quality"><?=ovm_job_quality_cell_html($r);?></div>
          </section>
          <section class="ovm-job-section">
            <div class="ovm-job-section-title">耗時</div>
            <div data-refresh-cell="timing">
              <?php foreach($timingSummary as $timingLine): ?>
                <div class="ovm-muted"><?=htmlspecialchars($timingLine, ENT_QUOTES);?></div>
              <?php endforeach; ?>
            </div>
          </section>
          <section class="ovm-job-section">
            <div class="ovm-job-section-title">輸出</div>
            <div class="ovm-job-output">
              <div>
                <span class="ovm-job-metric-label">影像</span>
                <span class="ovm-job-metric-value" data-refresh-cell="frames"><?=htmlspecialchars((string)($r['input_frame_count'] ?? ''), ENT_QUOTES);?> / <?=htmlspecialchars((string)($r['registered_frame_count'] ?? ''), ENT_QUOTES);?></span>
              </div>
              <div data-refresh-cell="artifacts"><?=ovm_job_artifacts_cell_html($r);?></div>
            </div>
          </section>
          <section class="ovm-job-section">
            <div class="ovm-job-section-title">產品</div>
            <div data-refresh-cell="products"><?=ovm_job_products_cell_html($r);?></div>
          </section>
        </div>
      </article>
    <?php endforeach; ?>
    <?php if(empty($rows)): ?>
      <div class="ovm-job-empty">目前沒有轉檔工作。</div>
    <?php endif; ?>
  </div>
  <?=ovm_job_pagination_html($listState);?>

  <?php if($isLoggedIn): ?>
  <div id="retryOpenMvsDialog" class="ovm-modal" role="dialog" aria-modal="true" hidden>
    <div class="ovm-modal-card">
      <div class="ovm-modal-head">
        <h3>重轉設定</h3>
        <button class="btn btn-xs btn-default" type="button" onclick="closeRetryOpenMvsDialog()">關閉</button>
      </div>
      <div class="ovm-modal-body">
        <div class="form-group">
          <label for="retryQualityPreset">產出品質</label>
          <select class="form-control" id="retryQualityPreset">
            <option value="fast">快速 fast</option>
            <option value="normal" selected>標準 normal（預設）</option>
            <option value="high">高品質 high</option>
          </select>
        </div>
        <div class="form-group">
          <label for="retryMode">重轉方式</label>
          <select class="form-control" id="retryMode">
            <option value="current">重轉目前這筆 #id</option>
            <option value="clone">複製成新的 #id</option>
          </select>
        </div>
        <div class="ovm-form-actions">
          <button class="btn btn-default" type="button" onclick="closeRetryOpenMvsDialog()">取消</button>
          <button class="btn btn-warning" type="button" onclick="confirmRetryOpenMvsJob()">確定重轉</button>
        </div>
      </div>
    </div>
  </div>
  <?php endif; ?>

  <div id="uploadProgressDialog" class="ovm-modal" role="dialog" aria-modal="true" hidden>
    <div class="ovm-modal-card">
      <div class="ovm-modal-head">
        <h3>檔案上傳中</h3>
        <button class="btn btn-xs btn-default" type="button" id="closeUploadProgress" hidden>關閉</button>
      </div>
      <div class="ovm-modal-body">
        <div class="ovm-upload-bar"><span id="uploadProgressFill"></span></div>
        <div class="ovm-upload-meta">
          <div>進度</div><div id="uploadProgressPercent">0%</div>
          <div>檔案</div><div id="uploadProgressFileName">-</div>
          <div>大小</div><div id="uploadProgressBytes">0 B / 0 B</div>
          <div>狀態</div><div id="uploadProgressMessage">正在上傳...</div>
        </div>
      </div>
    </div>
  </div>

	  <div id="jobReasonDialog" class="ovm-modal" role="dialog" aria-modal="true" hidden>
	    <div class="ovm-modal-card">
      <div class="ovm-modal-head">
        <h3>失敗原因</h3>
        <button class="btn btn-xs btn-default" type="button" onclick="closeReasonDialog()">關閉</button>
      </div>
      <div class="ovm-modal-body">
        <pre id="jobReasonDialogBody" class="ovm-reason-body"></pre>
	      </div>
	    </div>
	  </div>

	  <div id="jobDiagnosticsDialog" class="ovm-modal" role="dialog" aria-modal="true" hidden>
	    <div class="ovm-modal-card">
	      <div class="ovm-modal-head">
	        <h3>診斷摘要</h3>
	        <button class="btn btn-xs btn-default" type="button" onclick="closeDiagnosticsDialog()">關閉</button>
	      </div>
	      <div class="ovm-modal-body ovm-diagnostics-body">
	        <div id="jobDiagnosticsSummary" class="ovm-muted ovm-diagnostics-summary"></div>
	        <div id="jobDiagnosticsRows"></div>
	      </div>
	    </div>
	  </div>
	</div>

<script nonce="ovm">
document.title = "OpenMVS 轉檔";
var jobFailureReasons = <?=json_encode($failureReasons, JSON_UNESCAPED_UNICODE | JSON_HEX_TAG | JSON_HEX_APOS | JSON_HEX_QUOT | JSON_HEX_AMP);?>;
var selectedUploadFile = null;
var jobRefreshTimer = null;
var jobRefreshInFlight = false;

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

function updateJobCell($row, cell, html) {
  $row.find('[data-refresh-cell="' + cell + '"]').html(html || "");
}

function updateJobRow(row) {
  var $row = $("#job-" + row.id);
  if (!$row.length) return;
	  updateJobCell($row, "thumb", row.thumb_html);
	  updateJobCell($row, "status", row.status_html);
	  updateJobCell($row, "quality", row.quality_html);
	  updateJobCell($row, "timing", row.timing_html);
  updateJobCell($row, "frames", row.frames_html);
  updateJobCell($row, "artifacts", row.artifacts_html);
  updateJobCell($row, "products", row.products_html);
  updateJobCell($row, "actions", row.actions_html);
  initOpenMvsThumbs();
}

function refreshActiveJobs() {
  if (jobRefreshInFlight) return;
  jobRefreshInFlight = true;
  $.getJSON("api.php?mode=jobs_delta&" + window.location.search.replace(/^\?/, ""), function(jd) {
    if (jd && jd.failure_reasons) jobFailureReasons = jd.failure_reasons;
    if (jd && $.isArray(jd.rows)) {
      $.each(jd.rows, function(_, row) { updateJobRow(row); });
    }
    var hasActiveJobs = !!(jd && jd.has_active_jobs);
    $(".ovm-wrap").attr("data-has-active-jobs", hasActiveJobs ? "1" : "0");
    if (!hasActiveJobs && jobRefreshTimer) {
      clearInterval(jobRefreshTimer);
      jobRefreshTimer = null;
    }
  }).always(function() {
    jobRefreshInFlight = false;
  });
}

function startActiveJobRefresh() {
  if ($(".ovm-wrap").attr("data-has-active-jobs") !== "1") return;
  if (jobRefreshTimer) return;
  jobRefreshTimer = setInterval(refreshActiveJobs, 5000);
  refreshActiveJobs();
}

function formatUploadBytes(bytes) {
  bytes = Math.max(0, Number(bytes) || 0);
  if (bytes >= 1024 * 1024 * 1024) return (bytes / 1024 / 1024 / 1024).toFixed(2) + " GB";
  if (bytes >= 1024 * 1024) return (bytes / 1024 / 1024).toFixed(2) + " MB";
  if (bytes >= 1024) return (bytes / 1024).toFixed(1) + " KB";
  return bytes + " B";
}

function showUploadProgressDialog(file) {
  $("#closeUploadProgress").attr("hidden", "hidden");
  $("#uploadProgressFill").css("width", "0%");
  $("#uploadProgressPercent").text("0%");
  $("#uploadProgressFileName").text(file.name || "upload");
  $("#uploadProgressBytes").text("0 B / " + formatUploadBytes(file.size || 0));
  $("#uploadProgressMessage").text("正在上傳...");
  $("#uploadProgressDialog").removeAttr("hidden");
}

function updateUploadProgress(loaded, total) {
  var percent = total > 0 ? Math.min(100, Math.round((loaded / total) * 100)) : 0;
  $("#uploadProgressFill").css("width", percent + "%");
  $("#uploadProgressPercent").text(percent + "%");
  $("#uploadProgressBytes").text(formatUploadBytes(loaded) + " / " + (total > 0 ? formatUploadBytes(total) : "未知大小"));
}

function uploadResponseErrorMessage(xhr) {
  var message = "伺服器回應格式錯誤";
  if (xhr.status) message += " (HTTP " + xhr.status + ")";
  var snippet = String(xhr.responseText || "").replace(/\s+/g, " ").trim().slice(0, 180);
  return snippet ? message + ": " + snippet : message;
}

function checkUploadCaptcha(gdcode) {
  return new Promise(function(resolve, reject) {
    $.post("api.php?mode=checkGD", { gdcode: $.trim(gdcode || "") }, function(resp) {
      if ($.trim(String(resp || "")) === "OK") resolve();
      else reject(new Error("驗證碼錯誤，請重新輸入"));
    }).fail(function() {
      reject(new Error("驗證碼檢查失敗"));
    });
  });
}

function uploadWithProgress(formData) {
  return new Promise(function(resolve, reject) {
    var xhr = new XMLHttpRequest();
    xhr.open("POST", "api.php?mode=upload");
    xhr.upload.onprogress = function(event) { updateUploadProgress(event.loaded, event.total); };
    xhr.onload = function() {
      if (xhr.status < 200 || xhr.status >= 300) {
        reject(new Error(uploadResponseErrorMessage(xhr)));
        return;
      }
      try {
        resolve(JSON.parse(xhr.responseText || "{}"));
      } catch (error) {
        reject(new Error(uploadResponseErrorMessage(xhr)));
      }
    };
    xhr.onerror = function() { reject(new Error("上傳失敗")); };
    xhr.send(formData);
  });
}

function setSelectedFile(file) {
  selectedUploadFile = file || null;
  $("#selectedFileName").text(file ? file.name : "尚未選擇檔案");
}

function initOpenMvsThumbs() {
  var thumbs = Array.prototype.slice.call(document.querySelectorAll(".ovm-model-thumb[data-glb]"));
  if (!thumbs.length || typeof THREE === "undefined" || typeof THREE.GLTFLoader === "undefined") return;
  if (!window.openMvsThumbQueue) {
    window.openMvsThumbQueue = [];
    window.openMvsThumbActive = 0;
  }

  function enqueue(el) {
    if (el.dataset.queued === "1") return;
    el.dataset.queued = "1";
    window.openMvsThumbQueue.push(el);
    pump();
  }

  function pump() {
    while (window.openMvsThumbActive < 2 && window.openMvsThumbQueue.length > 0) {
      renderOpenMvsThumb(window.openMvsThumbQueue.shift(), pump);
    }
  }

  if ("IntersectionObserver" in window) {
    var observer = new IntersectionObserver(function(entries) {
      entries.forEach(function(entry) {
        if (!entry.isIntersecting) return;
        observer.unobserve(entry.target);
        enqueue(entry.target);
      });
    }, { rootMargin: "220px 0px" });
    thumbs.forEach(function(el) { observer.observe(el); });
    return;
  }

  thumbs.slice(0, 8).forEach(enqueue);
}

function renderOpenMvsThumb(el, onDone) {
  window.openMvsThumbActive = (window.openMvsThumbActive || 0) + 1;
  var finished = false;
  function finish() {
    if (finished) return;
    finished = true;
    window.openMvsThumbActive = Math.max(0, (window.openMvsThumbActive || 1) - 1);
    if (typeof onDone === "function") onDone();
  }

  var width = 400;
  var height = 360;
  var renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(1);
  renderer.setSize(width, height, false);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.domElement.style.width = "100%";
  renderer.domElement.style.height = "100%";
  el.innerHTML = "";
  el.appendChild(renderer.domElement);

  var scene = new THREE.Scene();
  scene.background = new THREE.Color(0x07111f);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x334155, 2.2));
  var keyLight = new THREE.DirectionalLight(0xffffff, 1.8);
  keyLight.position.set(4, 6, 5);
  scene.add(keyLight);
  var camera = new THREE.PerspectiveCamera(38, width / height, 0.01, 10000000);
  var loader = new THREE.GLTFLoader();

  if (typeof THREE.MeshoptDecoder !== "undefined") loader.setMeshoptDecoder(THREE.MeshoptDecoder);
  if (typeof THREE.DRACOLoader !== "undefined") {
    var dracoLoader = new THREE.DRACOLoader();
    dracoLoader.setDecoderPath("/john_web/assets/vendor/three/0.155.0/examples/jsm/libs/draco/");
    loader.setDRACOLoader(dracoLoader);
  }
  if (typeof THREE.KTX2Loader !== "undefined") {
    var ktx2Loader = new THREE.KTX2Loader();
    ktx2Loader.setTranscoderPath("/john_web/assets/vendor/three/0.155.0/examples/jsm/libs/basis/");
    ktx2Loader.detectSupport(renderer);
    loader.setKTX2Loader(ktx2Loader);
  }

  loader.load(el.dataset.glb, function(gltf) {
    try {
      var model = gltf.scene || (gltf.scenes && gltf.scenes[0]);
      if (!model) throw new Error("no scene");
      var box = new THREE.Box3().setFromObject(model);
      var center = box.getCenter(new THREE.Vector3());
      var size = box.getSize(new THREE.Vector3());
      model.position.sub(center);
      scene.add(model);

      var maxDim = Math.max(size.x, size.y, size.z, 1);
      var distance = maxDim / Math.tan(camera.fov * Math.PI / 360) * 0.72;
      camera.position.set(distance * 0.7, distance * 0.42, distance * 0.74);
      camera.lookAt(0, 0, 0);
      camera.near = Math.max(distance / 1000, 0.001);
      camera.far = distance * 1000;
      camera.updateProjectionMatrix();
      renderer.render(scene, camera);

      var dataUrl = renderer.domElement.toDataURL("image/png");
      var img = new Image();
      img.alt = "OpenMVS thumbnail";
      img.src = dataUrl;
      el.innerHTML = "";
      el.appendChild(img);
      saveOpenMvsThumb(el.dataset.modelId, dataUrl, el);
      disposeOpenMvsThumbScene(scene, renderer);
    } catch (error) {
      markOpenMvsThumbError(el, renderer);
    }
    finish();
  }, undefined, function() {
    markOpenMvsThumbError(el, renderer);
    finish();
  });
}

function markOpenMvsThumbError(el, renderer) {
  el.classList.add("model-thumb-error");
  el.innerHTML = "<span>縮圖失敗</span>";
  if (renderer) renderer.dispose();
}

function saveOpenMvsThumb(id, dataUrl, el) {
  if (!id || !dataUrl) return;
  $.post("api.php?mode=save_thumb", { id: id, image: dataUrl }, function(resp) {
    if (resp && resp.status === "OK" && resp.url) {
      var img = el.querySelector("img");
      if (img) img.src = resp.url;
    }
  }, "json");
}

function disposeOpenMvsThumbScene(scene, renderer) {
  scene.traverse(function(obj) {
    if (obj.geometry) obj.geometry.dispose();
    if (!obj.material) return;
    var materials = Array.isArray(obj.material) ? obj.material : [obj.material];
    materials.forEach(function(material) {
      Object.keys(material).forEach(function(key) {
        if (material[key] && material[key].isTexture) material[key].dispose();
      });
      material.dispose();
    });
  });
  renderer.dispose();
}

$(function() {
  startActiveJobRefresh();
  initOpenMvsThumbs();
});

$("#captchaImage").on("click", refreshCaptchaImage);
$("#closeUploadProgress").on("click", function() {
  $("#uploadProgressDialog").attr("hidden", "hidden");
});

$("#upfile").on("change", function() {
  setSelectedFile(this.files && this.files[0] ? this.files[0] : null);
});

$("#fileDropZone").on("dragover", function(event) {
  event.preventDefault();
  $(this).addClass("is-active");
}).on("dragleave drop", function(event) {
  event.preventDefault();
  $(this).removeClass("is-active");
  var file = event.originalEvent.dataTransfer && event.originalEvent.dataTransfer.files[0];
  if (!file) return;
  var dt = new DataTransfer();
  dt.items.add(file);
  document.getElementById("upfile").files = dt.files;
  setSelectedFile(file);
});

$("#uploadForm").on("submit", function(event) {
  event.preventDefault();
  var file = document.getElementById("upfile").files[0];
  if (!file) {
    $("#uploadStatus").text("請選擇 MP4 影片或圖片 ZIP");
    return;
  }
  var formData = new FormData(this);
  $("#uploadStatus").text("檢查驗證碼...");
  $("#uploadForm button[type=submit]").prop("disabled", true);
  checkUploadCaptcha($("#gdcode").val()).then(function() {
    $("#uploadStatus").text("");
    showUploadProgressDialog(file);
    return uploadWithProgress(formData);
  }).then(function(jd) {
    if (jd.status === "OK") {
      $("#uploadProgressMessage").text("上傳完成，已排入背景轉檔。");
      window.location.href = "index.php?highlight_job=" + encodeURIComponent(jd.id) + "#job-" + encodeURIComponent(jd.id);
      return;
    }
    $("#uploadProgressMessage").text(jd.reason || "上傳失敗");
    $("#closeUploadProgress").removeAttr("hidden");
    refreshCaptchaImage();
  }).catch(function(error) {
    var message = error.message || "上傳失敗";
    $("#uploadStatus").text(message);
    if (!$("#uploadProgressDialog").is("[hidden]")) {
      $("#uploadProgressMessage").text(message);
      $("#closeUploadProgress").removeAttr("hidden");
    }
    refreshCaptchaImage();
  }).finally(function() {
    $("#uploadForm button[type=submit]").prop("disabled", false);
  });
});
</script>

<?php require "{$base_dir}/foot.php"; ?>
