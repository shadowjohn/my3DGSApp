<?php
  if(session_status() === PHP_SESSION_NONE) @session_start();

  $chars = "3456789ABCDEFGHJKMNPQRSTUVWXY";
  $code = "";
  for($i = 0; $i < 4; $i++){
      $code .= $chars[random_int(0, strlen($chars) - 1)];
  }
  $_SESSION["GD_CODE"] = $code;

  $width = 112;
  $height = 44;
  $img = imagecreatetruecolor($width, $height);
  $bg = imagecolorallocate($img, 15, 23, 34);
  $fg = imagecolorallocate($img, 226, 232, 240);
  $noise = imagecolorallocate($img, 56, 189, 248);
  imagefilledrectangle($img, 0, 0, $width, $height, $bg);

  for($i = 0; $i < 35; $i++){
      imagesetpixel($img, random_int(0, $width - 1), random_int(0, $height - 1), $noise);
  }
  for($i = 0; $i < 3; $i++){
      imageline($img, random_int(0, $width), random_int(0, $height), random_int(0, $width), random_int(0, $height), $noise);
  }
  $font = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf";
  if(function_exists("imagettftext") && is_file($font)){
      for($i = 0; $i < strlen($code); $i++){
          imagettftext($img, 25, random_int(-25, 25), 10 + ($i * 24), random_int(31, 37), $fg, $font, $code[$i]);
      }
  } else {
      imagestring($img, 5, 35, 14, $code, $fg);
  }

  header("Content-Type: image/png");
  header("Cache-Control: no-store, no-cache, must-revalidate, max-age=0");
  header("Pragma: no-cache");
  imagepng($img);
  imagedestroy($img);
