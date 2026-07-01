<?php
  require __DIR__ . "/../../inc/config.php";
  require __DIR__ . "/inc/function.php";

  $root = dirname(__DIR__);
  $lockFile = __DIR__ . "/1_run.lock";
  $lockFp = fopen($lockFile, 'w');
  if(!$lockFp || !flock($lockFp, LOCK_EX | LOCK_NB)){
      echo "已有 Gaussian Splat 轉檔程序在執行中，略過本次。\n";
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
  register_shutdown_function(function() use($lockFp, $globalLockFp, &$activeJobId){
      if($activeJobId){
          try {
              $rows = selectSQL_SAFE("SELECT `status` FROM `gaussian_splat_jobs` WHERE `id`=? LIMIT 1", [$activeJobId]);
              if(isset($rows[0]['status']) && (string)$rows[0]['status'] === '1'){
                  updateSQL_SAFE(
                      'gaussian_splat_jobs',
                      [
                          'status'=>3,
                          'reason'=>'worker exited before completion',
                          'work_et_datetime'=>date('Y-m-d H:i:s'),
                          'current_stage'=>null,
                          'current_stage_label'=>'失敗',
                      ],
                      "`id`=?",
                      [$activeJobId]
                  );
                  gs_append_log_block($activeJobId, "[worker shutdown] worker exited before completion");
              }
          } catch(Throwable $e){
              echo date('H:i:s') . " worker shutdown guard skipped: " . $e->getMessage() . "\n";
          }
      }
      flock($globalLockFp, LOCK_UN);
      fclose($globalLockFp);
      flock($lockFp, LOCK_UN);
      fclose($lockFp);
  });

  function gs_active_photogrammetry_job_exists(){
      $openmvsRows = selectSQL_SAFE("SELECT `id` FROM `openmvs_jobs` WHERE `del`='0' AND `status`='1' LIMIT 1", []);
      if(!empty($openmvsRows)) return true;
      $gsRows = selectSQL_SAFE("SELECT `id` FROM `gaussian_splat_jobs` WHERE `del`='0' AND `status`='1' LIMIT 1", []);
      return !empty($gsRows);
  }

  function gs_confidence_gate_db_update($gate){
      $decision = (string)($gate['decision'] ?? '');
      $effectiveDecision = (string)($gate['effectiveDecision'] ?? $decision);
      $override = $gate['override'] ?? [];
      $overrideEnabled = is_array($override) && !empty($override['enabled']);
      $needsOverride = $decision === 'hold' ? 1 : 0;
      $overrideStatus = 'none';
      if($decision === 'hold' && $effectiveDecision === 'run_with_override'){
          $overrideStatus = 'overridden';
      } elseif($decision === 'hold'){
          $overrideStatus = 'waiting';
      } elseif($decision === 'reject'){
          $overrideStatus = 'blocked';
      } elseif($overrideEnabled){
          $overrideStatus = 'overridden';
      }

      $riskCount = 0;
      $risks = $gate['risks'] ?? [];
      if(is_array($risks)){
          foreach($risks as $risk){
              $risk = strtolower(trim((string)$risk));
              if($risk !== '' && !in_array($risk, ['low','none','ok'], true)) $riskCount++;
          }
      }

      $recommendationCount = 0;
      $recommendations = $gate['recommendations'] ?? [];
      if(is_array($recommendations)){
          foreach($recommendations as $item){
              if(trim((string)$item) !== '') $recommendationCount++;
          }
      }

      return [
          'confidence_score'=>is_numeric($gate['score'] ?? null) ? round((float)$gate['score'], 2) : null,
          'confidence_grade'=>(string)($gate['grade'] ?? ''),
          'confidence_decision'=>$decision,
          'confidence_effective_decision'=>$effectiveDecision,
          'confidence_gate_json'=>null,
          'confidence_risk_count'=>$riskCount,
          'confidence_recommendation_count'=>$recommendationCount,
          'confidence_needs_override'=>$needsOverride,
          'confidence_override_status'=>$overrideStatus,
          'confidence_updated_at'=>date('Y-m-d H:i:s'),
      ];
  }

  function gs_confidence_gate_reason($gate){
      $parts = [];
      $reason = trim((string)($gate['reason'] ?? ''));
      if($reason !== '') $parts[] = $reason;
      $recommendations = $gate['recommendations'] ?? [];
      if(!is_array($recommendations)) $recommendations = [];
      foreach($recommendations as $item){
          $item = trim((string)$item);
          if($item !== '' && !in_array($item, $parts, true)) $parts[] = $item;
      }
      return $parts ? implode("\n", $parts) : 'Confidence gate stopped this job.';
  }

  function gs_training_cap_for_mode($pipelineMode){
      $caps = [
          'fast' => ['GS_FAST_TRAIN_MAX_ITERATIONS', '10000'],
          'qa' => ['GS_QA_TRAIN_MAX_ITERATIONS', '30000'],
          'premium' => ['GS_PREMIUM_TRAIN_MAX_ITERATIONS', '60000'],
      ];
      if(!isset($caps[$pipelineMode])){
          throw new InvalidArgumentException("unsupported pipeline mode: {$pipelineMode}");
      }
      [$envName, $defaultCap] = $caps[$pipelineMode];
      $cap = trim((string)(getenv($envName) ?: $defaultCap));
      if(!preg_match('/^[1-9][0-9]*$/', $cap)){
          throw new InvalidArgumentException("invalid {$envName}: {$cap}");
      }
      return $cap;
  }

  function gs_python_bin(){
      $python = trim((string)(getenv('GS_PYTHON') ?: ''));
      return $python !== '' ? $python : '/DATA/conda_vm/gs_scene/bin/python';
  }

  function gs_sfm_matcher_from_env(){
      $matcher = strtolower(trim((string)(getenv('GS_SFM_MATCHER') ?: '')));
      if($matcher === '') return '';
      if(!in_array($matcher, ['exhaustive','sequential','hloc_lightglue'], true)){
          throw new InvalidArgumentException("invalid GS_SFM_MATCHER: {$matcher}");
      }
      return $matcher;
  }

  function gs_sfm_matcher_for_job($jobDir){
      $overridePath = "{$jobDir}/input/sfm_matcher.txt";
      if(is_file($overridePath)){
          $matcher = strtolower(trim((string)@file_get_contents($overridePath)));
          if($matcher === '') return '';
          if(!in_array($matcher, ['exhaustive','sequential','hloc_lightglue'], true)){
              throw new InvalidArgumentException("invalid job sfm_matcher.txt: {$matcher}");
          }
          return $matcher;
      }
      return gs_sfm_matcher_from_env();
  }

  function gs_hloc_match_window_from_env(){
      $window = trim((string)(getenv('GS_HLOC_MATCH_WINDOW') ?: ''));
      if($window === '') return '';
      if(!preg_match('/^(0|[1-9][0-9]*)$/', $window)){
          throw new InvalidArgumentException("invalid GS_HLOC_MATCH_WINDOW: {$window}");
      }
      return $window;
  }

  function gs_image_dir_count($dir){
      if(!is_dir($dir)) return 0;
      $count = 0;
      foreach(scandir($dir) ?: [] as $file){
          if($file === '.' || $file === '..') continue;
          $ext = strtolower(pathinfo($file, PATHINFO_EXTENSION));
          if(in_array($ext, ['jpg','jpeg','png'], true)) $count++;
      }
      return $count;
  }

  if(gs_active_photogrammetry_job_exists()){
      echo "已有 Photogrammetry 轉檔程序在執行中，略過本次。\n";
      exit(0);
  }

  $rows = selectSQL_SAFE("SELECT * FROM `gaussian_splat_jobs` WHERE `del`='0' AND `status`='0' ORDER BY `id` ASC LIMIT 1", []);
  foreach($rows as $row){
      $id = (int)$row['id'];
      $activeJobId = $id;
      $kind = strtolower((string)$row['kind']);
      $jobDir = "{$root}/uploads/{$id}";
      $input = "{$jobDir}/input/input.{$kind}";
      $pipelineInput = $input;
      $confidenceInput = $input;
      $logPath = "{$jobDir}/process.log";
      $timingReportPath = "{$jobDir}/timing_report.json";
      @unlink("{$jobDir}/.abort");
      @unlink($logPath);

      $workStart = date('Y-m-d H:i:s');
      updateSQL_SAFE(
          'gaussian_splat_jobs',
          [
              'status'=>1,
	              'work_st_datetime'=>$workStart,
	              'work_et_datetime'=>null,
	              'reason'=>'',
	              'process_log'=>'',
              'current_stage'=>'worker_start',
              'current_stage_label'=>'啟動 worker',
              'duration_seconds'=>null,
              'queue_seconds'=>null,
              'process_seconds'=>null,
          ],
          "`id`=?",
          [$id]
      );
      gs_append_log($id, "開始 Gaussian Splat pipeline");

      if(!is_file($input)) gs_fail($id, "input file missing");
      if(!in_array($kind, ['mp4','zip'], true)) gs_fail($id, "Gaussian worker accepts mp4 or zip input");
      if($kind === 'zip'){
          $imageCount = gs_image_dir_count("{$jobDir}/images");
          if($imageCount < 8) gs_fail($id, "ZIP image set missing or too small");
          $pipelineInput = "{$jobDir}/images";
          $confidenceInput = $pipelineInput;
          gs_append_log($id, "ZIP 圖片包：{$imageCount} 張圖片");
      }

      $gsPython = gs_python_bin();
      if(!is_file($gsPython) || !is_executable($gsPython)){
          gs_fail($id, "GS_PYTHON not executable: {$gsPython}");
      }

      updateSQL_SAFE(
          'gaussian_splat_jobs',
          ['current_stage'=>'confidence_gate','current_stage_label'=>'信心門檻檢查'],
          "`id`=?",
          [$id]
      );
      $gateCmd = escapeshellarg($gsPython) . " " . escapeshellarg("{$root}/scripts/confidence_gate.py") . " " .
          escapeshellarg($jobDir) . " " .
          escapeshellarg($confidenceInput);
      if((int)($row['confidence_override'] ?? 0) === 1){
          $gateCmd .= " --override --override-reason " . escapeshellarg((string)($row['confidence_override_reason'] ?? ''));
      }
      gs_append_log($id, "執行 confidence gate: {$gateCmd}");
      $gateOut = [];
      $gateOk = gs_run_cmd($gateCmd, $gateOut, 600, null, function($line) use($id, $logPath){
          file_put_contents($logPath, $line . "\n", FILE_APPEND);
          gs_append_log_block($id, $line);
      });
      if(!$gateOk) gs_fail($id, implode("\n", $gateOut));

      $gatePath = "{$jobDir}/confidence_gate.json";
      $gate = json_decode((string)@file_get_contents($gatePath), true);
      if(!is_array($gate)) gs_fail($id, "confidence_gate.json missing or malformed");
      $gateUpdate = gs_confidence_gate_db_update($gate);
      updateSQL_SAFE('gaussian_splat_jobs', $gateUpdate, "`id`=?", [$id]);

      $decision = (string)($gate['decision'] ?? '');
      $effectiveDecision = (string)($gate['effectiveDecision'] ?? $decision);
      gs_append_log($id, "Confidence gate: {$decision} / {$effectiveDecision}");
      if($effectiveDecision === 'warn'){
          gs_append_log($id, "Confidence gate warning: " . gs_confidence_gate_reason($gate));
      }
      if($effectiveDecision === 'hold'){
          $reason = gs_confidence_gate_reason($gate);
          updateSQL_SAFE(
              'gaussian_splat_jobs',
              array_merge($gateUpdate, [
                  'status'=>5,
                  'reason'=>$reason,
                  'work_et_datetime'=>date('Y-m-d H:i:s'),
                  'current_stage'=>'confidence_hold',
                  'current_stage_label'=>'等待覆核',
              ]),
              "`id`=?",
              [$id]
          );
          gs_append_log_block($id, "[confidence gate hold] {$reason}");
          continue;
      }
      if(!in_array($effectiveDecision, ['run','warn','run_with_override'], true)){
          updateSQL_SAFE(
              'gaussian_splat_jobs',
              array_merge($gateUpdate, [
                  'current_stage'=>'confidence_reject',
                  'current_stage_label'=>'信心門檻拒絕',
              ]),
              "`id`=?",
              [$id]
          );
          gs_fail($id, gs_confidence_gate_reason($gate));
      }

      $originLon = is_numeric($row['lon'] ?? null) ? (float)$row['lon'] : 120.61022;
      $originLat = is_numeric($row['lat'] ?? null) ? (float)$row['lat'] : 24.110946;
      $originAlt = is_numeric($row['alt'] ?? null) ? (float)$row['alt'] : 0.0;
      $env = [];
      $pipelineMode = strtolower((string)($row['pipeline_mode'] ?? 'fast'));
      if(!in_array($pipelineMode, ['fast','qa','premium'], true)) $pipelineMode = 'fast';
      $env['GS_PYTHON'] = $gsPython;
      $env['GS_PIPELINE_MODE'] = $pipelineMode;
      try {
          $sfmMatcher = gs_sfm_matcher_for_job($jobDir);
      } catch(Throwable $e){
          gs_fail($id, $e->getMessage());
      }
      if($sfmMatcher !== ''){
          $env['GS_SFM_MATCHER'] = $sfmMatcher;
          gs_append_log($id, "Gaussian SfM matcher: {$sfmMatcher}");
      }
      try {
          $hlocMatchWindow = gs_hloc_match_window_from_env();
      } catch(Throwable $e){
          gs_fail($id, $e->getMessage());
      }
      if($hlocMatchWindow !== ''){
          $env['GS_HLOC_MATCH_WINDOW'] = $hlocMatchWindow;
          gs_append_log($id, "Gaussian HLOC match window: {$hlocMatchWindow}");
      }
      try {
          $trainingCap = gs_training_cap_for_mode($pipelineMode);
      } catch(Throwable $e){
          gs_fail($id, $e->getMessage());
      }
      if($trainingCap !== ''){
          $env['GS_TRAIN_MAX_ITERATIONS'] = $trainingCap;
          gs_append_log($id, "Gaussian {$pipelineMode} training cap: GS_TRAIN_MAX_ITERATIONS={$trainingCap}");
      }
      if($kind === 'mp4'){
          $durationSeconds = gs_video_duration_seconds($input);
          if($durationSeconds !== null && $durationSeconds < 3.0){
              $env['GS_FRAME_MIN_FRAMES'] = '1';
              $env['GS_FRAME_TARGET_FPS'] = '12';
              gs_append_log($id, sprintf('短片實驗模式：影片 %.2f 秒，放寬最低 frame 數。', $durationSeconds));
          }
      }
      $cmd = gs_env_prefix($env) . escapeshellarg("{$root}/scripts/run_mvp_pipeline.sh") . " " .
          escapeshellarg($pipelineInput) . " " .
          escapeshellarg($jobDir) . " " .
          escapeshellarg((string)$originLon) . " " .
          escapeshellarg((string)$originLat) . " " .
          escapeshellarg((string)$originAlt);
      gs_append_log($id, "執行: {$cmd}");
      $out = [];
      $ok = gs_run_cmd($cmd, $out, 86400, function() use($id){
          return gs_is_abort_requested($id);
      }, function($line) use($id, $logPath){
          file_put_contents($logPath, $line . "\n", FILE_APPEND);
          gs_append_log_block($id, $line);
      });
      if(!$ok){
          if(gs_is_abort_requested($id)) gs_abort($id);
          gs_fail($id, implode("\n", $out));
      }

      $qa = json_decode(@file_get_contents("{$jobDir}/qa_report.json"), true);
      $timing = json_decode(@file_get_contents($timingReportPath), true);
      $workEnd = date('Y-m-d H:i:s');
      $queueSeconds = gs_seconds_between($row['c_datetime'] ?? null, $workStart);
      $processSeconds = gs_seconds_between($workStart, $workEnd);
      $durationSeconds = gs_seconds_between($row['c_datetime'] ?? null, $workEnd);
	      $upd = [
	          'work_et_datetime'=>$workEnd,
	          'reason'=>'',
	          'current_stage'=>null,
          'current_stage_label'=>'完成',
          'duration_seconds'=>$durationSeconds,
          'queue_seconds'=>$queueSeconds,
          'process_seconds'=>$processSeconds,
      ];
      if(is_array($timing) && isset($timing['duration_seconds'])){
          $upd['process_seconds'] = (int)round((float)$timing['duration_seconds']);
      }
      if(is_array($qa)){
          $upd['frame_count'] = $qa['frame_count'] ?? null;
          $upd['registered_frame_count'] = $qa['registered_frame_count'] ?? null;
          $upd['splat_file_size_mb'] = $qa['splat_file_size_mb'] ?? null;
      }
      gs_append_log($id, "Gaussian Splat pipeline 完成");
      $upd['status'] = 2;
      updateSQL_SAFE('gaussian_splat_jobs', $upd, "`id`=?", [$id]);
      $activeJobId = null;
  }

  echo "Done.\n";
