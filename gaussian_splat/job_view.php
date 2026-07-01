<?php
  if(!defined('GS_DEFAULT_ESTIMATE_SECONDS')){
      define('GS_DEFAULT_ESTIMATE_SECONDS', 1800);
  }
  if(!defined('GS_LIST_PER_PAGE')){
      define('GS_LIST_PER_PAGE', 15);
  }

  if(!function_exists('gs_status_text')){
      function gs_status_text($status){
          switch((string)$status){
              case '0': return '等待轉檔';
              case '1': return '轉檔中';
              case '2': return '已完成';
              case '3': return '失敗';
              case '4': return '已中止';
              case '5': return '等待覆核';
          }
          return '未知';
      }
  }

  if(!function_exists('gs_pipeline_mode_label')){
      function gs_pipeline_mode_label($mode){
          $labels = ['fast'=>'快速', 'qa'=>'驗證', 'premium'=>'進階'];
          $mode = trim((string)$mode);
          return $labels[$mode !== '' ? $mode : 'fast'] ?? $labels['fast'];
      }
  }

  if(!function_exists('gs_format_duration')){
      function gs_format_duration($seconds){
          if(!is_numeric($seconds)) return '尚未開始';
          $seconds = max(0, (int)round((float)$seconds));
          $hours = intdiv($seconds, 3600);
          $minutes = intdiv($seconds % 3600, 60);
          $remainSeconds = $seconds % 60;
          if($hours > 0) return "{$hours} 小時 {$minutes} 分";
          if($minutes > 0) return "{$minutes} 分 {$remainSeconds} 秒";
          return "{$remainSeconds} 秒";
      }
  }

  if(!function_exists('gs_elapsed_seconds')){
      function gs_elapsed_seconds($row){
          if(is_numeric($row['duration_seconds'] ?? null)){
              return (int)$row['duration_seconds'];
          }
          $start = $row['c_datetime'] ?? null;
          if(empty($start)) return null;
          $startTs = strtotime((string)$start);
          if($startTs === false) return null;
          $endTs = time();
          if(in_array((string)($row['status'] ?? ''), ['2','3','4','5'], true) && !empty($row['work_et_datetime'])){
              $endTs = strtotime((string)$row['work_et_datetime']);
          }
          if($endTs === false) return null;
          return max(0, $endTs - $startTs);
      }
  }

  if(!function_exists('gs_average_completed_duration')){
      function gs_average_completed_duration($rows){
          $durations = [];
          foreach($rows as $row){
              if((string)($row['status'] ?? '') === '2' && is_numeric($row['duration_seconds'] ?? null) && (int)$row['duration_seconds'] > 0){
                  $durations[] = (int)$row['duration_seconds'];
              }
          }
          if(!$durations) return GS_DEFAULT_ESTIMATE_SECONDS;
          return (int)round(array_sum($durations) / count($durations));
      }
  }

  if(!function_exists('gs_job_timing_summary')){
      function gs_job_timing_summary($row, $estimateSeconds){
          $elapsed = gs_elapsed_seconds($row);
          $status = (string)($row['status'] ?? '');
          $stage = trim((string)($row['current_stage_label'] ?? ''));
          $summary = [];
          if($status === '2'){
              $summary[] = '總耗時 ' . gs_format_duration($elapsed);
          } else {
              $summary[] = '已花 ' . gs_format_duration($elapsed);
              $summary[] = '粗估總長 ' . gs_format_duration($estimateSeconds);
              if(in_array($status, ['0','1'], true) && is_numeric($elapsed)){
                  $summary[] = '預估剩 ' . gs_format_duration(max(0, (int)$estimateSeconds - (int)$elapsed));
              }
          }
          if($stage !== '') $summary[] = '目前：' . $stage;
          return $summary;
      }
  }

  if(!function_exists('gs_short_failure_reason')){
      function gs_short_failure_reason($reason){
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
          if(strpos($reason, 'Video input requires OpenCV (cv2), which is not installed') !== false){
              return '缺少 OpenCV/cv2，worker 未使用 3DGS conda 環境。';
          }
          if(stripos($reason, 'failed') !== false || stripos($reason, 'error') !== false){
              return '轉檔失敗，請聯絡管理員查看詳細紀錄。';
          }

          $lines = preg_split('/\R/u', $reason);
          $shortReason = trim((string)($lines[0] ?? $reason));
          if(function_exists('mb_strlen') && mb_strlen($shortReason, 'UTF-8') > 80){
              return mb_substr($shortReason, 0, 80, 'UTF-8') . '...';
          }
          return strlen($shortReason) > 160 ? substr($shortReason, 0, 160) . '...' : $shortReason;
      }
  }

  if(!function_exists('gs_json_safe_text')){
      function gs_json_safe_text($value){
          $value = (string)$value;
          if($value === '') return '';
          if(function_exists('mb_convert_encoding')){
              return mb_convert_encoding($value, 'UTF-8', 'UTF-8');
          }
          return preg_replace('/[\x00-\x08\x0B\x0C\x0E-\x1F]/', '', $value);
      }
  }

  if(!function_exists('gs_upload_time_label')){
      function gs_upload_time_label($datetime){
          $datetime = trim((string)$datetime);
          if($datetime === '') return '未記錄';
          if(preg_match('/^0{4}-0{2}-0{2}/', $datetime)) return '未記錄';

          foreach(['Y-m-d H:i:s', 'Y-m-d H:i'] as $format){
              $dt = DateTime::createFromFormat('!' . $format, $datetime);
              $errors = DateTime::getLastErrors();
              $hasErrors = is_array($errors) && ((int)$errors['warning_count'] > 0 || (int)$errors['error_count'] > 0);
              if($dt instanceof DateTime && !$hasErrors && $dt->format($format) === $datetime){
                  return $dt->format('Y-m-d H:i');
              }
          }
          return $datetime;
      }
  }

  if(!function_exists('gs_job_search_status_codes')){
      function gs_job_search_status_codes($q){
          $q = trim((string)$q);
          $map = [
              '等待'=>'0', '待處理'=>'0', 'queue'=>'0',
              '轉檔'=>'1', '執行'=>'1', 'running'=>'1',
              '完成'=>'2', '已完成'=>'2', 'ready'=>'2',
              '失敗'=>'3', 'failed'=>'3',
              '中止'=>'4', '暫停'=>'4', 'abort'=>'4',
              '覆核'=>'5', 'review'=>'5',
          ];
          $codes = [];
          foreach($map as $label => $code){
              if($q !== '' && stripos($label, $q) !== false) $codes[$code] = $code;
          }
          if(in_array($q, ['0','1','2','3','4','5'], true)) $codes[$q] = $q;
          return array_values($codes);
      }
  }

  if(!function_exists('gs_job_search_where')){
      function gs_job_search_where($q, &$params){
          $params = [];
          $where = "`del`='0'";
          $q = trim((string)$q);
          if($q === '') return $where;
          $like = '%' . $q . '%';
          $parts = [
              "`title` LIKE :kw_title",
              "`orin_filename` LIKE :kw_file",
              "`email` LIKE :kw_email",
              "`pipeline_mode` LIKE :kw_mode",
              "CAST(`id` AS CHAR) LIKE :kw_id",
          ];
          $params = [
              'kw_title'=>$like,
              'kw_file'=>$like,
              'kw_email'=>$like,
              'kw_mode'=>$like,
              'kw_id'=>$like,
          ];
          foreach(gs_job_search_status_codes($q) as $i => $code){
              $key = "kw_status_{$i}";
              $parts[] = "`status`=:{$key}";
              $params[$key] = $code;
          }
          return $where . " AND (" . implode(" OR ", $parts) . ")";
      }
  }

  if(!function_exists('gs_job_search_suggestions')){
      function gs_job_search_suggestions(){
          $rows = selectSQL_SAFE_EX("
              SELECT `title`,`orin_filename`,`email`
              FROM `gaussian_splat_jobs`
              WHERE `del`='0'
              ORDER BY `id` DESC
              LIMIT 120
          ");
          $items = [];
          foreach($rows as $row){
              foreach(['title','orin_filename','email'] as $key){
                  $value = trim((string)($row[$key] ?? ''));
                  if($value !== '') $items[$value] = true;
                  if(count($items) >= 60) break 2;
              }
          }
          return array_keys($items);
      }
  }

  if(!function_exists('gs_job_list_state')){
      function gs_job_list_state($perPage=GS_LIST_PER_PAGE, $orderSql='`id` DESC'){
          $perPage = max(1, (int)$perPage);
          $q = trim((string)($_GET['q'] ?? ''));
          if(function_exists('mb_substr')) $q = mb_substr($q, 0, 80, 'UTF-8');
          else $q = substr($q, 0, 160);
          $page = max(1, (int)($_GET['p'] ?? 1));
          $params = [];
          $where = gs_job_search_where($q, $params);
          $countRows = selectSQL_SAFE_EX("SELECT COUNT(*) AS `c` FROM `gaussian_splat_jobs` WHERE {$where}", $params);
          $total = (int)($countRows[0]['c'] ?? 0);
          $pages = max(1, (int)ceil($total / $perPage));
          if($page > $pages) $page = $pages;
          $offset = ($page - 1) * $perPage;
          $rows = selectSQL_SAFE_EX(
              "SELECT * FROM `gaussian_splat_jobs` WHERE {$where} ORDER BY {$orderSql} LIMIT :limit OFFSET :offset",
              array_merge($params, ['limit'=>$perPage, 'offset'=>$offset])
          );
          return [
              'q'=>$q,
              'page'=>$page,
              'per_page'=>$perPage,
              'offset'=>$offset,
              'total'=>$total,
              'pages'=>$pages,
              'rows'=>$rows,
              'suggestions'=>gs_job_search_suggestions(),
          ];
      }
  }

  if(!function_exists('gs_job_list_url')){
      function gs_job_list_url($state, $page, $extra=[]){
          $query = array_merge($extra, ['p'=>max(1, (int)$page)]);
          if(trim((string)($state['q'] ?? '')) !== '') $query['q'] = (string)$state['q'];
          return '?' . http_build_query($query);
      }
  }

  if(!function_exists('gs_job_search_form_html')){
      function gs_job_search_form_html($state, $extra=[]){
          ob_start(); ?>
          <form class="gs-list-tools" method="get">
            <?php foreach($extra as $key => $value): ?>
              <input type="hidden" name="<?=htmlspecialchars((string)$key, ENT_QUOTES);?>" value="<?=htmlspecialchars((string)$value, ENT_QUOTES);?>">
            <?php endforeach; ?>
            <label for="gsJobSearch">搜尋</label>
            <input id="gsJobSearch" class="form-control" type="search" name="q" list="gsJobSearchList" value="<?=htmlspecialchars((string)($state['q'] ?? ''), ENT_QUOTES);?>" placeholder="編號、標題、檔名、信箱、狀態">
            <datalist id="gsJobSearchList">
              <?php foreach((array)($state['suggestions'] ?? []) as $item): ?>
                <option value="<?=htmlspecialchars((string)$item, ENT_QUOTES);?>"></option>
              <?php endforeach; ?>
            </datalist>
            <button class="btn btn-default" type="submit">查詢</button>
            <a class="btn btn-default" href="?">清除</a>
            <span class="gs-list-count">每頁 15 筆，共 <?=htmlspecialchars((string)($state['total'] ?? 0), ENT_QUOTES);?> 筆</span>
          </form>
          <?php return trim(ob_get_clean());
      }
  }

  if(!function_exists('gs_job_pagination_html')){
      function gs_job_pagination_html($state, $extra=[]){
          $page = (int)($state['page'] ?? 1);
          $pages = (int)($state['pages'] ?? 1);
          ob_start(); ?>
          <nav class="gs-pagination" aria-label="分頁">
            <a class="btn btn-default <?=$page <= 1 ? 'disabled' : '';?>" href="<?=htmlspecialchars(gs_job_list_url($state, max(1, $page - 1), $extra), ENT_QUOTES);?>">上一頁</a>
            <span>第 <?=$page;?> / <?=$pages;?> 頁</span>
            <a class="btn btn-default <?=$page >= $pages ? 'disabled' : '';?>" href="<?=htmlspecialchars(gs_job_list_url($state, min($pages, $page + 1), $extra), ENT_QUOTES);?>">下一頁</a>
          </nav>
          <?php return trim(ob_get_clean());
      }
  }

  if(!function_exists('gs_confidence_gate_from_row')){
      function gs_confidence_gate_from_row($row){
          $gate = [];
          $raw = trim((string)($row['confidence_gate_json'] ?? ''));
          if($raw !== ''){
              $decoded = json_decode($raw, true);
              if(is_array($decoded)) $gate = $decoded;
          }
          if(!$gate && is_numeric($row['id'] ?? null)){
              $id = (int)$row['id'];
              $gatePath = __DIR__ . "/uploads/{$id}/confidence_gate.json";
              if(is_file($gatePath)){
                  $decoded = json_decode((string)@file_get_contents($gatePath), true);
                  if(is_array($decoded)) $gate = $decoded;
              }
          }

          $hasGate = $gate || trim((string)($row['confidence_decision'] ?? '')) !== '' || is_numeric($row['confidence_score'] ?? null);
          if(!$hasGate) return null;

          $recommendations = $gate['recommendations'] ?? [];
          if(!is_array($recommendations)) $recommendations = [];
          $risks = $gate['risks'] ?? [];
          if(!is_array($risks)) $risks = [];

          return [
              'score'=>is_numeric($row['confidence_score'] ?? null) ? (float)$row['confidence_score'] : ($gate['score'] ?? null),
              'grade'=>(string)($row['confidence_grade'] ?? ($gate['grade'] ?? '')),
              'decision'=>(string)($row['confidence_decision'] ?? ($gate['decision'] ?? '')),
              'effectiveDecision'=>(string)($row['confidence_effective_decision'] ?? ($gate['effectiveDecision'] ?? '')),
              'override'=>[
                  'enabled'=>((int)($row['confidence_override'] ?? ($gate['override']['enabled'] ?? 0))) === 1,
                  'reason'=>(string)($row['confidence_override_reason'] ?? ($gate['override']['reason'] ?? '')),
              ],
              'createdAt'=>(string)($gate['createdAt'] ?? ''),
              'reason'=>(string)($gate['reason'] ?? ($row['reason'] ?? '')),
              'risks'=>$risks,
              'recommendations'=>$recommendations,
              'reportPath'=>(string)($gate['reportPath'] ?? ''),
              'gatePath'=>(string)($gate['gatePath'] ?? ''),
          ];
      }
  }

  if(!function_exists('gs_confidence_risk_count')){
      function gs_confidence_risk_count($gate){
          $risks = is_array($gate) ? ($gate['risks'] ?? []) : [];
          if(!is_array($risks)) return 0;
          $count = 0;
          foreach($risks as $risk){
              $risk = strtolower(trim((string)$risk));
              if($risk !== '' && !in_array($risk, ['low','none','ok'], true)) $count++;
          }
          return $count;
      }
  }

  if(!function_exists('gs_confidence_recommendation_count')){
      function gs_confidence_recommendation_count($gate){
          $items = is_array($gate) ? ($gate['recommendations'] ?? []) : [];
          if(!is_array($items)) return 0;
          $count = 0;
          foreach($items as $item){
              if(trim((string)$item) !== '') $count++;
          }
          return $count;
      }
  }

  if(!function_exists('gs_confidence_override_status')){
      function gs_confidence_override_status($gate){
          $decision = (string)($gate['decision'] ?? '');
          $effective = (string)($gate['effectiveDecision'] ?? $decision);
          $override = $gate['override'] ?? [];
          $overrideEnabled = is_array($override) && !empty($override['enabled']);
          if($decision === 'hold' && $effective === 'run_with_override') return 'overridden';
          if($decision === 'hold') return 'waiting';
          if($decision === 'reject') return 'blocked';
          return $overrideEnabled ? 'overridden' : 'none';
      }
  }

  if(!function_exists('gs_confidence_summary_from_row')){
      function gs_confidence_summary_from_row($row){
          $gate = gs_confidence_gate_from_row($row);
          $hasSummary = is_numeric($row['confidence_score'] ?? null) ||
              trim((string)($row['confidence_decision'] ?? '')) !== '' ||
              trim((string)($row['confidence_updated_at'] ?? '')) !== '' ||
              $gate;
          if(!$hasSummary) return null;

          $decision = trim((string)($row['confidence_decision'] ?? ''));
          if($decision === '' && $gate) $decision = (string)($gate['decision'] ?? '');
          $overrideStatus = trim((string)($row['confidence_override_status'] ?? ''));
          if($overrideStatus === '' && $gate) $overrideStatus = gs_confidence_override_status($gate);

          return [
              'score'=>is_numeric($row['confidence_score'] ?? null) ? (float)$row['confidence_score'] : ($gate['score'] ?? null),
              'grade'=>(string)($row['confidence_grade'] ?? ($gate['grade'] ?? '')),
              'decision'=>$decision,
              'riskCount'=>is_numeric($row['confidence_risk_count'] ?? null) ? (int)$row['confidence_risk_count'] : gs_confidence_risk_count($gate),
              'recommendationCount'=>is_numeric($row['confidence_recommendation_count'] ?? null) ? (int)$row['confidence_recommendation_count'] : gs_confidence_recommendation_count($gate),
              'needsOverride'=>is_numeric($row['confidence_needs_override'] ?? null) ? ((int)$row['confidence_needs_override'] === 1) : ($decision === 'hold'),
              'overrideStatus'=>$overrideStatus,
              'updatedAt'=>(string)($row['confidence_updated_at'] ?? ($gate['createdAt'] ?? '')),
          ];
      }
  }

  if(!function_exists('gs_confidence_summary_lines')){
      function gs_confidence_summary_lines($gate){
          if(!$gate) return [];
          $score = is_numeric($gate['score'] ?? null) ? number_format((float)$gate['score'], 2, '.', '') : '-';
          $grade = trim((string)($gate['grade'] ?? ''));
          $decision = trim((string)($gate['decision'] ?? ''));
          $effective = trim((string)($gate['effectiveDecision'] ?? ''));
          $lines = ['信心 ' . $score . ($grade !== '' ? " / {$grade}" : '')];
          if($decision !== '') $lines[] = '決策 ' . $decision . ($effective !== '' && $effective !== $decision ? " → {$effective}" : '');
          $reason = trim((string)($gate['reason'] ?? ''));
          if($reason !== '') $lines[] = $reason;
          foreach(($gate['recommendations'] ?? []) as $item){
              $item = trim((string)$item);
              if($item !== '') $lines[] = '建議 ' . $item;
              if(count($lines) >= 4) break;
          }
          return $lines;
      }
  }

  if(!function_exists('gs_confidence_summary_html')){
      function gs_confidence_summary_html($row){
          $lines = gs_confidence_summary_lines(gs_confidence_gate_from_row($row));
          if(!$lines) return '';
          ob_start();
          foreach($lines as $line): ?>
            <div class="gs-muted"><?=htmlspecialchars($line, ENT_QUOTES);?></div>
          <?php endforeach;
          return trim(ob_get_clean());
      }
  }

  if(!function_exists('gs_pipeline_stage_map')){
      function gs_pipeline_stage_map(){
          static $stageMap = null;
          if($stageMap !== null) return $stageMap;

          $stageMap = [
              'worker_start' => ['percent'=>3, 'step'=>'啟動中', 'label'=>'啟動 worker'],
              'frame_select' => ['percent'=>12, 'step'=>'1 / 7', 'label'=>'挑選影格'],
              'legacy_extract' => ['percent'=>12, 'step'=>'1 / 7', 'label'=>'擷取影格'],
              'colmap' => ['percent'=>28, 'step'=>'2 / 7', 'label'=>'COLMAP 相機姿態估算'],
              'frame_colmap' => ['percent'=>38, 'step'=>'3 / 7', 'label'=>'標註影格品質'],
              'enhance' => ['percent'=>46, 'step'=>'選用前處理', 'label'=>'影格增強'],
              'prepare_training_images' => ['percent'=>52, 'step'=>'選用前處理', 'label'=>'準備訓練影像'],
              'train' => ['percent'=>76, 'step'=>'4 / 7', 'label'=>'Gaussian 訓練'],
              'export' => ['percent'=>90, 'step'=>'5 / 7', 'label'=>'匯出 Splat'],
              'cleanup' => ['percent'=>96, 'step'=>'6 / 7', 'label'=>'清理 Splat'],
              'finalize' => ['percent'=>99, 'step'=>'7 / 7', 'label'=>'產生 metadata / QA'],
          ];
          return $stageMap;
      }
  }

  if(!function_exists('gs_job_progress')){
      function gs_job_progress($row){
          $status = (string)($row['status'] ?? '');
          if($status === '2'){
              return ['percent'=>100, 'step'=>'完成', 'label'=>'完成', 'active'=>false];
          }
          if($status === '0'){
              return ['percent'=>0, 'step'=>'等待中', 'label'=>'等待轉檔', 'active'=>true];
          }
          if($status === '5'){
              return ['percent'=>0, 'step'=>'等待覆核', 'label'=>'等待人工覆核', 'active'=>false];
          }
          if($status !== '1'){
              return ['percent'=>0, 'step'=>'已停止', 'label'=>gs_status_text($status), 'active'=>false];
          }

          $stageKey = trim((string)($row['current_stage'] ?? ''));
          $stageLabel = trim((string)($row['current_stage_label'] ?? ''));
          $stageMap = gs_pipeline_stage_map();
          if(isset($stageMap[$stageKey])){
              $progress = $stageMap[$stageKey];
              if($stageLabel !== '') $progress['label'] = $stageLabel;
              $progress['active'] = true;
              return $progress;
          }
          return ['percent'=>5, 'step'=>'處理中', 'label'=>$stageLabel !== '' ? $stageLabel : '轉檔中', 'active'=>true];
      }
  }

  if(!function_exists('gs_job_splat_path')){
      function gs_job_splat_path($id){
          $id = (int)$id;
          $cleanSplat = "uploads/{$id}/exports/splat.clean.ply";
          $rawSplat = "uploads/{$id}/exports/splat.ply";
          return is_file(__DIR__ . "/{$cleanSplat}") ? $cleanSplat : $rawSplat;
      }
  }

  if(!function_exists('gs_job_preview_image_path')){
      function gs_job_preview_image_path($id){
          $id = (int)$id;
          if($id <= 0) return '';
          $preferred = "uploads/{$id}/processed/images/frame_00001.jpg";
          if(is_file(__DIR__ . "/{$preferred}")) return $preferred;
          $matches = glob(__DIR__ . "/uploads/{$id}/processed/images/*.{jpg,jpeg,png,webp}", GLOB_BRACE);
          if(!$matches) return '';
          sort($matches, SORT_NATURAL);
          $path = str_replace('\\', '/', $matches[0]);
          $base = str_replace('\\', '/', __DIR__ . '/');
          return strpos($path, $base) === 0 ? substr($path, strlen($base)) : '';
      }
  }

  if(!function_exists('gs_thumb_cache_dir')){
      function gs_thumb_cache_dir(){
          return __DIR__ . "/uploads/_thumbs";
      }
  }

  if(!function_exists('gs_job_thumb_cache_path')){
      function gs_job_thumb_cache_path($id){
          $id = (int)$id;
          return gs_thumb_cache_dir() . "/output_{$id}.png";
      }
  }

  if(!function_exists('gs_job_thumb_cache_url')){
      function gs_job_thumb_cache_url($id){
          $id = (int)$id;
          $path = gs_job_thumb_cache_path($id);
          $stamp = is_file($path) ? filemtime($path) : time();
          return "uploads/_thumbs/output_{$id}.png?v={$stamp}";
      }
  }

  if(!function_exists('gs_job_needs_output_thumb')){
      function gs_job_needs_output_thumb($row){
          $id = (int)($row['id'] ?? 0);
          if($id <= 0 || (string)($row['status'] ?? '') !== '2') return false;
          if(is_file(gs_job_thumb_cache_path($id))) return false;
          return gs_splat_artifact_for_job($id) !== null;
      }
  }

  if(!function_exists('gs_job_thumb_queue_payload')){
      function gs_job_thumb_queue_payload($rows, $limit=3){
          $ids = [];
          $limit = max(1, (int)$limit);
          foreach($rows as $row){
              if(gs_job_needs_output_thumb($row)){
                  $ids[] = (int)$row['id'];
                  if(count($ids) >= $limit) break;
              }
          }
          return $ids;
      }
  }

  if(!function_exists('gs_delete_thumb_cache')){
      function gs_delete_thumb_cache($id){
          $path = gs_job_thumb_cache_path($id);
          if(is_file($path)) @unlink($path);
      }
  }

  if(!function_exists('gs_job_thumbnail_cell_html')){
      function gs_job_thumbnail_cell_html($row){
          $id = (int)($row['id'] ?? 0);
          $viewerUrl = "viewer_splat.php?id={$id}";
          $thumbPath = gs_job_thumb_cache_path($id);
          $preview = gs_job_preview_image_path($id);
          $needsOutputThumb = gs_job_needs_output_thumb($row);

          ob_start(); ?>
          <div class="gs-thumb-pair">
            <div class="gs-thumb-item">
              <div class="gs-thumb-title">原始</div>
              <?php if($id > 0 && $preview !== ''): ?>
                <div class="gs-model-thumb model-thumb-ready">
                  <img src="<?=htmlspecialchars($preview, ENT_QUOTES);?>" alt="Gaussian Splat job <?=$id;?> source thumbnail">
                </div>
              <?php else: ?>
                <div class="gs-model-thumb model-thumb-empty"><span>-</span></div>
              <?php endif; ?>
            </div>
            <div class="gs-thumb-item">
              <div class="gs-thumb-title">成果</div>
          <?php if($id > 0 && is_file($thumbPath)){
              $thumbUrl = gs_job_thumb_cache_url($id);
              ?>
              <a class="gs-thumb-link" href="<?=htmlspecialchars($viewerUrl, ENT_QUOTES);?>" target="_blank" rel="noopener">
                <div class="gs-model-thumb model-thumb-ready">
                  <img src="<?=htmlspecialchars($thumbUrl, ENT_QUOTES);?>" alt="Gaussian Splat job <?=$id;?> output thumbnail">
                </div>
              </a>
              <?php
          } else if($needsOutputThumb){
              ?>
              <a class="gs-thumb-link" href="<?=htmlspecialchars($viewerUrl, ENT_QUOTES);?>" target="_blank" rel="noopener">
                <div class="gs-model-thumb model-thumb-pending" data-missing-output-thumb="1" data-job-id="<?=$id;?>"><span>等待成果</span></div>
              </a>
              <?php
          } else {
              ?>
              <div class="gs-model-thumb model-thumb-empty"><span>等待成果</span></div>
              <?php
          }
          ?>
            </div>
          </div>
          <?php return trim(ob_get_clean());
      }
  }

  if(!function_exists('gs_splat_artifact_extensions')){
      function gs_splat_artifact_extensions(){
          return ['ply', 'splat', 'ksplat', 'spz'];
      }
  }

  if(!function_exists('gs_splat_job_relative_path')){
      function gs_splat_job_relative_path($id, $path){
          $id = (int)$id;
          $path = str_replace('\\', '/', trim((string)$path));
          if($path === '' || $path[0] === '/' || strpos($path, '://') !== false) return '';
          if(strpos("/{$path}/", '/../') !== false) return '';
          $prefix = "uploads/{$id}/";
          return strpos($path, $prefix) === 0 ? substr($path, strlen($prefix)) : $path;
      }
  }

  if(!function_exists('gs_splat_artifact_uuid')){
      function gs_splat_artifact_uuid($id, $jobRelativePath){
          $id = (int)$id;
          $jobRelativePath = gs_splat_job_relative_path($id, $jobRelativePath);
          if($id <= 0 || $jobRelativePath === '') return '';
          return "gs_{$id}_" . substr(hash('sha256', "{$id}|{$jobRelativePath}"), 0, 32);
      }
  }

  if(!function_exists('gs_splat_artifact_full_path')){
      function gs_splat_artifact_full_path($id, $jobRelativePath){
          $id = (int)$id;
          $jobRelativePath = gs_splat_job_relative_path($id, $jobRelativePath);
          if($id <= 0 || $jobRelativePath === '') return '';
          $ext = strtolower(pathinfo($jobRelativePath, PATHINFO_EXTENSION));
          if(!in_array($ext, gs_splat_artifact_extensions(), true)) return '';
          $publicPath = "uploads/{$id}/{$jobRelativePath}";
          $real = realpath(__DIR__ . "/{$publicPath}");
          $allowedRoot = realpath(__DIR__ . "/uploads");
          if(!$real || !$allowedRoot || strpos($real, $allowedRoot . DIRECTORY_SEPARATOR) !== 0) return '';
          return is_file($real) ? $publicPath : '';
      }
  }

  if(!function_exists('gs_splat_manifest_candidates')){
      function gs_splat_manifest_candidates($id){
          $id = (int)$id;
          $candidates = [];
          foreach(['delivery_manifest.json', 'engine_contract.json'] as $jsonFile){
              $data = json_decode((string)@file_get_contents(__DIR__ . "/uploads/{$id}/{$jsonFile}"), true);
              if(!is_array($data)) continue;
              foreach((array)($data['delivery_tracks'] ?? []) as $track){
                  if(($track['track'] ?? '') === 'splat' && is_array($track['primary_artifact'] ?? null)){
                      $candidates[] = $track['primary_artifact']['path'] ?? '';
                  }
              }
              foreach((array)($data['artifacts'] ?? []) as $artifact){
                  if(($artifact['type'] ?? '') === 'splat') $candidates[] = $artifact['path'] ?? '';
              }
          }
          return $candidates;
      }
  }

  if(!function_exists('gs_splat_artifact_for_job')){
      function gs_splat_artifact_for_job($id){
          $id = (int)$id;
          if($id <= 0) return null;
          $candidates = array_merge(
              gs_splat_manifest_candidates($id),
              ["exports/splat.clean.ply", "exports/splat.trench.ply", "exports/splat.ply"]
          );
          foreach($candidates as $candidate){
              $jobRelativePath = gs_splat_job_relative_path($id, $candidate);
              $publicPath = gs_splat_artifact_full_path($id, $jobRelativePath);
              if($publicPath === '') continue;
              $real = realpath(__DIR__ . "/{$publicPath}");
              $ext = strtolower(pathinfo($publicPath, PATHINFO_EXTENSION));
              $uuid = gs_splat_artifact_uuid($id, $jobRelativePath);
              return [
                  'job_id'=>$id,
                  'uuid'=>$uuid,
                  'path'=>$publicPath,
                  'realpath'=>$real,
                  'format'=>$ext,
                  'mime_type'=>'application/octet-stream',
                  'size_bytes'=>is_file($real) ? (int)filesize($real) : 0,
                  'url'=>"api.php?mode=getSplat&uuid=" . rawurlencode($uuid),
              ];
          }
          return null;
      }
  }

  if(!function_exists('gs_splat_artifact_from_uuid')){
      function gs_splat_artifact_from_uuid($uuid){
          $uuid = trim((string)$uuid);
          if(!preg_match('/^gs_([1-9][0-9]*)_[a-f0-9]{32}$/', $uuid, $m)) return null;
          $artifact = gs_splat_artifact_for_job((int)$m[1]);
          if(!$artifact || !hash_equals($artifact['uuid'], $uuid)) return null;
          return $artifact;
      }
  }

  if(!function_exists('gs_job_confidence_report_url')){
      function gs_job_confidence_report_url($id){
          $id = (int)$id;
          $path = "uploads/{$id}/confidence_report.json";
          return is_file(__DIR__ . "/{$path}") ? $path : '';
      }
  }

  if(!function_exists('gs_job_confidence_gate_url')){
      function gs_job_confidence_gate_url($id){
          $id = (int)$id;
          $path = "uploads/{$id}/confidence_gate.json";
          return is_file(__DIR__ . "/{$path}") ? $path : '';
      }
  }

  if(!function_exists('gs_job_artifact_links')){
      function gs_job_artifact_links($id){
          $id = (int)$id;
          $files = [
              ['group'=>'Pipeline', 'label'=>'timing_report.json', 'path'=>"uploads/{$id}/timing_report.json"],
              ['group'=>'Engine Runs', 'label'=>'engine_contract.json', 'path'=>"uploads/{$id}/engine_contract.json"],
              ['group'=>'Artifacts', 'label'=>'appearance_summary.json', 'path'=>"uploads/{$id}/evidence/appearance_summary.json"],
              ['group'=>'Artifacts', 'label'=>'splat_summary.json', 'path'=>"uploads/{$id}/evidence/splat_summary.json"],
              ['group'=>'Artifacts', 'label'=>'compare_report.json', 'path'=>"uploads/{$id}/compare/compare_report.json"],
              ['group'=>'Validation', 'label'=>'validation_report.json', 'path'=>"uploads/{$id}/validation/validation_report.json"],
              ['group'=>'Validation', 'label'=>'qa_validation_report.json', 'path'=>"uploads/{$id}/validation/qa_validation_report.json"],
              ['group'=>'Delivery', 'label'=>'delivery_manifest.json', 'path'=>"uploads/{$id}/delivery_manifest.json"],
          ];
          $links = [];
          foreach($files as $file){
              if(is_file(__DIR__ . "/" . $file['path'])) $links[] = $file;
          }
          return $links;
      }
  }

  if(!function_exists('gs_job_status_cell_html')){
      function gs_job_status_cell_html($row){
          $progress = gs_job_progress($row);
          $shortReason = gs_short_failure_reason($row['reason'] ?? '');
          ob_start();
          ?>
            <div class="gs-status-main"><?=htmlspecialchars(gs_status_text($row['status'] ?? ''), ENT_QUOTES);?></div>
            <div class="gs-muted">模式：<?=htmlspecialchars(gs_pipeline_mode_label($row['pipeline_mode'] ?? 'fast'), ENT_QUOTES);?></div>
            <?php if($progress['active']): ?>
              <div class="gs-muted"><?=htmlspecialchars((string)($progress['percent'] ?? 0), ENT_QUOTES);?>% · <?=htmlspecialchars((string)($progress['step'] ?? ''), ENT_QUOTES);?> · <?=htmlspecialchars((string)($progress['label'] ?? ''), ENT_QUOTES);?></div>
              <div class="gs-progress-mini"><span style="width:<?=min(100, max(0, (int)$progress['percent']));?>%;"></span></div>
            <?php else: ?>
              <div class="gs-muted"><?=htmlspecialchars((string)($progress['step'] ?? ''), ENT_QUOTES);?> · <?=htmlspecialchars((string)($progress['label'] ?? ''), ENT_QUOTES);?></div>
            <?php endif; ?>
            <?php if($shortReason !== ''): ?>
              <div class="gs-failure-inline"><?=htmlspecialchars($shortReason, ENT_QUOTES);?></div>
            <?php endif; ?>
            <?=gs_confidence_summary_html($row);?>
          <?php
          return trim(ob_get_clean());
      }
  }

  if(!function_exists('gs_job_timing_cell_html')){
      function gs_job_timing_cell_html($row, $estimateSeconds){
          $timingSummary = gs_job_timing_summary($row, $estimateSeconds);
          ob_start();
          foreach($timingSummary as $timingLine): ?>
            <div class="gs-muted"><?=htmlspecialchars($timingLine, ENT_QUOTES);?></div>
          <?php endforeach;
          return trim(ob_get_clean());
      }
  }

  if(!function_exists('gs_job_frames_cell_html')){
      function gs_job_frames_cell_html($row){
          ob_start();
          ?><?=htmlspecialchars((string)($row['frame_count'] ?? ''), ENT_QUOTES);?> / <?=htmlspecialchars((string)($row['registered_frame_count'] ?? ''), ENT_QUOTES);?><?php
          return trim(ob_get_clean());
      }
  }

  if(!function_exists('gs_job_actions_cell_html')){
      function gs_job_actions_cell_html($row){
          $id = (int)($row['id'] ?? 0);
          $splat = gs_job_splat_path($id);
          $isReady = (string)($row['status'] ?? '') === '2';
          $hasSplat = $isReady && is_file(__DIR__ . "/{$splat}");
          $shortReason = gs_short_failure_reason($row['reason'] ?? '');
          ob_start();
          $hasAction = false;
          if($hasSplat):
              $hasAction = true; ?>
              <button class="btn btn-xs btn-success" type="button" onclick="openSplatViewer(<?=$id;?>)">檢視</button>
          <?php endif;
          if($shortReason !== ''):
              $hasAction = true; ?>
              <button class="btn btn-xs btn-default" type="button" onclick="openReasonDialog(<?=$id;?>)">原因</button>
          <?php endif;
          if(!$hasAction): ?>
              <span class="gs-muted">-</span>
          <?php endif;
          return trim(ob_get_clean());
      }
  }

  if(!function_exists('gs_job_delta_payload')){
      function gs_job_delta_payload($rows){
          $estimateSeconds = gs_average_completed_duration($rows);
          $hasActiveJobs = false;
          $failureReasons = [];
          $payloadRows = [];

          foreach($rows as $row){
              $id = (int)($row['id'] ?? 0);
              $active = in_array((string)($row['status'] ?? ''), ['0','1'], true);
              if($active) $hasActiveJobs = true;

              $fullReason = trim((string)($row['reason'] ?? ''));
              if($fullReason !== '') $failureReasons[(string)$id] = gs_json_safe_text($fullReason);

              $payloadRows[] = [
                  'id' => $id,
                  'active' => $active,
                  'thumb_html' => gs_job_thumbnail_cell_html($row),
                  'status_html' => gs_job_status_cell_html($row),
                  'timing_html' => gs_job_timing_cell_html($row, $estimateSeconds),
                  'frames_html' => gs_job_frames_cell_html($row),
                  'actions_html' => gs_job_actions_cell_html($row),
                  'confidence_gate' => gs_confidence_gate_from_row($row),
                  'confidence_summary' => gs_confidence_summary_from_row($row),
              ];
          }

          return [
              'estimate_seconds' => $estimateSeconds,
              'has_active_jobs' => $hasActiveJobs,
              'failure_reasons' => $failureReasons,
              'thumb_queue' => gs_job_thumb_queue_payload($rows, 3),
              'rows' => $payloadRows,
          ];
      }
  }
