function openOpenMvsViewer(id, productId) {
  var url = "viewer_mesh.php?id=" + encodeURIComponent(id);
  if (productId) url += "&product_id=" + encodeURIComponent(productId);
  window.open(url, "_blank", "noopener");
}

var openMvsRetryRequest = null;

function postOpenMvsAdminAction(button, id, action, fallbackMessage, extraData) {
  var $button = button ? $(button) : $();
  if ($button.length && $button.prop("disabled")) return;
  $button.prop("disabled", true).addClass("disabled");
  var payload = { id: id, action: action };
  if (extraData) $.extend(payload, extraData);
  $.post("api.php?mode=admin_action", payload, function (jd) {
    if (jd && jd.status === "OK") {
      window.location.reload();
      return;
    }
    window.alert((jd && jd.reason) || fallbackMessage);
  }, "json").fail(function () {
    window.alert(fallbackMessage + "，請確認登入狀態後再試一次。");
  }).always(function () {
    $button.prop("disabled", false).removeClass("disabled");
  });
}

function retryOpenMvsJob(button, id) {
  if (id === undefined) {
    id = button;
    button = null;
  }
  openMvsRetryRequest = { button: button, id: id };
  $("#retryQualityPreset").val("normal");
  $("#retryMode").val("current");
  $("#retryOpenMvsDialog").removeAttr("hidden");
  $("#retryQualityPreset").trigger("focus");
}

function closeRetryOpenMvsDialog() {
  $("#retryOpenMvsDialog").attr("hidden", "hidden");
  openMvsRetryRequest = null;
}

function confirmRetryOpenMvsJob() {
  if (!openMvsRetryRequest) return;
  var button = openMvsRetryRequest.button;
  var id = openMvsRetryRequest.id;
  var quality_preset = $("#retryQualityPreset").val() || "normal";
  var retry_mode = $("#retryMode").val() || "current";
  if ($.inArray(quality_preset, ["fast", "normal", "high"]) < 0) quality_preset = "normal";
  if ($.inArray(retry_mode, ["current", "clone"]) < 0) retry_mode = "current";
  $("#retryOpenMvsDialog").attr("hidden", "hidden");
  openMvsRetryRequest = null;
  postOpenMvsAdminAction(button, id, "retry", "重轉失敗", {
    quality_preset: quality_preset,
    retry_mode: retry_mode
  });
}

function startOpenMvsJob(button, id) {
  if (!window.confirm("確定要啟動這筆暫停工作嗎？系統會重新排入待處理佇列。")) return;
  postOpenMvsAdminAction(button, id, "start", "啟動失敗");
}

function pauseOpenMvsJob(button, id) {
  if (!window.confirm("確定要暫停目前轉檔嗎？系統會嘗試停止背景程序。")) return;
  postOpenMvsAdminAction(button, id, "abort", "暫停失敗");
}

function deleteOpenMvsJob(button, id) {
  if (!window.confirm("確定要刪除這筆資料嗎？刪除後列表將不再顯示。")) return;
  postOpenMvsAdminAction(button, id, "delete", "刪除失敗");
}

function finishOpenMvsProductAction() {
  if (typeof refreshActiveJobs === "function") {
    $(".ovm-wrap").attr("data-has-active-jobs", "1");
    if (typeof startActiveJobRefresh === "function") startActiveJobRefresh();
    else refreshActiveJobs();
    return;
  }
  window.location.reload();
}

function postOpenMvsProductAction(button, payload, fallbackMessage) {
  var $button = button ? $(button) : $();
  if ($button.length && $button.prop("disabled")) return;
  $button.prop("disabled", true).addClass("disabled");
  $.post("api.php?mode=product_action", payload, function (jd) {
    if (jd && jd.status === "OK") {
      finishOpenMvsProductAction();
      return;
    }
    window.alert((jd && jd.reason) || fallbackMessage);
  }, "json").fail(function () {
    window.alert(fallbackMessage + "，請確認登入狀態後再試一次。");
  }).always(function () {
    $button.prop("disabled", false).removeClass("disabled");
  });
}

function createOpenMvsProduct(button, jobId, textureSize) {
  postOpenMvsProductAction(button, {
    action: "create_glb",
    job_id: jobId,
    texture_size: textureSize
  }, "產品產製失敗");
}

function deleteOpenMvsProduct(button, productId) {
  if (!window.confirm("確定要刪除這個產品嗎？")) return;
  postOpenMvsProductAction(button, {
    action: "delete",
    product_id: productId
  }, "產品刪除失敗");
}

function refreshJobLog(id, targetSelector) {
  $.getJSON("api.php?mode=get_log&id=" + encodeURIComponent(id), function (jd) {
    if (jd.status === "OK") {
      $(targetSelector).text(jd.log || "");
    }
  });
}

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
    var logPath = job.diagnostic_log_path ? " - " + job.diagnostic_log_path : "";
    $("#jobDiagnosticsSummary").text((job.diagnostic_summary || "沒有診斷摘要") + logPath);
    if (!items.length) {
      $("#jobDiagnosticsRows").html('<div class="ovm-muted">沒有重複警告或錯誤。</div>');
      return;
    }
    var html = '<table class="table table-condensed ovm-table"><thead><tr><th>Stage</th><th>Pattern</th><th>Severity</th><th>Count</th></tr></thead><tbody>';
    $.each(items, function (_, row) {
      html += '<tr><td>' + $("<div>").text(row.stage || "").html() + '</td><td>' + $("<div>").text(row.pattern_id || "").html() + '</td><td>' + $("<div>").text(row.severity || "").html() + '</td><td>' + $("<div>").text(row.pattern_count || "").html() + '</td></tr>';
    });
    html += "</tbody></table>";
    $("#jobDiagnosticsRows").html(html);
  });
}
