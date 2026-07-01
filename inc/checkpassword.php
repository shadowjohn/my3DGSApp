<?php
  if(!function_exists('auth_current_user')){
      function auth_current_user(){
          return (isset($_SESSION["login_user"]) && is_array($_SESSION["login_user"])) ? $_SESSION["login_user"] : null;
      }
  }

  if(!function_exists('auth_is_logged_in')){
      function auth_is_logged_in(){
          return auth_current_user() !== null;
      }
  }

  if(!function_exists('auth_is_admin')){
      function auth_is_admin(){
          $user = auth_current_user();
          return $user && (int)($user['is_admin'] ?? 0) === 1;
      }
  }

  if(!function_exists('auth_login_url')){
      function auth_login_url(){
          $next = $_SERVER['REQUEST_URI'] ?? '/john_web/openmvs/index.php';
          if(strpos($next, '/john_web/') !== 0) $next = '/john_web/openmvs/index.php';
          return '/john_web/login.php?next=' . rawurlencode($next);
      }
  }

  if(!function_exists('auth_require_login')){
      function auth_require_login($adminOnly=false){
          if(php_sapi_name() === 'cli') return;
          if(auth_is_logged_in() && (!$adminOnly || auth_is_admin())) return;
          $loginUrl = auth_login_url();
          header("Location: {$loginUrl}");
          exit();
      }
  }

  auth_require_login();
