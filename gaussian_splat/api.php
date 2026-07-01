<?php
  require __DIR__ . "/../inc/config.php";
  require_once __DIR__ . "/job_view.php";

  define('GS_MIN_VIDEO_SECONDS', 3.0);

  function gs_json($data){
      header('Content-Type: application/json; charset=utf-8');
      echo json_encode($data, JSON_UNESCAPED_UNICODE);
      exit();
  }

  function gs_plain_error($statusCode, $message){
      http_response_code((int)$statusCode);
      header('Content-Type: text/plain; charset=utf-8');
      echo $message;
      exit();
  }

  function gs_ext($name){
      return strtolower(pathinfo($name, PATHINFO_EXTENSION));
  }

  function gs_zip_image_entries($path){
      if(!class_exists('ZipArchive') || !is_file($path)) return [];
      $zip = new ZipArchive();
      if($zip->open($path) !== true) return [];
      $entries = [];
      for($i = 0; $i < $zip->numFiles; $i++){
          $name = (string)$zip->getNameIndex($i);
          $cleanName = str_replace('\\', '/', $name);
          $base = basename($cleanName);
          if($cleanName === '' || substr($cleanName, -1) === '/' || $base === '' || $base[0] === '.') continue;
          if(strpos($cleanName, '__MACOSX/') === 0 || strpos($cleanName, '/__MACOSX/') !== false) continue;
          $ext = gs_ext($base);
          if(in_array($ext, ['jpg','jpeg','png'], true)){
              $entries[] = ['index'=>$i, 'name'=>$cleanName, 'ext'=>$ext];
          }
      }
      $zip->close();
      usort($entries, function($a, $b){
          return strnatcasecmp($a['name'], $b['name']);
      });
      return $entries;
  }

  function gs_zip_image_reject_reason($path){
      if(!class_exists('ZipArchive')) return 'PHP ZipArchive 未啟用，無法讀取 ZIP';
      $count = count(gs_zip_image_entries($path));
      if($count < 8) return 'ZIP 圖片至少需要 8 張 JPG/PNG，請確認壓縮檔內容';
      return '';
  }

  function gs_extract_zip_images($zipPath, $targetDir){
      $entries = gs_zip_image_entries($zipPath);
      if(count($entries) < 8) return false;
      if(is_dir($targetDir)){
          foreach(scandir($targetDir) ?: [] as $child){
              if($child === '.' || $child === '..') continue;
              gs_delete_reconvert_path($targetDir . DIRECTORY_SEPARATOR . $child);
          }
      } elseif(!mkdir($targetDir, 0777, true)){
          return false;
      }

      $zip = new ZipArchive();
      if($zip->open($zipPath) !== true) return false;
      $i = 1;
      foreach($entries as $entry){
          $source = $zip->getStream((string)$zip->getNameIndex((int)$entry['index']));
          if(!$source){
              $zip->close();
              return false;
          }
          $ext = $entry['ext'] === 'jpeg' ? 'jpg' : $entry['ext'];
          $dest = sprintf('%s/frame_%05d.%s', $targetDir, $i, $ext);
          $out = fopen($dest, 'wb');
          if(!$out){
              fclose($source);
              $zip->close();
              return false;
          }
          stream_copy_to_stream($source, $out);
          fclose($source);
          fclose($out);
          if(@getimagesize($dest) === false){
              $zip->close();
              return false;
          }
          @chmod($dest, 0664);
          $i++;
      }
      $zip->close();
      @chmod($targetDir, 0775);
      return true;
  }

  function gs_numeric_or_null($value){
      return is_numeric($value) ? (float)$value : null;
  }

  function gs_pipeline_mode_or_null($value){
      $value = trim((string)$value);
      if($value === '') return 'fast';
      return in_array($value, ['fast','qa','premium'], true) ? $value : null;
  }

  function gs_format_duration_seconds($seconds){
      $text = number_format((float)$seconds, 2, '.', '');
      return rtrim(rtrim($text, '0'), '.');
  }

  function gs_video_duration_seconds($path){
      if(!function_exists('exec') || !is_file($path)) return null;

      $cmd = "ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 " . escapeshellarg($path);
      $output = [];
      $exitCode = 0;
      @exec($cmd, $output, $exitCode);
      if($exitCode !== 0 || empty($output)) return null;

      $duration = trim((string)$output[0]);
      return is_numeric($duration) ? (float)$duration : null;
  }

  function gs_video_duration_reject_reason($path){
      $duration = gs_video_duration_seconds($path);
      if($duration === null){
          return '無法讀取影片長度，請確認 MP4 檔案可播放';
      }
      if($duration < GS_MIN_VIDEO_SECONDS){
          return '影片太短（' . gs_format_duration_seconds($duration) . ' 秒）。Gaussian Splat 至少需要 3 秒影片，建議拍攝 10 秒以上並慢慢環繞主體。';
      }
      return '';
  }

  function gs_public_splat_artifact($artifact){
      return [
          'uuid'=>$artifact['uuid'],
          'job_id'=>$artifact['job_id'],
          'format'=>$artifact['format'],
          'mime_type'=>$artifact['mime_type'],
          'size_bytes'=>$artifact['size_bytes'],
          'url'=>$artifact['url'],
      ];
  }

  function gs_stream_splat_artifact($artifact){
      if(!$artifact) gs_plain_error(404, 'artifact not found');
      $path = (string)($artifact['realpath'] ?? '');
      $ext = strtolower((string)($artifact['format'] ?? ''));
      if(!in_array($ext, ['ply','splat','ksplat','spz'], true)){
          gs_plain_error(415, 'unsupported splat extension');
      }
      if($path === '' || !is_file($path)) gs_plain_error(404, 'artifact not found');
      $size = filesize($path);
      if($size === false) gs_plain_error(404, 'artifact not found');

      $start = 0;
      $end = (int)$size - 1;
      $range = trim((string)($_SERVER['HTTP_RANGE'] ?? ''));
      if($range !== ''){
          if(!preg_match('/^bytes=(\d*)-(\d*)$/', $range, $m)) gs_plain_error(416, 'invalid range');
          if($m[1] === '' && $m[2] === '') gs_plain_error(416, 'invalid range');
          if($m[1] === ''){
              $suffix = (int)$m[2];
              $start = max(0, (int)$size - $suffix);
          } else {
              $start = (int)$m[1];
              if($m[2] !== '') $end = min((int)$end, (int)$m[2]);
          }
          if($start > $end || $start >= $size){
              header("Content-Range: bytes */{$size}");
              gs_plain_error(416, 'invalid range');
          }
          http_response_code(206);
          header("Content-Range: bytes {$start}-{$end}/{$size}");
      }

      header('Content-Type: application/octet-stream');
      header('Accept-Ranges: bytes');
      header('Content-Disposition: inline; filename="' . basename($path) . '"');
      header('Content-Length: ' . ((int)$end - (int)$start + 1));
      if(($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'HEAD') exit();

      $fp = fopen($path, 'rb');
      if(!$fp) gs_plain_error(404, 'artifact not found');
      fseek($fp, (int)$start);
      $remaining = (int)$end - (int)$start + 1;
      while($remaining > 0 && !feof($fp)){
          $chunk = fread($fp, min(1048576, $remaining));
          if($chunk === false || $chunk === '') break;
          echo $chunk;
          $remaining -= strlen($chunk);
          flush();
      }
      fclose($fp);
      exit();
  }

  function gs_captcha_matches($gdcode){
      $sessionCode = $_SESSION['GD_CODE'] ?? '';
      return $gdcode !== '' && $sessionCode !== '' && strtoupper($gdcode) === strtoupper($sessionCode);
  }

  function gs_mark_failed($id, $reason){
      if($id > 0){
          updateSQL_SAFE(
              'gaussian_splat_jobs',
              ['status'=>3,'reason'=>$reason,'work_et_datetime'=>date('Y-m-d H:i:s')],
              "`id`=?",
              [$id]
          );
      }
  }

  function gs_reconvert_source_input($sourceRow){
      $sourceId = (int)($sourceRow['id'] ?? 0);
      $kind = strtolower((string)($sourceRow['kind'] ?? 'mp4'));
      $sourceInput = __DIR__ . "/uploads/{$sourceId}/input/input.{$kind}";
      if(!is_file($sourceInput)){
          $matches = glob(__DIR__ . "/uploads/{$sourceId}/input/input.*");
          $sourceInput = $matches[0] ?? '';
          $kind = $sourceInput !== '' ? strtolower(pathinfo($sourceInput, PATHINFO_EXTENSION)) : $kind;
      }
      if($sourceId <= 0 || $sourceInput === '' || !is_file($sourceInput)){
          gs_json(['status'=>'NO','reason'=>'找不到來源檔']);
      }
      return [$sourceId, $kind, $sourceInput];
  }

  function gs_delete_reconvert_path($path){
      if(is_dir($path) && !is_link($path)){
          foreach(scandir($path) ?: [] as $child){
              if($child === '.' || $child === '..') continue;
              gs_delete_reconvert_path($path . DIRECTORY_SEPARATOR . $child);
          }
          @rmdir($path);
          return;
      }
      if(is_file($path) || is_link($path)) @unlink($path);
  }

  function gs_reset_reconvert_job($sourceRow, $pipelineMode){
      [$sourceId, $kind, $sourceInput] = gs_reconvert_source_input($sourceRow);
      $jobDir = __DIR__ . "/uploads/{$sourceId}";
      $realUploads = realpath(__DIR__ . "/uploads");
      $realJobDir = realpath($jobDir);
      if(!$realUploads || !$realJobDir || strpos($realJobDir, $realUploads . DIRECTORY_SEPARATOR) !== 0){
          gs_json(['status'=>'NO','reason'=>'重轉目錄錯誤']);
      }
      gs_delete_thumb_cache($sourceId);
      foreach(scandir($realJobDir) ?: [] as $child){
          if($child === '.' || $child === '..' || $child === 'input') continue;
          gs_delete_reconvert_path($realJobDir . DIRECTORY_SEPARATOR . $child);
      }
      if($kind === 'zip' && !gs_extract_zip_images($sourceInput, "{$jobDir}/images")){
          gs_json(['status'=>'NO','reason'=>'ZIP 圖片解壓失敗']);
      }

      $labels = ['fast'=>'快速', 'qa'=>'標準', 'premium'=>'精緻'];
      $label = $labels[$pipelineMode] ?? $labels['fast'];
      $baseTitle = trim((string)($sourceRow['title'] ?? $sourceRow['orin_filename'] ?? '3DGS'));
      $baseTitle = preg_replace('/[- ]*(快速|標準|精緻|驗證|進階)(\s*v\d+)?$/u', '', $baseTitle);
      $title = trim($baseTitle) . "-{$label}";

      updateSQL_SAFE(
          'gaussian_splat_jobs',
          [
              'title'=>$title,
              'c_datetime'=>date('Y-m-d H:i:s'),
              'status'=>0,
              'reason'=>'',
              'kind'=>$kind,
              'pipeline_mode'=>$pipelineMode,
              'work_st_datetime'=>null,
              'work_et_datetime'=>null,
              'process_log'=>'',
              'current_stage'=>null,
              'current_stage_label'=>null,
              'duration_seconds'=>null,
              'queue_seconds'=>null,
              'process_seconds'=>null,
              'frame_count'=>null,
              'registered_frame_count'=>null,
              'splat_file_size_mb'=>null,
              'confidence_score'=>null,
              'confidence_grade'=>null,
              'confidence_decision'=>null,
              'confidence_effective_decision'=>null,
              'confidence_gate_json'=>null,
              'confidence_override'=>0,
              'confidence_override_reason'=>null,
              'confidence_risk_count'=>0,
              'confidence_recommendation_count'=>0,
              'confidence_needs_override'=>0,
              'confidence_override_status'=>null,
              'confidence_updated_at'=>null,
          ],
          "`id`=?",
          [$sourceId]
      );

      return [
          'id'=>$sourceId,
          'source_job_id'=>$sourceId,
          'title'=>$title,
          'status'=>'queued',
          'preset'=>$pipelineMode,
          'progress'=>0,
          'target'=>'same',
      ];
  }

  function gs_create_reconvert_job($sourceRow, $pipelineMode){
      [$sourceId, $kind, $sourceInput] = gs_reconvert_source_input($sourceRow);

      $countRows = selectSQL_SAFE(
          "SELECT COUNT(*) AS `c` FROM `gaussian_splat_jobs` WHERE `del`='0' AND `orin_filename`=?",
          [$sourceRow['orin_filename'] ?? '']
      );
      $version = max(2, ((int)($countRows[0]['c'] ?? 1)) + 1);
      $labels = ['fast'=>'快速', 'qa'=>'標準', 'premium'=>'精緻'];
      $label = $labels[$pipelineMode] ?? $labels['fast'];
      $baseTitle = trim((string)($sourceRow['title'] ?? $sourceRow['orin_filename'] ?? '3DGS'));
      $baseTitle = preg_replace('/[- ]*(快速|標準|精緻|驗證|進階)?\s*v\d+$/u', '', $baseTitle);
      $title = trim($baseTitle) . "-{$label} v{$version}";

      $m = [
          'title'=>$title,
          'email'=>$sourceRow['email'] ?? '',
          'orin_filename'=>$sourceRow['orin_filename'] ?? basename($sourceInput),
          'c_datetime'=>date('Y-m-d H:i:s'),
          'IP'=>function_exists('ip') ? ip() : ($_SERVER['REMOTE_ADDR'] ?? ''),
          'status'=>0,
          'reason'=>'',
          'kind'=>$kind,
          'pipeline_mode'=>$pipelineMode,
          'del'=>0,
      ];
      foreach(['lon','lat','alt','heading','pitch','roll','scale','camera_lon','camera_lat','camera_alt','camera_heading','camera_pitch','camera_roll'] as $key){
          if(array_key_exists($key, $sourceRow)) $m[$key] = $sourceRow[$key];
      }

      $newId = (int)insertSQL('gaussian_splat_jobs', $m);
      $root = __DIR__ . "/uploads/{$newId}";
      $inputDir = "{$root}/input";
      if(!is_dir($inputDir) && !mkdir($inputDir, 0777, true)){
          gs_mark_failed($newId, '建立重轉目錄失敗');
          gs_json(['status'=>'NO','reason'=>'建立重轉目錄失敗']);
      }
      $dest = "{$inputDir}/input.{$kind}";
      if(!copy($sourceInput, $dest) || !is_file($dest)){
          gs_mark_failed($newId, '複製來源檔失敗');
          gs_json(['status'=>'NO','reason'=>'複製來源檔失敗']);
      }
      if($kind === 'zip' && !gs_extract_zip_images($dest, "{$root}/images")){
          gs_mark_failed($newId, 'ZIP 圖片解壓失敗');
          gs_json(['status'=>'NO','reason'=>'ZIP 圖片解壓失敗']);
      }
      @chmod($root, 0775);
      @chmod($inputDir, 0775);
      @chmod($dest, 0664);

      return [
          'id'=>$newId,
          'source_job_id'=>$sourceId,
          'version'=>$version,
          'title'=>$title,
          'status'=>'queued',
          'preset'=>$pipelineMode,
          'progress'=>0,
      ];
  }

  $mode = $_GET['mode'] ?? '';

  switch($mode){
      case 'checkGD':
          $gdcode = trim($_POST['gdcode'] ?? '');
          if(gs_captcha_matches($gdcode)){
              echo "OK";
          }
          exit();

      case 'resolveSplat':
          require_once __DIR__ . "/job_view.php";
          $id = (int)($_GET['id'] ?? 0);
          $artifact = gs_splat_artifact_for_job($id);
          if(!$artifact) gs_json(['status'=>'NO','reason'=>'artifact not found']);
          gs_json(['status'=>'OK','artifact'=>gs_public_splat_artifact($artifact)]);

      case 'getSplat':
          require_once __DIR__ . "/job_view.php";
          $uuid = trim((string)($_GET['uuid'] ?? ''));
          $artifact = gs_splat_artifact_from_uuid($uuid);
          gs_stream_splat_artifact($artifact);

      case 'upload':
          $title = trim($_POST['title'] ?? '');
          $gdcode = trim($_POST['gdcode'] ?? '');
          $email = trim($_POST['email'] ?? '');
          $pipelineMode = gs_pipeline_mode_or_null($_POST['pipeline_mode'] ?? '');
          $lon = gs_numeric_or_null($_POST['lon'] ?? null);
          $lat = gs_numeric_or_null($_POST['lat'] ?? null);
          $alt = is_numeric($_POST['alt'] ?? null) ? (float)$_POST['alt'] : 0.0;

          if(!gs_captcha_matches($gdcode)){
              gs_json(['status'=>'NO','reason'=>'驗證碼錯誤...']);
          }
          $_SESSION['GD_CODE'] = "囧";

          if($title === '') gs_json(['status'=>'NO','reason'=>'請輸入標題']);
          if($pipelineMode === null) gs_json(['status'=>'NO','reason'=>'模式錯誤']);
          if(!isset($_FILES['upfile']) || $_FILES['upfile']['error'] !== 0 || ($_FILES['upfile']['size'] ?? 0) <= 0){
              gs_json(['status'=>'NO','reason'=>'請選擇 MP4 影片或 ZIP 圖片包']);
          }

          $ext = gs_ext($_FILES['upfile']['name']);
          if($ext !== 'mp4' && $ext !== 'zip') gs_json(['status'=>'NO','reason'=>'目前僅支援 MP4 影片或 ZIP 圖片包']);

          if($ext === 'mp4'){
              $durationRejectReason = gs_video_duration_reject_reason($_FILES['upfile']['tmp_name']);
              if($durationRejectReason !== '') gs_json(['status'=>'NO','reason'=>$durationRejectReason]);
          }
          if($ext === 'zip'){
              $zipRejectReason = gs_zip_image_reject_reason($_FILES['upfile']['tmp_name']);
              if($zipRejectReason !== '') gs_json(['status'=>'NO','reason'=>$zipRejectReason]);
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
              'pipeline_mode' => $pipelineMode,
              'del' => 0,
              'lon' => $lon,
              'lat' => $lat,
              'alt' => $alt,
              'scale' => 1,
          ];

          $id = (int)insertSQL('gaussian_splat_jobs', $m);
          $root = __DIR__ . "/uploads/{$id}";
          $inputDir = "{$root}/input";
          if(!is_dir($inputDir) && !mkdir($inputDir, 0777, true)){
              gs_mark_failed($id, '建立上傳目錄失敗');
              gs_json(['status'=>'NO','reason'=>'建立上傳目錄失敗']);
          }

          $dest = "{$inputDir}/input.{$ext}";
          if(!move_uploaded_file($_FILES['upfile']['tmp_name'], $dest) || !is_file($dest)){
              gs_mark_failed($id, '上傳後找不到檔案');
              gs_json(['status'=>'NO','reason'=>'上傳後找不到檔案']);
          }
          if($ext === 'zip' && !gs_extract_zip_images($dest, "{$root}/images")){
              gs_mark_failed($id, 'ZIP 圖片解壓失敗');
              gs_json(['status'=>'NO','reason'=>'ZIP 圖片解壓失敗']);
          }
          @chmod($root, 0775);
          @chmod($inputDir, 0775);
          @chmod($dest, 0664);

          gs_json(['status'=>'OK','id'=>$id]);

      case 'get_log':
          require "{$base_dir}/inc/checkpassword.php";
          require_once __DIR__ . "/job_view.php";
          $id = (int)($_GET['id'] ?? 0);
          $rows = selectSQL_SAFE("SELECT * FROM `gaussian_splat_jobs` WHERE `id`=? LIMIT 1", [$id]);
          $row = $rows[0] ?? [];
          gs_json([
              'status'=>'OK',
              'reason'=>$row['reason'] ?? '',
              'log'=>$row['process_log'] ?? '',
              'job_status'=>(string)($row['status'] ?? ''),
              'pipeline_mode'=>(string)($row['pipeline_mode'] ?? 'fast'),
              'pipeline_mode_label'=>gs_pipeline_mode_label($row['pipeline_mode'] ?? 'fast'),
              'confidence_gate'=>gs_confidence_gate_from_row($row),
              'confidence_summary'=>gs_confidence_summary_from_row($row),
              'confidence_report_url'=>gs_job_confidence_report_url($id),
              'confidence_gate_url'=>gs_job_confidence_gate_url($id),
              'artifact_links'=>gs_job_artifact_links($id),
          ]);

      case 'jobs_delta':
          $listState = gs_job_list_state(15);
          $rows = $listState['rows'];
          $payload = gs_job_delta_payload($rows);
          gs_json([
              'status'=>'OK',
              'has_active_jobs'=>$payload['has_active_jobs'],
              'thumb_queue'=>$payload['thumb_queue'],
              'rows'=>$payload['rows'],
              'failure_reasons'=>$payload['failure_reasons'],
          ]);

      case 'save_thumb':
          $id = (int)($_POST['id'] ?? 0);
          $image = (string)($_POST['image'] ?? '');
          if($id <= 0) gs_json(['status'=>'NO','reason'=>'縮圖工作編號錯誤']);

          $rows = selectSQL_SAFE("SELECT `id`,`del`,`status` FROM `gaussian_splat_jobs` WHERE `id`=? LIMIT 1", [$id]);
          if(empty($rows) || (string)($rows[0]['del'] ?? '1') !== '0'){
              gs_json(['status'=>'NO','reason'=>'找不到工作，不能儲存縮圖']);
          }
          if((string)($rows[0]['status'] ?? '') !== '2'){
              gs_json(['status'=>'NO','reason'=>'工作尚未完成，不能儲存成果縮圖']);
          }
          $thumbPath = gs_job_thumb_cache_path($id);
          if(is_file($thumbPath)){
              gs_json(['status'=>'OK','url'=>gs_job_thumb_cache_url($id)]);
          }
          if(gs_splat_artifact_for_job($id) === null){
              gs_json(['status'=>'NO','reason'=>'找不到 Splat，不能儲存成果縮圖']);
          }
          if(!preg_match('~^data:image/png;base64,([A-Za-z0-9+/=]+)$~', $image, $m)){
              gs_json(['status'=>'NO','reason'=>'縮圖格式錯誤']);
          }

          $bin = base64_decode($m[1], true);
          if($bin === false || strlen($bin) < 100 || strlen($bin) > 1024 * 1024 || substr($bin, 0, 8) !== "\x89PNG\r\n\x1a\n"){
              gs_json(['status'=>'NO','reason'=>'縮圖資料錯誤']);
          }

          $dir = gs_thumb_cache_dir();
          if(!is_dir($dir) && !mkdir($dir, 0777, true)){
              gs_json(['status'=>'NO','reason'=>'thumb dir not writable']);
          }
          if(!is_dir($dir) || !is_writable($dir)){
              gs_json(['status'=>'NO','reason'=>'thumb dir not writable']);
          }

          if(file_put_contents($thumbPath, $bin, LOCK_EX) === false){
              gs_json(['status'=>'NO','reason'=>'縮圖寫入失敗']);
          }
          @chmod($thumbPath, 0666);
          gs_json(['status'=>'OK','url'=>gs_job_thumb_cache_url($id)]);

      case 'save_transform':
          require "{$base_dir}/inc/checkpassword.php";
          $id = (int)($_POST['id'] ?? 0);
          $data = json_decode(base64_decode($_POST['data'] ?? ''), true);
          if($id <= 0 || !is_array($data)) gs_json(['status'=>'NO','reason'=>'定位資料格式錯誤']);

          $fields = [];
          foreach(['lon','lat','alt','heading','pitch','roll','scale','camera_lon','camera_lat','camera_alt','camera_heading','camera_pitch','camera_roll'] as $key){
              if(isset($data[$key]) && is_numeric($data[$key])){
                  $fields[$key] = (float)$data[$key];
              }
          }
          if($fields){
              updateSQL_SAFE('gaussian_splat_jobs', $fields, "`id`=?", [$id]);
          }

          $jobDir = __DIR__ . "/uploads/{$id}";
          if(!is_dir($jobDir) && !mkdir($jobDir, 0777, true)){
              gs_json(['status'=>'NO','reason'=>'建立工作目錄失敗']);
          }
          $json = json_encode($data, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
          if(file_put_contents("{$jobDir}/transform.json", $json . "\n") === false){
              gs_json(['status'=>'NO','reason'=>'儲存定位資料失敗']);
          }
          @chmod("{$jobDir}/transform.json", 0644);
          gs_json(['status'=>'OK']);

      case 'admin_action':
          require "{$base_dir}/inc/checkpassword.php";
          $id = (int)($_POST['id'] ?? 0);
          $action = $_POST['action'] ?? '';
          if($id <= 0) gs_json(['status'=>'NO','reason'=>'工作編號錯誤']);
          $sourceRows = selectSQL_SAFE("SELECT * FROM `gaussian_splat_jobs` WHERE `id`=? LIMIT 1", [$id]);
          if(!$sourceRows) gs_json(['status'=>'NO','reason'=>'找不到工作']);
          $sourceRow = $sourceRows[0];
          $currentStatus = (string)($sourceRow['status'] ?? '');

          if($action === 'reconvert'){
              $reconvertAllowedStatuses = ['2','3','4','5'];
              $reconvertPipelineMode = gs_pipeline_mode_or_null($_POST['pipeline_mode'] ?? ($sourceRow['pipeline_mode'] ?? 'fast'));
              $reconvertTarget = ($_POST['reconvert_target'] ?? 'new') === 'same' ? 'same' : 'new';
              if($reconvertPipelineMode === null) gs_json(['status'=>'NO','reason'=>'重轉模式錯誤']);
              if(!in_array($currentStatus, $reconvertAllowedStatuses, true)){
                  gs_json(['status'=>'NO','reason'=>'不能重轉執行中或排隊中的工作']);
              }
              $job = $reconvertTarget === 'same'
                  ? gs_reset_reconvert_job($sourceRow, $reconvertPipelineMode)
                  : gs_create_reconvert_job($sourceRow, $reconvertPipelineMode);
              gs_json(['status'=>'OK','id'=>$job['id'],'job'=>$job]);
          }

          if($action === 'confidence_override'){
              $overrideReason = trim((string)($_POST['confidence_override_reason'] ?? ''));
              if($overrideReason === '') $overrideReason = '人工覆核啟動';
              $heldRows = selectSQL_SAFE("SELECT `id` FROM `gaussian_splat_jobs` WHERE `id`=? AND `status`='5' LIMIT 1", [$id]);
              if(!$heldRows) gs_json(['status'=>'NO','reason'=>'只有等待覆核的工作可以覆核啟動']);
              updateSQL_SAFE(
                  'gaussian_splat_jobs',
                  [
                      'status'=>0,
                      'reason'=>'',
                      'work_st_datetime'=>null,
                      'work_et_datetime'=>null,
                      'current_stage'=>null,
                      'current_stage_label'=>null,
                      'confidence_override'=>1,
                      'confidence_override_reason'=>$overrideReason,
                  ],
                  "`id`=?",
                  [$id]
              );
              $abortFile = __DIR__ . "/uploads/{$id}/.abort";
              if(is_file($abortFile)) @unlink($abortFile);
              gs_json(['status'=>'OK']);
          }

          if($action === 'abort'){
              $abortAllowedStatuses = ['0','1'];
              if(!in_array($currentStatus, $abortAllowedStatuses, true)){
                  gs_json(['status'=>'NO','reason'=>'不能中止已完成、失敗或等待覆核的工作']);
              }
              $dir = __DIR__ . "/uploads/{$id}";
              if($currentStatus === '1'){
                  if(is_dir($dir)){
                      file_put_contents("{$dir}/.abort", date('Y-m-d H:i:s'));
                  }
              }
              updateSQL_SAFE(
                  'gaussian_splat_jobs',
                  ['status'=>4,'reason'=>'使用者中止','work_et_datetime'=>date('Y-m-d H:i:s')],
                  "`id`=? AND `status` IN (0,1)",
                  [$id]
              );
              gs_json(['status'=>'OK']);
          }

          gs_json(['status'=>'NO','reason'=>'未知的操作']);
  }

  gs_json(['status'=>'NO','reason'=>'未知模式']);
