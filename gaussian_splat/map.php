<?php
  require __DIR__ . "/../inc/config.php";
  require "{$base_dir}/inc/checkpassword.php";
  $include_mode = "easymap7115";

  $id = (int)($_GET['id'] ?? 0);
  $rows = selectSQL_SAFE("SELECT * FROM `gaussian_splat_jobs` WHERE `id`=? AND `del`='0' LIMIT 1", [$id]);
  if(!$rows) exit("工作不存在");

  $info = $rows[0];
  $isReady = (string)$info['status'] === '2';
  if(!$isReady) exit("工作尚未完成");

  $cleanSplat = "uploads/{$id}/exports/splat.clean.ply";
  $rawSplat = "uploads/{$id}/exports/splat.ply";
  $splat = is_file(__DIR__ . "/{$cleanSplat}") ? $cleanSplat : $rawSplat;
  if(!is_file(__DIR__ . "/{$splat}")) exit("找不到 splat 檔");

  function gs_value($value, $default){
      return ($value !== null && $value !== '') ? $value : $default;
  }

  $viewerSrc = "viewer_splat.php?id={$id}";

  require "{$base_dir}/html.php";
  require "{$base_dir}/head.php";
?>
<title>Gaussian Splat 定位校正</title>
<?php
  require "{$base_dir}/head_end.php";
  require "{$base_dir}/body.php";
  require "{$base_dir}/top.php";
?>
<style nonce="gg">
  #layout{display:grid;grid-template-columns:minmax(420px,1fr) 360px;gap:12px;padding:12px;max-width:1440px;margin:0 auto;}
  #map{height:720px;border:1px solid #bbb;background:#eef2f6;}
  #panel{border:1px solid #bbb;padding:12px;background:#fff;}
  #panel h3{margin-top:0;font-size:18px;}
  #panel label{display:block;margin-top:10px;font-weight:600;}
  #panel input{width:100%;height:32px;padding:4px 8px;border:1px solid #bbb;border-radius:4px;}
  #panel .field-row{display:grid;grid-template-columns:1fr 1fr;gap:8px;}
  #preview{width:100%;height:280px;border:1px solid #bbb;margin-top:12px;background:#111827;}
  #saveStatus{display:block;min-height:20px;margin-top:8px;color:#667085;}
  @media (max-width: 900px){
    #layout{grid-template-columns:1fr;}
    #map{height:520px;}
  }
