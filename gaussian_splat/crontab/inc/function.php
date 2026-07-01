<?php
  function gs_remember_cmd_output(&$out, $line){
      $out[] = $line;
      if(count($out) > 500){
          array_shift($out);
      }
  }

  function gs_run_cmd($cmd, &$out=null, $timeout=86400, $abortChecker=null, $lineCallback=null){
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
                  gs_remember_cmd_output($out, $line);
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
              if($pid > 0){
                  @exec("pkill -TERM -P " . escapeshellarg((string)$pid));
              }
              proc_terminate($process);
              gs_remember_cmd_output($out, "aborted by user");
              if(is_callable($lineCallback)) $lineCallback("aborted by user");
              fclose($pipes[1]);
              proc_close($process);
              return false;
          }

          usleep(250000);
      }

      $chunk = stream_get_contents($pipes[1]);
      if($chunk !== false && $chunk !== ''){
          $buffer .= $chunk;
      }
      if($buffer !== ''){
          $line = rtrim($buffer, "\r\n");
          gs_remember_cmd_output($out, $line);
          if(is_callable($lineCallback)) $lineCallback($line);
      }

      fclose($pipes[1]);
      $closeCode = proc_close($process);
      if($exitCode === null || $exitCode === -1){
          $exitCode = $closeCode;
      }
      return $exitCode === 0;
  }

  function gs_append_log($id, $msg){
      $line = date('H:i:s') . " " . $msg . "\n";
      echo $line;
      global $pdo;
      if(isset($pdo)){
          $stmt = $pdo->prepare("UPDATE `gaussian_splat_jobs` SET `process_log` = RIGHT(CONCAT(IFNULL(`process_log`,''), ?), 60000) WHERE `id`=?");
          $stmt->execute([$line, $id]);
      }
      gs_check_abort($id);
  }

  function gs_parse_timing_stage_line($msg){
      $msg = trim((string)$msg);
      if(strpos($msg, '[timing] START ') !== 0) return null;
      if(preg_match('/^\[timing\] START ([A-Za-z0-9_-]+) (.+)$/', $msg, $m)){
          return ['key'=>$m[1], 'label'=>$m[2]];
      }
      return null;
  }

  function gs_update_timing_stage_from_line($id, $msg){
      $stage = gs_parse_timing_stage_line($msg);
      if(!$stage) return;
      updateSQL_SAFE(
          'gaussian_splat_jobs',
          ['current_stage'=>$stage['key'], 'current_stage_label'=>$stage['label']],
          "`id`=?",
          [$id]
      );
  }

  function gs_seconds_between($start, $end){
      if(empty($start) || empty($end)) return null;
      $startTs = strtotime((string)$start);
      $endTs = strtotime((string)$end);
      if($startTs === false || $endTs === false) return null;
      return max(0, $endTs - $startTs);
  }

  function gs_video_duration_seconds($path){
      if(!is_file($path)) return null;
      $cmd = "ffprobe -v error -show_entries format=duration -of default=nk=1:nw=1 " . escapeshellarg($path);
      $out = [];
      $exitCode = 0;
      @exec($cmd, $out, $exitCode);
      if($exitCode !== 0 || !isset($out[0])) return null;
      $duration = (float)trim((string)$out[0]);
      return $duration > 0 ? $duration : null;
  }

  function gs_env_prefix(array $env){
      if(!$env) return '';
      $parts = ['env'];
      foreach($env as $key => $value){
          $parts[] = escapeshellarg($key . '=' . $value);
      }
      return implode(' ', $parts) . ' ';
  }

  function gs_append_log_block($id, $msg){
      $msg = trim((string)$msg);
      if($msg === '') return;
      gs_update_timing_stage_from_line($id, $msg);

      $line = $msg . "\n";
      echo $line;
      global $pdo;
      if(isset($pdo)){
          $stmt = $pdo->prepare("UPDATE `gaussian_splat_jobs` SET `process_log` = RIGHT(CONCAT(IFNULL(`process_log`,''), ?), 60000) WHERE `id`=?");
          $stmt->execute([$line, $id]);
      }
  }

  function gs_is_abort_requested($id){
      $root = dirname(dirname(__DIR__));
      $flag = "{$root}/uploads/{$id}/.abort";
      if(is_file($flag)){
          return true;
      }

      $rows = selectSQL_SAFE("SELECT `status` FROM `gaussian_splat_jobs` WHERE `id`=? LIMIT 1", [$id]);
      return isset($rows[0]['status']) && (string)$rows[0]['status'] !== '1';
  }

  function gs_abort($id, $reason='使用者中止'){
      updateSQL_SAFE(
          'gaussian_splat_jobs',
          ['status'=>4,'reason'=>$reason,'work_et_datetime'=>date('Y-m-d H:i:s')],
          "`id`=?",
          [$id]
      );
      gs_append_log_block($id, "[使用者中止] {$reason}");
      $root = dirname(dirname(__DIR__));
      $flag = "{$root}/uploads/{$id}/.abort";
      @unlink($flag);
      exit(0);
  }

  function gs_check_abort($id){
      if(gs_is_abort_requested($id)){
          gs_abort($id);
      }
  }

  function gs_fail($id, $reason){
      updateSQL_SAFE(
          'gaussian_splat_jobs',
          ['status'=>3,'reason'=>$reason,'work_et_datetime'=>date('Y-m-d H:i:s')],
          "`id`=?",
          [$id]
      );
      gs_append_log_block($id, $reason);
      exit(1);
  }
