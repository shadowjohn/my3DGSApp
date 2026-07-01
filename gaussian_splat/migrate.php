<?php
  require __DIR__ . "/../inc/config.php";
  if(php_sapi_name() !== 'cli'){
      require "{$base_dir}/inc/checkpassword.php";
  }

  $log = [];
  $ok = true;

  $createSQL = "
CREATE TABLE IF NOT EXISTS `gaussian_splat_jobs` (
  `id` int(11) NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `title` varchar(255) DEFAULT NULL COMMENT '名稱',
  `orin_filename` varchar(255) DEFAULT NULL COMMENT '原檔名',
  `c_datetime` datetime DEFAULT NULL COMMENT '上傳時間',
  `IP` varchar(30) DEFAULT NULL COMMENT '上傳者 IP',
  `status` int(11) DEFAULT 0 COMMENT '0 waiting 1 running 2 ready 3 failed 4 aborted 5 waiting_override',
  `reason` text DEFAULT NULL COMMENT '失敗原因',
  `work_st_datetime` datetime DEFAULT NULL COMMENT '轉檔開始時間',
  `work_et_datetime` datetime DEFAULT NULL COMMENT '轉檔結束時間',
  `lon` double DEFAULT NULL COMMENT '坐標 lon',
  `lat` double DEFAULT NULL COMMENT '坐標 lat',
  `alt` double DEFAULT NULL COMMENT '坐標高度',
  `heading` double DEFAULT NULL COMMENT 'heading',
  `pitch` double DEFAULT NULL COMMENT 'pitch',
  `roll` double DEFAULT NULL COMMENT 'roll',
  `scale` double DEFAULT 1 COMMENT 'scale',
  `camera_lon` double DEFAULT NULL COMMENT '預設相機 lon',
  `camera_lat` double DEFAULT NULL COMMENT '預設相機 lat',
  `camera_alt` double DEFAULT NULL COMMENT '預設相機高度',
  `camera_heading` double DEFAULT NULL COMMENT '預設相機 heading',
  `camera_pitch` double DEFAULT NULL COMMENT '預設相機 pitch',
  `camera_roll` double DEFAULT NULL COMMENT '預設相機 roll',
  `kind` varchar(30) DEFAULT NULL COMMENT 'mp4',
  `pipeline_mode` varchar(30) DEFAULT 'fast' COMMENT 'pipeline mode',
  `email` varchar(512) DEFAULT NULL COMMENT '通知 email',
  `del` int(11) NOT NULL DEFAULT 0 COMMENT '0 active 1 deleted',
  `process_log` text DEFAULT NULL COMMENT '執行 log',
  `current_stage` varchar(80) DEFAULT NULL COMMENT '目前 pipeline 階段 key',
  `current_stage_label` varchar(255) DEFAULT NULL COMMENT '目前 pipeline 階段名稱',
  `duration_seconds` int(11) DEFAULT NULL COMMENT '上傳入隊到完成總秒數',
  `queue_seconds` int(11) DEFAULT NULL COMMENT '排隊秒數',
  `process_seconds` int(11) DEFAULT NULL COMMENT 'worker 轉檔秒數',
  `frame_count` int(11) DEFAULT NULL COMMENT '抽幀數',
  `registered_frame_count` int(11) DEFAULT NULL COMMENT 'COLMAP registered frames',
  `splat_file_size_mb` double DEFAULT NULL COMMENT 'splat.ply MB',
  `confidence_score` decimal(5,2) DEFAULT NULL COMMENT 'capture confidence score',
  `confidence_grade` varchar(20) DEFAULT NULL COMMENT 'capture confidence grade',
  `confidence_decision` varchar(60) DEFAULT NULL COMMENT 'confidence gate decision',
  `confidence_effective_decision` varchar(60) DEFAULT NULL COMMENT 'confidence effective decision',
  `confidence_gate_json` text DEFAULT NULL COMMENT 'confidence gate JSON',
  `confidence_override` int(11) NOT NULL DEFAULT 0 COMMENT 'manual confidence override',
  `confidence_override_reason` text DEFAULT NULL COMMENT 'manual confidence override reason',
  `confidence_risk_count` int(11) NOT NULL DEFAULT 0 COMMENT 'non-low confidence risk count',
  `confidence_recommendation_count` int(11) NOT NULL DEFAULT 0 COMMENT 'confidence recommendation count',
  `confidence_needs_override` tinyint(1) NOT NULL DEFAULT 0 COMMENT 'confidence gate needs manual override',
  `confidence_override_status` varchar(32) DEFAULT NULL COMMENT 'confidence override status',
  `confidence_updated_at` datetime DEFAULT NULL COMMENT 'confidence summary updated time',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Gaussian Splat jobs';
  ";

  $columns = [
      ['title', "varchar(255) DEFAULT NULL COMMENT '名稱'", 'id'],
      ['orin_filename', "varchar(255) DEFAULT NULL COMMENT '原檔名'", 'title'],
      ['c_datetime', "datetime DEFAULT NULL COMMENT '上傳時間'", 'orin_filename'],
      ['IP', "varchar(30) DEFAULT NULL COMMENT '上傳者 IP'", 'c_datetime'],
      ['status', "int(11) DEFAULT 0 COMMENT '0 waiting 1 running 2 ready 3 failed 4 aborted 5 waiting_override'", 'IP'],
      ['reason', "text DEFAULT NULL COMMENT '失敗原因'", 'status'],
      ['work_st_datetime', "datetime DEFAULT NULL COMMENT '轉檔開始時間'", 'reason'],
      ['work_et_datetime', "datetime DEFAULT NULL COMMENT '轉檔結束時間'", 'work_st_datetime'],
      ['lon', "double DEFAULT NULL COMMENT '坐標 lon'", 'work_et_datetime'],
      ['lat', "double DEFAULT NULL COMMENT '坐標 lat'", 'lon'],
      ['alt', "double DEFAULT NULL COMMENT '坐標高度'", 'lat'],
      ['heading', "double DEFAULT NULL COMMENT 'heading'", 'alt'],
      ['pitch', "double DEFAULT NULL COMMENT 'pitch'", 'heading'],
      ['roll', "double DEFAULT NULL COMMENT 'roll'", 'pitch'],
      ['scale', "double DEFAULT 1 COMMENT 'scale'", 'roll'],
      ['camera_lon', "double DEFAULT NULL COMMENT '預設相機 lon'", 'scale'],
      ['camera_lat', "double DEFAULT NULL COMMENT '預設相機 lat'", 'camera_lon'],
      ['camera_alt', "double DEFAULT NULL COMMENT '預設相機高度'", 'camera_lat'],
      ['camera_heading', "double DEFAULT NULL COMMENT '預設相機 heading'", 'camera_alt'],
      ['camera_pitch', "double DEFAULT NULL COMMENT '預設相機 pitch'", 'camera_heading'],
      ['camera_roll', "double DEFAULT NULL COMMENT '預設相機 roll'", 'camera_pitch'],
      ['kind', "varchar(30) DEFAULT NULL COMMENT 'mp4'", 'camera_roll'],
      ['pipeline_mode', "varchar(30) DEFAULT 'fast' COMMENT 'pipeline mode'", 'kind'],
      ['email', "varchar(512) DEFAULT NULL COMMENT '通知 email'", 'pipeline_mode'],
      ['del', "int(11) NOT NULL DEFAULT 0 COMMENT '0 active 1 deleted'", 'email'],
      ['process_log', "text DEFAULT NULL COMMENT '執行 log'", 'del'],
      ['current_stage', "varchar(80) DEFAULT NULL COMMENT '目前 pipeline 階段 key'", 'process_log'],
      ['current_stage_label', "varchar(255) DEFAULT NULL COMMENT '目前 pipeline 階段名稱'", 'current_stage'],
      ['duration_seconds', "int(11) DEFAULT NULL COMMENT '上傳入隊到完成總秒數'", 'current_stage_label'],
      ['queue_seconds', "int(11) DEFAULT NULL COMMENT '排隊秒數'", 'duration_seconds'],
      ['process_seconds', "int(11) DEFAULT NULL COMMENT 'worker 轉檔秒數'", 'queue_seconds'],
      ['frame_count', "int(11) DEFAULT NULL COMMENT '抽幀數'", 'process_seconds'],
      ['registered_frame_count', "int(11) DEFAULT NULL COMMENT 'COLMAP registered frames'", 'frame_count'],
      ['splat_file_size_mb', "double DEFAULT NULL COMMENT 'splat.ply MB'", 'registered_frame_count'],
      ['confidence_score', "decimal(5,2) DEFAULT NULL COMMENT 'capture confidence score'", 'splat_file_size_mb'],
      ['confidence_grade', "varchar(20) DEFAULT NULL COMMENT 'capture confidence grade'", 'confidence_score'],
      ['confidence_decision', "varchar(60) DEFAULT NULL COMMENT 'confidence gate decision'", 'confidence_grade'],
      ['confidence_effective_decision', "varchar(60) DEFAULT NULL COMMENT 'confidence effective decision'", 'confidence_decision'],
      ['confidence_gate_json', "text DEFAULT NULL COMMENT 'confidence gate JSON'", 'confidence_effective_decision'],
      ['confidence_override', "int(11) NOT NULL DEFAULT 0 COMMENT 'manual confidence override'", 'confidence_gate_json'],
      ['confidence_override_reason', "text DEFAULT NULL COMMENT 'manual confidence override reason'", 'confidence_override'],
      ['confidence_risk_count', "int(11) NOT NULL DEFAULT 0 COMMENT 'non-low confidence risk count'", 'confidence_override_reason'],
      ['confidence_recommendation_count', "int(11) NOT NULL DEFAULT 0 COMMENT 'confidence recommendation count'", 'confidence_risk_count'],
      ['confidence_needs_override', "tinyint(1) NOT NULL DEFAULT 0 COMMENT 'confidence gate needs manual override'", 'confidence_recommendation_count'],
      ['confidence_override_status', "varchar(32) DEFAULT NULL COMMENT 'confidence override status'", 'confidence_needs_override'],
      ['confidence_updated_at', "datetime DEFAULT NULL COMMENT 'confidence summary updated time'", 'confidence_override_status'],
  ];

  try {
      $pdo->exec($createSQL);
      $log[] = ['ok', 'gaussian_splat_jobs table ready'];
  } catch(PDOException $e){
      $log[] = ['fail', 'create table failed: ' . $e->getMessage()];
      $ok = false;
  }

  $existCols = [];
  $existColDefs = [];
  if($ok){
      try {
          $rows = $pdo->query("SHOW COLUMNS FROM `gaussian_splat_jobs`")->fetchAll(PDO::FETCH_ASSOC);
          foreach($rows as $row){
              $existCols[] = $row['Field'];
              $existColDefs[$row['Field']] = $row;
          }
      } catch(PDOException $e){
          $log[] = ['fail', 'show columns failed: ' . $e->getMessage()];
          $ok = false;
      }
  }

  if($ok){
      foreach($columns as $column){
          [$name, $definition, $after] = $column;
          if(in_array($name, $existCols, true)){
              $log[] = ['skip', "column `{$name}` already exists"];
              continue;
          }

          $sql = "ALTER TABLE `gaussian_splat_jobs` ADD COLUMN `{$name}` {$definition} AFTER `{$after}`";
          try {
              $pdo->exec($sql);
              $existCols[] = $name;
              $existColDefs[$name] = ['Field'=>$name, 'Type'=>$definition];
              $log[] = ['add', "column `{$name}` added"];
          } catch(PDOException $e){
              $log[] = ['fail', "column `{$name}` add failed: " . $e->getMessage()];
              $ok = false;
          }
      }
  }

  if($ok && isset($existColDefs['confidence_score']) && strtolower((string)$existColDefs['confidence_score']['Type']) !== 'decimal(5,2)'){
      try {
          $pdo->exec("ALTER TABLE `gaussian_splat_jobs` MODIFY COLUMN `confidence_score` decimal(5,2) DEFAULT NULL COMMENT 'capture confidence score'");
          $log[] = ['add', 'column `confidence_score` type repaired to decimal(5,2)'];
      } catch(PDOException $e){
          $log[] = ['fail', 'column `confidence_score` type repair failed: ' . $e->getMessage()];
          $ok = false;
      }
  }

  if(php_sapi_name() === 'cli'){
      foreach($log as $entry){
          [$type, $message] = $entry;
          echo '[' . strtoupper($type) . '] ' . $message . PHP_EOL;
      }
      echo $ok ? "gaussian_splat_jobs migration complete\n" : "gaussian_splat_jobs migration failed\n";
      exit($ok ? 0 : 1);
  }
?>
<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <title>Gaussian Splat Migration</title>
  <style>
    body{font-family:monospace;padding:20px;background:#f5f5f5;}
    table{border-collapse:collapse;width:100%;max-width:900px;}
    td{padding:6px 10px;border-bottom:1px solid #ddd;}
    .ok,.add{color:#16803c;font-weight:bold;}
    .skip{color:#667085;}
    .fail{color:#c1121f;font-weight:bold;}
  </style>
</head>
<body>
  <h2>Gaussian Splat Migration</h2>
  <table>
    <tbody>
<?php foreach($log as $entry): [$type, $message] = $entry; ?>
      <tr>
        <td class="<?=$type;?>"><?=htmlspecialchars(strtoupper($type));?></td>
        <td><?=htmlspecialchars($message);?></td>
      </tr>
<?php endforeach; ?>
    </tbody>
  </table>
  <p><?= $ok ? 'gaussian_splat_jobs migration complete' : 'gaussian_splat_jobs migration failed'; ?></p>
</body>
</html>
