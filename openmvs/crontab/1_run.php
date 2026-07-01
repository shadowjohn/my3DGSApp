<?php
  require __DIR__ . "/../../inc/config.php";
  require __DIR__ . "/inc/function.php";

  $root = dirname(__DIR__);
  $lockFile = __DIR__ . "/1_run.lock";
  $lockFp = fopen($lockFile, 'w');
  if(!$lockFp || !flock($lockFp, LOCK_EX | LOCK_NB)){
      echo "已有 OpenMVS 轉檔程序在執行中，略過本次。\n";
      exit(0);
  }
  fwrite($lockFp, getmypid());
  $globalLockFile = dirname($root) . "/.photogrammetry_worker.lock";
  $globalLockFp = fopen($globalLockFile, 'w');
  if(!$globalLockFp || !flock($globalLockFp, LOCK_EX | LOCK_NB)){
      echo "已有 Photogrammetry 轉檔程序在執行中，略過本次。\n";
      flock($lockFp, LOCK_UN);
      fclose($lockFp);
      if($globalLockFp) fclose($globalLockFp);
      exit(0);
  }
  fwrite($globalLockFp, getmypid());
  $activeJobId = null;
  $activeProductId = null;
  register_shutdown_function(function() use($lockFp, $globalLockFp, &$activeJobId, &$activeProductId){
      if($activeJobId){
          try {
              $rows = selectSQL_SAFE("SELECT `status` FROM `openmvs_jobs` WHERE `id`=? LIMIT 1", [$activeJobId]);
              if(isset($rows[0]['status']) && (string)$rows[0]['status'] === '1'){
                  $fields = ovm_finish_timing_fields($activeJobId, date('Y-m-d H:i:s'));
                  $fields['status'] = 3;
                  $fields['reason'] = 'worker exited before completion';
                  $fields['current_stage'] = null;
                  $fields['current_stage_label'] = '失敗';
                  updateSQL_SAFE('openmvs_jobs', $fields, "`id`=?", [$activeJobId]);
                  ovm_append_log_block($activeJobId, "[worker shutdown] worker exited before completion");
              }
          } catch(Throwable $e){
              echo date('H:i:s') . " worker shutdown guard skipped: " . $e->getMessage() . "\n";
          }
      }
      if($activeProductId){
          try {
              $rows = selectSQL_SAFE("SELECT `status` FROM `openmvs_products` WHERE `id`=? LIMIT 1", [$activeProductId]);
              if(isset($rows[0]['status']) && (string)$rows[0]['status'] === '1'){
                  updateSQL_SAFE(
                      'openmvs_products',
                      [
                          'status'=>3,
                          'work_et_datetime'=>date('Y-m-d H:i:s'),
                          'reason'=>'product worker exited before completion',
                          'error_message'=>'product worker exited before completion',
                          'current_stage'=>'failed',
                      ],
                      "`id`=?",
                      [$activeProductId]
                  );
                  ovm_append_product_log_block($activeProductId, "[worker shutdown] product worker exited before completion");
              }
          } catch(Throwable $e){
              echo date('H:i:s') . " product worker shutdown guard skipped: " . $e->getMessage() . "\n";
          }
      }
      flock($globalLockFp, LOCK_UN);
      fclose($globalLockFp);
      flock($lockFp, LOCK_UN);
      fclose($lockFp);
  });

  function ovm_active_photogrammetry_job_exists(){
      $openmvsRows = selectSQL_SAFE("SELECT `id` FROM `openmvs_jobs` WHERE `del`='0' AND `status`='1' LIMIT 1", []);
      if(!empty($openmvsRows)) return true;
      $gsRows = selectSQL_SAFE("SELECT `id` FROM `gaussian_splat_jobs` WHERE `del`='0' AND `status`='1' LIMIT 1", []);
      return !empty($gsRows);
  }

  if(ovm_active_photogrammetry_job_exists()){
      echo "已有 Photogrammetry 轉檔程序在執行中，略過本次。\n";
      exit(0);
  }

  function ovm_append_product_log_block($productId, $msg){
      $msg = trim((string)$msg);
      if($msg === '') return;
      $line = $msg . "\n";
      echo $line;
      global $pdo;
      if(isset($pdo)){
          try {
              $stmt = $pdo->prepare("UPDATE `openmvs_products` SET `process_log` = RIGHT(CONCAT(IFNULL(`process_log`,''), ?), 60000) WHERE `id`=?");
              $stmt->execute([$line, (int)$productId]);
          } catch(Throwable $e){
              echo date('H:i:s') . " product DB log skipped: " . $e->getMessage() . "\n";
          }
      }
  }

  function ovm_fail_product($productId, $reason){
      $reason = trim((string)$reason);
      if($reason === '') $reason = 'product export failed';
      updateSQL_SAFE(
          'openmvs_products',
          [
              'status'=>3,
              'work_et_datetime'=>date('Y-m-d H:i:s'),
              'reason'=>$reason,
              'error_message'=>$reason,
              'current_stage'=>'failed',
          ],
          "`id`=?",
          [(int)$productId]
      );
      ovm_append_product_log_block($productId, $reason);
  }

	  $rows = selectSQL_SAFE("SELECT * FROM `openmvs_jobs` WHERE `del`='0' AND `status`='0' ORDER BY `id` ASC LIMIT 1", []);
	  foreach($rows as $row){
	      $id = (int)$row['id'];
	      $activeJobId = $id;
	      $kind = strtolower((string)$row['kind']);
	      $jobDir = "{$root}/uploads/{$id}";
	      $input = "{$jobDir}/input/input.{$kind}";
	      $logPath = ovm_job_pipeline_log_path($id);
	      $logDir = dirname($logPath);
	      if(!is_dir($logDir)) @mkdir($logDir, 0777, true);
	      @unlink("{$jobDir}/.abort");
	      @unlink($logPath);
	      $maskMode = strtolower(trim((string)($row['mask_mode'] ?? 'none')));
	      if(!in_array($maskMode, ['none','provided','auto'], true)) $maskMode = 'none';
	      $qualityPreset = strtolower(trim((string)($row['quality_preset'] ?? 'normal')));
	      if(!in_array($qualityPreset, ['fast','normal','high'], true)) $qualityPreset = 'normal';
	      $row['kind'] = $kind;
	      $row['mask_mode'] = $maskMode;
	      $row['quality_preset'] = $qualityPreset;

      $workStart = date('Y-m-d H:i:s');
      updateSQL_SAFE(
          'openmvs_jobs',
          [
              'status'=>1,
              'work_st_datetime'=>$workStart,
              'work_et_datetime'=>null,
	              'process_log'=>'',
	              'current_stage'=>'worker_start',
	              'current_stage_label'=>'啟動 worker',
	              'duration_seconds'=>null,
	              'queue_seconds'=>null,
	              'process_seconds'=>null,
	              'diagnostic_status'=>null,
	              'diagnostic_score'=>null,
	              'diagnostic_summary'=>null,
	              'diagnostic_log_path'=>"uploads/{$id}/logs/openmvs_pipeline.log",
	              'capture_source_type'=>ovm_capture_source_type($kind),
	              'capture_quality_score'=>null,
	              'capture_quality_grade'=>null,
	              'capture_quality_decision'=>null,
	              'capture_mask_status'=>$maskMode,
	              'capture_frame_count'=>null,
	              'capture_selected_frame_count'=>null,
	              'capture_aligned_camera_count'=>null,
	              'capture_registered_ratio'=>null,
	              'capture_warning_count'=>0,
	              'capture_updated_at'=>$workStart,
	          ],
	          "`id`=?",
	          [$id]
	      );
	      ovm_clear_job_diagnostics($id);
	      ovm_append_log($id, "開始 OpenMVS pipeline");

      if(!is_file($input)) ovm_fail($id, "input file missing");
      if(!in_array($kind, ['mp4', 'zip'], true)) ovm_fail($id, "OpenMVS cron worker accepts mp4 or zip input");

      $originLon = is_numeric($row['lon'] ?? null) ? (float)$row['lon'] : 120.61022;
      $originLat = is_numeric($row['lat'] ?? null) ? (float)$row['lat'] : 24.110946;
      $originAlt = is_numeric($row['alt'] ?? null) ? (float)$row['alt'] : 0.0;
      $pipelineMode = 'openmvs_native';
      $pipelineModeFile = "{$jobDir}/input/pipeline_mode.txt";
      if(is_file($pipelineModeFile)){
          $candidateMode = strtolower(trim((string)@file_get_contents($pipelineModeFile)));
          $pipelineMode = ovm_normalize_pipeline_mode($candidateMode);
      }
      $frameEnv = '';
      $capturePreset = trim((string)($row['capture_preset'] ?? ''));
      if(preg_match('/(?:^|_)frames_(\d+)(?:$|_)/', $capturePreset, $m)){
          $maxFrames = max(8, min(240, (int)$m[1]));
          $frameEnv = "OVM_MAX_FRAMES=" . escapeshellarg((string)$maxFrames) . " ";
          ovm_append_log($id, "frame limit: {$maxFrames}");
      }

      $cmd = "env OVM_MASK_MODE=" . escapeshellarg($maskMode) . " " .
          "OVM_QUALITY_PRESET=" . escapeshellarg($qualityPreset) . " " .
          $frameEnv .
          "OVM_PIPELINE_MODE=" . escapeshellarg($pipelineMode) . " " .
          escapeshellarg("{$root}/scripts/run_openmvs_pipeline.sh") . " " .
          escapeshellarg($input) . " " .
          escapeshellarg($jobDir) . " " .
          escapeshellarg((string)$originLon) . " " .
          escapeshellarg((string)$originLat) . " " .
          escapeshellarg((string)$originAlt);
      ovm_append_log($id, "pipeline mode: {$pipelineMode}");
	      ovm_append_log($id, "quality preset: {$qualityPreset}");
	      ovm_append_log($id, "執行: {$cmd}");

	      $out = [];
	      $ok = ovm_run_cmd($cmd, $out, 172800, function() use($id){
	          return ovm_is_abort_requested($id);
	      }, function($line) use($id, $logPath){
	          @file_put_contents($logPath, $line . "\n", FILE_APPEND);
	          ovm_append_log_block($id, $line);
	      });
      if(!$ok){
          if(ovm_is_abort_requested($id)) ovm_abort($id);
          $reason = implode("\n", $out);
          $diagnostics = [];
          $diagFields = ovm_finalize_job_diagnostics($id, $logPath, [], "openmvs.nonzero_exit failed", $diagnostics);
	          $captureFields = ovm_capture_summary_fields($row, [], $diagnostics);
	          updateSQL_SAFE('openmvs_jobs', array_merge($diagFields, $captureFields), "`id`=?", [$id]);
          ovm_fail($id, $reason);
      }

      updateSQL_SAFE(
          'openmvs_jobs',
          ['current_stage'=>'standard_artifacts','current_stage_label'=>'產生標準交付證據'],
          "`id`=?",
          [$id]
      );
      $contractWarning = '';
      $contractCommands = [
          'engine_contract' => "python3 " . escapeshellarg("{$root}/scripts/build_engine_contract.py") . " " .
              escapeshellarg($jobDir) . " --mode fast --pipeline-mode " . escapeshellarg($pipelineMode),
          'validation_report' => "python3 " . escapeshellarg("{$root}/scripts/build_validation_report.py") . " " .
              escapeshellarg($jobDir),
          'delivery_manifest' => "python3 " . escapeshellarg("{$root}/scripts/build_delivery_manifest.py") . " " .
              escapeshellarg($jobDir),
      ];
      foreach($contractCommands as $contractKey => $contractCmd){
          ovm_append_log($id, "產生 {$contractKey}: {$contractCmd}");
          $contractOut = [];
          $contractOk = ovm_run_cmd($contractCmd, $contractOut, 600, function() use($id){
              return ovm_is_abort_requested($id);
          }, function($line) use($id, $logPath){
              @file_put_contents($logPath, $line . "\n", FILE_APPEND);
              ovm_append_log_block($id, $line);
          });
          if(!$contractOk){
              if(ovm_is_abort_requested($id)) ovm_abort($id);
              $contractWarning .= "\nopenmvs.contract_artifact_failed standard contract artifact failed: {$contractKey}";
              ovm_append_log_block($id, "[standard contract warning] {$contractKey} failed");
          }
      }

      $qaPath = "{$jobDir}/qa_report.json";
      $qaWarning = '';
      $qa = [];
      if(!is_file($qaPath)){
          $qaWarning = "openmvs.qa_report_missing qa_report.json missing";
      } else {
          $qa = json_decode((string)@file_get_contents($qaPath), true);
          if(json_last_error() !== JSON_ERROR_NONE || !is_array($qa)){
              $qa = [];
              $qaWarning = "openmvs.qa_report_malformed qa_report.json malformed";
          }
      }
      $workEnd = date('Y-m-d H:i:s');
      $queueSeconds = ovm_seconds_between($row['c_datetime'] ?? null, $workStart);
      $processSeconds = ovm_seconds_between($workStart, $workEnd);
      $upd = [
          'work_et_datetime'=>$workEnd,
          'current_stage'=>null,
          'current_stage_label'=>'已完成',
          'duration_seconds'=>$processSeconds,
          'queue_seconds'=>$queueSeconds,
          'process_seconds'=>$processSeconds,
      ];
      if(is_array($qa)){
          $upd['input_frame_count'] = $qa['input_frame_count'] ?? null;
          $upd['registered_frame_count'] = $qa['registered_frame_count'] ?? null;
          $upd['glb_file_size_mb'] = $qa['glb_file_size_mb'] ?? null;
          $upd['mesh_file_size_mb'] = $qa['mesh_file_size_mb'] ?? null;
	          $upd['texture_black_pixel_ratio'] = $qa['texture_black_pixel_ratio'] ?? null;
	          $upd['texture_white_empty_pixel_ratio'] = $qa['texture_white_empty_pixel_ratio'] ?? null;
	          $upd['texture_width'] = $qa['texture_width'] ?? null;
	          $upd['texture_height'] = $qa['texture_height'] ?? null;
	          $upd['texture_patch_count'] = $qa['texture_patch_count'] ?? null;
	      }
	      $diagnostics = [];
	      $diagFields = ovm_finalize_job_diagnostics($id, $logPath, $qa, trim($qaWarning . $contractWarning), $diagnostics);
	      $upd = array_merge($upd, $diagFields, ovm_capture_summary_fields($row, $qa, $diagnostics));
	      ovm_append_log($id, "OpenMVS pipeline 完成");
	      $upd['status'] = 2;
	      updateSQL_SAFE('openmvs_jobs', $upd, "`id`=?", [$id]);
	      $activeJobId = null;
	  }

  $productRows = selectSQL_SAFE("SELECT * FROM `openmvs_products` WHERE `product_type`='glb' AND `status`='0' AND `del`='0' ORDER BY `id` ASC LIMIT 1", []);
  foreach($productRows as $productRow){
      $productId = (int)$productRow['id'];
      $jobId = (int)$productRow['job_id'];
      $textureSize = (int)$productRow['texture_size'];
      $workStart = date('Y-m-d H:i:s');
      $claimStmt = $pdo->prepare("
          UPDATE `openmvs_products` SET
              `status`='1',
              `work_st_datetime`=?,
              `work_et_datetime`=NULL,
              `reason`='',
              `error_message`='',
              `process_log`='',
              `current_stage`='product_start'
          WHERE `id`=? AND `status`='0' AND `del`='0'
      ");
      $claimStmt->execute([$workStart, $productId]);
      if($claimStmt->rowCount() <= 0){
          continue;
      }
      $activeProductId = $productId;
      ovm_append_product_log_block($productId, "開始 OpenMVS GLB product {$textureSize}");

      if(!in_array($textureSize, [512, 2048, 4096, 8192], true)){
          ovm_fail_product($productId, "invalid OVM_PRODUCT_TEXTURE_SIZE: {$textureSize}");
          continue;
      }

      $jobRows = selectSQL_SAFE("SELECT * FROM `openmvs_jobs` WHERE `id`=? AND `del`='0' LIMIT 1", [$jobId]);
      if(empty($jobRows)){
          ovm_fail_product($productId, "source job missing");
          continue;
      }
      $jobRow = $jobRows[0];
      $kind = strtolower((string)$jobRow['kind']);
      $jobDir = "{$root}/uploads/{$jobId}";
      $input = "{$jobDir}/input/input.{$kind}";
      if(!is_file($input)){
          ovm_fail_product($productId, "input file missing");
          continue;
      }
      if(!in_array($kind, ['mp4', 'zip'], true)){
          ovm_fail_product($productId, "OpenMVS product worker accepts mp4 or zip input");
          continue;
      }

      $originLon = is_numeric($jobRow['lon'] ?? null) ? (float)$jobRow['lon'] : 120.61022;
      $originLat = is_numeric($jobRow['lat'] ?? null) ? (float)$jobRow['lat'] : 24.110946;
      $originAlt = is_numeric($jobRow['alt'] ?? null) ? (float)$jobRow['alt'] : 0.0;
      $productOutputDir = "{$jobDir}/products/glb_{$textureSize}";
      $productFilePath = "uploads/{$jobId}/products/glb_{$textureSize}/model.glb";
      $productModelPath = "{$productOutputDir}/model.glb";
      $cmd = "env OVM_PRODUCT_TEXTURE_SIZE=" . escapeshellarg((string)$textureSize) . " " .
          "OVM_PRODUCT_OUTPUT_DIR=" . escapeshellarg($productOutputDir) . " " .
          escapeshellarg("{$root}/scripts/run_openmvs_pipeline.sh") . " " .
          escapeshellarg($input) . " " .
          escapeshellarg($jobDir) . " " .
          escapeshellarg((string)$originLon) . " " .
          escapeshellarg((string)$originLat) . " " .
          escapeshellarg((string)$originAlt);
      ovm_append_product_log_block($productId, "執行: {$cmd}");

      $out = [];
      $ok = ovm_run_cmd($cmd, $out, 86400, null, function($line) use($productId){
          ovm_append_product_log_block($productId, $line);
      });
      if(!$ok){
          ovm_fail_product($productId, implode("\n", $out));
          continue;
      }
      if(!is_file($productModelPath)){
          ovm_fail_product($productId, "product model.glb missing");
          continue;
      }

      $productFileSizeMb = number_format((float)filesize($productModelPath) / 1048576, 3, '.', '');
      updateSQL_SAFE(
          'openmvs_products',
          [
              'status'=>2,
              'work_et_datetime'=>date('Y-m-d H:i:s'),
              'current_stage'=>null,
              'file_path'=>$productFilePath,
              'file_size_mb'=>$productFileSizeMb,
          ],
          "`id`=?",
          [$productId]
      );
      ovm_append_product_log_block($productId, "OpenMVS GLB product 完成: {$productFilePath}");
      $activeProductId = null;
  }

  echo "Done.\n";
?>
