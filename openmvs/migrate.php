<?php
  require __DIR__ . "/../inc/config.php";
  if(php_sapi_name() !== 'cli'){
      require "{$base_dir}/inc/checkpassword.php";
  }

  $log = [];
  $ok = true;

  $createSQL = "
CREATE TABLE IF NOT EXISTS `openmvs_jobs` (
  `id` int(11) NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `title` varchar(255) DEFAULT NULL COMMENT '名稱',
  `orin_filename` varchar(255) DEFAULT NULL COMMENT '原檔名',
  `c_datetime` datetime DEFAULT NULL COMMENT '上傳時間',
  `IP` varchar(30) DEFAULT NULL COMMENT '上傳者 IP',
  `status` int(11) DEFAULT 0 COMMENT '0 pending 1 running 2 ready 3 failed 4 paused',
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
  `kind` varchar(30) DEFAULT NULL COMMENT 'mp4 or zip',
  `mask_mode` varchar(30) DEFAULT 'none' COMMENT 'none provided auto',
  `quality_preset` varchar(20) DEFAULT 'normal' COMMENT 'fast normal high',
  `capture_source_type` varchar(30) DEFAULT NULL COMMENT 'capture source type images video 360_video',
  `capture_preset` varchar(40) DEFAULT 'normal_orbit' COMMENT 'capture preset',
  `capture_quality_score` decimal(5,2) DEFAULT NULL COMMENT 'capture quality score 0-100',
  `capture_quality_grade` varchar(8) DEFAULT NULL COMMENT 'capture quality grade',
  `capture_quality_decision` varchar(32) DEFAULT NULL COMMENT 'run warn hold reject',
  `capture_mask_status` varchar(32) DEFAULT NULL COMMENT 'capture mask status',
  `capture_frame_count` int(11) DEFAULT NULL COMMENT 'capture frame count',
  `capture_selected_frame_count` int(11) DEFAULT NULL COMMENT 'selected frame count',
  `capture_aligned_camera_count` int(11) DEFAULT NULL COMMENT 'aligned camera count',
  `capture_registered_ratio` decimal(6,4) DEFAULT NULL COMMENT 'aligned camera ratio',
  `capture_warning_count` int(11) NOT NULL DEFAULT 0 COMMENT 'capture warning count',
  `capture_updated_at` datetime DEFAULT NULL COMMENT 'capture summary updated time',
  `email` varchar(512) DEFAULT NULL COMMENT '通知 email',
  `del` int(11) NOT NULL DEFAULT 0 COMMENT '0 active 1 deleted',
  `process_log` text DEFAULT NULL COMMENT '執行 log',
  `current_stage` varchar(80) DEFAULT NULL COMMENT '目前 pipeline 階段 key',
  `current_stage_label` varchar(255) DEFAULT NULL COMMENT '目前 pipeline 階段名稱',
  `duration_seconds` int(11) DEFAULT NULL COMMENT '本次 worker 轉檔秒數',
  `queue_seconds` int(11) DEFAULT NULL COMMENT '排隊秒數',
  `process_seconds` int(11) DEFAULT NULL COMMENT 'worker 轉檔秒數',
  `input_frame_count` int(11) DEFAULT NULL COMMENT '輸入影格或圖片數',
  `registered_frame_count` int(11) DEFAULT NULL COMMENT 'COLMAP registered frames',
  `glb_file_size_mb` double DEFAULT NULL COMMENT 'model.glb MB',
  `mesh_file_size_mb` double DEFAULT NULL COMMENT 'mesh ply MB',
  `texture_black_pixel_ratio` double DEFAULT NULL COMMENT 'texture dark pixel ratio',
  `texture_white_empty_pixel_ratio` double DEFAULT NULL COMMENT 'texture white empty pixel ratio',
	  `texture_width` int(11) DEFAULT NULL COMMENT 'texture width',
	  `texture_height` int(11) DEFAULT NULL COMMENT 'texture height',
	  `texture_patch_count` int(11) DEFAULT NULL COMMENT 'OpenMVS texture patch count',
	  `diagnostic_status` varchar(16) DEFAULT NULL COMMENT 'ok warning error',
	  `diagnostic_score` decimal(5,2) DEFAULT NULL COMMENT 'diagnostic quality score 0-100',
	  `diagnostic_summary` text DEFAULT NULL COMMENT 'diagnostic short summary',
	  `diagnostic_log_path` varchar(512) DEFAULT NULL COMMENT 'raw diagnostic log path',
	  PRIMARY KEY (`id`)
	) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='OpenMVS jobs';
	  ";

	  $diagnosticsSQL = "
	CREATE TABLE IF NOT EXISTS `openmvs_job_diagnostics` (
	  `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
	  `job_id` BIGINT NOT NULL,
	  `stage` VARCHAR(64) NOT NULL,
	  `pattern_id` VARCHAR(128) NOT NULL,
	  `severity` VARCHAR(16) NOT NULL DEFAULT 'info',
	  `pattern_count` INT NOT NULL DEFAULT 0,
	  `first_seen_line` INT NULL,
	  `last_seen_line` INT NULL,
	  `message_sample` TEXT NULL,
	  `message_summary` TEXT NULL,
	  `raw_log_path` VARCHAR(512) NULL,
	  `diagnostic_category` varchar(64) DEFAULT NULL,
	  `diagnostic_code` varchar(128) DEFAULT NULL,
	  `diagnostic_severity` varchar(16) DEFAULT NULL,
	  `diagnostic_count` int(11) NOT NULL DEFAULT 0,
	  `diagnostic_value` varchar(128) DEFAULT NULL,
	  `diagnostic_message` text DEFAULT NULL,
	  `diagnostic_source` varchar(512) DEFAULT NULL,
	  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	  `updated_at` DATETIME NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
	  UNIQUE KEY `uq_job_stage_pattern` (`job_id`, `stage`, `pattern_id`),
	  INDEX `idx_job_id` (`job_id`),
	  INDEX `idx_stage` (`stage`),
	  INDEX `idx_pattern_id` (`pattern_id`),
	  INDEX `idx_severity` (`severity`)
	) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='OpenMVS job diagnostics';
	  ";

	  $productsSQL = "
CREATE TABLE IF NOT EXISTS `openmvs_products` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `job_id` int(11) NOT NULL,
  `product_type` varchar(30) DEFAULT 'glb',
  `source_product_id` int(11) DEFAULT NULL,
  `texture_size` int(11) DEFAULT NULL,
  `status` int(11) DEFAULT 0 COMMENT '0 pending 1 running 2 ready 3 failed 4 paused',
  `file_path` varchar(512) DEFAULT NULL,
  `file_size_mb` double DEFAULT NULL,
  `reason` text DEFAULT NULL,
  `error_message` text DEFAULT NULL,
  `process_log` text DEFAULT NULL,
  `current_stage` varchar(80) DEFAULT NULL,
  `createAt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `work_st_datetime` datetime DEFAULT NULL,
  `work_et_datetime` datetime DEFAULT NULL,
  `del` int(11) NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  INDEX `idx_job_id` (`job_id`),
  INDEX `idx_product_type` (`product_type`),
  INDEX `idx_texture_size` (`texture_size`),
  INDEX `idx_status` (`status`),
  INDEX `idx_del` (`del`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='OpenMVS products';
	  ";

  $columns = [
      ['title', "varchar(255) DEFAULT NULL COMMENT '名稱'", 'id'],
      ['orin_filename', "varchar(255) DEFAULT NULL COMMENT '原檔名'", 'title'],
      ['c_datetime', "datetime DEFAULT NULL COMMENT '上傳時間'", 'orin_filename'],
      ['IP', "varchar(30) DEFAULT NULL COMMENT '上傳者 IP'", 'c_datetime'],
      ['status', "int(11) DEFAULT 0 COMMENT '0 pending 1 running 2 ready 3 failed 4 paused'", 'IP'],
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
      ['kind', "varchar(30) DEFAULT NULL COMMENT 'mp4 or zip'", 'scale'],
      ['mask_mode', "varchar(30) DEFAULT 'none' COMMENT 'none provided auto'", 'kind'],
      ['quality_preset', "varchar(20) DEFAULT 'normal' COMMENT 'fast normal high'", 'mask_mode'],
      ['capture_source_type', "varchar(30) DEFAULT NULL COMMENT 'capture source type images video 360_video'", 'quality_preset'],
      ['capture_preset', "varchar(40) DEFAULT 'normal_orbit' COMMENT 'capture preset'", 'capture_source_type'],
      ['capture_quality_score', "decimal(5,2) DEFAULT NULL COMMENT 'capture quality score 0-100'", 'capture_preset'],
      ['capture_quality_grade', "varchar(8) DEFAULT NULL COMMENT 'capture quality grade'", 'capture_quality_score'],
      ['capture_quality_decision', "varchar(32) DEFAULT NULL COMMENT 'run warn hold reject'", 'capture_quality_grade'],
      ['capture_mask_status', "varchar(32) DEFAULT NULL COMMENT 'capture mask status'", 'capture_quality_decision'],
      ['capture_frame_count', "int(11) DEFAULT NULL COMMENT 'capture frame count'", 'capture_mask_status'],
      ['capture_selected_frame_count', "int(11) DEFAULT NULL COMMENT 'selected frame count'", 'capture_frame_count'],
      ['capture_aligned_camera_count', "int(11) DEFAULT NULL COMMENT 'aligned camera count'", 'capture_selected_frame_count'],
      ['capture_registered_ratio', "decimal(6,4) DEFAULT NULL COMMENT 'aligned camera ratio'", 'capture_aligned_camera_count'],
      ['capture_warning_count', "int(11) NOT NULL DEFAULT 0 COMMENT 'capture warning count'", 'capture_registered_ratio'],
      ['capture_updated_at', "datetime DEFAULT NULL COMMENT 'capture summary updated time'", 'capture_warning_count'],
      ['email', "varchar(512) DEFAULT NULL COMMENT '通知 email'", 'capture_updated_at'],
      ['del', "int(11) NOT NULL DEFAULT 0 COMMENT '0 active 1 deleted'", 'email'],
      ['process_log', "text DEFAULT NULL COMMENT '執行 log'", 'del'],
      ['current_stage', "varchar(80) DEFAULT NULL COMMENT '目前 pipeline 階段 key'", 'process_log'],
      ['current_stage_label', "varchar(255) DEFAULT NULL COMMENT '目前 pipeline 階段名稱'", 'current_stage'],
      ['duration_seconds', "int(11) DEFAULT NULL COMMENT '本次 worker 轉檔秒數'", 'current_stage_label'],
      ['queue_seconds', "int(11) DEFAULT NULL COMMENT '排隊秒數'", 'duration_seconds'],
      ['process_seconds', "int(11) DEFAULT NULL COMMENT 'worker 轉檔秒數'", 'queue_seconds'],
      ['input_frame_count', "int(11) DEFAULT NULL COMMENT '輸入影格或圖片數'", 'process_seconds'],
      ['registered_frame_count', "int(11) DEFAULT NULL COMMENT 'COLMAP registered frames'", 'input_frame_count'],
      ['glb_file_size_mb', "double DEFAULT NULL COMMENT 'model.glb MB'", 'registered_frame_count'],
      ['mesh_file_size_mb', "double DEFAULT NULL COMMENT 'mesh ply MB'", 'glb_file_size_mb'],
      ['texture_black_pixel_ratio', "double DEFAULT NULL COMMENT 'texture dark pixel ratio'", 'mesh_file_size_mb'],
      ['texture_white_empty_pixel_ratio', "double DEFAULT NULL COMMENT 'texture white empty pixel ratio'", 'texture_black_pixel_ratio'],
	      ['texture_width', "int(11) DEFAULT NULL COMMENT 'texture width'", 'texture_white_empty_pixel_ratio'],
	      ['texture_height', "int(11) DEFAULT NULL COMMENT 'texture height'", 'texture_width'],
	      ['texture_patch_count', "int(11) DEFAULT NULL COMMENT 'OpenMVS texture patch count'", 'texture_height'],
	      ['diagnostic_status', "varchar(16) DEFAULT NULL COMMENT 'ok warning error'", 'texture_patch_count'],
	      ['diagnostic_score', "decimal(5,2) DEFAULT NULL COMMENT 'diagnostic quality score 0-100'", 'diagnostic_status'],
	      ['diagnostic_summary', "text DEFAULT NULL COMMENT 'diagnostic short summary'", 'diagnostic_score'],
	      ['diagnostic_log_path', "varchar(512) DEFAULT NULL COMMENT 'raw diagnostic log path'", 'diagnostic_summary'],
	  ];

	  $diagnosticColumns = [
	      ['diagnostic_category', "varchar(64) DEFAULT NULL", 'raw_log_path'],
	      ['diagnostic_code', "varchar(128) DEFAULT NULL", 'diagnostic_category'],
	      ['diagnostic_severity', "varchar(16) DEFAULT NULL", 'diagnostic_code'],
	      ['diagnostic_count', "int(11) NOT NULL DEFAULT 0", 'diagnostic_severity'],
	      ['diagnostic_value', "varchar(128) DEFAULT NULL", 'diagnostic_count'],
	      ['diagnostic_message', "text DEFAULT NULL", 'diagnostic_value'],
	      ['diagnostic_source', "varchar(512) DEFAULT NULL", 'diagnostic_message'],
	  ];

	  $productColumns = [
	      ['id', "int(11) NOT NULL AUTO_INCREMENT PRIMARY KEY", ''],
	      ['job_id', "int(11) NOT NULL", 'id'],
	      ['product_type', "varchar(30) DEFAULT 'glb'", 'job_id'],
	      ['source_product_id', "int(11) DEFAULT NULL", 'product_type'],
	      ['texture_size', "int(11) DEFAULT NULL", 'source_product_id'],
	      ['status', "int(11) DEFAULT 0 COMMENT '0 pending 1 running 2 ready 3 failed 4 paused'", 'texture_size'],
	      ['file_path', "varchar(512) DEFAULT NULL", 'status'],
	      ['file_size_mb', "double DEFAULT NULL", 'file_path'],
	      ['reason', "text DEFAULT NULL", 'file_size_mb'],
	      ['error_message', "text DEFAULT NULL", 'reason'],
	      ['process_log', "text DEFAULT NULL", 'error_message'],
	      ['current_stage', "varchar(80) DEFAULT NULL", 'process_log'],
	      ['createAt', "datetime NOT NULL DEFAULT CURRENT_TIMESTAMP", 'current_stage'],
	      ['work_st_datetime', "datetime DEFAULT NULL", 'createAt'],
	      ['work_et_datetime', "datetime DEFAULT NULL", 'work_st_datetime'],
	      ['del', "int(11) NOT NULL DEFAULT 0", 'work_et_datetime'],
	  ];

	  $productIndexes = [
	      ['idx_job_id', "(`job_id`)"],
	      ['idx_product_type', "(`product_type`)"],
	      ['idx_texture_size', "(`texture_size`)"],
	      ['idx_status', "(`status`)"],
	      ['idx_del', "(`del`)"],
	  ];

	  try {
	      $pdo->exec($createSQL);
	      $log[] = ['ok', 'openmvs_jobs table ready'];
	  } catch(PDOException $e){
	      $log[] = ['fail', 'create table failed: ' . $e->getMessage()];
	      $ok = false;
	  }

	  if($ok){
	      try {
	          $pdo->exec($diagnosticsSQL);
	          $log[] = ['ok', 'openmvs_job_diagnostics table ready'];
	      } catch(PDOException $e){
	          $log[] = ['fail', 'create diagnostics table failed: ' . $e->getMessage()];
	          $ok = false;
	      }
	  }

	  if($ok){
	      try {
	          $pdo->exec($productsSQL);
	          $log[] = ['ok', 'openmvs_products table ready'];
	      } catch(PDOException $e){
	          $log[] = ['fail', 'create products table failed: ' . $e->getMessage()];
	          $ok = false;
	      }
	  }

  $existCols = [];
  if($ok){
      try {
          $rows = $pdo->query("SHOW COLUMNS FROM `openmvs_jobs`")->fetchAll(PDO::FETCH_ASSOC);
          foreach($rows as $row){
              $existCols[] = $row['Field'];
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

          $sql = "ALTER TABLE `openmvs_jobs` ADD COLUMN `{$name}` {$definition} AFTER `{$after}`";
          try {
              $pdo->exec($sql);
              $existCols[] = $name;
              $log[] = ['add', "column `{$name}` added"];
          } catch(PDOException $e){
              $log[] = ['fail', "column `{$name}` add failed: " . $e->getMessage()];
              $ok = false;
          }
      }
  }

  $existDiagnosticCols = [];
  if($ok){
      try {
          $rows = $pdo->query("SHOW COLUMNS FROM `openmvs_job_diagnostics`")->fetchAll(PDO::FETCH_ASSOC);
          foreach($rows as $row){
              $existDiagnosticCols[] = $row['Field'];
          }
      } catch(PDOException $e){
          $log[] = ['fail', 'show diagnostics columns failed: ' . $e->getMessage()];
          $ok = false;
      }
  }

  if($ok){
      foreach($diagnosticColumns as $column){
          [$name, $definition, $after] = $column;
          if(in_array($name, $existDiagnosticCols, true)){
              $log[] = ['skip', "diagnostic column `{$name}` already exists"];
              continue;
          }

          $sql = "ALTER TABLE `openmvs_job_diagnostics` ADD COLUMN `{$name}` {$definition} AFTER `{$after}`";
          try {
              $pdo->exec($sql);
              $existDiagnosticCols[] = $name;
              $log[] = ['add', "diagnostic column `{$name}` added"];
          } catch(PDOException $e){
              $log[] = ['fail', "diagnostic column `{$name}` add failed: " . $e->getMessage()];
              $ok = false;
          }
      }
  }

  $existProductCols = [];
  if($ok){
      try {
          $rows = $pdo->query("SHOW COLUMNS FROM `openmvs_products`")->fetchAll(PDO::FETCH_ASSOC);
          foreach($rows as $row){
              $existProductCols[] = $row['Field'];
          }
      } catch(PDOException $e){
          $log[] = ['fail', 'show product columns failed: ' . $e->getMessage()];
          $ok = false;
      }
  }

  if($ok){
      foreach($productColumns as $column){
          [$name, $definition, $after] = $column;
          if(in_array($name, $existProductCols, true)){
              $log[] = ['skip', "product column `{$name}` already exists"];
              continue;
          }

          $place = $after === '' ? 'FIRST' : "AFTER `{$after}`";
          $sql = "ALTER TABLE `openmvs_products` ADD COLUMN `{$name}` {$definition} {$place}";
          try {
              $pdo->exec($sql);
              $existProductCols[] = $name;
              $log[] = ['add', "product column `{$name}` added"];
          } catch(PDOException $e){
              $log[] = ['fail', "product column `{$name}` add failed: " . $e->getMessage()];
              $ok = false;
          }
      }
  }

  $existProductIndexes = [];
  if($ok){
      try {
          $rows = $pdo->query("SHOW INDEX FROM `openmvs_products`")->fetchAll(PDO::FETCH_ASSOC);
          foreach($rows as $row){
              $existProductIndexes[] = $row['Key_name'];
          }
      } catch(PDOException $e){
          $log[] = ['fail', 'show product indexes failed: ' . $e->getMessage()];
          $ok = false;
      }
  }

  if($ok){
      foreach($productIndexes as $index){
          [$name, $definition] = $index;
          if(in_array($name, $existProductIndexes, true)){
              $log[] = ['skip', "product index `{$name}` already exists"];
              continue;
          }

          $sql = "ALTER TABLE `openmvs_products` ADD INDEX `{$name}` {$definition}";
          try {
              $pdo->exec($sql);
              $existProductIndexes[] = $name;
              $log[] = ['add', "product index `{$name}` added"];
          } catch(PDOException $e){
              $log[] = ['fail', "product index `{$name}` add failed: " . $e->getMessage()];
              $ok = false;
          }
      }
  }

  if(php_sapi_name() === 'cli'){
      foreach($log as $entry){
          [$type, $message] = $entry;
          echo '[' . strtoupper($type) . '] ' . $message . PHP_EOL;
      }
      echo $ok ? "openmvs_jobs migration complete\n" : "openmvs_jobs migration failed\n";
      exit($ok ? 0 : 1);
  }
?>
<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <title>OpenMVS Migration</title>
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
  <h2>OpenMVS Migration</h2>
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
  <p><?= $ok ? 'openmvs_jobs migration complete' : 'openmvs_jobs migration failed'; ?></p>
</body>
</html>
