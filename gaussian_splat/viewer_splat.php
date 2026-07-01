<?php
  require __DIR__ . "/../inc/config.php";
  require_once __DIR__ . "/job_view.php";

  $id = (int)($_GET['id'] ?? 0);
  $srcParam = trim((string)($_GET['src'] ?? ''));
  if($id <= 0 && ctype_digit($srcParam)) $id = (int)$srcParam;
  $studioJobId = trim((string)($_GET['studio_job_id'] ?? ''));
  $artifact = $id > 0 ? gs_splat_artifact_for_job($id) : null;
  if($id > 0 && !$artifact){
      http_response_code(404);
      exit("找不到 Splat 產物");
  }

  $bootstrap = [
      'src'=>$artifact ? "api.php?mode=getSplat&uuid=" . rawurlencode($artifact['uuid']) : '',
      "format"=>$artifact['format'] ?? '',
      'job_id'=>$id,
      'artifact_uuid'=>$artifact['uuid'] ?? '',
      'artifact_size_bytes'=>$artifact['size_bytes'] ?? 0,
      'studio_job_id'=>$studioJobId,
  ];

  $bootstrapJson = json_encode($bootstrap, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
?><!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Gaussian Splat 檢視器</title>
  <style>
    html,
    body,
    #viewer-root {
      margin: 0;
      width: 100%;
      height: 100%;
      overflow: hidden;
      background: #101820;
      color: #f4f7fb;
      font-family: Arial, "Noto Sans TC", sans-serif;
    }

    #status {
      position: fixed;
      left: 312px;
      right: 12px;
      top: 12px;
      z-index: 10;
      max-width: calc(100vw - 324px);
      padding: 8px 10px;
      border: 1px solid rgba(255, 255, 255, .2);
      border-radius: 6px;
      background: rgba(16, 24, 32, .82);
      font-size: 13px;
      line-height: 1.5;
      overflow-wrap: anywhere;
    }

    #download-progress {
      margin-top: 8px;
    }

    #download-progress[hidden] {
      display: none;
    }

    #download-progress {
      height: 8px;
      border: 1px solid rgba(255, 255, 255, .22);
      border-radius: 999px;
      background: rgba(255, 255, 255, .08);
      overflow: hidden;
    }

    #download-progress-fill {
      display: block;
      width: 0;
      height: 100%;
      background: #2dd4bf;
      transition: width .12s linear;
    }

    #download-progress-text {
      display: block;
      margin-top: 4px;
      color: #dce7ef;
      font-size: 12px;
      font-variant-numeric: tabular-nums;
    }

    #rotation-panel {
      position: fixed;
      left: 12px;
      top: 12px;
      z-index: 11;
      width: 276px;
      box-sizing: border-box;
      padding: 10px;
      border: 1px solid rgba(255, 255, 255, .22);
      border-radius: 6px;
      background: rgba(16, 24, 32, .88);
      box-shadow: 0 10px 30px rgba(0, 0, 0, .25);
      font-size: 12px;
      line-height: 1.35;
    }

    #viewer-help {
      position: fixed;
      left: 12px;
      bottom: 12px;
      z-index: 10;
      box-sizing: border-box;
      max-width: calc(100vw - 24px);
      padding: 7px 9px;
      border: 1px solid rgba(255, 255, 255, .2);
      border-radius: 6px;
      background: rgba(16, 24, 32, .82);
      color: #dce7ef;
      font-size: 12px;
      line-height: 1.35;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .rotation-heading {
      margin-bottom: 8px;
      font-size: 13px;
      font-weight: 700;
    }

    #rotation-values,
    #rotation-query {
      display: block;
      margin-bottom: 6px;
      padding: 6px 7px;
      border-radius: 4px;
      background: rgba(255, 255, 255, .08);
      color: #f4f7fb;
      font-family: Consolas, Monaco, monospace;
      font-size: 12px;
      font-variant-numeric: tabular-nums;
      overflow-wrap: anywhere;
    }

    .rotation-row {
      display: grid;
      grid-template-columns: 28px minmax(0, 1fr) 68px;
      gap: 7px;
      align-items: center;
      min-height: 34px;
    }

    .rotation-row label {
      font-weight: 700;
      color: #dce7ef;
    }

    .rotation-row input[type="range"] {
      width: 100%;
      accent-color: #2dd4bf;
    }

    .rotation-row input[type="number"] {
      width: 68px;
      box-sizing: border-box;
      padding: 5px 6px;
      border: 1px solid rgba(255, 255, 255, .25);
      border-radius: 4px;
      background: rgba(255, 255, 255, .08);
      color: #f4f7fb;
      font: inherit;
      font-variant-numeric: tabular-nums;
    }

    .rotation-row select {
      grid-column: 2 / 4;
      min-width: 0;
      box-sizing: border-box;
      padding: 5px 6px;
      border: 1px solid rgba(255, 255, 255, .25);
      border-radius: 4px;
      background: rgba(255, 255, 255, .08);
      color: #f4f7fb;
      font: inherit;
      color-scheme: dark;
    }

    .rotation-row select option {
      background: #101820;
      color: #f4f7fb;
    }

    .rotation-actions {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-top: 8px;
    }

    .rotation-actions button {
      min-height: 30px;
      border: 1px solid rgba(255, 255, 255, .25);
      border-radius: 4px;
      background: rgba(255, 255, 255, .1);
      color: #f4f7fb;
      font: inherit;
      cursor: pointer;
    }

    .rotation-actions button:hover {
      background: rgba(255, 255, 255, .18);
    }

    @media (max-width: 720px) {
      #rotation-panel {
        right: 12px;
        width: auto;
      }

      #status {
        left: 12px;
        top: auto;
        bottom: 12px;
        max-width: calc(100vw - 24px);
      }

      #viewer-help {
        bottom: 86px;
      }
    }
  </style>
  <script type="importmap">
    {
      "imports": {
        "three": "/john_web/assets/vendor/three/0.155.0/build/three.module.js",
        "@mkkellogg/gaussian-splats-3d": "/john_web/assets/vendor/gaussian-splats-3d/0.4.7/build/gaussian-splats-3d.module.js"
      }
    }
  </script>
