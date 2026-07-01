<?php
  $GLOBAL_USER_AGENT = 'Mozilla/5.0';
  @ini_set('user_agent', $GLOBAL_USER_AGENT);
  $SP = DIRECTORY_SEPARATOR;
  $base_dir = "/var/www/html/john_web";
  if(session_status() === PHP_SESSION_NONE) @session_start();

  // 請在站台外部建立實際 DB 連線檔，避免帳密進版控。
  require "/var/www/db_conn.php";
  require "{$base_dir}{$SP}inc{$SP}include.php";
