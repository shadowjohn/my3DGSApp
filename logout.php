<?php
  require __DIR__ . "/inc/config.php";
  unset($_SESSION["login_user"]);
  session_regenerate_id(true);
  header("Location: /john_web/login.php");
  exit();
