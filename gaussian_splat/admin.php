<?php
  require __DIR__ . "/../inc/config.php";
  require "{$base_dir}/inc/checkpassword.php";
  require_once __DIR__ . "/job_view.php";

  $sortMap = [
      'id' => '`id`',
      'score' => '`confidence_score`',
      'grade' => '`confidence_grade`',
      'decision' => '`confidence_decision`',
      'review' => '`confidence_needs_override`',
      'override' => '`confidence_override_status`',
  ];
  $sort = $_GET['sort'] ?? 'id';
  if(!isset($sortMap[$sort])) $sort = 'id';
  $dir = strtolower((string)($_GET['dir'] ?? 'desc')) === 'asc' ? 'asc' : 'desc';
  $sortDir = strtoupper($dir);
  $orderBy = $sortMap[$sort];
  $listState = gs_job_list_state(15, "{$orderBy} {$sortDir}, `id` DESC");
  $rows = $listState['rows'];

  function gs_admin_sort_link($key, $label){
      global $sort, $dir;
      $nextDir = ($sort === $key && $dir === 'desc') ? 'asc' : 'desc';
      $suffix = $sort === $key ? ($dir === 'desc' ? ' ▼' : ' ▲') : '';
      $params = ['sort'=>$key, 'dir'=>$nextDir];
      $q = trim((string)($_GET['q'] ?? ''));
      if($q !== '') $params['q'] = $q;
      $url = 'admin.php?' . http_build_query($params);
      return '<a href="' . htmlspecialchars($url, ENT_QUOTES) . '">' . htmlspecialchars($label . $suffix, ENT_QUOTES) . '</a>';
  }

  function gs_admin_status_text($status){
      switch((string)$status){
          case '0': return '等待';
          case '1': return '執行中';
          case '2': return '完成';
          case '3': return '失敗';
          case '4': return '中止';
          case '5': return '等待覆核';
      }
      return '未知';
  }

  function gs_admin_status_class($status){
      switch((string)$status){
          case '0': return 'queued';
          case '1': return 'running';
          case '2': return 'done';
          case '3': return 'failed';
          case '4': return 'aborted';
          case '5': return 'review';
      }
      return 'unknown';
  }

  function gs_admin_format_duration($seconds){
      if(!is_numeric($seconds)) return '-';
      $seconds = max(0, (int)round((float)$seconds));
      $hours = intdiv($seconds, 3600);
      $minutes = intdiv($seconds % 3600, 60);
      $remainSeconds = $seconds % 60;
      if($hours > 0) return "{$hours} 小時 {$minutes} 分";
      if($minutes > 0) return "{$minutes} 分 {$remainSeconds} 秒";
      return "{$remainSeconds} 秒";
  }

  function gs_admin_short_failure_reason($reason){
      $reason = trim((string)$reason);
      if($reason === '') return '';

      if(strpos($reason, '影片太短') !== false){
          if(preg_match('/影片太短[^。]*。/u', $reason, $m)) return $m[0];
          return '影片太短。';
      }
      if(strpos($reason, 'candidate frame count is lower than 8') !== false || strpos($reason, 'selected frame count is lower than 8') !== false){
          return '可用影格不足，影片可能太短。';
      }
      if(strpos($reason, 'input file missing') !== false){
          return '找不到上傳影片。';
      }
      if(stripos($reason, 'failed') !== false || stripos($reason, 'error') !== false){
          return '轉檔失敗，請查看詳細紀錄。';
      }

      $lines = preg_split('/\R/u', $reason);
      $shortReason = trim((string)($lines[0] ?? $reason));
      if(function_exists('mb_strlen') && mb_strlen($shortReason, 'UTF-8') > 80){
          return mb_substr($shortReason, 0, 80, 'UTF-8') . '...';
      }
      return strlen($shortReason) > 160 ? substr($shortReason, 0, 160) . '...' : $shortReason;
  }

  function gs_admin_confidence_summary($row){
      $gate = [];
      $raw = trim((string)($row['confidence_gate_json'] ?? ''));
      if($raw !== ''){
          $decoded = json_decode($raw, true);
          if(is_array($decoded)) $gate = $decoded;
      }
      if(!$gate && trim((string)($row['confidence_decision'] ?? '')) === '' && !is_numeric($row['confidence_score'] ?? null)){
          return [];
      }

      $score = is_numeric($row['confidence_score'] ?? null) ? number_format((float)$row['confidence_score'], 2, '.', '') : '-';
      $grade = trim((string)($row['confidence_grade'] ?? ($gate['grade'] ?? '')));
      $decision = trim((string)($row['confidence_decision'] ?? ($gate['decision'] ?? '')));
      $effective = trim((string)($row['confidence_effective_decision'] ?? ($gate['effectiveDecision'] ?? '')));
      $lines = ['信心 ' . $score . ($grade !== '' ? " / {$grade}" : '')];
      if($decision !== '') $lines[] = '決策 ' . $decision . ($effective !== '' && $effective !== $decision ? " → {$effective}" : '');
      $reason = trim((string)($gate['reason'] ?? ''));
      if($reason !== '') $lines[] = $reason;
      $recommendations = $gate['recommendations'] ?? [];
      if(is_array($recommendations)){
          foreach($recommendations as $item){
              $item = trim((string)$item);
              if($item !== '') $lines[] = '建議 ' . $item;
              if(count($lines) >= 4) break;
          }
      }
      return $lines;
  }

  function gs_admin_confidence_summary_from_row($row){
      return gs_confidence_summary_from_row($row);
  }

  function gs_admin_confidence_cell_html($row){
      $summary = gs_admin_confidence_summary_from_row($row);
      if(!$summary) return '<span class="gs-admin-file">-</span>';
      $score = is_numeric($summary['score'] ?? null) ? number_format((float)$summary['score'], 2, '.', '') : '-';
      $grade = trim((string)($summary['grade'] ?? ''));
      $decision = trim((string)($summary['decision'] ?? ''));
      $overrideStatus = trim((string)($summary['overrideStatus'] ?? ''));
      $riskCount = (int)($summary['riskCount'] ?? 0);
      $recommendationCount = (int)($summary['recommendationCount'] ?? 0);
      $needsReview = !empty($summary['needsOverride']) ? '等待覆核' : '免覆核';
      $decisionLabelMap = [
          'run'=>'建議執行',
          'warn'=>'可執行有風險',
          'hold'=>'等待覆核',
          'reject'=>'不建議重建',
      ];
      $overrideLabelMap = [
          'none'=>'未覆核',
          'waiting'=>'等待覆核',
          'overridden'=>'已覆核',
          'blocked'=>'已阻擋',
      ];
      $decisionLabel = $decisionLabelMap[$decision] ?? ($decision !== '' ? $decision : '-');
      $overrideLabel = $overrideLabelMap[$overrideStatus] ?? $overrideStatus;
      ob_start();
      ?>
        <div class="gs-admin-confidence-main"><?=htmlspecialchars($score . ($grade !== '' ? " / {$grade}" : ''), ENT_QUOTES);?></div>
        <div class="gs-admin-confidence-sub"><?=htmlspecialchars($decisionLabel, ENT_QUOTES);?> · <?=htmlspecialchars($needsReview, ENT_QUOTES);?></div>
        <div class="gs-admin-confidence-sub">風險 <?=htmlspecialchars((string)$riskCount, ENT_QUOTES);?> / 建議 <?=htmlspecialchars((string)$recommendationCount, ENT_QUOTES);?></div>
        <?php if($overrideStatus !== ''): ?>
          <div class="gs-admin-confidence-sub"><?=htmlspecialchars($overrideLabel, ENT_QUOTES);?></div>
        <?php endif; ?>
      <?php
      return trim(ob_get_clean());
  }

  function gs_admin_timing_rows($path){
      if(!is_file($path)) return [];
      $data = json_decode(@file_get_contents($path), true);
      if(!is_array($data)) return [];
      $rows = [];
      foreach(($data['stages'] ?? []) as $stage){
          if(!is_array($stage)) continue;
          $rows[] = [
              'label' => (string)($stage['label'] ?? $stage['key'] ?? ''),
              'status' => (string)($stage['status'] ?? ''),
              'duration' => $stage['duration_seconds'] ?? null,
          ];
      }
      return $rows;
  }

  require "{$base_dir}/html.php";
  require "{$base_dir}/head.php";
