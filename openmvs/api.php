<?php
  require __DIR__ . "/../inc/config.php";

  define('OVM_MIN_VIDEO_SECONDS', 3.0);

  function ovm_json($data){
      header('Content-Type: application/json; charset=utf-8');
      echo json_encode($data, JSON_UNESCAPED_UNICODE);
      exit();
  }

  function ovm_ext($name){
      return strtolower(pathinfo($name, PATHINFO_EXTENSION));
  }

  function ovm_job_glb_path($id){
      $id = (int)$id;
      return "uploads/{$id}/exports/model.glb";
  }

  function ovm_existing_artifact_url($id, $relative){
      $id = (int)$id;
      $url = "uploads/{$id}/{$relative}";
      return is_file(__DIR__ . "/{$url}") ? $url : '';
  }

  function ovm_thumb_cache_dir(){
      return __DIR__ . "/uploads/_thumbs";
  }

  function ovm_thumb_cache_path($id){
      $id = (int)$id;
      return ovm_thumb_cache_dir() . "/{$id}.png";
  }

  function ovm_thumb_cache_url($id){
      $id = (int)$id;
      $path = ovm_thumb_cache_path($id);
      $stamp = is_file($path) ? filemtime($path) : time();
      return "uploads/_thumbs/{$id}.png?v={$stamp}";
  }

  function ovm_delete_thumb_cache($id){
      $path = ovm_thumb_cache_path($id);
      if(is_file($path)) @unlink($path);
  }

  function ovm_numeric_or_null($value){
      return is_numeric($value) ? (float)$value : null;
  }

  function ovm_format_duration_seconds($seconds){
      $text = number_format((float)$seconds, 2, '.', '');
      return rtrim(rtrim($text, '0'), '.');
  }

  function ovm_video_duration_seconds($path){
      if(!function_exists('exec') || !is_file($path)) return null;
      $cmd = "ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 " . escapeshellarg($path);
      $output = [];
      $exitCode = 0;
      @exec($cmd, $output, $exitCode);
      if($exitCode !== 0 || empty($output)) return null;
      $duration = trim((string)$output[0]);
      return is_numeric($duration) ? (float)$duration : null;
  }

  function ovm_video_duration_reject_reason($path){
      $duration = ovm_video_duration_seconds($path);
      if($duration === null) return '無法讀取影片長度，請確認 MP4 檔案可播放';
      if($duration < OVM_MIN_VIDEO_SECONDS){
          return '影片太短（' . ovm_format_duration_seconds($duration) . ' 秒）。OpenMVS 至少需要 3 秒影片，建議拍攝 10 秒以上並慢慢環繞主體。';
      }
      return '';
  }

  function ovm_zip_contains_usable_images($path){
      if(!class_exists('ZipArchive') || !is_file($path)) return false;
      $zip = new ZipArchive();
      if($zip->open($path) !== true) return false;
      $allowed = ['jpg'=>true, 'jpeg'=>true, 'png'=>true, 'tif'=>true, 'tiff'=>true];
      $usable = false;
      for($i = 0; $i < $zip->numFiles; $i++){
          $name = str_replace('\\', '/', (string)$zip->getNameIndex($i));
          if($name === '' || substr($name, -1) === '/') continue;
          $parts = explode('/', $name);
          if($name[0] === '/' || in_array('..', $parts, true)) continue;
          if(substr(strtolower($name), -9) === '.mask.png') continue;
          $ext = ovm_ext($name);
          if(isset($allowed[$ext])){
              $usable = true;
              break;
          }
      }
      $zip->close();
      return $usable;
  }

  function ovm_zip_contains_masks($path){
      if(!class_exists('ZipArchive') || !is_file($path)) return false;
      $zip = new ZipArchive();
      if($zip->open($path) !== true) return false;
      $hasMask = false;
      for($i = 0; $i < $zip->numFiles; $i++){
          $name = str_replace('\\', '/', (string)$zip->getNameIndex($i));
          if($name === '' || substr($name, -1) === '/') continue;
          $parts = explode('/', $name);
          if($name[0] === '/' || in_array('..', $parts, true)) continue;
          if(substr(strtolower($name), -9) === '.mask.png'){
              $hasMask = true;
              break;
          }
      }
      $zip->close();
      return $hasMask;
  }

  function ovm_normalize_mask_mode($mode){
      $mode = strtolower(trim((string)$mode));
      if(in_array($mode, ['provided','auto'], true)) return $mode;
      return 'none';
  }

  function ovm_normalize_quality_preset($preset){
      $preset = strtolower(trim((string)$preset));
      if(in_array($preset, ['fast','normal','high'], true)) return $preset;
      return 'normal';
  }

  function ovm_captcha_matches($gdcode){
      $sessionCode = $_SESSION['GD_CODE'] ?? '';
      return $gdcode !== '' && $sessionCode !== '' && strtoupper($gdcode) === strtoupper($sessionCode);
  }

  function ovm_mark_failed($id, $reason){
      if($id > 0){
          updateSQL_SAFE(
              'openmvs_jobs',
              ['status'=>3,'reason'=>$reason,'work_et_datetime'=>date('Y-m-d H:i:s')],
              "`id`=?",
              [$id]
          );
      }
  }

  function ovm_remove_path($path){
      if(is_link($path) || is_file($path)){
          @unlink($path);
          return;
      }
      if(!is_dir($path)) return;
      $items = scandir($path);
      if($items === false) return;
      foreach($items as $item){
          if($item === '.' || $item === '..') continue;
          ovm_remove_path($path . DIRECTORY_SEPARATOR . $item);
      }
      @rmdir($path);
  }

  function ovm_product_dir($jobId, $productType, $textureSize){
      $jobId = (int)$jobId;
      $productType = strtolower(trim((string)$productType));
      $textureSize = (int)$textureSize;
      if($jobId <= 0 || $productType !== 'glb' || $textureSize <= 0) return '';
      return "uploads/{$jobId}/products/glb_{$textureSize}";
  }

  function ovm_product_model_path($jobId, $textureSize){
      $dir = ovm_product_dir($jobId, 'glb', $textureSize);
      return $dir === '' ? '' : "{$dir}/model.glb";
  }

  function ovm_product_dir_safe_path_for_row($row, &$path=null){
      $path = null;
      $jobId = (int)($row['job_id'] ?? 0);
      $relative = ovm_product_dir($jobId, $row['product_type'] ?? '', $row['texture_size'] ?? 0);
      if($relative === '') return false;
      $uploadsRoot = realpath(__DIR__ . '/uploads');
      if($uploadsRoot === false) return false;
      $realPath = realpath(__DIR__ . "/" . $relative);
      if($realPath === false) return true;
      $allowedPrefix = $uploadsRoot . DIRECTORY_SEPARATOR . $jobId . DIRECTORY_SEPARATOR . 'products' . DIRECTORY_SEPARATOR;
      if(strpos($realPath . DIRECTORY_SEPARATOR, $allowedPrefix) !== 0) return false;
      $path = $realPath;
      return true;
  }

  function ovm_product_dir_is_safe_for_row($row){
      $path = null;
      return ovm_product_dir_safe_path_for_row($row, $path);
  }

  function ovm_remove_product_dir_for_row($row){
      $path = null;
      if(!ovm_product_dir_safe_path_for_row($row, $path)) return false;
      if($path !== null) ovm_remove_path($path);
      return true;
  }

  function ovm_job_has_running_products($id){
      $rows = selectSQL_SAFE("SELECT `id` FROM `openmvs_products` WHERE `job_id`=? AND `del`='0' AND `status`='1' LIMIT 1", [(int)$id]);
      return !empty($rows);
  }

  function ovm_clear_products_for_job($id){
      $id = (int)$id;
      if($id <= 0) return true;
      if(ovm_job_has_running_products($id)) return false;
      updateSQL_SAFE('openmvs_products', ['del'=>1], "`job_id`=? AND `del`='0' AND `status`<>'1'", [$id]);
      if(ovm_job_has_running_products($id)) return false;
      ovm_remove_path(__DIR__ . "/uploads/{$id}/products");
      return true;
  }

	  function ovm_clear_generated_outputs($id){
	      $id = (int)$id;
	      if($id <= 0) return;
	      $jobDir = __DIR__ . "/uploads/{$id}";
	      ovm_delete_thumb_cache($id);
	      foreach(['images','colmap','mvs','exports','logs','.npm-cache'] as $dir){
	          ovm_remove_path("{$jobDir}/{$dir}");
	      }
	      foreach(['.abort','process.log','input_manifest.json','colmap_manifest.json','qa_report.json','engine_contract.json','delivery_manifest.json','failure_summary.json'] as $file){
	          ovm_remove_path("{$jobDir}/{$file}");
	      }
	      ovm_remove_path("{$jobDir}/mask_manifest.json");
	      ovm_remove_path("{$jobDir}/validation");
	  }

	  function ovm_clear_diagnostics($id){
	      global $pdo;
	      if(!isset($pdo)) return;
	      try {
	          $stmt = $pdo->prepare("DELETE FROM `openmvs_job_diagnostics` WHERE `job_id`=?");
	          $stmt->execute([(int)$id]);
	      } catch(Throwable $e){
	      }
	  }

  function ovm_queue_reset_fields(){
      return [
          'status'=>0,
          'reason'=>'',
          'process_log'=>'',
          'work_st_datetime'=>null,
          'work_et_datetime'=>null,
          'current_stage'=>null,
          'current_stage_label'=>'待處理',
          'duration_seconds'=>null,
          'queue_seconds'=>null,
          'process_seconds'=>null,
          'input_frame_count'=>null,
          'registered_frame_count'=>null,
          'glb_file_size_mb'=>null,
          'mesh_file_size_mb'=>null,
          'texture_black_pixel_ratio'=>null,
          'texture_white_empty_pixel_ratio'=>null,
	          'texture_width'=>null,
	          'texture_height'=>null,
	          'texture_patch_count'=>null,
	          'diagnostic_status'=>null,
	          'diagnostic_score'=>null,
	          'diagnostic_summary'=>null,
	          'diagnostic_log_path'=>null,
	          'capture_source_type'=>null,
	          'capture_quality_score'=>null,
	          'capture_quality_grade'=>null,
	          'capture_quality_decision'=>null,
	          'capture_mask_status'=>null,
	          'capture_frame_count'=>null,
	          'capture_selected_frame_count'=>null,
	          'capture_aligned_camera_count'=>null,
	          'capture_registered_ratio'=>null,
	          'capture_warning_count'=>0,
	          'capture_updated_at'=>null,
	      ];
	  }

	  function ovm_clone_job_for_retry($row, $qualityPreset){
	      $sourceId = (int)($row['id'] ?? 0);
	      $kind = strtolower(trim((string)($row['kind'] ?? '')));
	      if($sourceId <= 0 || !in_array($kind, ['mp4','zip'], true)) return 0;

	      $sourceInput = __DIR__ . "/uploads/{$sourceId}/input/input.{$kind}";
	      if(!is_file($sourceInput)) return 0;

	      $sourceTitle = trim((string)($row['title'] ?? ''));
	      $title = $sourceTitle !== '' ? $sourceTitle . ' 重轉' : 'OpenMVS 重轉';
	      $m = [
	          'title' => $title,
	          'email' => $row['email'] ?? '',
	          'orin_filename' => $row['orin_filename'] ?? '',
	          'c_datetime' => date('Y-m-d H:i:s'),
	          'IP' => function_exists('ip') ? ip() : ($_SERVER['REMOTE_ADDR'] ?? ''),
	          'status' => 0,
	          'reason' => '',
	          'kind' => $kind,
	          'mask_mode' => ovm_normalize_mask_mode($row['mask_mode'] ?? 'none'),
	          'quality_preset' => ovm_normalize_quality_preset($qualityPreset),
	          'del' => 0,
	          'lon' => $row['lon'] ?? null,
	          'lat' => $row['lat'] ?? null,
	          'alt' => $row['alt'] ?? 0,
	          'heading' => $row['heading'] ?? null,
	          'pitch' => $row['pitch'] ?? null,
	          'roll' => $row['roll'] ?? null,
	          'scale' => $row['scale'] ?? 1,
	      ];

	      $newId = (int)insertSQL('openmvs_jobs', $m);
	      $newRoot = __DIR__ . "/uploads/{$newId}";
	      $newInputDir = "{$newRoot}/input";
	      if($newId <= 0) return 0;
	      if(!is_dir($newInputDir) && !mkdir($newInputDir, 0777, true)){
	          updateSQL_SAFE('openmvs_jobs', ['del'=>1,'reason'=>'建立複製重轉目錄失敗'], "`id`=?", [$newId]);
	          return 0;
	      }
	      if(!copy($sourceInput, "{$newInputDir}/input.{$kind}")){
	          updateSQL_SAFE('openmvs_jobs', ['del'=>1,'reason'=>'複製原始檔失敗'], "`id`=?", [$newId]);
	          return 0;
	      }

	      $sourceMode = __DIR__ . "/uploads/{$sourceId}/input/pipeline_mode.txt";
	      $modeText = is_file($sourceMode) ? (string)@file_get_contents($sourceMode) : "colmap\n";
	      if(trim($modeText) === '') $modeText = "colmap\n";
	      @file_put_contents("{$newInputDir}/pipeline_mode.txt", $modeText);
	      @chmod($newRoot, 0775);
	      @chmod($newInputDir, 0775);
	      @chmod("{$newInputDir}/input.{$kind}", 0664);
	      @chmod("{$newInputDir}/pipeline_mode.txt", 0664);
	      return $newId;
	  }

	  $mode = $_GET['mode'] ?? '';

	  switch($mode){
	      case 'getGLB':
	          $uuid = (string)($_GET['uuid'] ?? '');
	          $item = $_SESSION['openmvs_glb_tokens'][$uuid] ?? null;
	          if(!is_array($item) || (int)($item['expires'] ?? 0) < time()){
	              http_response_code(404);
	              exit('GLB not found');
	          }
	          $relative = (string)($item['path'] ?? '');
	          if(!preg_match('~^uploads/[1-9][0-9]*/(?:exports/model(?:_2048_webp)?\.glb|products/glb_(?:512|2048|4096|8192)/model\.glb)$~', $relative)){
	              http_response_code(404);
	              exit('GLB not found');
	          }
	          $path = __DIR__ . "/" . $relative;
	          if(!is_file($path)){
	              http_response_code(404);
	              exit('GLB not found');
	          }
	          $size = filesize($path);
	          while(ob_get_level() > 0) ob_end_clean();
	          header('Content-Type: model/gltf-binary');
	          header('Content-Length: ' . (string)$size);
	          header('Content-Disposition: inline; filename="openmvs-' . (int)($item['id'] ?? 0) . '.glb"');
	          header('Cache-Control: private, max-age=0, must-revalidate');
	          readfile($path);
	          exit();

	      case 'checkGD':
	          $gdcode = trim($_POST['gdcode'] ?? '');
	          if(ovm_captcha_matches($gdcode)) echo "OK";
	          exit();

      case 'upload':
          $title = trim($_POST['title'] ?? '');
          $gdcode = trim($_POST['gdcode'] ?? '');
          $email = trim($_POST['email'] ?? '');
          $maskMode = ovm_normalize_mask_mode($_POST['mask_mode'] ?? 'none');
          $qualityPreset = ovm_normalize_quality_preset($_POST['quality_preset'] ?? 'normal');
          $lon = ovm_numeric_or_null($_POST['lon'] ?? null);
          $lat = ovm_numeric_or_null($_POST['lat'] ?? null);
          $alt = is_numeric($_POST['alt'] ?? null) ? (float)$_POST['alt'] : 0.0;

          if(!ovm_captcha_matches($gdcode)) ovm_json(['status'=>'NO','reason'=>'驗證碼錯誤...']);
          $_SESSION['GD_CODE'] = "囧";

          if($title === '') ovm_json(['status'=>'NO','reason'=>'請輸入標題']);
          if(!isset($_FILES['upfile']) || $_FILES['upfile']['error'] !== 0 || ($_FILES['upfile']['size'] ?? 0) <= 0){
              ovm_json(['status'=>'NO','reason'=>'請選擇 MP4 影片或圖片 ZIP']);
          }

          $ext = ovm_ext($_FILES['upfile']['name']);
          if(!in_array($ext, ['mp4', 'zip'], true)){
              ovm_json(['status'=>'NO','reason'=>'目前僅支援 MP4 影片或 ZIP 圖片包']);
          }

          if($ext === 'mp4'){
              $durationRejectReason = ovm_video_duration_reject_reason($_FILES['upfile']['tmp_name']);
              if($durationRejectReason !== '') ovm_json(['status'=>'NO','reason'=>$durationRejectReason]);
          }

          if($ext === 'zip' && !ovm_zip_contains_usable_images($_FILES['upfile']['tmp_name'])){
              ovm_json(['status'=>'NO','reason'=>'ZIP 內沒有可用圖片']);
          }
          if($maskMode === 'provided'){
              if($ext !== 'zip') ovm_json(['status'=>'NO','reason'=>'使用 .mask.png 時請上傳 ZIP 圖片包']);
              if(!ovm_zip_contains_masks($_FILES['upfile']['tmp_name'])) ovm_json(['status'=>'NO','reason'=>'ZIP 內沒有 .mask.png 遮罩檔']);
          }

          $m = [
              'title' => $title,
              'email' => $email,
              'orin_filename' => basename($_FILES['upfile']['name']),
              'c_datetime' => date('Y-m-d H:i:s'),
              'IP' => function_exists('ip') ? ip() : ($_SERVER['REMOTE_ADDR'] ?? ''),
              'status' => 0,
              'reason' => '',
              'kind' => $ext,
              'mask_mode' => $maskMode,
              'quality_preset' => $qualityPreset,
              'del' => 0,
              'lon' => $lon,
              'lat' => $lat,
              'alt' => $alt,
              'scale' => 1,
          ];

          $id = (int)insertSQL('openmvs_jobs', $m);
          $root = __DIR__ . "/uploads/{$id}";
          $inputDir = "{$root}/input";
          if(!is_dir($inputDir) && !mkdir($inputDir, 0777, true)){
              ovm_mark_failed($id, '建立上傳目錄失敗');
              ovm_json(['status'=>'NO','reason'=>'建立上傳目錄失敗']);
          }

          $dest = "{$inputDir}/input.{$ext}";
          if(!move_uploaded_file($_FILES['upfile']['tmp_name'], $dest) || !is_file($dest)){
              ovm_mark_failed($id, '上傳後找不到檔案');
              ovm_json(['status'=>'NO','reason'=>'上傳後找不到檔案']);
          }
          @chmod($root, 0775);
          @chmod($inputDir, 0775);
          @chmod($dest, 0664);
          @file_put_contents("{$inputDir}/pipeline_mode.txt", "openmvs_native\n");
          @chmod("{$inputDir}/pipeline_mode.txt", 0664);

          ovm_json(['status'=>'OK','id'=>$id]);

      case 'get_log':
          require "{$base_dir}/inc/checkpassword.php";
          $id = (int)($_GET['id'] ?? 0);
          $rows = selectSQL_SAFE("SELECT `reason`,`process_log` FROM `openmvs_jobs` WHERE `id`=? LIMIT 1", [$id]);
	          ovm_json([
	              'status'=>'OK',
	              'reason'=>$rows[0]['reason'] ?? '',
	              'log'=>$rows[0]['process_log'] ?? '',
	              'engine_contract_url'=>ovm_existing_artifact_url($id, 'engine_contract.json'),
	              'validation_report_url'=>ovm_existing_artifact_url($id, 'validation/validation_report.json'),
	              'delivery_manifest_url'=>ovm_existing_artifact_url($id, 'delivery_manifest.json'),
	              'failure_summary_url'=>ovm_existing_artifact_url($id, 'failure_summary.json'),
	          ]);

	      case 'get_diagnostics':
	          require "{$base_dir}/inc/checkpassword.php";
	          $id = (int)($_GET['id'] ?? 0);
	          $jobs = selectSQL_SAFE("SELECT `diagnostic_status`,`diagnostic_score`,`diagnostic_summary`,`diagnostic_log_path` FROM `openmvs_jobs` WHERE `id`=? LIMIT 1", [$id]);
	          $items = selectSQL_SAFE("
	              SELECT `stage`,`pattern_id`,`severity`,`pattern_count`,`first_seen_line`,`last_seen_line`,`message_sample`,`message_summary`,`raw_log_path`,`diagnostic_category`,`diagnostic_code`,`diagnostic_severity`,`diagnostic_count`,`diagnostic_value`,`diagnostic_message`,`diagnostic_source`
	              FROM `openmvs_job_diagnostics`
	              WHERE `job_id`=?
	              ORDER BY FIELD(`severity`, 'error', 'warning', 'info'), `pattern_count` DESC
	          ", [$id]);
	          ovm_json([
	              'status'=>'OK',
	              'job'=>$jobs[0] ?? [],
	              'items'=>$items,
	          ]);

      case 'jobs_delta':
          require_once __DIR__ . "/job_view.php";
          $listState = ovm_job_list_state(15);
          $rows = $listState['rows'];
          $payload = ovm_job_delta_payload($rows);
          ovm_json([
              'status'=>'OK',
              'has_active_jobs'=>$payload['has_active_jobs'],
              'rows'=>$payload['rows'],
              'failure_reasons'=>$payload['failure_reasons'],
          ]);

      case 'save_thumb':
          $id = (int)($_POST['id'] ?? 0);
          $image = (string)($_POST['image'] ?? '');
          if($id <= 0) ovm_json(['status'=>'NO','reason'=>'縮圖工作編號錯誤']);

          $rows = selectSQL_SAFE("SELECT `id`,`status`,`del` FROM `openmvs_jobs` WHERE `id`=? LIMIT 1", [$id]);
          if(empty($rows) || (string)($rows[0]['del'] ?? '1') !== '0' || (string)($rows[0]['status'] ?? '') !== '2'){
              ovm_json(['status'=>'NO','reason'=>'工作尚未完成，不能儲存縮圖']);
          }
          if(!is_file(__DIR__ . "/" . ovm_job_glb_path($id))){
              ovm_json(['status'=>'NO','reason'=>'找不到 GLB，不能儲存縮圖']);
          }
          if(!preg_match('~^data:image/png;base64,([A-Za-z0-9+/=]+)$~', $image, $m)){
              ovm_json(['status'=>'NO','reason'=>'縮圖格式錯誤']);
          }

          $bin = base64_decode($m[1], true);
          if($bin === false || strlen($bin) < 100 || strlen($bin) > 1024 * 1024 || substr($bin, 0, 8) !== "\x89PNG\r\n\x1a\n"){
              ovm_json(['status'=>'NO','reason'=>'縮圖資料錯誤']);
          }

          $dir = ovm_thumb_cache_dir();
          if(!is_dir($dir) && !mkdir($dir, 0777, true)){
              ovm_json(['status'=>'NO','reason'=>'thumb dir not writable']);
          }
          if(!is_dir($dir) || !is_writable($dir)){
              ovm_json(['status'=>'NO','reason'=>'thumb dir not writable']);
          }

          $path = ovm_thumb_cache_path($id);
          if(file_put_contents($path, $bin, LOCK_EX) === false){
              ovm_json(['status'=>'NO','reason'=>'縮圖寫入失敗']);
          }
          @chmod($path, 0666);
          ovm_json(['status'=>'OK','url'=>ovm_thumb_cache_url($id)]);

      case 'save_transform':
          require "{$base_dir}/inc/checkpassword.php";
          $id = (int)($_POST['id'] ?? 0);
          $data = json_decode(base64_decode($_POST['data'] ?? ''), true);
          if($id <= 0 || !is_array($data)) ovm_json(['status'=>'NO','reason'=>'定位資料格式錯誤']);

          $fields = [];
          foreach(['lon','lat','alt','heading','pitch','roll','scale'] as $key){
              if(isset($data[$key]) && is_numeric($data[$key])) $fields[$key] = (float)$data[$key];
          }
          if($fields) updateSQL_SAFE('openmvs_jobs', $fields, "`id`=?", [$id]);

          $jobDir = __DIR__ . "/uploads/{$id}";
          if(!is_dir($jobDir) && !mkdir($jobDir, 0777, true)){
              ovm_json(['status'=>'NO','reason'=>'建立工作目錄失敗']);
          }
          $json = json_encode($data, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
          if(file_put_contents("{$jobDir}/transform.json", $json . "\n") === false){
              ovm_json(['status'=>'NO','reason'=>'儲存定位資料失敗']);
          }
          @chmod("{$jobDir}/transform.json", 0644);
          ovm_json(['status'=>'OK']);

      case 'product_action':
          require "{$base_dir}/inc/checkpassword.php";
          require_once __DIR__ . "/job_view.php";
          $action = $_POST['action'] ?? '';

          if($action === 'create_glb'){
              $jobId = (int)($_POST['job_id'] ?? 0);
              $textureSize = (int)($_POST['texture_size'] ?? 0);
              if($jobId <= 0) ovm_json(['status'=>'NO','reason'=>'工作編號錯誤']);
              if(!ovm_product_texture_size_valid($textureSize)) ovm_json(['status'=>'NO','reason'=>'貼圖尺寸錯誤']);

              $jobs = selectSQL_SAFE("SELECT `id`,`status`,`del` FROM `openmvs_jobs` WHERE `id`=? LIMIT 1", [$jobId]);
              if(empty($jobs) || (string)($jobs[0]['del'] ?? '1') !== '0'){
                  ovm_json(['status'=>'NO','reason'=>'找不到這筆工作']);
              }
              if((string)($jobs[0]['status'] ?? '') !== '2'){
                  ovm_json(['status'=>'NO','reason'=>'工作尚未完成，不能建立產品']);
              }

              $response = null;
              $locked = false;
              try {
                  $pdo->exec("LOCK TABLES `openmvs_products` WRITE");
                  $locked = true;
                  $failed = selectSQL_SAFE("SELECT * FROM `openmvs_products` WHERE `job_id`=? AND `product_type`='glb' AND `texture_size`=? AND `del`='0' AND `status`='3' LIMIT 1", [$jobId, $textureSize]);
                  if(!empty($failed)){
                      if(!ovm_remove_product_dir_for_row($failed[0])){
                          $response = ['status'=>'NO','reason'=>'產品目錄不安全，已略過重產'];
                          throw new RuntimeException('unsafe product dir');
                      }
                      updateSQL_SAFE('openmvs_products', [
                          'status'=>0,
                          'source_product_id'=>null,
                          'file_path'=>'',
                          'file_size_mb'=>null,
                          'reason'=>'',
                          'error_message'=>'',
                          'process_log'=>'',
                          'current_stage'=>'',
                          'work_st_datetime'=>null,
                          'work_et_datetime'=>null,
                      ], "`id`=?", [(int)$failed[0]['id']]);
                      $response = ['status'=>'OK','id'=>(int)$failed[0]['id'],'reset'=>true];
                  } else if(!empty($existing = selectSQL_SAFE("SELECT `id` FROM `openmvs_products` WHERE `job_id`=? AND `product_type`='glb' AND `texture_size`=? AND `del`='0' LIMIT 1", [$jobId, $textureSize]))){
                      $response = ['status'=>'OK','id'=>(int)$existing[0]['id'],'existing'=>true];
                  } else {
                      $productId = (int)insertSQL('openmvs_products', [
                          'job_id'=>$jobId,
                          'product_type'=>'glb',
                          'texture_size'=>$textureSize,
                          'status'=>0,
                          'createAt'=>date('Y-m-d H:i:s'),
                          'del'=>0,
                      ]);
                      $response = ['status'=>'OK','id'=>$productId,'existing'=>false];
                  }
              } catch(Throwable $e){
                  if($response === null) $response = ['status'=>'NO','reason'=>'產品佇列鎖定失敗'];
              }
              if($locked){
                  try {
                      $pdo->exec("UNLOCK TABLES");
                  } catch(Throwable $e){
                      $response = ['status'=>'NO','reason'=>'產品佇列解鎖失敗'];
                  }
              }
              ovm_json($response);
          }

          if($action === 'delete'){
              $productId = (int)($_POST['product_id'] ?? 0);
              if($productId <= 0) ovm_json(['status'=>'NO','reason'=>'產品編號錯誤']);
              $products = selectSQL_SAFE("SELECT * FROM `openmvs_products` WHERE `id`=? AND `del`='0' LIMIT 1", [$productId]);
              if(empty($products)) ovm_json(['status'=>'NO','reason'=>'找不到這筆產品']);
              if(!in_array((string)($products[0]['status'] ?? ''), ['0','2','3','4'], true)){
                  ovm_json(['status'=>'NO','reason'=>'產製中不能刪除']);
              }
              if(!ovm_product_dir_is_safe_for_row($products[0])){
                  ovm_json(['status'=>'NO','reason'=>'產品目錄不安全，已略過刪除']);
              }
              $deleteStmt = $pdo->prepare("UPDATE `openmvs_products` SET `del`='1' WHERE `id`=? AND `del`='0' AND `status` IN ('0','2','3','4')");
              $deleteStmt->execute([$productId]);
              if($deleteStmt->rowCount() <= 0){
                  ovm_json(['status'=>'NO','reason'=>'產品狀態已變更，請重新整理']);
              }
              ovm_remove_product_dir_for_row($products[0]);
              ovm_json(['status'=>'OK']);
          }

          ovm_json(['status'=>'NO','reason'=>'未知的產品操作']);

      case 'admin_action':
          require "{$base_dir}/inc/checkpassword.php";
          $id = (int)($_POST['id'] ?? 0);
          $action = $_POST['action'] ?? '';
          if($id <= 0) ovm_json(['status'=>'NO','reason'=>'工作編號錯誤']);
          $rows = selectSQL_SAFE("SELECT * FROM `openmvs_jobs` WHERE `id`=? LIMIT 1", [$id]);
          if(empty($rows) || (string)($rows[0]['del'] ?? '1') !== '0'){
              ovm_json(['status'=>'NO','reason'=>'找不到這筆工作']);
          }
          $currentStatus = (string)($rows[0]['status'] ?? '');

	          if($action === 'retry'){
	              if(!in_array($currentStatus, ['2','3'], true)) ovm_json(['status'=>'NO','reason'=>'只有失敗或已完成的工作可以重轉']);
	              $qualityPreset = ovm_normalize_quality_preset($_POST['quality_preset'] ?? ($rows[0]['quality_preset'] ?? 'normal'));
	              $retryMode = strtolower(trim((string)($_POST['retry_mode'] ?? 'current')));
	              if($retryMode === 'retry_clone') $retryMode = 'clone';
	              if(!in_array($retryMode, ['current','clone'], true)) $retryMode = 'current';
	              if($retryMode === 'clone'){
	                  $newId = ovm_clone_job_for_retry($rows[0], $qualityPreset);
	                  if($newId <= 0) ovm_json(['status'=>'NO','reason'=>'複製重轉失敗']);
	                  ovm_json(['status'=>'OK','id'=>$newId,'retry_mode'=>'clone']);
	              }
	              if(!ovm_clear_products_for_job($id)) ovm_json(['status'=>'NO','reason'=>'產品產製中，請稍後重轉']);
	              ovm_clear_generated_outputs($id);
	              ovm_clear_diagnostics($id);
	              updateSQL_SAFE(
	                  'openmvs_jobs',
	                  array_merge(ovm_queue_reset_fields(), ['quality_preset'=>$qualityPreset]),
                  "`id`=?",
                  [$id]
              );
              ovm_json(['status'=>'OK','id'=>$id,'retry_mode'=>'current']);
          }

	          if($action === 'start'){
	              if($currentStatus !== '4') ovm_json(['status'=>'NO','reason'=>'只能啟動暫停中的工作']);
	              if(!ovm_clear_products_for_job($id)) ovm_json(['status'=>'NO','reason'=>'產品產製中，請稍後啟動']);
	              ovm_clear_generated_outputs($id);
	              ovm_clear_diagnostics($id);
	              updateSQL_SAFE(
	                  'openmvs_jobs',
                  ovm_queue_reset_fields(),
                  "`id`=?",
                  [$id]
              );
              ovm_json(['status'=>'OK']);
          }

          if($action === 'abort'){
              if($currentStatus !== '1') ovm_json(['status'=>'NO','reason'=>'轉檔中才能暫停']);
              $dir = __DIR__ . "/uploads/{$id}";
              if(is_dir($dir)) file_put_contents("{$dir}/.abort", date('Y-m-d H:i:s'));
              updateSQL_SAFE(
                  'openmvs_jobs',
                  ['status'=>4,'reason'=>'暫停','work_et_datetime'=>date('Y-m-d H:i:s')],
                  "`id`=?",
                  [$id]
              );
              ovm_json(['status'=>'OK']);
          }

          if($action === 'delete'){
              if(!in_array($currentStatus, ['0','4','2','3'], true)){
                  ovm_json(['status'=>'NO','reason'=>'這個狀態不能刪除']);
              }
              ovm_remove_path(__DIR__ . "/uploads/{$id}/.abort");
              updateSQL_SAFE(
                  'openmvs_jobs',
                  ['del'=>1],
                  "`id`=?",
                  [$id]
              );
              ovm_json(['status'=>'OK']);
          }

          ovm_json(['status'=>'NO','reason'=>'未知的操作']);
  }

  ovm_json(['status'=>'NO','reason'=>'未知模式']);
?>