</style>
<div id="layout">
  <div id="map"></div>
  <div id="panel">
    <h3>定位校正：<?=htmlspecialchars($info['title'] ?: $info['orin_filename'], ENT_QUOTES);?></h3>
    <div class="field-row">
      <label>經度 <input id="lon" placeholder="例：120.61022" value="<?=htmlspecialchars((string)gs_value($info['lon'], 120.61022), ENT_QUOTES);?>"></label>
      <label>緯度 <input id="lat" placeholder="例：24.110946" value="<?=htmlspecialchars((string)gs_value($info['lat'], 24.110946), ENT_QUOTES);?>"></label>
    </div>
    <div class="field-row">
      <label>高度 <input id="alt" placeholder="18 樓約 72 公尺" value="<?=htmlspecialchars((string)gs_value($info['alt'], 72), ENT_QUOTES);?>"></label>
      <label>比例 <input id="scale" placeholder="例：1" value="<?=htmlspecialchars((string)gs_value($info['scale'], 1), ENT_QUOTES);?>"></label>
    </div>
    <div class="field-row">
      <label>模型方向 <input id="heading" placeholder="0=北，90=東，180=南，270=西" value="<?=htmlspecialchars((string)gs_value($info['heading'], 0), ENT_QUOTES);?>"></label>
      <label>俯仰 <input id="pitch" placeholder="例：0" value="<?=htmlspecialchars((string)gs_value($info['pitch'], 0), ENT_QUOTES);?>"></label>
    </div>
    <label>翻滾 <input id="roll" placeholder="例：0" value="<?=htmlspecialchars((string)gs_value($info['roll'], 0), ENT_QUOTES);?>"></label>
    <div class="field-row">
      <label>圖台旋轉 <input id="map_rotate" value="0" placeholder="0=正北，順時針角度"></label>
      <label>方向旋轉 <input id="map_rotate_range" type="range" min="0" max="360" step="1" value="0"></label>
    </div>

    <h4>相機</h4>
    <div class="field-row">
      <label>相機經度 <input id="camera_lon" placeholder="留空則使用經度" value="<?=htmlspecialchars((string)gs_value($info['camera_lon'], ''), ENT_QUOTES);?>"></label>
      <label>相機緯度 <input id="camera_lat" placeholder="留空則使用緯度" value="<?=htmlspecialchars((string)gs_value($info['camera_lat'], ''), ENT_QUOTES);?>"></label>
    </div>
    <label>相機高度 <input id="camera_alt" placeholder="例：180" value="<?=htmlspecialchars((string)gs_value($info['camera_alt'], 180), ENT_QUOTES);?>"></label>
    <div class="field-row">
      <label>相機方向 <input id="camera_heading" placeholder="0=北，90=東，180=南，270=西" value="<?=htmlspecialchars((string)gs_value($info['camera_heading'], 0), ENT_QUOTES);?>"></label>
      <label>相機俯仰 <input id="camera_pitch" placeholder="例：-35" value="<?=htmlspecialchars((string)gs_value($info['camera_pitch'], -35), ENT_QUOTES);?>"></label>
    </div>
    <label>相機翻滾 <input id="camera_roll" placeholder="例：0" value="<?=htmlspecialchars((string)gs_value($info['camera_roll'], 0), ENT_QUOTES);?>"></label>

    <p><a target="_blank" rel="noopener" href="<?=htmlspecialchars($viewerSrc, ENT_QUOTES);?>">開啟獨立檢視器</a></p>
    <iframe id="preview" src="<?=htmlspecialchars($viewerSrc, ENT_QUOTES);?>"></iframe>
    <button class="btn btn-default" id="locate2d" type="button">2D 定位</button>
    <button class="btn btn-default" id="locate3d" type="button">3D 定位</button>
    <button class="btn btn-default" id="applyMapRotate" type="button">套用圖台旋轉</button>
    <button class="btn btn-primary" id="save" type="button">儲存定位</button>
    <span id="saveStatus"></span>
  </div>
</div>
<script nonce="gg">
  document.title = "Gaussian Splat 定位校正";

  var map = new Easymap("map");

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

  map.panToXYZ(new dgXY(targetLon(), targetLat()), 19);

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

  function payload() {
    return {
      lon: numberOrNull("#lon"),
      lat: numberOrNull("#lat"),
      alt: numberOrNull("#alt"),
      heading: numberOrNull("#heading"),
      pitch: numberOrNull("#pitch"),
      roll: numberOrNull("#roll"),
      scale: numberOrNull("#scale"),
      camera_lon: numberOrNull("#camera_lon"),
      camera_lat: numberOrNull("#camera_lat"),
      camera_alt: numberOrNull("#camera_alt"),
      camera_heading: numberOrNull("#camera_heading"),
      camera_pitch: numberOrNull("#camera_pitch"),
      camera_roll: numberOrNull("#camera_roll"),
      map_rotate: numberOrNull("#map_rotate")
    };
  }

  map.attachEvent("onclick", function(evt, dgxy) {
    var xy = dgxy || evt;
    if(!xy) return;
    $("#lon").val(parseFloat(xy.x).toFixed(7));
    $("#lat").val(parseFloat(xy.y).toFixed(7));
  });

  $("#map_rotate,#map_rotate_range").on("input change", function() {
    syncRotateInputs("#" + this.id);
    applyMapRotate();
  });

  $("#applyMapRotate").on("click", applyMapRotate);
  $("#locate2d").on("click", locate2d);
  $("#locate3d").on("click", locate3d);

  $("#save").on("click", function() {
    $("#saveStatus").text("正在儲存...");
    $.post("api.php?mode=save_transform", {
      id: <?=$id;?>,
      data: base64_encode(JSON.stringify(payload()))
    }, function(jd) {
      if(jd.status === "OK") $("#saveStatus").text("已儲存。");
      else $("#saveStatus").text(jd.reason || "儲存失敗。");
    }, "json").fail(function(){
      $("#saveStatus").text("儲存失敗。");
    });
  });
</script>
</body></html>
