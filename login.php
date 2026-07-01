<?php
  require __DIR__ . "/inc/config.php";

  function login_safe_next($next){
      $next = trim((string)$next);
      if($next === '') return '/john_web/openmvs/index.php';
      if(preg_match('~^https?://~i', $next) || strpos($next, '//') === 0) return '/john_web/openmvs/index.php';
      if(strpos($next, '/john_web/') === 0) return $next;
      if($next[0] !== '/') return '/john_web/' . ltrim($next, '/');
      return '/john_web/openmvs/index.php';
  }

  $next = login_safe_next($_POST['next'] ?? ($_GET['next'] ?? ''));
  $error = '';

  if($_SERVER['REQUEST_METHOD'] === 'POST'){
      $loginid = trim((string)($_POST['loginid'] ?? ''));
      $loginpd = (string)($_POST['loginpd'] ?? '');
      $gdcode = strtoupper(trim((string)($_POST['gdcode'] ?? '')));
      $sessionCode = strtoupper((string)($_SESSION['GD_CODE'] ?? ''));

      if($gdcode === '' || $sessionCode === '' || !hash_equals($sessionCode, $gdcode)){
          $error = '驗證碼錯誤';
      } else if($loginid === '' || $loginpd === ''){
          $error = '請輸入帳號與密碼';
      } else {
          $rows = selectSQL_SAFE_EX("
              SELECT `id`,`loginid`,`name`,`is_admin`,`loginpd`
              FROM `users`
              WHERE `loginid`=:loginid AND `del`='0'
              LIMIT 1
          ", ['loginid'=>$loginid]);
          $row = $rows[0] ?? null;
          $passwordHash = hash('sha256', $loginpd);
          if($row && hash_equals((string)$row['loginpd'], $passwordHash)){
              session_regenerate_id(true);
              $_SESSION["login_user"] = [
                  'id'=>(int)$row['id'],
                  'loginid'=>(string)$row['loginid'],
                  'name'=>(string)$row['name'],
                  'is_admin'=>(int)$row['is_admin'],
              ];
              unset($_SESSION['GD_CODE']);
              header("Location: {$next}");
              exit();
          }
          $error = '帳號或密碼錯誤';
      }
  }

  if(!empty($_SESSION["login_user"]) && $_SERVER['REQUEST_METHOD'] !== 'POST'){
      header("Location: {$next}");
      exit();
  }

  require "{$base_dir}/html.php";
  require "{$base_dir}/head.php";
?>
<title>登入</title>
<?php
  require "{$base_dir}/head_end.php";
  require "{$base_dir}/body.php";
  require "{$base_dir}/top.php";
?>
<main class="jw-login-page">
  <section class="jw-login-card">
    <div class="jw-login-status">
      <span>Focusit Studio</span>
      <span id="loginClock"><?=date('H:i:s');?></span>
    </div>
    <p class="jw-login-kicker">ADMIN ACCESS</p>
    <h1>後台管理者登入</h1>
    <p class="jw-login-subtitle">Focusit Studio 管理工作台</p>
    <?php if($error !== ''): ?>
      <div class="jw-login-message"><?=htmlspecialchars($error, ENT_QUOTES);?></div>
    <?php endif; ?>
    <form class="jw-login-form" method="post" autocomplete="off">
      <input type="hidden" name="next" value="<?=htmlspecialchars($next, ENT_QUOTES);?>">
      <label class="jw-login-field">
        <span>帳號</span>
        <input type="text" name="loginid" maxlength="80" autocomplete="username" required>
      </label>
      <label class="jw-login-field">
        <span>密碼</span>
        <input type="password" name="loginpd" maxlength="160" autocomplete="current-password" required>
      </label>
      <div class="jw-login-gd">
        <label class="jw-login-field">
          <span>驗證碼</span>
          <input type="text" name="gdcode" maxlength="4" autocomplete="off" autocapitalize="characters" required>
        </label>
        <img src="/john_web/gd.php?_t=<?=time();?>" alt="重新產生驗證碼" title="重新產生驗證碼" onclick="this.src='/john_web/gd.php?_t=' + Date.now();">
      </div>
      <div class="jw-login-actions">
        <button type="submit">確定登入</button>
      </div>
    </form>
  </section>
</main>
<script>
function updateLoginClock() {
  var el = document.getElementById("loginClock");
  if (!el) return;
  el.textContent = new Date().toLocaleTimeString("zh-TW", { hour12: false });
}
updateLoginClock();
setInterval(updateLoginClock, 1000);
</script>
<?php require "{$base_dir}/foot.php"; ?>
