<?php
  require __DIR__ . "/inc/config.php";

  $isLoggedIn = !empty($_SESSION["login_user"]);
  require "{$base_dir}/html.php";
  require "{$base_dir}/head.php";
?>
<title>Focusit Studio</title>
<?php
  require "{$base_dir}/head_end.php";
  require "{$base_dir}/body.php";
  require "{$base_dir}/top.php";
?>
<main class="jw-home">
  <section class="jw-home-hero">
    <div>
      <h1>Focusit Studio</h1>
      <p>3D 重建與空間影像處理工作台</p>
    </div>
    <div class="jw-home-tags" aria-label="Focusit technology tags">
      <span>GIS</span>
      <span>MIS</span>
      <span>AI</span>
      <span>IoT</span>
    </div>
  </section>

  <section class="jw-home-grid" aria-label="Focusit Studio modules">
    <a class="jw-home-card" href="/john_web/openmvs/index.php">
      <strong>OpenMVS</strong>
      <span>MP4 / ZIP 影像重建 GLB，適合網格與模型檢視。</span>
    </a>
    <a class="jw-home-card" href="/john_web/gaussian_splat/index.php">
      <strong>GaussianSplat</strong>
      <span>快速建立 3D Gaussian Splat 場景，支援線上檢視。</span>
    </a>
    <a class="jw-home-card" href="<?=$isLoggedIn ? '/john_web/openmvs/admin.php' : '/john_web/login.php';?>">
      <strong>後台管理</strong>
      <span>管理轉檔工作、覆核狀態與系統產物。</span>
    </a>
  </section>

  <section class="jw-home-note">
    <strong>準線智慧科技</strong>
    <span>智慧環境監控、資訊平台整合與空間資料服務的內部工具入口。</span>
  </section>
</main>
<?php require "{$base_dir}/foot.php"; ?>
