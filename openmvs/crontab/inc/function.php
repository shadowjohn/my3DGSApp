<?php
  function ovm_remember_cmd_output(&$out, $line){
      $out[] = $line;
      if(count($out) > 500) array_shift($out);
  }

	  function ovm_run_cmd($cmd, &$out=null, $timeout=86400, $abortChecker=null, $lineCallback=null){
      $out = [];
      $timeout = max(1, (int)$timeout);
      $process = proc_open(
          "exec timeout {$timeout} " . $cmd . " 2>&1",
          [
              0 => ['file', '/dev/null', 'r'],
              1 => ['pipe', 'w'],
          ],
          $pipes
      );
      if(!is_resource($process)){
          $out[] = "failed to start command";
          return false;
      }

      stream_set_blocking($pipes[1], false);
      $buffer = '';
      $exitCode = null;
      while(true){
          $chunk = stream_get_contents($pipes[1]);
          if($chunk !== false && $chunk !== ''){
              $buffer .= $chunk;
              while(($pos = strpos($buffer, "\n")) !== false){
                  $line = rtrim(substr($buffer, 0, $pos), "\r\n");
                  $buffer = substr($buffer, $pos + 1);
                  ovm_remember_cmd_output($out, $line);
                  if(is_callable($lineCallback)) $lineCallback($line);
              }
          }

          $status = proc_get_status($process);
          if(!$status['running']){
              $exitCode = $status['exitcode'];
              break;
          }

          if(is_callable($abortChecker) && $abortChecker()){
              $pid = (int)$status['pid'];
              if($pid > 0) @exec("pkill -TERM -P " . escapeshellarg((string)$pid));
              proc_terminate($process);
              ovm_remember_cmd_output($out, "aborted by user");
              if(is_callable($lineCallback)) $lineCallback("aborted by user");
              fclose($pipes[1]);
              proc_close($process);
              return false;
          }
          usleep(250000);
      }

      $chunk = stream_get_contents($pipes[1]);
      if($chunk !== false && $chunk !== '') $buffer .= $chunk;
      if($buffer !== ''){
          $line = rtrim($buffer, "\r\n");
          ovm_remember_cmd_output($out, $line);
          if(is_callable($lineCallback)) $lineCallback($line);
      }

      fclose($pipes[1]);
      $closeCode = proc_close($process);
      if($exitCode === null || $exitCode === -1) $exitCode = $closeCode;
	      return $exitCode === 0;
	  }

	  function ovm_job_log_dir($id){
	      $root = dirname(dirname(__DIR__));
	      return "{$root}/uploads/" . (int)$id . "/logs";
	  }

	  function ovm_job_pipeline_log_path($id){
	      return ovm_job_log_dir($id) . "/openmvs_pipeline.log";
	  }

	  function ovm_relative_openmvs_path($path){
	      $root = dirname(dirname(__DIR__));
	      $path = (string)$path;
	      return strpos($path, $root . '/') === 0 ? substr($path, strlen($root) + 1) : $path;
	  }

	  function ovm_append_log($id, $msg){
	      $line = date('H:i:s') . " " . $msg . "\n";
	      echo $line;
	      global $pdo;
	      if(isset($pdo)){
	          try {
	              $stmt = $pdo->prepare("UPDATE `openmvs_jobs` SET `process_log` = RIGHT(CONCAT(IFNULL(`process_log`,''), ?), 60000) WHERE `id`=?");
	              $stmt->execute([$line, $id]);
	          } catch(Throwable $e){
	              echo date('H:i:s') . " DB log skipped: " . $e->getMessage() . "\n";
	          }
	      }
	      ovm_check_abort($id);
	  }

  function ovm_parse_timing_stage_line($msg){
      $msg = trim((string)$msg);
      if(strpos($msg, '[timing] START ') !== 0) return null;
      if(preg_match('/^\[timing\] START ([A-Za-z0-9_-]+) (.+)$/', $msg, $m)){
          return ['key'=>$m[1], 'label'=>$m[2]];
      }
      return null;
  }

  function ovm_normalize_pipeline_mode($mode){
      $mode = strtolower(trim((string)$mode));
      switch($mode){
          case '':
          case 'native':
          case 'openmvs_native':
          case 'openmvs-native':
          case 'createstructure':
          case 'create_structure':
              return 'openmvs_native';
          case 'standard':
          case 'colmap':
          case 'interface_colmap':
          case 'interface-colmap':
              return 'colmap';
          default:
              return 'openmvs_native';
      }
  }

	  function ovm_update_timing_stage_from_line($id, $msg){
	      $stage = ovm_parse_timing_stage_line($msg);
	      if(!$stage) return;
	      updateSQL_SAFE(
          'openmvs_jobs',
          ['current_stage'=>$stage['key'], 'current_stage_label'=>$stage['label']],
          "`id`=?",
          [$id]
	      );
	  }

	  function ovm_diagnostic_patterns(){
	      return [
	          'openmvs.linear_solver_failure' => [
	              'severity' => 'error',
	              'summary' => 'Linear solver failures',
	              'regex' => '/linear solver|failed to converge|Cholesky|numerical/i',
	          ],
	          'openmvs.texture_patch_rejected' => [
	              'severity' => 'warning',
	              'summary' => 'Texture patches rejected',
	              'regex' => '/rejected .*patch|patch .*rejected|no valid view/i',
	          ],
	          'openmvs.cpu_fallback' => [
	              'severity' => 'warning',
	              'summary' => 'GPU failed, CPU fallback used',
	              'regex' => '/CPU fallback|falling back to CPU|retrying with CPU|--cuda-device -2/i',
	          ],
	          'openmvs.out_of_memory' => [
	              'severity' => 'error',
	              'summary' => 'Out of memory',
	              'regex' => '/out of memory|std::bad_alloc|bad allocation|cannot allocate memory|^Killed$/i',
	          ],
	          'openmvs.missing_scene' => [
	              'severity' => 'error',
	              'summary' => 'Missing or unreadable scene file',
	              'regex' => '/missing .*scene|scene.*not found|cannot load .*\\.mvs|failed .*open .*\\.mvs/i',
	          ],
	          'openmvs.process_timeout' => [
	              'severity' => 'error',
	              'summary' => 'Process timed out',
	              'regex' => '/timed out|timeout|exit status 124|status 124/i',
	          ],
	          'openmvs.nonzero_exit' => [
	              'severity' => 'error',
	              'summary' => 'Process exited with a non-zero status',
	              'regex' => '/non-zero|nonzero|exit code [1-9][0-9]*|failed$/i',
	          ],
	          'openmvs.qa_report_missing' => [
	              'severity' => 'warning',
	              'summary' => 'QA report missing',
	              'regex' => '/openmvs\.qa_report_missing|qa_report\.json missing/i',
	          ],
	          'openmvs.qa_report_malformed' => [
	              'severity' => 'warning',
	              'summary' => 'QA report malformed',
	              'regex' => '/openmvs\.qa_report_malformed|qa_report\.json malformed/i',
	          ],
	          'openmvs.contract_artifact_failed' => [
	              'severity' => 'warning',
	              'summary' => 'Standard contract artifact failed',
	              'regex' => '/openmvs\.contract_artifact_failed|standard contract artifact failed/i',
	          ],
	      ];
	  }

	  function ovm_parse_log_diagnostics($text, $rawLogPath=''){
	      $patterns = ovm_diagnostic_patterns();
	      $stage = 'unknown';
	      $rows = [];
	      $successfulStages = [];
	      $lines = preg_split('/\R/u', (string)$text);

	      foreach($lines as $index => $line){
	          $lineNo = $index + 1;
	          $trimmed = trim((string)$line);
	          if($trimmed === '') continue;

	          $parsedStage = ovm_parse_timing_stage_line($trimmed);
	          if($parsedStage && !empty($parsedStage['key'])){
	              $stage = $parsedStage['key'];
	              continue;
	          }
	          if(preg_match('/^\[timing\] END ([A-Za-z0-9_-]+) success$/', $trimmed, $m)){
	              $successfulStages[$m[1]] = true;
	              continue;
	          }

	          foreach($patterns as $patternId => $pattern){
	              if(!preg_match($pattern['regex'], $trimmed)) continue;
	              $key = $stage . '|' . $patternId;
	              if(!isset($rows[$key])){
	                  $sample = function_exists('mb_substr') ? mb_substr($trimmed, 0, 500, 'UTF-8') : substr($trimmed, 0, 500);
	                  $rows[$key] = [
	                      'stage' => $stage,
	                      'pattern_id' => $patternId,
	                      'severity' => $pattern['severity'],
	                      'pattern_count' => 0,
	                      'first_seen_line' => $lineNo,
	                      'last_seen_line' => $lineNo,
	                      'message_sample' => $sample,
	                      'message_summary' => $pattern['summary'],
	                      'raw_log_path' => $rawLogPath,
	                  ];
	              }
	              $rows[$key]['pattern_count']++;
	              $rows[$key]['last_seen_line'] = $lineNo;
	          }
	      }

	      foreach($rows as &$row){
	          if(
	              ($row['pattern_id'] ?? '') === 'openmvs.linear_solver_failure' &&
	              ($row['stage'] ?? '') === 'openmvs_create_structure' &&
	              !empty($successfulStages['openmvs_create_structure'])
	          ){
	              $row['severity'] = 'warning';
	          }
	      }
	      unset($row);

	      return array_values($rows);
	  }

	  function ovm_capture_source_type($kind){
	      $kind = strtolower(trim((string)$kind));
	      if($kind === 'zip') return 'images';
	      if($kind === 'mp4') return 'video';
	      return null;
	  }

	  function ovm_capture_quality_from_ratio($ratio, $warningCount){
	      if(!is_numeric($ratio)) return [null, null, null];
	      $score = max(0, min(100, (float)$ratio * 100 - ((int)$warningCount * 5)));
	      if($score >= 90) return [$score, 'A', 'run'];
	      if($score >= 75) return [$score, 'B', 'run'];
	      if($score >= 60) return [$score, 'C', 'warn'];
	      if($score >= 40) return [$score, 'D', 'hold'];
	      return [$score, 'F', 'reject'];
	  }

	  function ovm_capture_summary_fields($row, $qa, $diagnostics){
	      $row = is_array($row) ? $row : [];
	      $qa = is_array($qa) ? $qa : [];
	      $frameCount = $qa['input_frame_count'] ?? null;
	      $alignedCount = $qa['registered_frame_count'] ?? null;
	      $ratio = (is_numeric($frameCount) && (int)$frameCount > 0 && is_numeric($alignedCount))
	          ? ((float)$alignedCount / (float)$frameCount)
	          : null;
	      $warningCount = 0;
	      foreach((array)$diagnostics as $diag){
	          if(($diag['severity'] ?? '') === 'warning') $warningCount += (int)($diag['pattern_count'] ?? 0);
	      }
	      [$score, $grade, $decision] = ovm_capture_quality_from_ratio($ratio, $warningCount);
	      $preset = array_key_exists('capture_preset', $row) ? trim((string)$row['capture_preset']) : '';
	      $maskStatus = array_key_exists('mask_mode', $row) ? trim((string)$row['mask_mode']) : '';
	      return [
	          'capture_source_type' => ovm_capture_source_type($row['kind'] ?? ''),
	          'capture_preset' => $preset !== '' ? $preset : null,
	          'capture_quality_score' => is_numeric($score) ? number_format((float)$score, 2, '.', '') : null,
	          'capture_quality_grade' => $grade,
	          'capture_quality_decision' => $decision,
	          'capture_mask_status' => $maskStatus !== '' ? $maskStatus : null,
	          'capture_frame_count' => $frameCount,
	          'capture_selected_frame_count' => $frameCount,
	          'capture_aligned_camera_count' => $alignedCount,
	          'capture_registered_ratio' => is_numeric($ratio) ? number_format((float)$ratio, 4, '.', '') : null,
	          'capture_warning_count' => $warningCount,
	          'capture_updated_at' => date('Y-m-d H:i:s'),
	      ];
	  }

	  function ovm_clear_job_diagnostics($id){
	      global $pdo;
	      if(!isset($pdo)) return;
	      try {
	          $stmt = $pdo->prepare("DELETE FROM `openmvs_job_diagnostics` WHERE `job_id`=?");
	          $stmt->execute([(int)$id]);
	      } catch(Throwable $e){
	          echo date('H:i:s') . " diagnostics clear skipped: " . $e->getMessage() . "\n";
	      }
	  }

	  function ovm_upsert_job_diagnostics($id, $diagnostics){
	      global $pdo;
	      if(!isset($pdo)) return;
	      try {
	          $stmt = $pdo->prepare("
	              INSERT INTO `openmvs_job_diagnostics`
	                  (`job_id`,`stage`,`pattern_id`,`severity`,`pattern_count`,`first_seen_line`,`last_seen_line`,`message_sample`,`message_summary`,`raw_log_path`,`diagnostic_category`,`diagnostic_code`,`diagnostic_severity`,`diagnostic_count`,`diagnostic_value`,`diagnostic_message`,`diagnostic_source`)
	              VALUES
	                  (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
	              ON DUPLICATE KEY UPDATE
	                  `severity`=VALUES(`severity`),
	                  `pattern_count`=VALUES(`pattern_count`),
	                  `first_seen_line`=VALUES(`first_seen_line`),
	                  `last_seen_line`=VALUES(`last_seen_line`),
	                  `message_sample`=VALUES(`message_sample`),
	                  `message_summary`=VALUES(`message_summary`),
	                  `raw_log_path`=VALUES(`raw_log_path`),
	                  `diagnostic_category`=VALUES(`diagnostic_category`),
	                  `diagnostic_code`=VALUES(`diagnostic_code`),
	                  `diagnostic_severity`=VALUES(`diagnostic_severity`),
	                  `diagnostic_count`=VALUES(`diagnostic_count`),
	                  `diagnostic_value`=VALUES(`diagnostic_value`),
	                  `diagnostic_message`=VALUES(`diagnostic_message`),
	                  `diagnostic_source`=VALUES(`diagnostic_source`)
	          ");
	          foreach($diagnostics as $row){
	              $code = (string)($row['pattern_id'] ?? '');
	              $category = explode('.', $code, 2)[0] ?: 'openmvs';
	              $severity = $row['severity'] ?? 'info';
	              $count = (int)($row['pattern_count'] ?? 0);
	              $message = $row['message_summary'] ?? null;
	              $source = $row['raw_log_path'] ?? null;
	              $stmt->execute([
	                  (int)$id,
	                  $row['stage'],
	                  $code,
	                  $severity,
	                  $count,
	                  $row['first_seen_line'],
	                  $row['last_seen_line'],
	                  $row['message_sample'],
	                  $message,
	                  $source,
	                  $category,
	                  $code,
	                  $severity,
	                  $count,
	                  null,
	                  $message,
	                  $source,
	              ]);
	          }
	      } catch(Throwable $e){
	          echo date('H:i:s') . " diagnostics upsert skipped: " . $e->getMessage() . "\n";
	      }
	  }

	  function ovm_diagnostic_summary_fields($diagnostics, $logPath, $successSummary=''){
	      $errorCount = 0;
	      $warningCount = 0;
	      $parts = [];

	      foreach($diagnostics as $row){
	          $count = (int)($row['pattern_count'] ?? 0);
	          if(($row['severity'] ?? '') === 'error') $errorCount += $count;
	          if(($row['severity'] ?? '') === 'warning') $warningCount += $count;
	          if(count($parts) < 3){
	              $parts[] = ($row['message_summary'] ?? $row['pattern_id']) . " x " . $count;
	          }
	      }

	      $status = $errorCount > 0 ? 'error' : ($warningCount > 0 ? 'warning' : 'ok');
	      $score = max(0, 100 - min(100, ($errorCount * 25) + ($warningCount * 5)));
	      $summary = $parts ? implode('; ', $parts) : ($successSummary !== '' ? $successSummary : 'No repeated OpenMVS diagnostics');

	      return [
	          'diagnostic_status' => $status,
	          'diagnostic_score' => number_format((float)$score, 2, '.', ''),
	          'diagnostic_summary' => $summary,
	          'diagnostic_log_path' => ovm_relative_openmvs_path($logPath),
	      ];
	  }

	  function ovm_success_diagnostic_summary($qa){
	      if(!is_array($qa)) return '';
	      $parts = [];
	      if(isset($qa['input_frame_count'], $qa['registered_frame_count'])){
	          $parts[] = $qa['registered_frame_count'] . '/' . $qa['input_frame_count'] . ' images registered';
	      }
	      if(isset($qa['texture_patch_count'])){
	          $parts[] = $qa['texture_patch_count'] . ' texture patches';
	      }
	      if(isset($qa['glb_file_size_mb'])){
	          $parts[] = 'GLB ' . $qa['glb_file_size_mb'] . ' MB';
	      }
	      return implode('; ', $parts);
	  }

	  function ovm_finalize_job_diagnostics($id, $logPath, $qa=[], $extraLine='', &$diagnosticsOut=null){
	      $text = is_file($logPath) ? (string)@file_get_contents($logPath) : '';
	      if(trim($extraLine) !== '') $text .= "\n" . trim($extraLine) . "\n";
	      $relativeLogPath = ovm_relative_openmvs_path($logPath);
	      $diagnostics = ovm_parse_log_diagnostics($text, $relativeLogPath);
	      if(func_num_args() >= 5) $diagnosticsOut = $diagnostics;
	      ovm_clear_job_diagnostics($id);
	      ovm_upsert_job_diagnostics($id, $diagnostics);
	      return ovm_diagnostic_summary_fields($diagnostics, $logPath, ovm_success_diagnostic_summary($qa));
	  }

	  function ovm_append_log_block($id, $msg){
	      $msg = trim((string)$msg);
	      if($msg === '') return;
	      ovm_update_timing_stage_from_line($id, $msg);
	      $line = $msg . "\n";
	      echo $line;
	  }

  function ovm_seconds_between($start, $end){
      if(empty($start) || empty($end)) return null;
      $startTs = strtotime((string)$start);
      $endTs = strtotime((string)$end);
      if($startTs === false || $endTs === false) return null;
      return max(0, $endTs - $startTs);
  }

  function ovm_finish_timing_fields($id, $workEnd){
      $fields = ['work_et_datetime'=>$workEnd];
      $rows = selectSQL_SAFE("SELECT `work_st_datetime` FROM `openmvs_jobs` WHERE `id`=? LIMIT 1", [$id]);
      $processSeconds = ovm_seconds_between($rows[0]['work_st_datetime'] ?? null, $workEnd);
      if(is_numeric($processSeconds)){
          $fields['duration_seconds'] = $processSeconds;
          $fields['process_seconds'] = $processSeconds;
      }
      return $fields;
  }

  function ovm_is_abort_requested($id){
      $root = dirname(dirname(__DIR__));
      $flag = "{$root}/uploads/{$id}/.abort";
      if(is_file($flag)) return true;
      $rows = selectSQL_SAFE("SELECT `status` FROM `openmvs_jobs` WHERE `id`=? LIMIT 1", [$id]);
      return isset($rows[0]['status']) && (string)$rows[0]['status'] !== '1';
  }

  function ovm_abort($id, $reason='暫停'){
      $workEnd = date('Y-m-d H:i:s');
      $fields = ovm_finish_timing_fields($id, $workEnd);
      $fields['status'] = 4;
      $fields['reason'] = $reason;
      updateSQL_SAFE(
          'openmvs_jobs',
          $fields,
          "`id`=?",
          [$id]
      );
      ovm_append_log_block($id, "[暫停] {$reason}");
      $root = dirname(dirname(__DIR__));
      @unlink("{$root}/uploads/{$id}/.abort");
      exit(0);
  }

  function ovm_write_failure_contract($id, $reason){
      $root = dirname(dirname(__DIR__));
      $jobDir = "{$root}/uploads/" . (int)$id;
      if(!is_dir($jobDir)) return;

      $rows = selectSQL_SAFE("SELECT `current_stage` FROM `openmvs_jobs` WHERE `id`=? LIMIT 1", [(int)$id]);
      $stage = trim((string)($rows[0]['current_stage'] ?? 'unknown'));
      if($stage === '') $stage = 'unknown';

      $warnings = [];
      $logPath = ovm_job_pipeline_log_path($id);
      $logText = is_file($logPath) ? (string)@file_get_contents($logPath) : '';
      foreach(ovm_parse_log_diagnostics($logText, ovm_relative_openmvs_path($logPath)) as $diag){
          $warning = trim((string)($diag['pattern_id'] ?? ''));
          if($warning !== '') $warnings[] = $warning . ' ' . trim((string)($diag['message_summary'] ?? ''));
      }
      foreach(selectSQL_SAFE("SELECT `pattern_id`,`message_summary` FROM `openmvs_job_diagnostics` WHERE `job_id`=? ORDER BY `pattern_count` DESC", [(int)$id]) as $diag){
          $warning = trim((string)($diag['pattern_id'] ?? ''));
          if($warning !== '') $warnings[] = $warning . ' ' . trim((string)($diag['message_summary'] ?? ''));
      }
      $warnings = array_values(array_unique($warnings));

      $cmd = "python3 " . escapeshellarg("{$root}/scripts/build_failure_summary.py") . " " .
          escapeshellarg($jobDir) . " --failed-stage " . escapeshellarg($stage) .
          " --reason " . escapeshellarg((string)$reason);
      foreach($warnings as $warning){
          $cmd .= " --diagnostic-warning " . escapeshellarg($warning);
      }
      $out = [];
      if(!ovm_run_cmd($cmd, $out, 120)){
          ovm_append_log_block($id, "[failure contract warning] " . implode("\n", $out));
      } else {
          ovm_append_log_block($id, "[failure contract] failure_summary.json");
      }
  }

  function ovm_check_abort($id){
      if(ovm_is_abort_requested($id)) ovm_abort($id);
  }

  function ovm_fail($id, $reason){
      ovm_write_failure_contract($id, $reason);
      $workEnd = date('Y-m-d H:i:s');
      $fields = ovm_finish_timing_fields($id, $workEnd);
      $fields['status'] = 3;
      $fields['reason'] = $reason;
      updateSQL_SAFE(
          'openmvs_jobs',
          $fields,
          "`id`=?",
          [$id]
      );
      ovm_append_log_block($id, $reason);
      exit(1);
  }
?>
