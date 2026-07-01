<?php
    $asset_url = (isset($asset_url) && $asset_url !== "") ? $asset_url : "/john_web/assets";
    $css_url = (isset($css_url) && $css_url !== "") ? $css_url : "/john_web/css";
    $js_url = (isset($js_url) && $js_url !== "") ? $js_url : "/john_web/js";
    $include_mode = (isset($include_mode) && !empty($include_mode)) ? (string)$include_mode : "";
    $include_modes = array_values(array_filter(array_map('trim', preg_split('/[|,]+/', strtolower($include_mode)))));

    if(!function_exists('has_include_mode')){
        function has_include_mode($mode){
            global $include_modes;
            return in_array(strtolower((string)$mode), $include_modes, true);
        }
    }
?>
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width" />
    <link href="<?=$asset_url;?>/favicon.ico" rel="icon" type="image/x-icon">

    <link nonce="gg" rel="stylesheet" href="<?=$js_url;?>/bootstrap5.3.2/bootstrap.min.css">
    <link nonce="gg" rel="stylesheet" href="<?=$css_url;?>/bootstrap-icons.css">
    <link nonce="gg" rel="stylesheet" href="<?=$css_url;?>/font-awesome.min.css">
    <link nonce="gg" href="<?=$css_url;?>/layout.css" rel="stylesheet" type="text/css">
    <link nonce="gg" href="<?=$css_url;?>/basic.css" rel="stylesheet" type="text/css">
    <link nonce="gg" href="<?=$css_url;?>/main.css" rel="stylesheet" type="text/css">
    <link nonce="gg" href="<?=$css_url;?>/Mobile.css" rel="stylesheet" type="text/css">
    <link nonce="gg" href="<?=$css_url;?>/style.css" rel="stylesheet" type="text/css">
    <link nonce="gg" href="<?=$css_url;?>/john_web.css" rel="stylesheet" type="text/css">

    <?php if(has_include_mode("jquery-ui") || has_include_mode("jqueryui")): ?>
    <link nonce="gg" rel="stylesheet" href="<?=$js_url;?>/jquery-ui/jquery-ui.min.css">
    <link nonce="gg" rel="stylesheet" href="<?=$js_url;?>/jquery-ui/jquery-ui.theme.min.css">
    <?php endif; ?>

    <script nonce="gg" src="<?=$js_url;?>/jquery.min.js"></script>
    <script nonce="gg" src="<?=$js_url;?>/jquery-migrate.min.js"></script>
    <script nonce="gg" src="<?=$js_url;?>/bootstrap5.3.2/bootstrap.bundle.min.js"></script>
    <?php if(has_include_mode("jquery-ui") || has_include_mode("jqueryui")): ?>
    <script nonce="gg" src="<?=$js_url;?>/jquery-ui/jquery-ui.min.js"></script>
    <?php endif; ?>
    <script nonce="gg" src="<?=$js_url;?>/myphp.js"></script>
    <script nonce="gg" src="<?=$js_url;?>/mybox.js"></script>
    <script nonce="gg" src="<?=$js_url;?>/include.js"></script>
    <script nonce="gg">window.CSRF_TOKEN = <?= function_exists("csrf_token") ? (function_exists("my_json_encode") ? my_json_encode(csrf_token()) : json_encode(csrf_token(), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES)) : "\"\"" ?>;</script>

    <?php if(has_include_mode("threejs155") || has_include_mode("three155")): ?>
    <script type="importmap">
      {
        "imports": {
          "three": "/john_web/assets/vendor/three/0.155.0/build/three.module.js",
          "three/addons/": "/john_web/assets/vendor/three/0.155.0/examples/jsm/"
        }
      }
    </script>
    <?php elseif(has_include_mode("threejs") || has_include_mode("three")): ?>
    <script type="importmap">
      {
        "imports": {
          "three": "/john_web/assets/vendor/three/0.165.0/build/three.module.js",
          "three/addons/": "/john_web/assets/vendor/three/0.165.0/examples/jsm/"
        }
      }
    </script>
    <?php endif; ?>