?>
<script src="js/function.js"></script>
<title>Gaussian Splat 轉檔後台</title>
<?php
  require "{$base_dir}/head_end.php";
  require "{$base_dir}/body.php";
  require "{$base_dir}/top.php";
?>
<style nonce="gg">
  html, html body{background:#0f1722;color:#e5edf7;}
  .gs-admin{--panel:#111b2a;--panel-2:#162235;--line:#334155;--muted:#9fb0c3;--text:#e5edf7;--title:#f8fafc;--accent:#38bdf8;--warn:#facc15;max-width:1440px;margin:0 auto;padding:22px 20px 42px;}
  .gs-admin-header{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:14px;}
  .gs-admin h2{margin:0;color:#f8fafc;font-size:28px;font-weight:700;letter-spacing:0;}
  .gs-admin-back-btn{background:#1d2a3a;border-color:#3b4a5f;color:#e5edf7;}
  .gs-admin-back-btn:hover,.gs-admin-back-btn:focus{background:#26364a;border-color:#5a718b;color:#fff;}
  .gs-admin-toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:0 0 12px;color:var(--muted);font-size:13px;}
  .gs-admin-sortbar a{color:#bfdbfe;text-decoration:underline;margin-left:8px;}
  .gs-list-tools{display:grid;grid-template-columns:auto minmax(240px,1fr) auto auto auto;gap:10px;align-items:center;margin:0 0 14px;padding:12px;border:1px solid var(--line);border-radius:6px;background:var(--panel);}
  .gs-list-tools label{margin:0;color:#dbe7f3;font-weight:700;}
  .gs-list-tools .form-control{background:#0f1722;color:#f8fafc;border-color:#3b4a5f;box-shadow:none;}
  .gs-list-count{color:var(--muted);font-size:12px;white-space:nowrap;}
  .gs-pagination{display:flex;justify-content:center;align-items:center;gap:10px;margin-top:14px;color:#cbd5e1;}
  .gs-pagination .disabled{pointer-events:none;opacity:.45;}
  .gs-admin-list{display:grid;gap:12px;}
  .gs-admin-job{border:1px solid var(--line);border-radius:6px;background:var(--panel);overflow:hidden;}
  .gs-admin-job-head{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:16px;padding:14px 16px;background:#17243a;border-bottom:1px solid #26364a;}
  .gs-admin-title-row{display:flex;align-items:center;gap:10px;min-width:0;}
  .gs-admin-id{flex:0 0 auto;color:#bfdbfe;font-weight:700;font-variant-numeric:tabular-nums;}
  .gs-admin-title{margin:0;color:var(--title);font-size:19px;line-height:1.35;font-weight:700;overflow-wrap:anywhere;}
  .gs-admin-mode{flex:0 0 auto;border:1px solid #3b4a5f;border-radius:999px;padding:2px 8px;color:#dbe7f3;font-size:12px;background:#0f172a;}
  .gs-admin-file{margin-top:4px;font-size:12px;color:#9fb0c3;line-height:1.35;word-break:break-word;}
  .gs-admin-head-side{display:flex;align-items:flex-start;gap:12px;}
  .gs-admin-status{display:inline-block;border-radius:999px;padding:4px 10px;font-size:13px;font-weight:700;white-space:nowrap;}
  .gs-admin-status-queued{background:#334155;color:#e2e8f0;}
  .gs-admin-status-running{background:#075985;color:#bae6fd;}
  .gs-admin-status-done{background:#14532d;color:#bbf7d0;}
  .gs-admin-status-failed{background:#7f1d1d;color:#fecaca;}
  .gs-admin-status-aborted{background:#713f12;color:#fde68a;}
  .gs-admin-status-review{background:#7c2d12;color:#fed7aa;}
  .gs-admin-status-unknown{background:#334155;color:#e2e8f0;}
  .gs-admin-actions{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:6px;max-width:360px;}
  .gs-admin-actions .btn{margin:0;}
  .gs-admin-job-body{display:grid;grid-template-columns:minmax(190px,.85fr) minmax(190px,.85fr) minmax(220px,1fr) minmax(280px,1.35fr);gap:18px;padding:14px 16px;}
  .gs-admin-section{min-width:0;}
  .gs-admin-section-title{margin-bottom:7px;color:#cbd5e1;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;}
  .gs-admin-reason{font-size:13px;line-height:1.45;color:#ffb4b4;overflow-wrap:anywhere;}
  .gs-admin-progress{height:8px;border-radius:999px;background:#0b1220;border:1px solid #334155;overflow:hidden;margin-top:8px;max-width:360px;}
  .gs-admin-progress span{display:block;height:100%;background:#14b8a6;}
  .gs-admin-progress-meta{margin-top:6px;font-size:12px;color:#cbd5e1;font-variant-numeric:tabular-nums;}
  .gs-admin-empty{padding:28px;text-align:center;color:var(--muted);border:1px solid var(--line);border-radius:6px;background:var(--panel);}
  .gs-admin-confidence{margin-top:6px;font-size:12px;line-height:1.45;color:#facc15;max-width:320px;}
  .gs-admin-confidence-cell{font-size:12px;line-height:1.45;color:#dbe7f3;}
  .gs-admin-confidence-main{font-size:15px;font-weight:700;color:#f8fafc;}
  .gs-admin-confidence-sub{color:#9fb0c3;}
  .gs-admin-metrics{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px 14px;}
  .gs-admin-metric-label{display:block;color:var(--muted);font-size:12px;}
  .gs-admin-metric-value{display:block;color:var(--title);font-size:15px;font-variant-numeric:tabular-nums;overflow-wrap:anywhere;}
  .gs-admin-duration{line-height:1.7;font-variant-numeric:tabular-nums;}
  .gs-admin-duration-current{font-size:12px;color:#9fb0c3;white-space:normal;line-height:1.45;}
  .gs-admin-stage-head{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:7px;}
  .gs-admin-stage-head a{color:#dbeafe;font-size:12px;font-weight:700;text-decoration:underline;white-space:nowrap;}
  .gs-admin-stage-list{font-size:12px;color:#9fb0c3;line-height:1.45;max-height:126px;overflow:auto;padding-right:6px;}
  .gs-admin-stage-row{display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:8px;padding:2px 0;}
  .gs-admin-stage-name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
  .gs-admin-frame,.gs-admin-size{font-variant-numeric:tabular-nums;white-space:nowrap;}
  .gs-admin-links{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px;}
  .gs-admin-qa-link{min-width:44px;}
  @media (max-width: 1120px){
    .gs-admin-job-body{grid-template-columns:repeat(2,minmax(0,1fr));}
  }
  @media (max-width: 760px){
    .gs-admin{padding:18px 12px 32px;}
    .gs-admin-header,.gs-admin-toolbar,.gs-admin-job-head{display:block;}
    .gs-list-tools{grid-template-columns:1fr;}
    .gs-admin h2{font-size:24px;}
    .gs-admin-back-btn{margin-top:10px;}
    .gs-admin-sortbar{margin-top:8px;}
    .gs-admin-head-side{display:block;margin-top:10px;}
    .gs-admin-actions{justify-content:flex-start;margin-top:10px;max-width:none;}
    .gs-admin-job-body{grid-template-columns:1fr;}
  }
  .gs-log-dialog[hidden]{display:none;}
  .gs-log-dialog{position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,.64);display:flex;align-items:center;justify-content:center;padding:20px;}
  .gs-log-dialog-panel{width:min(980px,calc(100vw - 32px));max-height:calc(100vh - 48px);display:flex;flex-direction:column;border:1px solid #2dd36f;border-radius:8px;background:#07110b;box-shadow:0 24px 70px rgba(0,0,0,.55);overflow:hidden;}
  .gs-log-dialog-head{flex:0 0 auto;display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 14px;background:#0b1c10;color:#d7ffe1;border-bottom:1px solid rgba(45,211,111,.45);}
  .gs-log-dialog-head h3{margin:0;font-size:18px;line-height:1.3;}
  .gs-reconvert-body{padding:16px;background:#08131f;color:#e5edf7;}
  .gs-reconvert-row{display:grid;grid-template-columns:92px minmax(0,1fr);gap:10px;margin-bottom:10px;font-size:14px;}
  .gs-reconvert-row span:first-child{color:#9fb0c3;}
  .gs-reconvert-mode{width:100%;max-width:280px;background:#0f172a;color:#f8fafc;border:1px solid #334155;border-radius:4px;padding:7px 9px;}
  .gs-reconvert-options{display:grid;gap:6px;}
  .gs-reconvert-options label{margin:0;font-weight:400;color:#e5edf7;}
  .gs-reconvert-options input{margin-right:6px;}
  .gs-reconvert-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:16px;}
  .gs-reconvert-status{margin-top:8px;color:#facc15;font-size:13px;}
  .gs-confidence-panel{flex:0 0 auto;padding:14px 16px;border-bottom:1px solid rgba(45,211,111,.28);background:#08131f;color:#e5edf7;}
  .gs-confidence-top{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:10px;}
  .gs-confidence-title{font-size:16px;font-weight:700;color:#f8fafc;}
  .gs-confidence-score{font-size:12px;color:#9fb0c3;margin-top:3px;}
  .gs-confidence-badge{display:inline-block;border-radius:999px;padding:4px 9px;font-size:12px;font-weight:700;white-space:nowrap;}
  .gs-confidence-badge-run{background:#14532d;color:#bbf7d0;}
  .gs-confidence-badge-warn{background:#713f12;color:#fde68a;}
  .gs-confidence-badge-hold{background:#7c2d12;color:#fed7aa;}
  .gs-confidence-badge-reject{background:#7f1d1d;color:#fecaca;}
  .gs-confidence-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;}
  .gs-confidence-section h4{margin:0 0 6px;font-size:12px;color:#cbd5e1;text-transform:uppercase;}
  .gs-confidence-chip{display:inline-block;margin:0 5px 5px 0;padding:3px 7px;border:1px solid #334155;border-radius:999px;background:#0f172a;color:#dbe7f3;font-size:12px;}
  .gs-confidence-list{margin:0;padding-left:18px;font-size:13px;line-height:1.5;}
  .gs-confidence-muted{font-size:13px;color:#9fb0c3;}
  .gs-confidence-debug{margin-top:10px;font-size:12px;}
  .gs-confidence-debug a{color:#93c5fd;text-decoration:underline;margin-right:10px;}
  .gs-confidence-override{margin-top:8px;font-size:13px;color:#facc15;}
  .gs-confidence-override .btn{margin-left:8px;}
  .gs-log-terminal{flex:1 1 auto;min-height:0;max-height:none;overflow:auto;margin:0;padding:16px;background:#020617;color:#3cff71;font-family:Consolas,Monaco,"Courier New",monospace;font-size:14px;line-height:1.55;white-space:pre-wrap;word-break:break-word;}
  @media (max-width: 760px){
    .gs-confidence-top{display:block;}
    .gs-confidence-badge{margin-top:8px;}
    .gs-confidence-grid{grid-template-columns:1fr;}
  }
</style>

<div class="gs-admin">
  <div class="gs-admin-header">
    <h2>Gaussian Splat 轉檔後台</h2>
    <a class="btn btn-default gs-admin-back-btn" href="index.php">回前台</a>
  </div>
  <div class="gs-admin-toolbar">
    <div>工作列表</div>
    <div class="gs-admin-sortbar">
      排序：
      <?=gs_admin_sort_link('id', '編號');?>
      <?=gs_admin_sort_link('score', '信心');?>
      <?=gs_admin_sort_link('grade', '等級');?>
      <?=gs_admin_sort_link('decision', '決策');?>
      <?=gs_admin_sort_link('review', '覆核');?>
      <?=gs_admin_sort_link('override', '覆核狀態');?>
    </div>
  </div>
  <?=gs_job_search_form_html($listState, ['sort'=>$sort, 'dir'=>$dir]);?>
  <div class="gs-admin-list">
      <?php foreach($rows as $r):
          $id = (int)$r['id'];
          $qa = "uploads/{$id}/qa_report.json";
          $timing = "uploads/{$id}/timing_report.json";
          $cleanSplat = "uploads/{$id}/exports/splat.clean.ply";
          $rawSplat = "uploads/{$id}/exports/splat.ply";
          $splat = is_file(__DIR__ . "/{$cleanSplat}") ? $cleanSplat : $rawSplat;
          $isReady = (string)$r['status'] === '2';
          $isRunning = (string)$r['status'] === '1';
          $isHeld = (string)$r['status'] === '5';
          $currentMode = $r['pipeline_mode'] ?? 'fast';
          $currentModeJs = htmlspecialchars(json_encode($currentMode, JSON_UNESCAPED_UNICODE), ENT_QUOTES);
          $sourceFileJs = htmlspecialchars(json_encode($r['orin_filename'] ?? '', JSON_UNESCAPED_UNICODE), ENT_QUOTES);
          $canReconvert = in_array((string)$r['status'], ['2','3','4','5'], true);
          $canAbort = in_array((string)$r['status'], ['0','1'], true);
          $hasSplat = $isReady && is_file(__DIR__ . "/{$splat}");
          $timingRows = gs_admin_timing_rows(__DIR__ . "/{$timing}");
          $shortReason = gs_admin_short_failure_reason($r['reason'] ?? '');
          $confidenceCellHtml = gs_admin_confidence_cell_html($r);
          $statusClass = gs_admin_status_class($r['status']);
          $progress = gs_job_progress($r);
          $progressLabel = (string)($progress['label'] ?? ($r['current_stage_label'] ?: gs_admin_status_text($r['status'])));
      ?>
        <article class="gs-admin-job gs-admin-job-<?=$statusClass;?>">
          <header class="gs-admin-job-head">
            <div>
              <div class="gs-admin-title-row">
                <span class="gs-admin-id">#<?=$id;?></span>
                <h3 class="gs-admin-title"><?=htmlspecialchars($r['title'] ?: $r['orin_filename'], ENT_QUOTES);?></h3>
                <span class="gs-admin-mode"><?=htmlspecialchars(gs_pipeline_mode_label($currentMode), ENT_QUOTES);?></span>
              </div>
              <div class="gs-admin-file"><?=htmlspecialchars($r['orin_filename'] ?? '', ENT_QUOTES);?></div>
            </div>
            <div class="gs-admin-head-side">
              <span class="gs-admin-status gs-admin-status-<?=$statusClass;?>"><?=htmlspecialchars(gs_admin_status_text($r['status']), ENT_QUOTES);?></span>
              <div class="gs-admin-actions">
                <?php if($canReconvert): ?>
                  <button class="btn btn-xs btn-warning" type="button" onclick="openReconvertDialog(<?=$id;?>,<?=$currentModeJs;?>,<?=$sourceFileJs;?>)">重轉</button>
                <?php endif; ?>
                <?php if($isHeld): ?>
                  <button class="btn btn-xs btn-primary" type="button" onclick="confirmConfidenceOverride(<?=$id;?>)">覆核啟動</button>
                <?php endif; ?>
                <?php if($canAbort): ?>
                  <button class="btn btn-xs btn-danger" type="button" onclick="confirmAdminAction(<?=$id;?>,'abort','中止')">中止</button>
                <?php endif; ?>
                <button class="btn btn-xs btn-default" type="button" onclick="openJobDetail(<?=$id;?>)">詳細</button>
                <?php if($hasSplat): ?>
                  <button class="btn btn-xs btn-success" type="button" onclick="openSplatViewer(<?=$id;?>)">檢視</button>
                <?php endif; ?>
              </div>
            </div>
          </header>

          <div class="gs-admin-job-body">
            <section class="gs-admin-section">
              <div class="gs-admin-section-title">狀態</div>
              <?php if($shortReason !== ''): ?>
                <div class="gs-admin-reason"><?=htmlspecialchars($shortReason, ENT_QUOTES);?></div>
              <?php else: ?>
                <div class="gs-admin-file">目前：<?=htmlspecialchars($progressLabel, ENT_QUOTES);?></div>
                <?php if($progress['active']): ?>
                  <div class="gs-admin-progress-meta"><?=htmlspecialchars((string)($progress['percent'] ?? 0), ENT_QUOTES);?>% · <?=htmlspecialchars((string)($progress['step'] ?? ''), ENT_QUOTES);?></div>
                  <div class="gs-admin-progress"><span style="width:<?=min(100, max(0, (int)$progress['percent']));?>%;"></span></div>
                <?php endif; ?>
              <?php endif; ?>
            </section>

            <section class="gs-admin-section gs-admin-confidence-cell">
              <div class="gs-admin-section-title">信心</div>
              <?= $confidenceCellHtml; ?>
            </section>

            <section class="gs-admin-section">
              <div class="gs-admin-section-title">耗時與輸出</div>
              <div class="gs-admin-metrics">
                <div><span class="gs-admin-metric-label">排隊</span><span class="gs-admin-metric-value"><?=htmlspecialchars(gs_admin_format_duration($r['queue_seconds'] ?? null), ENT_QUOTES);?></span></div>
                <div><span class="gs-admin-metric-label">轉檔</span><span class="gs-admin-metric-value"><?=htmlspecialchars(gs_admin_format_duration($r['process_seconds'] ?? null), ENT_QUOTES);?></span></div>
                <div><span class="gs-admin-metric-label">總計</span><span class="gs-admin-metric-value"><?=htmlspecialchars(gs_admin_format_duration($r['duration_seconds'] ?? null), ENT_QUOTES);?></span></div>
                <div><span class="gs-admin-metric-label">影格</span><span class="gs-admin-metric-value"><?=htmlspecialchars((string)($r['frame_count'] ?? ''), ENT_QUOTES);?> / <?=htmlspecialchars((string)($r['registered_frame_count'] ?? ''), ENT_QUOTES);?></span></div>
                <div><span class="gs-admin-metric-label">Splat MB</span><span class="gs-admin-metric-value"><?=htmlspecialchars((string)($r['splat_file_size_mb'] ?: '-'), ENT_QUOTES);?></span></div>
              </div>
              <div class="gs-admin-links">
                <?php if(is_file(__DIR__ . "/{$qa}")): ?><a class="btn btn-xs btn-info gs-admin-qa-link" href="<?=$qa;?>" target="_blank">品管</a><?php endif; ?>
              </div>
            </section>

            <section class="gs-admin-section">
              <div class="gs-admin-stage-head">
                <div class="gs-admin-section-title">階段明細</div>
                <?php if(is_file(__DIR__ . "/{$timing}")): ?>
                  <a href="<?=$timing;?>" target="_blank">timing_report.json</a>
                <?php endif; ?>
              </div>
              <div class="gs-admin-stage-list">
                <?php foreach($timingRows as $stage): ?>
                  <div class="gs-admin-stage-row">
                    <span class="gs-admin-stage-name"><?=htmlspecialchars($stage['label'], ENT_QUOTES);?></span>
                    <span><?=htmlspecialchars($stage['status'], ENT_QUOTES);?></span>
                    <span><?=htmlspecialchars(gs_admin_format_duration($stage['duration']), ENT_QUOTES);?></span>
                  </div>
                <?php endforeach; ?>
                <?php if(!$timingRows): ?>
                  <div class="gs-admin-file">尚未產生 timing report。</div>
                <?php endif; ?>
              </div>
            </section>
          </div>
        </article>
      <?php endforeach; ?>
    <?php if(empty($rows)): ?>
      <div class="gs-admin-empty">目前沒有工作。</div>
    <?php endif; ?>
  </div>
  <?=gs_job_pagination_html($listState, ['sort'=>$sort, 'dir'=>$dir]);?>
</div>

<div id="jobLogDialog" class="gs-log-dialog" hidden>
  <div class="gs-log-dialog-panel" role="dialog" aria-modal="true" aria-labelledby="jobLogDialogTitle">
    <div class="gs-log-dialog-head">
      <h3 id="jobLogDialogTitle">詳細紀錄</h3>
      <button class="btn btn-xs btn-default" type="button" onclick="closeJobDetail()">關閉</button>
    </div>
    <div id="confidencePreviewPanel" class="gs-confidence-panel" hidden></div>
    <div id="artifactPreviewPanel" class="gs-confidence-panel" hidden></div>
    <pre id="jobLogDialogBody" class="gs-log-terminal"></pre>
  </div>
</div>

<div id="reconvertDialog" class="gs-log-dialog" hidden>
  <div class="gs-log-dialog-panel" role="dialog" aria-modal="true" aria-labelledby="reconvertDialogTitle">
    <div class="gs-log-dialog-head">
      <h3 id="reconvertDialogTitle">重轉設定</h3>
      <button class="btn btn-xs btn-default" type="button" onclick="closeReconvertDialog()">關閉</button>
    </div>
    <div class="gs-reconvert-body">
      <div class="gs-reconvert-row"><span>來源影片</span><strong id="reconvertSourceFile">input.mp4</strong></div>
      <div class="gs-reconvert-row"><span>目前模式</span><strong id="reconvertCurrentMode">快速</strong></div>
      <div class="gs-reconvert-row">
        <span>重轉方式</span>
        <div class="gs-reconvert-options">
          <label><input type="radio" name="reconvertTarget" value="same">同編號重轉（覆蓋舊結果）</label>
          <label><input type="radio" name="reconvertTarget" value="new" checked>新建編號重轉（保留舊結果）</label>
        </div>
      </div>
      <div class="gs-reconvert-row">
        <span>轉檔模式</span>
        <select id="reconvertMode" class="gs-reconvert-mode">
          <option value="fast">快速</option>
          <option value="qa">標準</option>
          <option value="premium">精緻</option>
        </select>
      </div>
      <div class="gs-reconvert-status" id="reconvertStatus"></div>
      <div class="gs-reconvert-actions">
        <button class="btn btn-default" type="button" onclick="closeReconvertDialog()">取消</button>
        <button class="btn btn-warning" type="button" id="reconvertStartButton" onclick="submitReconvert()">開始重轉</button>
      </div>
    </div>
  </div>
</div>

<script nonce="gg">
document.title = "Gaussian Splat 轉檔後台";
var JOB_LOG_REFRESH_MS = 2000;
var jobLogRefreshTimer = null;
var activeJobLogId = null;
var reconvertJobId = null;
var reconvertModeLabels = { fast: "快速", qa: "標準", premium: "精緻" };

function confirmAdminAction(id, action, label) {
  if(!confirm("確定要" + label + "工作 #" + id + "？")) return;
  jobAction(id, action);
}

function setReconvertBusy(isBusy) {
  $("#reconvertStartButton").prop("disabled", isBusy).text(isBusy ? "送出中..." : "開始重轉");
}

function openReconvertDialog(id, currentMode, sourceFile) {
  currentMode = /^(fast|qa|premium)$/.test(String(currentMode || "")) ? currentMode : "fast";
  reconvertJobId = id;
  $("#reconvertSourceFile").text(sourceFile || "input.mp4");
  $("#reconvertCurrentMode").text(reconvertModeLabels[currentMode] || currentMode);
  $("#reconvertMode").val(currentMode);
  $("input[name='reconvertTarget'][value='new']").prop("checked", true);
  $("#reconvertStatus").text("");
  setReconvertBusy(false);
  $("#reconvertDialog").removeAttr("hidden");
}

function closeReconvertDialog() {
  reconvertJobId = null;
  $("#reconvertDialog").attr("hidden", "hidden");
}

function submitReconvert() {
  if (!reconvertJobId) return;
  var mode = String($("#reconvertMode").val() || "fast").trim().toLowerCase();
  if (!/^(fast|qa|premium)$/.test(mode)) {
    alert("重轉模式只允許 fast、qa、premium");
    return;
  }
  var target = String($("input[name='reconvertTarget']:checked").val() || "new");
  if (!/^(same|new)$/.test(target)) target = "new";
  $("#reconvertStatus").text(target === "same" ? "正在重排這個編號..." : "正在建立新編號...");
  setReconvertBusy(true);
  jobAction(reconvertJobId, "reconvert", null, mode, target);
}

function confirmConfidenceOverride(id) {
  var reason = prompt("請輸入覆核啟動原因", "");
  if (reason === null) return;
  jobAction(id, "confidence_override", reason);
}

function jobAction(id, action, reason, mode, target) {
  var payload = { id: id, action: action };
  if (typeof reason !== "undefined") {
    payload.confidence_override_reason = reason;
  }
  if (typeof mode !== "undefined" && mode !== null) {
    payload.pipeline_mode = mode;
  }
  if (typeof target !== "undefined" && target !== null) {
    payload.reconvert_target = target;
  }
  $.post("api.php?mode=admin_action", payload, function(jd) {
    if (jd.status === "OK") {
      if (action === "reconvert" && jd.id) {
        location.href = "admin.php";
        return;
      }
      location.reload();
    } else {
      if (action === "reconvert") setReconvertBusy(false);
      alert(jd.reason || "操作失敗");
    }
  }, "json").fail(function() {
    if (action === "reconvert") setReconvertBusy(false);
    alert("操作失敗");
  });
}

function escapeHtml(value) {
  return String(value == null ? "" : value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function confidenceBadgeInfo(gate) {
  var effective = String(gate.effectiveDecision || gate.decision || "").toLowerCase();
  var decision = String(gate.decision || "").toLowerCase();
  if (effective === "reject" || decision === "reject") {
    return { label: "不建議重建", className: "gs-confidence-badge-reject" };
  }
  if (effective === "run_with_override") {
    return { label: "覆核後執行", className: "gs-confidence-badge-hold" };
  }
  if (effective === "hold" || decision === "hold") {
    return { label: "等待覆核", className: "gs-confidence-badge-hold" };
  }
  if (effective === "warn" || decision === "warn") {
    return { label: "可執行但有風險", className: "gs-confidence-badge-warn" };
  }
  return { label: "建議執行", className: "gs-confidence-badge-run" };
}

function confidenceRiskHtml(risks) {
  risks = risks || {};
  var keys = Object.keys(risks);
  if (!keys.length) return '<div class="gs-confidence-muted">目前沒有風險資料。</div>';
  return keys.map(function(key) {
    return '<span class="gs-confidence-chip">' + escapeHtml(key) + ': ' + escapeHtml(risks[key]) + '</span>';
  }).join("");
}

function confidenceRecommendationHtml(items) {
  if (!$.isArray(items) || !items.length) {
    return '<div class="gs-confidence-muted">目前沒有補拍建議。</div>';
  }
  return '<ul class="gs-confidence-list">' + items.map(function(item) {
    return '<li>' + escapeHtml(item) + '</li>';
  }).join("") + '</ul>';
}

function renderConfidencePreview(jd) {
  var panel = $("#confidencePreviewPanel");
  var gate = jd && jd.confidence_gate ? jd.confidence_gate : null;
  if (!gate) {
    panel.attr("hidden", "hidden").empty();
    return;
  }

  var badge = confidenceBadgeInfo(gate);
  var score = $.isNumeric(gate.score) ? Number(gate.score).toFixed(2) : "-";
  var grade = gate.grade ? " / " + gate.grade : "";
  var decision = gate.decision || "-";
  var effective = gate.effectiveDecision && gate.effectiveDecision !== decision ? " → " + gate.effectiveDecision : "";
  var override = gate.override || {};
  var overrideText = override.enabled ? "已覆核：" + (override.reason || "未填寫原因") : "尚未覆核";
  var overrideButton = String(jd.job_status || "") === "5"
    ? ' <button class="btn btn-xs btn-primary" type="button" onclick="confirmConfidenceOverride(activeJobLogId)">覆核啟動</button>'
    : "";
  var debugLinks = [];
  if (jd.confidence_report_url) {
    debugLinks.push('<a href="' + encodeURI(jd.confidence_report_url) + '" target="_blank">confidence_report.json</a>');
  }
  if (jd.confidence_gate_url) {
    debugLinks.push('<a href="' + encodeURI(jd.confidence_gate_url) + '" target="_blank">confidence_gate.json</a>');
  }

  panel.html(
    '<div class="gs-confidence-top">' +
      '<div>' +
        '<div class="gs-confidence-title">Confidence Preview</div>' +
        '<div class="gs-confidence-score">Score / Grade：' + escapeHtml(score + grade) + ' · Decision：' + escapeHtml(decision + effective) + '</div>' +
      '</div>' +
      '<span class="gs-confidence-badge ' + badge.className + '">' + escapeHtml(badge.label) + '</span>' +
    '</div>' +
    '<div class="gs-confidence-grid">' +
      '<div class="gs-confidence-section"><h4>Risks</h4>' + confidenceRiskHtml(gate.risks) + '</div>' +
      '<div class="gs-confidence-section"><h4>Recommendations</h4>' + confidenceRecommendationHtml(gate.recommendations) + '</div>' +
    '</div>' +
    '<div class="gs-confidence-override">' + escapeHtml(overrideText) + overrideButton + '</div>' +
    '<div class="gs-confidence-debug">' + (debugLinks.length ? debugLinks.join("") : '<span class="gs-confidence-muted">尚未產生 debug JSON。</span>') + '</div>'
  ).removeAttr("hidden");
}

function renderArtifactPreview(jd) {
  var panel = $("#artifactPreviewPanel");
  var links = jd && $.isArray(jd.artifact_links) ? jd.artifact_links : [];
  if (!links.length) {
    panel.attr("hidden", "hidden").empty();
    return;
  }
  var grouped = {};
  links.forEach(function(link) {
    var group = link.group || "Artifacts";
    if (!grouped[group]) grouped[group] = [];
    grouped[group].push(link);
  });
  var sections = Object.keys(grouped).map(function(group) {
    var anchors = grouped[group].map(function(link) {
      return '<a href="' + encodeURI(link.path || "") + '" target="_blank">' + escapeHtml(link.label || link.path || "") + '</a>';
    }).join("");
    return '<div class="gs-confidence-section"><h4>' + escapeHtml(group) + '</h4><div class="gs-confidence-debug">' + anchors + '</div></div>';
  }).join("");
  panel.html(
    '<div class="gs-confidence-top">' +
      '<div>' +
        '<div class="gs-confidence-title">Project Detail</div>' +
        '<div class="gs-confidence-score">Pipeline / Engine Runs / Artifacts / Validation / Delivery</div>' +
      '</div>' +
    '</div>' +
    '<div class="gs-confidence-grid">' + sections + '</div>'
  ).removeAttr("hidden");
}

function stopJobLogRefresh() {
  if (jobLogRefreshTimer) {
    clearInterval(jobLogRefreshTimer);
    jobLogRefreshTimer = null;
  }
}

function isJobLogPinnedToBottom() {
  var body = document.getElementById("jobLogDialogBody");
  if (!body) return true;
  return body.scrollHeight - body.scrollTop - body.clientHeight < 48;
}

function renderJobLog(jd) {
  var body = document.getElementById("jobLogDialogBody");
  if (!body) return;
  renderConfidencePreview(jd);
  renderArtifactPreview(jd);
  var keepAtBottom = isJobLogPinnedToBottom();
  var parts = [];
  parts.push("模式：" + (jd.pipeline_mode_label || "快速"));
  if (jd.reason) {
    parts.push("異常原因:\n" + jd.reason);
  }
  if (jd.log) {
    parts.push("完整紀錄:\n" + jd.log);
  }
  body.textContent = parts.join("\n\n") || "沒有紀錄。";
  if (keepAtBottom) {
    body.scrollTop = body.scrollHeight;
  }
}

function refreshJobDetail(id, showLoading) {
  if (showLoading) {
    $("#jobLogDialogBody").text("讀取中...");
    $("#confidencePreviewPanel").attr("hidden", "hidden").empty();
    $("#artifactPreviewPanel").attr("hidden", "hidden").empty();
  }
  $.getJSON("api.php?mode=get_log&id=" + encodeURIComponent(id), function(jd) {
    if (activeJobLogId !== id || $("#jobLogDialog").is("[hidden]")) return;
    if (jd.status !== "OK") {
      renderConfidencePreview({});
      renderArtifactPreview({});
      $("#jobLogDialogBody").text(jd.reason || "讀取失敗");
      return;
    }
    renderJobLog(jd);
  }).fail(function() {
    if (activeJobLogId === id && !$("#jobLogDialog").is("[hidden]")) {
      $("#jobLogDialogBody").text("讀取失敗");
    }
  });
}

function startJobLogRefresh(id) {
  stopJobLogRefresh();
  jobLogRefreshTimer = setInterval(function() {
    refreshJobDetail(id, false);
  }, JOB_LOG_REFRESH_MS);
}

function closeJobDetail() {
  stopJobLogRefresh();
  activeJobLogId = null;
  $("#confidencePreviewPanel").attr("hidden", "hidden").empty();
  $("#artifactPreviewPanel").attr("hidden", "hidden").empty();
  $("#jobLogDialog").attr("hidden", "hidden");
}

function openJobDetail(id) {
  activeJobLogId = id;
  $("#jobLogDialogTitle").text("工作 #" + id + " 詳細紀錄");
  $("#jobLogDialog").removeAttr("hidden");
  refreshJobDetail(id, true);
  startJobLogRefresh(id);
}

$(document).on("keydown", function(event) {
  if (event.key === "Escape") {
    closeReconvertDialog();
    closeJobDetail();
  }
});
</script>
</body></html>