</head>
<body>
  <div id="viewer-root"></div>
  <aside id="rotation-panel" aria-label="旋轉控制 Rotation controls">
    <div class="rotation-heading">旋轉 Rotation</div>
    <output id="rotation-values">rx=0 ry=0 rz=0</output>
    <output id="rotation-query">rx=0&amp;ry=0&amp;rz=0</output>
    <div class="rotation-row">
      <label for="rotation-rx">RX</label>
      <input id="rotation-rx" data-rotation-axis="rx" type="range" min="-360" max="360" step="1" value="0">
      <input id="rotation-rx-value" data-rotation-axis="rx" type="number" min="-360" max="360" step="0.25" value="0">
    </div>
    <div class="rotation-row">
      <label for="rotation-ry">RY</label>
      <input id="rotation-ry" data-rotation-axis="ry" type="range" min="-360" max="360" step="1" value="0">
      <input id="rotation-ry-value" data-rotation-axis="ry" type="number" min="-360" max="360" step="0.25" value="0">
    </div>
    <div class="rotation-row">
      <label for="rotation-rz">RZ</label>
      <input id="rotation-rz" data-rotation-axis="rz" type="range" min="-360" max="360" step="1" value="0">
      <input id="rotation-rz-value" data-rotation-axis="rz" type="number" min="-360" max="360" step="0.25" value="0">
    </div>
    <div class="rotation-row">
      <label for="rotation-up">上方向 UP</label>
      <select id="rotation-up" data-camera-up-mode>
        <option value="view">view</option>
        <option value="world">world</option>
        <option value="world-flip">world-flip</option>
        <option value="scene">scene</option>
        <option value="scene-flip">scene-flip</option>
      </select>
    </div>
    <div class="rotation-actions">
      <button id="rotation-reset" type="button">重設 Reset</button>
      <button id="rotation-copy" type="button">複製 Copy</button>
    </div>
  </aside>
  <div id="viewer-help">滑鼠拖曳旋轉 / 右鍵平移 / 滾輪縮放 / W/F 前進 / S/B 後退 / A/D 左右</div>
  <div id="status">
    <div id="status-text">載入中 Loading</div>
    <div id="download-progress" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0" hidden>
      <span id="download-progress-fill"></span>
    </div>
    <small id="download-progress-text" hidden>0%</small>
  </div>
  <script>
    window.GS_SPLAT_VIEWER_BOOTSTRAP = <?=$bootstrapJson;?>;
  </script>
  <script type="module" src="js/gaussian_splat_viewer.js?v=20260630-download-progress"></script>
</body>
</html>
