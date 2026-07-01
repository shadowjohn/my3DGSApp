<?php
  require __DIR__ . "/inc/config.php";

  if(php_sapi_name() !== 'cli'){
      http_response_code(403);
      echo "請於 CLI 執行：php migrate.php";
      exit();
  }

  $log = [];
  $ok = true;

  $createSQL = "
CREATE TABLE IF NOT EXISTS `users` (
  `id` int(11) NOT NULL AUTO_INCREMENT COMMENT '流水號',
  `loginid` varchar(80) NOT NULL COMMENT '登入帳號',
  `loginpd` char(64) NOT NULL COMMENT 'sha256 password',
  `name` varchar(120) NOT NULL DEFAULT '' COMMENT '姓名',
  `is_admin` tinyint(1) NOT NULL DEFAULT 0 COMMENT '0 user 1 admin',
  `createAt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
  `del` tinyint(1) NOT NULL DEFAULT 0 COMMENT '0 active 1 deleted',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_users_loginid` (`loginid`),
  KEY `idx_users_del` (`del`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='登入使用者';
  ";

  $columns = [
      ['loginid', "varchar(80) NOT NULL COMMENT '登入帳號'", 'id'],
      ['loginpd', "char(64) NOT NULL COMMENT 'sha256 password'", 'loginid'],
      ['name', "varchar(120) NOT NULL DEFAULT '' COMMENT '姓名'", 'loginpd'],
      ['is_admin', "tinyint(1) NOT NULL DEFAULT 0 COMMENT '0 user 1 admin'", 'name'],
      ['createAt', "datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間'", 'is_admin'],
      ['del', "tinyint(1) NOT NULL DEFAULT 0 COMMENT '0 active 1 deleted'", 'createAt'],
  ];

  try {
      $pdo->exec($createSQL);
      $log[] = ['ok', 'users table ready'];
  } catch(PDOException $e){
      $log[] = ['fail', 'create users failed: ' . $e->getMessage()];
      $ok = false;
  }

  $existCols = [];
  if($ok){
      try {
          $rows = $pdo->query("SHOW COLUMNS FROM `users`")->fetchAll(PDO::FETCH_ASSOC);
          foreach($rows as $row) $existCols[] = $row['Field'];
      } catch(PDOException $e){
          $log[] = ['fail', 'show users columns failed: ' . $e->getMessage()];
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
          try {
              $pdo->exec("ALTER TABLE `users` ADD COLUMN `{$name}` {$definition} AFTER `{$after}`");
              $existCols[] = $name;
              $log[] = ['add', "column `{$name}` added"];
          } catch(PDOException $e){
              $log[] = ['fail', "column `{$name}` add failed: " . $e->getMessage()];
              $ok = false;
          }
      }
  }

  if($ok){
      try {
          $adminPassword = (string)getenv('FOCUSIT_ADMIN_PASSWORD');
          if($adminPassword === ''){
              $log[] = ['skip', 'admin user seed skipped: set FOCUSIT_ADMIN_PASSWORD to create/reset admin'];
          } else {
              $sql = "
INSERT INTO `users` (`loginid`,`loginpd`,`name`,`is_admin`,`createAt`,`del`)
VALUES (:admin_loginid, SHA2(:admin_password, 256), :admin_name, 1, NOW(), 0)
ON DUPLICATE KEY UPDATE
  `loginpd`=VALUES(`loginpd`),
  `name`=VALUES(`name`),
  `is_admin`=1,
  `del`=0
              ";
              $q = $pdo->prepare($sql);
              $q->execute([
                  ':admin_loginid'=>'admin',
                  ':admin_password'=>$adminPassword,
                  ':admin_name'=>'系統管理員',
              ]);
              $log[] = ['ok', 'admin user ready'];
          }
      } catch(PDOException $e){
          $log[] = ['fail', 'seed admin failed: ' . $e->getMessage()];
          $ok = false;
      }
  }

  foreach($log as $entry){
      [$type, $message] = $entry;
      echo '[' . strtoupper($type) . '] ' . $message . PHP_EOL;
  }
  echo $ok ? "users migration complete\n" : "users migration failed\n";
  exit($ok ? 0 : 1);
