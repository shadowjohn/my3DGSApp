function openSplatViewer(id) {
  window.open("viewer_splat.php?id=" + encodeURIComponent(id), "_blank", "noopener");
}

function refreshJobLog(id, targetSelector) {
  $.getJSON("api.php?mode=get_log&id=" + encodeURIComponent(id), function (jd) {
    if (jd.status === "OK") {
      $(targetSelector).text(jd.log || "");
    }
  });
}
