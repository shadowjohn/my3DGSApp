<?php
  $jwTopScript = (string)($_SERVER['SCRIPT_NAME'] ?? '');
  $jwTopCurrent = '';
  if(strpos($jwTopScript, '/openmvs/') !== false) $jwTopCurrent = 'openmvs';
  if(strpos($jwTopScript, '/gaussian_splat/') !== false) $jwTopCurrent = 'gaussian_splat';
  if(strpos($jwTopScript, '/login.php') !== false) $jwTopCurrent = 'login';
  $jwTopUser = (isset($_SESSION["login_user"]) && is_array($_SESSION["login_user"])) ? $_SESSION["login_user"] : null;
  $jwTopUserName = $jwTopUser ? trim((string)($jwTopUser['name'] ?? $jwTopUser['loginid'] ?? '')) : '';
  if($jwTopUserName === '') $jwTopUserName = '已登入';
?>
<nav class="jw-topbar" aria-label="主選單">
  <div class="jw-topbar-inner">
    <a class="jw-brand" href="/john_web/">Focusit Studio</a>
    <div class="jw-nav">
      <a class="<?=$jwTopCurrent === 'openmvs' ? 'is-active' : '';?>" href="/john_web/openmvs/index.php">OpenMVS</a>
      <a class="<?=$jwTopCurrent === 'gaussian_splat' ? 'is-active' : '';?>" href="/john_web/gaussian_splat/index.php">GaussianSplat</a>
    </div>
    <div class="jw-user">
      <?php if($jwTopUser): ?>
        <span class="jw-user-name"><?=htmlspecialchars($jwTopUserName, ENT_QUOTES);?></span>
        <a href="/john_web/logout.php">登出</a>
      <?php else: ?>
        <a class="<?=$jwTopCurrent === 'login' ? 'is-active' : '';?>" href="/john_web/login.php">登入</a>
      <?php endif; ?>
    </div>
  </div>
</nav>
