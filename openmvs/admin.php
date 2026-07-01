<?php
  require __DIR__ . "/../inc/config.php";
  require "{$base_dir}/inc/checkpassword.php";
  require_once __DIR__ . "/job_view.php";

  $listState = ovm_job_list_state(15);
  $rows = $listState['rows'];
  $estimateSeconds = ovm_average_completed_duration($rows);
  $failureReasons = [];
  foreach($rows as $row){
      $fullReason = trim((string)($row['reason'] ?? ''));
      if($fullReason !== '') $failureReasons[(string)$row['id']] = ovm_json_safe_text($fullReason);
  }

  require "{$base_dir}/html.php";
  require "{$base_dir}/head.php";
?>
<script src="js/function.js"></script>
<title>OpenMVS 轉檔後台</title>
<?php
  require "{$base_dir}/head_end.php";
  require "{$base_dir}/body.php";
  require "{$base_dir}/top.php";
?>
<style nonce="ovm-admin">
  html, html body{background:#111827;color:#e5edf7;}
  .ovm-admin{max-width:1440px;margin:0 auto;padding:22px 20px 42px;}
  .ovm-admin-header{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:14px;}
  .ovm-admin h2{margin:0;color:#f8fafc;font-size:28px;font-weight:700;letter-spacing:0;}
  .ovm-admin-back-btn{background:#1d2a3a;border-color:#3b4a5f;color:#e5edf7;}
  .ovm-admin-back-btn:hover,.ovm-admin-back-btn:focus{background:#26364a;border-color:#5a718b;color:#fff;}
  .ovm-admin-toolbar{margin:0 0 12px;color:#9fb0c3;font-size:13px;}
  .ovm-list-tools{display:grid;grid-template-columns:auto minmax(240px,1fr) auto auto auto;gap:10px;align-items:center;margin:0 0 14px;padding:12px;border:1px solid #334155;border-radius:6px;background:#111b2a;}
  .ovm-list-tools label{margin:0;color:#dbe7f3;font-weight:700;}
  .ovm-list-tools .form-control{background:#0f1722;color:#f8fafc;border-color:#3b4a5f;box-shadow:none;}
  .ovm-list-count{color:#9fb0c3;font-size:12px;white-space:nowrap;}
  .ovm-pagination{display:flex;justify-content:center;align-items:center;gap:10px;margin-top:14px;color:#cbd5e1;}
  .ovm-pagination .disabled{pointer-events:none;opacity:.45;}
  .ovm-admin-list{display:grid;gap:12px;}
  .ovm-admin-job{border:1px solid #334155;border-radius:6px;background:#111b2a;overflow:hidden;}
  .ovm-admin-job-head{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:16px;padding:14px 16px;background:#18263b;border-bottom:1px solid #29384d;}
  .ovm-admin-title-row{display:flex;align-items:center;gap:10px;min-width:0;}
  .ovm-admin-id{flex:0 0 auto;color:#bfdbfe;font-weight:700;font-variant-numeric:tabular-nums;}
  .ovm-admin-title{margin:0;color:#f8fafc;font-size:19px;line-height:1.35;font-weight:700;overflow-wrap:anywhere;}
  .ovm-admin-file{margin-top:4px;font-size:12px;color:#9fb0c3;line-height:1.35;word-break:break-word;}
  .ovm-admin-actions{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:6px;max-width:420px;}
  .ovm-admin-actions .btn{margin:0;}
  .ovm-admin-job-body{display:grid;grid-template-columns:minmax(190px,.85fr) minmax(220px,1fr) minmax(190px,.85fr) minmax(260px,1.1fr);gap:18px;padding:14px 16px;}
  .ovm-admin-section{min-width:0;}
  .ovm-admin-section-title{margin-bottom:7px;color:#cbd5e1;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;}
  .ovm-muted{color:#9fb0c3;font-size:12px;line-height:1.45;}
  .ovm-status-main{font-size:15px;font-weight:600;color:#f8fafc;}
  .ovm-quality{display:inline-block;min-width:48px;border-radius:4px;padding:2px 6px;font-size:12px;font-weight:700;text-align:center;}
  .ovm-quality-5{background:#166534;color:#dcfce7;}
  .ovm-quality-4{background:#0f766e;color:#ccfbf1;}
  .ovm-quality-3{background:#854d0e;color:#fef3c7;}
  .ovm-quality-2{background:#9a3412;color:#ffedd5;}
  .ovm-quality-1{background:#991b1b;color:#fee2e2;}
  .ovm-progress-mini{height:7px;border-radius:999px;background:#0b1220;border:1px solid #334155;overflow:hidden;margin-top:7px;}
  .ovm-progress-mini span{display:block;height:100%;background:#38bdf8;}
  .ovm-admin-empty{padding:28px;text-align:center;color:#9fb0c3;border:1px solid #334155;border-radius:6px;background:#111b2a;}
  .ovm-product-list{display:grid;gap:6px;}
  .ovm-product-row{display:flex;align-items:center;gap:6px;flex-wrap:wrap;}
  .ovm-product-size{min-width:70px;color:#f8fafc;font-size:12px;font-weight:700;}
  .ovm-modal[hidden]{display:none;}
  .ovm-modal{position:fixed;z-index:10000;inset:0;background:rgba(2,6,23,.72);display:flex;align-items:center;justify-content:center;padding:20px;}
  .ovm-modal-card{width:min(620px,calc(100vw - 32px));border:1px solid #334155;border-radius:6px;background:#111b2a;color:#e5edf7;box-shadow:0 24px 80px rgba(0,0,0,.45);}
  .ovm-modal-head{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px 16px;border-bottom:1px solid #26364a;}
  .ovm-modal-head h3{margin:0;font-size:18px;color:#f8fafc;}
  .ovm-modal-body{padding:16px;}
  .ovm-reason-body{max-height:58vh;overflow:auto;background:#020617;color:#3cff71;border:1px solid #334155;border-radius:4px;padding:14px;font-size:14px;line-height:1.55;white-space:pre-wrap;}
  .ovm-diagnostics-body{max-height:72vh;overflow:auto;}
  .ovm-diagnostics-summary{max-height:24vh;overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere;margin-bottom:12px;}
  .ovm-form-actions{display:flex;align-items:center;justify-content:flex-end;gap:10px;margin-top:14px;}
  .ovm-admin .btn-default{background:#1d2a3a;border-color:#3b4a5f;color:#e5edf7;}
  .ovm-admin .btn-default:hover,.ovm-admin .btn-default:focus{background:#26364a;border-color:#5a718b;color:#fff;}
  .ovm-admin .btn-success{background:#15803d;border-color:#15803d;color:#fff;}
  .ovm-admin .btn-warning{background:#b45309;border-color:#b45309;color:#fff;}
  .ovm-admin .btn-danger{background:#b91c1c;border-color:#b91c1c;color:#fff;}
  @media (max-width: 760px){
    .ovm-admin{padding:18px 12px 32px;}
    .ovm-admin-header,.ovm-admin-job-head{display:block;}
    .ovm-list-tools{grid-template-columns:1fr;}
    .ovm-admin h2{font-size:24px;}
    .ovm-admin-back-btn{margin-top:10px;}
    .ovm-admin-actions{justify-content:flex-start;margin-top:10px;max-width:none;}
    .ovm-admin-job-body{grid-template-columns:1fr;}
  }
  @media (min-width: 761px) and (max-width: 1080px){
    .ovm-admin-job-body{grid-template-columns:repeat(2,minmax(0,1fr));}
  }
</style>

<div class="ovm-admin">
  <div class="ovm-admin-header">
    <h2>OpenMVS 轉檔後台</h2>
    <a class="btn btn-default ovm-admin-back-btn" href="index.php">回前台</a>
  </div>
  <div class="ovm-admin-toolbar">工作列表</div>
  <?=ovm_job_search_form_html($listState);?>
  <div class="ovm-admin-list">
    <?php foreach($rows as $r):
        $id = (int)$r['id'];
    ?>
      <article class="ovm-admin-job">
        <header class="ovm-admin-job-head">
          <div>
            <div class="ovm-admin-title-row">
              <span class="ovm-admin-id">#<?=$id;?></span>
              <h3 class="ovm-admin-title"><?=htmlspecialchars($r['title'] ?: $r['orin_filename'], ENT_QUOTES);?></h3>
            </div>
            <div class="ovm-admin-file"><?=htmlspecialchars($r['orin_filename'] ?? '', ENT_QUOTES);?></div>
          </div>
          <div class="ovm-admin-actions">
            <?=ovm_job_actions_cell_html($r);?>
          </div>
        </header>
        <div class="ovm-admin-job-body">
          <section class="ovm-admin-section">
            <div class="ovm-admin-section-title">狀態</div>
            <?=ovm_job_status_cell_html($r);?>
          </section>
          <section class="ovm-admin-section">
            <div class="ovm-admin-section-title">品質</div>
            <?=ovm_job_quality_cell_html($r);?>
          </section>
          <section class="ovm-admin-section">
            <div class="ovm-admin-section-title">耗時 / 影格</div>
            <?=ovm_job_timing_cell_html($r, $estimateSeconds);?>
            <div class="ovm-muted">影格 <?=ovm_job_frames_cell_html($r);?></div>
          </section>
          <section class="ovm-admin-section">
            <div class="ovm-admin-section-title">輸出</div>
            <?=ovm_job_artifacts_cell_html($r);?>
          </section>
          <section class="ovm-admin-section">
            <div class="ovm-admin-section-title">產品</div>
            <div data-refresh-cell="products"><?=ovm_job_products_cell_html($r);?></div>
          </section>
        </div>
      </article>
    <?php endforeach; ?>
    <?php if(empty($rows)): ?>
      <div class="ovm-admin-empty">目前沒有工作。</div>
    <?php endif; ?>
  </div>
  <?=ovm_job_pagination_html($listState);?>

  <div id="retryOpenMvsDialog" class="ovm-modal" role="dialog" aria-modal="true" hidden>
    <div class="ovm-modal-card">
      <div class="ovm-modal-head">
        <h3>重轉設定</h3>
        <button class="btn btn-xs btn-default" type="button" onclick="closeRetryOpenMvsDialog()">關閉</button>
      </div>
      <div class="ovm-modal-body">
        <div class="form-group">
          <label>產出品質</label>
          <select id="retryQualityPreset" class="form-control">
            <option value="fast">快速 fast</option>
            <option value="normal" selected>標準 normal</option>
            <option value="high">高品質 high</option>
          </select>
        </div>
        <div class="form-group">
          <label>重轉方式</label>
          <select id="retryMode" class="form-control">
            <option value="current" selected>同編號重轉</option>
            <option value="clone">新建編號重轉</option>
          </select>
        </div>
        <div class="ovm-form-actions">
          <button class="btn btn-default" type="button" onclick="closeRetryOpenMvsDialog()">取消</button>
          <button class="btn btn-warning" type="button" onclick="confirmRetryOpenMvsJob()">確定重轉</button>
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

<script nonce="ovm-admin">
document.title = "OpenMVS 轉檔後台";
var jobFailureReasons = <?=json_encode($failureReasons, JSON_UNESCAPED_UNICODE | JSON_HEX_TAG | JSON_HEX_APOS | JSON_HEX_QUOT | JSON_HEX_AMP);?>;

function openReasonDialog(id) {
  var reason = jobFailureReasons[String(id)] || "這筆工作沒有失敗原因。";
  $("#jobReasonDialogBody").text(reason);
  $("#jobReasonDialog").removeAttr("hidden");
}

function closeReasonDialog() {
  $("#jobReasonDialog").attr("hidden", "hidden");
  $("#jobReasonDialogBody").text("");
}
</script>

<?php require "{$base_dir}/foot.php"; ?>
