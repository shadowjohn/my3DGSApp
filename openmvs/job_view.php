<?php
  if(!defined('OVM_DEFAULT_ESTIMATE_SECONDS')){
      define('OVM_DEFAULT_ESTIMATE_SECONDS', 3600);
  }
  if(!defined('OVM_LIST_PER_PAGE')){
      define('OVM_LIST_PER_PAGE', 15);
  }

  if(!function_exists('ovm_status_text')){
      function ovm_status_text($status){
          switch((string)$status){
              case '0': return '待處理';
              case '1': return '轉檔中';
              case '2': return '已完成';
              case '3': return '失敗';
              case '4': return '暫停';
          }
          return '未知';
      }
  }

  if(!function_exists('ovm_product_texture_sizes')){
      function ovm_product_texture_sizes(){
          return [512, 2048, 4096, 8192];
      }
  }

  if(!function_exists('ovm_product_texture_size_valid')){
      function ovm_product_texture_size_valid($size){
          return in_array((int)$size, ovm_product_texture_sizes(), true);
      }
  }

  if(!function_exists('ovm_product_status_text')){
      function ovm_product_status_text($status){
          switch((string)$status){
              case '0': return '待處理';
              case '1': return '產製中';
              case '2': return '已完成';
              case '3': return '失敗';
              case '4': return '暫停';
          }
          return '未知';
      }
  }

  if(!function_exists('ovm_product_file_size_mb')){
      function ovm_product_file_size_mb($path){
          $path = trim((string)$path);
          if($path === '') return null;
          if($path[0] !== '/') $path = __DIR__ . "/" . $path;
          return is_file($path) ? round(filesize($path) / 1048576, 2) : null;
      }
  }

  if(!function_exists('ovm_products_for_job')){
      function ovm_products_for_job($jobId){
          $jobId = (int)$jobId;
          if($jobId <= 0) return [];
          return selectSQL_SAFE(
              "SELECT * FROM `openmvs_products` WHERE `job_id`=? AND `del`='0' ORDER BY `product_type`, `texture_size`",
              [$jobId]
          );
      }
  }

  if(!function_exists('ovm_job_has_active_products')){
      function ovm_job_has_active_products($jobId){
          $jobId = (int)$jobId;
          if($jobId <= 0) return false;
          $rows = selectSQL_SAFE(
              "SELECT `id` FROM `openmvs_products` WHERE `job_id`=? AND `del`='0' AND `status` IN ('0','1') LIMIT 1",
              [$jobId]
          );
          return !empty($rows);
      }
  }

  if(!function_exists('ovm_format_duration')){
      function ovm_format_duration($seconds){
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

  if(!function_exists('ovm_percent_label')){
      function ovm_percent_label($ratio){
          if(!is_numeric($ratio)) return '';
          return number_format((float)$ratio * 100, 1, '.', '') . '%';
      }
  }

	  if(!function_exists('ovm_mask_mode_label')){
	      function ovm_mask_mode_label($mode){
	          switch((string)$mode){
	              case 'provided': return 'ZIP mask';
	              case 'auto': return 'Auto mask';
	              default: return 'No mask';
	          }
	      }
	  }

	  if(!function_exists('ovm_quality_preset_label')){
	      function ovm_quality_preset_label($preset){
	          switch((string)$preset){
	              case 'fast': return '快速 fast';
	              case 'high': return '高品質 high';
	              default: return '標準 normal';
	          }
	      }
	  }

	  if(!function_exists('ovm_capture_decision_label')){
	      function ovm_capture_decision_label($decision){
	          switch((string)$decision){
	              case 'run': return '建議執行';
	              case 'warn': return '可執行但有風險';
	              case 'hold': return '等待覆核';
	              case 'reject': return '不建議重建';
	          }
	          return '';
	      }
	  }

	  if(!function_exists('ovm_diagnostic_quality_level')){
	      function ovm_diagnostic_quality_level($row){
	          if(($row['diagnostic_status'] ?? '') === 'error') return [1, '失敗'];
	          $score = is_numeric($row['diagnostic_score'] ?? null) ? (float)$row['diagnostic_score'] : null;
	          if($score === null) return [3, '未知'];
	          if($score >= 90) return [5, '優'];
	          if($score >= 75) return [4, '良'];
	          if($score >= 50) return [3, '可用'];
	          if($score >= 25) return [2, '注意'];
	          return [1, '失敗'];
	      }
	  }

  if(!function_exists('ovm_job_json_artifact')){
      function ovm_job_json_artifact($id, $relative){
          $id = (int)$id;
          if($id <= 0) return [];
          $path = __DIR__ . "/uploads/{$id}/{$relative}";
          if(!is_file($path)) return [];
          $data = json_decode((string)@file_get_contents($path), true);
          return is_array($data) ? $data : [];
      }
  }

  if(!function_exists('ovm_validation_status_label')){
      function ovm_validation_status_label($status){
          switch((string)$status){
              case 'deliverable': return '可交付';
              case 'review_needed': return '需覆核';
              case 'recapture_recommended': return '建議補拍';
              case 'engine_failed': return '引擎失敗';
          }
          return (string)$status;
      }
  }

  if(!function_exists('ovm_root_cause_label')){
      function ovm_root_cause_label($rootCause){
          switch((string)$rootCause){
              case 'capture': return '拍攝問題';
              case 'engine': return '引擎問題';
              case 'texture': return '貼圖問題';
              case 'input': return '輸入問題';
              case 'viewer': return '檢視問題';
              case 'unknown': return '未知';
          }
          return (string)$rootCause;
      }
  }

  if(!function_exists('ovm_contract_summary_lines')){
      function ovm_contract_summary_lines($validation, $failure){
          $lines = [];
          $failure = is_array($failure) ? $failure : [];
          if($failure){
              $lines[] = 'Failure ' . ovm_root_cause_label($failure['root_cause'] ?? 'unknown');
              if(!empty($failure['failed_stage'])) $lines[] = '失敗階段 ' . $failure['failed_stage'];
              if(!empty($failure['recapture_recommended'])) $lines[] = '建議補拍';
              $lines[] = !empty($failure['retryable']) ? '可重轉' : '不建議直接重轉';
              foreach(array_slice((array)($failure['recommendations'] ?? []), 0, 2) as $item){
                  if(trim((string)$item) !== '') $lines[] = (string)$item;
              }
              foreach(array_slice((array)($failure['diagnostic_warnings'] ?? []), 0, 2) as $item){
                  if(trim((string)$item) !== '') $lines[] = (string)$item;
              }
              return $lines;
          }

          $decision = is_array($validation) ? ($validation['decision'] ?? []) : [];
          if(!is_array($decision) || !$decision) return [];
          $grade = trim((string)($decision['grade'] ?? ''));
          $lines[] = 'Validation ' . ovm_validation_status_label($decision['status'] ?? '') . ($grade !== '' ? ' / ' . $grade : '');
          $lines[] = '來源：' . ovm_root_cause_label($decision['root_cause'] ?? 'unknown');
          $summary = trim((string)($decision['summary'] ?? ''));
          if($summary !== '') $lines[] = $summary;
          return $lines;
      }
  }

  if(!function_exists('ovm_contract_summary_html')){
      function ovm_contract_summary_html($lines, $detailJobId=0){
          if(!$lines) return '';
          $hasTruncated = false;
          ob_start();
          foreach($lines as $line):
              if(trim((string)$line) === '') continue;
              [$shortLine, $truncated] = ovm_short_diagnostic_summary((string)$line, 120);
              $hasTruncated = $hasTruncated || $truncated; ?>
              <div class="ovm-muted ovm-quality-summary"><?=htmlspecialchars($shortLine, ENT_QUOTES);?></div>
          <?php endforeach;
          if($hasTruncated && (int)$detailJobId > 0): ?>
              <button class="btn btn-xs btn-default" type="button" onclick="openDiagnosticsDialog(<?=(int)$detailJobId;?>)">詳細</button>
          <?php endif;
          return trim(ob_get_clean());
      }
  }

  if(!function_exists('ovm_job_validation_summary_html')){
      function ovm_job_validation_summary_html($id){
          return ovm_contract_summary_html(ovm_contract_summary_lines(
              ovm_job_json_artifact($id, 'validation/validation_report.json'),
              []
          ), $id);
      }
  }

  if(!function_exists('ovm_job_failure_summary_html')){
      function ovm_job_failure_summary_html($id){
          return ovm_contract_summary_html(ovm_contract_summary_lines(
              [],
              ovm_job_json_artifact($id, 'failure_summary.json')
          ), $id);
      }
  }

  if(!function_exists('ovm_elapsed_seconds')){
      function ovm_elapsed_seconds($row){
          if(is_numeric($row['process_seconds'] ?? null)){
              return max(0, (int)$row['process_seconds']);
          }
          $start = $row['work_st_datetime'] ?? null;
          if(!empty($start)){
              $startTs = strtotime((string)$start);
              if($startTs === false) return null;
              $endTs = time();
              if(in_array((string)($row['status'] ?? ''), ['2','3','4'], true)){
                  if(empty($row['work_et_datetime'])) return null;
                  $endTs = strtotime((string)$row['work_et_datetime']);
              }
              if($endTs === false) return null;
              return max(0, $endTs - $startTs);
          }
          if(is_numeric($row['duration_seconds'] ?? null)){
              return max(0, (int)$row['duration_seconds']);
          }
          return null;
      }
  }

  if(!function_exists('ovm_average_completed_duration')){
      function ovm_average_completed_duration($rows){
          $durations = [];
          foreach($rows as $row){
              if((string)($row['status'] ?? '') !== '2') continue;
              $elapsed = ovm_elapsed_seconds($row);
              if(is_numeric($elapsed) && (int)$elapsed > 0){
                  $durations[] = (int)$elapsed;
              }
          }
          if(!$durations) return OVM_DEFAULT_ESTIMATE_SECONDS;
          return (int)round(array_sum($durations) / count($durations));
      }
  }

  if(!function_exists('ovm_job_timing_summary')){
      function ovm_job_timing_summary($row, $estimateSeconds){
          $elapsed = ovm_elapsed_seconds($row);
          $status = (string)($row['status'] ?? '');
          $stage = trim((string)($row['current_stage_label'] ?? ''));
          $summary = [];
          if($status === '2'){
              $summary[] = '總耗時 ' . ovm_format_duration($elapsed);
          } else {
              $summary[] = '已花 ' . ovm_format_duration($elapsed);
              $summary[] = '粗估總長 ' . ovm_format_duration($estimateSeconds);
              if(in_array($status, ['0','1'], true) && is_numeric($elapsed)){
                  $summary[] = '預估剩 ' . ovm_format_duration(max(0, (int)$estimateSeconds - (int)$elapsed));
              }
          }
          if($stage !== '') $summary[] = '目前：' . $stage;
          return $summary;
      }
  }

  if(!function_exists('ovm_short_failure_reason')){
      function ovm_short_failure_reason($reason){
          $reason = trim((string)$reason);
          if($reason === '') return '';
          if(strpos($reason, '影片太短') !== false) return '影片太短。';
          if(strpos($reason, 'ZIP 內沒有可用圖片') !== false) return 'ZIP 內沒有可用圖片。';
          if(strpos($reason, 'missing required tool') !== false) return '缺少 COLMAP/OpenMVS 工具，請檢查環境。';
          if(strpos($reason, 'input file missing') !== false) return '找不到上傳檔案。';
          if(stripos($reason, 'failed') !== false || stripos($reason, 'error') !== false) return '轉檔失敗，請查看詳細紀錄。';

          $lines = preg_split('/\R/u', $reason);
          $shortReason = trim((string)($lines[0] ?? $reason));
          if(function_exists('mb_strlen') && mb_strlen($shortReason, 'UTF-8') > 80){
              return mb_substr($shortReason, 0, 80, 'UTF-8') . '...';
          }
          return strlen($shortReason) > 160 ? substr($shortReason, 0, 160) . '...' : $shortReason;
      }
  }

  if(!function_exists('ovm_short_diagnostic_summary')){
      function ovm_short_diagnostic_summary($summary, $limit=120){
          $summary = trim(preg_replace('/\s+/u', ' ', (string)$summary));
          if($summary === '') return ['', false];
          if(function_exists('mb_strlen') && mb_strlen($summary, 'UTF-8') > $limit){
              return [mb_substr($summary, 0, $limit, 'UTF-8') . '...', true];
          }
          if(!function_exists('mb_strlen') && strlen($summary) > $limit * 2){
              return [substr($summary, 0, $limit * 2) . '...', true];
          }
          return [$summary, false];
      }
  }

  if(!function_exists('ovm_json_safe_text')){
      function ovm_json_safe_text($value){
          $value = (string)$value;
          if($value === '') return '';
          if(function_exists('mb_convert_encoding')){
              return mb_convert_encoding($value, 'UTF-8', 'UTF-8');
          }
          return preg_replace('/[\x00-\x08\x0B\x0C\x0E-\x1F]/', '', $value);
      }
  }

  if(!function_exists('ovm_upload_time_label')){
      function ovm_upload_time_label($datetime){
          $datetime = trim((string)$datetime);
          if($datetime === '') return '未記錄';
          if(preg_match('/^0{4}-0{2}-0{2}/', $datetime)) return '未記錄';
          $ts = strtotime($datetime);
          return $ts === false ? $datetime : date('Y-m-d H:i', $ts);
      }
  }

  if(!function_exists('ovm_job_search_status_codes')){
      function ovm_job_search_status_codes($q){
          $q = trim((string)$q);
          $map = [
              '待處理'=>'0', '等待'=>'0', 'queue'=>'0',
              '轉檔'=>'1', '處理'=>'1', 'running'=>'1',
              '完成'=>'2', '已完成'=>'2', 'ready'=>'2',
              '失敗'=>'3', 'failed'=>'3',
              '暫停'=>'4', 'paused'=>'4',
          ];
          $codes = [];
          foreach($map as $label => $code){
              if($q !== '' && stripos($label, $q) !== false) $codes[$code] = $code;
          }
          if(in_array($q, ['0','1','2','3','4'], true)) $codes[$q] = $q;
          return array_values($codes);
      }
  }

  if(!function_exists('ovm_job_search_where')){
      function ovm_job_search_where($q, &$params){
          $params = [];
          $where = "`del`='0'";
          $q = trim((string)$q);
          if($q === '') return $where;

          $like = '%' . $q . '%';
          $parts = [
              "`title` LIKE :kw_title",
              "`orin_filename` LIKE :kw_file",
              "`email` LIKE :kw_email",
              "CAST(`id` AS CHAR) LIKE :kw_id",
          ];
          $params = [
              'kw_title'=>$like,
              'kw_file'=>$like,
              'kw_email'=>$like,
              'kw_id'=>$like,
          ];
          foreach(ovm_job_search_status_codes($q) as $i => $code){
              $key = "kw_status_{$i}";
              $parts[] = "`status`=:{$key}";
              $params[$key] = $code;
          }
          return $where . " AND (" . implode(" OR ", $parts) . ")";
      }
  }

  if(!function_exists('ovm_job_search_suggestions')){
      function ovm_job_search_suggestions(){
          $rows = selectSQL_SAFE_EX("
              SELECT `title`,`orin_filename`,`email`
              FROM `openmvs_jobs`
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

  if(!function_exists('ovm_job_list_state')){
      function ovm_job_list_state($perPage=OVM_LIST_PER_PAGE, $orderSql='`id` DESC'){
          $perPage = max(1, (int)$perPage);
          $q = trim((string)($_GET['q'] ?? ''));
          if(function_exists('mb_substr')) $q = mb_substr($q, 0, 80, 'UTF-8');
          else $q = substr($q, 0, 160);
          $page = max(1, (int)($_GET['p'] ?? 1));
          $params = [];
          $where = ovm_job_search_where($q, $params);
          $countRows = selectSQL_SAFE_EX("SELECT COUNT(*) AS `c` FROM `openmvs_jobs` WHERE {$where}", $params);
          $total = (int)($countRows[0]['c'] ?? 0);
          $pages = max(1, (int)ceil($total / $perPage));
          if($page > $pages) $page = $pages;
          $offset = ($page - 1) * $perPage;
          $rows = selectSQL_SAFE_EX(
              "SELECT * FROM `openmvs_jobs` WHERE {$where} ORDER BY {$orderSql} LIMIT :limit OFFSET :offset",
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
              'suggestions'=>ovm_job_search_suggestions(),
          ];
      }
  }

  if(!function_exists('ovm_job_list_url')){
      function ovm_job_list_url($state, $page, $extra=[]){
          $query = array_merge($extra, ['p'=>max(1, (int)$page)]);
          if(trim((string)($state['q'] ?? '')) !== '') $query['q'] = (string)$state['q'];
          return '?' . http_build_query($query);
      }
  }

  if(!function_exists('ovm_job_search_form_html')){
      function ovm_job_search_form_html($state, $extra=[]){
          ob_start(); ?>
          <form class="ovm-list-tools" method="get">
            <?php foreach($extra as $key => $value): ?>
              <input type="hidden" name="<?=htmlspecialchars((string)$key, ENT_QUOTES);?>" value="<?=htmlspecialchars((string)$value, ENT_QUOTES);?>">
            <?php endforeach; ?>
            <label for="ovmJobSearch">搜尋</label>
            <input id="ovmJobSearch" class="form-control" type="search" name="q" list="ovmJobSearchList" value="<?=htmlspecialchars((string)($state['q'] ?? ''), ENT_QUOTES);?>" placeholder="編號、標題、檔名、信箱、狀態">
            <datalist id="ovmJobSearchList">
              <?php foreach((array)($state['suggestions'] ?? []) as $item): ?>
                <option value="<?=htmlspecialchars((string)$item, ENT_QUOTES);?>"></option>
              <?php endforeach; ?>
            </datalist>
            <button class="btn btn-default" type="submit">查詢</button>
            <a class="btn btn-default" href="?">清除</a>
            <span class="ovm-list-count">每頁 15 筆，共 <?=htmlspecialchars((string)($state['total'] ?? 0), ENT_QUOTES);?> 筆</span>
          </form>
          <?php return trim(ob_get_clean());
      }
  }

  if(!function_exists('ovm_job_pagination_html')){
      function ovm_job_pagination_html($state, $extra=[]){
          $page = (int)($state['page'] ?? 1);
          $pages = (int)($state['pages'] ?? 1);
          ob_start(); ?>
          <nav class="ovm-pagination" aria-label="分頁">
            <a class="btn btn-default <?=$page <= 1 ? 'disabled' : '';?>" href="<?=htmlspecialchars(ovm_job_list_url($state, max(1, $page - 1), $extra), ENT_QUOTES);?>">上一頁</a>
            <span>第 <?=$page;?> / <?=$pages;?> 頁</span>
            <a class="btn btn-default <?=$page >= $pages ? 'disabled' : '';?>" href="<?=htmlspecialchars(ovm_job_list_url($state, min($pages, $page + 1), $extra), ENT_QUOTES);?>">下一頁</a>
          </nav>
          <?php return trim(ob_get_clean());
      }
  }

  if(!function_exists('ovm_pipeline_stage_map')){
      function ovm_pipeline_stage_map(){
          static $stageMap = null;
          if($stageMap !== null) return $stageMap;

          $stageMap = [
              'worker_start' => ['percent'=>2, 'step'=>'啟動中', 'label'=>'啟動 worker'],
              'prepare_images' => ['percent'=>10, 'step'=>'1 / 11', 'label'=>'準備影像'],
              'colmap_feature' => ['percent'=>18, 'step'=>'2 / 11', 'label'=>'COLMAP 特徵擷取'],
              'colmap_matcher' => ['percent'=>28, 'step'=>'3 / 11', 'label'=>'COLMAP 特徵匹配'],
              'colmap_mapper' => ['percent'=>40, 'step'=>'4 / 11', 'label'=>'COLMAP 稀疏重建'],
              'colmap_undistort' => ['percent'=>50, 'step'=>'5 / 11', 'label'=>'COLMAP 影像校正'],
              'prepare_masks' => ['percent'=>54, 'step'=>'6 / 12', 'label'=>'準備遮罩'],
              'openmvs_interface' => ['percent'=>58, 'step'=>'7 / 12', 'label'=>'匯入 OpenMVS'],
              'openmvs_create_structure' => ['percent'=>58, 'step'=>'2 / 8', 'label'=>'OpenMVS 原生 SfM'],
              'openmvs_densify' => ['percent'=>68, 'step'=>'8 / 12', 'label'=>'OpenMVS 密集點雲'],
              'openmvs_reconstruct' => ['percent'=>78, 'step'=>'9 / 12', 'label'=>'OpenMVS 建立網格'],
              'openmvs_refine' => ['percent'=>84, 'step'=>'10 / 12', 'label'=>'OpenMVS 精修網格'],
              'openmvs_texture' => ['percent'=>92, 'step'=>'11 / 12', 'label'=>'OpenMVS 貼圖'],
              'export_glb' => ['percent'=>97, 'step'=>'12 / 12', 'label'=>'匯出 GLB'],
              'embed_glb' => ['percent'=>98, 'step'=>'嵌入貼圖', 'label'=>'嵌入 GLB 貼圖'],
              'standard_artifacts' => ['percent'=>99, 'step'=>'標準證據', 'label'=>'產生標準交付證據'],
              'finalize' => ['percent'=>99, 'step'=>'收尾', 'label'=>'產生 metadata / QA'],
          ];
          return $stageMap;
      }
  }

  if(!function_exists('ovm_job_progress')){
      function ovm_job_progress($row){
          $status = (string)($row['status'] ?? '');
          if($status === '2') return ['percent'=>100, 'step'=>'已完成', 'label'=>'已完成', 'active'=>false];
          if($status === '0') return ['percent'=>0, 'step'=>'待處理', 'label'=>'待處理', 'active'=>true];
          if($status === '4') return ['percent'=>0, 'step'=>'暫停', 'label'=>'暫停', 'active'=>false];
          if($status !== '1') return ['percent'=>0, 'step'=>ovm_status_text($status), 'label'=>ovm_status_text($status), 'active'=>false];

          $stageKey = trim((string)($row['current_stage'] ?? ''));
          $stageLabel = trim((string)($row['current_stage_label'] ?? ''));
          $stageMap = ovm_pipeline_stage_map();
          if(isset($stageMap[$stageKey])){
              $progress = $stageMap[$stageKey];
              if($stageLabel !== '') $progress['label'] = $stageLabel;
              $progress['active'] = true;
              return $progress;
          }
          return ['percent'=>5, 'step'=>'處理中', 'label'=>$stageLabel !== '' ? $stageLabel : '轉檔中', 'active'=>true];
      }
  }

  if(!function_exists('ovm_job_glb_path')){
      function ovm_job_glb_path($id){
          $id = (int)$id;
          return "uploads/{$id}/exports/model.glb";
      }
  }

  if(!function_exists('ovm_job_source_preview_path')){
      function ovm_job_source_preview_path($id){
          $id = (int)$id;
          if($id <= 0) return '';
          $preferred = "uploads/{$id}/images/frame_00001.jpg";
          if(is_file(__DIR__ . "/{$preferred}")) return $preferred;
          $matches = glob(__DIR__ . "/uploads/{$id}/images/*.{jpg,jpeg,png,webp}", GLOB_BRACE);
          if(!$matches) return '';
          sort($matches, SORT_NATURAL);
          $path = str_replace('\\', '/', $matches[0]);
          $base = str_replace('\\', '/', __DIR__ . '/');
          return strpos($path, $base) === 0 ? substr($path, strlen($base)) : '';
      }
  }

  if(!function_exists('ovm_job_thumb_cache_path')){
      function ovm_job_thumb_cache_path($id){
          $id = (int)$id;
          return __DIR__ . "/uploads/_thumbs/{$id}.png";
      }
  }

  if(!function_exists('ovm_job_thumb_cache_url')){
      function ovm_job_thumb_cache_url($id){
          $id = (int)$id;
          $path = ovm_job_thumb_cache_path($id);
          $stamp = is_file($path) ? filemtime($path) : time();
          return "uploads/_thumbs/{$id}.png?v={$stamp}";
      }
  }

  if(!function_exists('ovm_job_viewer_url')){
      function ovm_job_viewer_url($id){
          return "viewer_mesh.php?id=" . (int)$id;
      }
  }

  if(!function_exists('ovm_job_thumbnail_cell_html')){
      function ovm_job_thumbnail_cell_html($row){
          $id = (int)($row['id'] ?? 0);
          $glb = ovm_job_glb_path($id);
          $glbPath = __DIR__ . "/{$glb}";
          $thumbPath = ovm_job_thumb_cache_path($id);
          $viewerUrl = ovm_job_viewer_url($id);
          $sourcePreview = ovm_job_source_preview_path($id);

          ob_start(); ?>
          <div class="ovm-thumb-pair">
            <div class="ovm-thumb-item">
              <div class="ovm-thumb-title">原始</div>
              <?php if($sourcePreview !== ''): ?>
                <div class="ovm-model-thumb model-thumb-ready">
                  <img src="<?=htmlspecialchars($sourcePreview, ENT_QUOTES);?>" alt="OpenMVS job <?=$id;?> source thumbnail">
                </div>
              <?php else: ?>
                <div class="ovm-model-thumb model-thumb-empty"><span>-</span></div>
              <?php endif; ?>
            </div>
            <div class="ovm-thumb-item">
              <div class="ovm-thumb-title">成果</div>
          <?php if($id > 0 && is_file($thumbPath)){
              $thumbUrl = ovm_job_thumb_cache_url($id);
              ?>
              <a class="ovm-thumb-link" href="<?=htmlspecialchars($viewerUrl, ENT_QUOTES);?>" target="_blank" rel="noopener">
                <div class="ovm-model-thumb model-thumb-ready">
                  <img src="<?=htmlspecialchars($thumbUrl, ENT_QUOTES);?>" alt="OpenMVS job <?=$id;?> output thumbnail">
                </div>
              </a>
              <?php
          } else if($id > 0 && is_file($glbPath)){
              ?>
              <a class="ovm-thumb-link" href="<?=htmlspecialchars($viewerUrl, ENT_QUOTES);?>" target="_blank" rel="noopener">
                <div class="ovm-model-thumb model-thumb-pending" data-glb="<?=htmlspecialchars($glb, ENT_QUOTES);?>" data-model-id="<?=$id;?>">
                  <span>產生縮圖</span>
                </div>
              </a>
              <?php
          } else {
              ?>
              <div class="ovm-model-thumb model-thumb-empty"><span>等待成果</span></div>
              <?php
          }
          ?>
            </div>
          </div>
          <?php return trim(ob_get_clean());
      }
  }

	  if(!function_exists('ovm_job_status_cell_html')){
	      function ovm_job_status_cell_html($row){
	          $progress = ovm_job_progress($row);
          ob_start();
          ?>
            <div class="ovm-status-main"><?=htmlspecialchars(ovm_status_text($row['status'] ?? ''), ENT_QUOTES);?></div>
            <?php if($progress['active']): ?>
              <div class="ovm-muted"><?=htmlspecialchars((string)($progress['percent'] ?? 0), ENT_QUOTES);?>% · <?=htmlspecialchars((string)($progress['step'] ?? ''), ENT_QUOTES);?> · <?=htmlspecialchars((string)($progress['label'] ?? ''), ENT_QUOTES);?></div>
              <div class="ovm-progress-mini"><span style="width:<?=min(100, max(0, (int)$progress['percent']));?>%;"></span></div>
            <?php else: ?>
              <div class="ovm-muted"><?=htmlspecialchars((string)($progress['step'] ?? ''), ENT_QUOTES);?> · <?=htmlspecialchars((string)($progress['label'] ?? ''), ENT_QUOTES);?></div>
            <?php endif; ?>
          <?php
          return trim(ob_get_clean());
	      }
	  }

	  if(!function_exists('ovm_job_quality_cell_html')){
	      function ovm_job_quality_cell_html($row){
	          $id = (int)($row['id'] ?? 0);
	          [$level, $label] = ovm_diagnostic_quality_level($row);
	          $summary = trim((string)($row['diagnostic_summary'] ?? ''));
	          [$shortSummary, $summaryTruncated] = ovm_short_diagnostic_summary($summary);
	          $preset = trim((string)($row['capture_preset'] ?? ''));
	          $qualityPreset = ovm_quality_preset_label($row['quality_preset'] ?? 'normal');
	          $ratio = ovm_percent_label($row['capture_registered_ratio'] ?? null);
	          $decision = ovm_capture_decision_label($row['capture_quality_decision'] ?? '');
	          ob_start();
	          ?>
	            <div class="ovm-quality ovm-quality-<?=$level;?>">Q<?=$level;?> <?=htmlspecialchars($label, ENT_QUOTES);?></div>
	            <?php if($shortSummary !== ''): ?>
	              <div class="ovm-muted ovm-quality-summary"><?=htmlspecialchars($shortSummary, ENT_QUOTES);?></div>
	              <?php if($summaryTruncated): ?>
	                <button class="btn btn-xs btn-default" type="button" onclick="openDiagnosticsDialog(<?=$id;?>)">詳細</button>
	              <?php endif; ?>
	            <?php endif; ?>
	            <?php if($preset !== ''): ?>
	              <div class="ovm-muted">拍攝模式 <?=htmlspecialchars($preset, ENT_QUOTES);?></div>
	            <?php endif; ?>
	            <div class="ovm-muted">產出品質 <?=htmlspecialchars($qualityPreset, ENT_QUOTES);?></div>
	            <?php if($ratio !== ''): ?>
	              <div class="ovm-muted">註冊比例 <?=htmlspecialchars($ratio, ENT_QUOTES);?></div>
	            <?php endif; ?>
	            <?php if($decision !== ''): ?>
	              <div class="ovm-muted">品質決策 <?=htmlspecialchars($decision, ENT_QUOTES);?></div>
	            <?php endif; ?>
	            <?=ovm_job_validation_summary_html($id);?>
	          <?php
	          return trim(ob_get_clean());
	      }
	  }

	  if(!function_exists('ovm_job_timing_cell_html')){
	      function ovm_job_timing_cell_html($row, $estimateSeconds){
          $timingSummary = ovm_job_timing_summary($row, $estimateSeconds);
          ob_start();
          foreach($timingSummary as $timingLine): ?>
            <div class="ovm-muted"><?=htmlspecialchars($timingLine, ENT_QUOTES);?></div>
          <?php endforeach;
          return trim(ob_get_clean());
      }
  }

  if(!function_exists('ovm_job_frames_cell_html')){
      function ovm_job_frames_cell_html($row){
          ob_start();
          ?><?=htmlspecialchars((string)($row['input_frame_count'] ?? ''), ENT_QUOTES);?> / <?=htmlspecialchars((string)($row['registered_frame_count'] ?? ''), ENT_QUOTES);?><?php
          return trim(ob_get_clean());
      }
  }

	  if(!function_exists('ovm_job_artifacts_cell_html')){
	      function ovm_job_artifacts_cell_html($row){
          $id = (int)($row['id'] ?? 0);
          $glb = $row['glb_file_size_mb'] ?? '';
          $mesh = $row['mesh_file_size_mb'] ?? '';
          $textureWidth = $row['texture_width'] ?? '';
          $textureHeight = $row['texture_height'] ?? '';
          $texturePatchCount = $row['texture_patch_count'] ?? '';
          $textureSummary = '';
          if($textureWidth !== '' && $textureWidth !== null && $textureHeight !== '' && $textureHeight !== null){
              $textureSummary = $textureWidth . '×' . $textureHeight;
          }
          if($texturePatchCount !== '' && $texturePatchCount !== null){
              $textureSummary .= ($textureSummary !== '' ? ' / ' : '') . $texturePatchCount . ' patches';
          }
          $black = ovm_percent_label($row['texture_black_pixel_ratio'] ?? null);
          $white = ovm_percent_label($row['texture_white_empty_pixel_ratio'] ?? null);
          ob_start();
          ?>
            <div class="ovm-muted">GLB <?=htmlspecialchars((string)$glb, ENT_QUOTES);?> MB</div>
            <div class="ovm-muted">Mesh <?=htmlspecialchars((string)$mesh, ENT_QUOTES);?> MB</div>
            <?php if($textureSummary !== ''): ?>
              <div class="ovm-muted">Texture <?=htmlspecialchars((string)$textureSummary, ENT_QUOTES);?></div>
            <?php endif; ?>
            <?php if($black !== '' || $white !== ''): ?>
              <div class="ovm-muted">Black <?=htmlspecialchars($black, ENT_QUOTES);?> / Empty <?=htmlspecialchars($white, ENT_QUOTES);?></div>
            <?php endif; ?>
            <?=ovm_job_failure_summary_html($id);?>
            <div class="ovm-muted">
              <?php foreach(ovm_job_standard_artifact_links($id) as $label => $url): ?>
                <a href="<?=htmlspecialchars($url, ENT_QUOTES);?>" target="_blank" rel="noopener"><?=htmlspecialchars($label, ENT_QUOTES);?></a>
              <?php endforeach; ?>
            </div>
          <?php
          return trim(ob_get_clean());
	      }
	  }

  if(!function_exists('ovm_job_products_cell_html')){
      function ovm_job_products_cell_html($row){
          $id = (int)($row['id'] ?? 0);
          $isReadyJob = (string)($row['status'] ?? '') === '2';
          $isAdminUser = !empty($_SESSION["login_user"]);
          $products = [];
          foreach(ovm_products_for_job($id) as $product){
              if((string)($product['product_type'] ?? '') !== 'glb') continue;
              $products[(int)($product['texture_size'] ?? 0)] = $product;
          }

          ob_start();
          if(!$isReadyJob): ?>
            <div class="ovm-muted">工作完成後可產製 GLB 產品。</div>
          <?php else: ?>
            <div class="ovm-product-list">
              <?php foreach(ovm_product_texture_sizes() as $size):
                  $product = $products[$size] ?? null;
                  $status = $product ? (string)($product['status'] ?? '') : '';
                  $stage = trim((string)($product['current_stage'] ?? ''));
                  $message = trim((string)($product['error_message'] ?? ''));
                  if($message === '') $message = trim((string)($product['reason'] ?? ''));
                  $filePath = trim((string)($product['file_path'] ?? ''));
                  if($filePath === '') $filePath = "uploads/{$id}/products/glb_{$size}/model.glb";
                  $modelExists = $product && $status === '2' && is_file(__DIR__ . "/{$filePath}");
                  $mb = $product && is_numeric($product['file_size_mb'] ?? null) ? round((float)$product['file_size_mb'], 2) : ovm_product_file_size_mb($filePath);
                  ?>
                  <div class="ovm-product-row">
                    <span class="ovm-product-size">GLB <?=$size;?></span>
                    <?php if(!$product): ?>
                      <?php if($isAdminUser): ?>
                        <button class="btn btn-xs btn-default" type="button" onclick="createOpenMvsProduct(this, <?=$id;?>, <?=$size;?>)">產製 <?=$size;?></button>
                      <?php else: ?>
                        <span class="ovm-muted">尚未產製</span>
                      <?php endif; ?>
                    <?php elseif(in_array($status, ['0','1'], true)): ?>
                      <span class="ovm-muted"><?=htmlspecialchars(ovm_product_status_text($status), ENT_QUOTES);?><?=($stage !== '' ? ' · ' . htmlspecialchars($stage, ENT_QUOTES) : '');?> · 請稍候</span>
                    <?php elseif($modelExists): ?>
                      <span class="ovm-muted"><?=htmlspecialchars((string)$mb, ENT_QUOTES);?> MB</span>
                      <button class="btn btn-xs btn-success" type="button" onclick="openOpenMvsViewer(<?=$id;?>, <?=(int)$product['id'];?>)">檢視</button>
                      <?php if($isAdminUser): ?>
                        <button class="btn btn-xs btn-danger" type="button" onclick="deleteOpenMvsProduct(this, <?=(int)$product['id'];?>)">刪除</button>
                      <?php endif; ?>
                    <?php elseif($status === '2'): ?>
                      <span class="ovm-muted">找不到 model.glb</span>
                    <?php elseif($status === '3'): ?>
                      <span class="ovm-muted">失敗<?=($message !== '' ? ' · ' . htmlspecialchars(ovm_short_failure_reason($message), ENT_QUOTES) : '');?></span>
                      <?php if($isAdminUser): ?>
                        <button class="btn btn-xs btn-warning" type="button" onclick="createOpenMvsProduct(this, <?=$id;?>, <?=$size;?>)">重產</button>
                      <?php endif; ?>
                    <?php else: ?>
                      <span class="ovm-muted"><?=htmlspecialchars(ovm_product_status_text($status), ENT_QUOTES);?></span>
                    <?php endif; ?>
                  </div>
              <?php endforeach; ?>
            </div>
          <?php endif;
          return trim(ob_get_clean());
      }
  }

  if(!function_exists('ovm_job_standard_artifact_links')){
      function ovm_job_standard_artifact_links($id){
          $id = (int)$id;
          if($id <= 0) return [];
          $items = [
              '引擎合約' => "uploads/{$id}/engine_contract.json",
              '驗證報告' => "uploads/{$id}/validation/validation_report.json",
              '交付清單' => "uploads/{$id}/delivery_manifest.json",
              '失敗摘要' => "uploads/{$id}/failure_summary.json",
          ];
          foreach($items as $label => $url){
              if(!is_file(__DIR__ . "/{$url}")) unset($items[$label]);
          }
          return $items;
      }
  }

  if(!function_exists('ovm_job_actions_cell_html')){
      function ovm_job_actions_cell_html($row){
          $id = (int)($row['id'] ?? 0);
          $glb = ovm_job_glb_path($id);
          $jobStatus = (string)($row['status'] ?? '');
          $isReady = $jobStatus === '2';
          $hasGlb = $isReady && is_file(__DIR__ . "/{$glb}");
          $shortReason = ovm_short_failure_reason($row['reason'] ?? '');
          $isAdminUser = !empty($_SESSION["login_user"]);
          ob_start();
          $hasAction = false;
          if($hasGlb):
              $hasAction = true; ?>
              <button class="btn btn-xs btn-success" type="button" onclick="openOpenMvsViewer(<?=$id;?>)">檢視</button>
          <?php endif;
	          if($shortReason !== ''):
	              $hasAction = true; ?>
	              <button class="btn btn-xs btn-default" type="button" onclick="openReasonDialog(<?=$id;?>)">原因</button>
	          <?php endif;
	          if($isAdminUser && trim((string)($row['diagnostic_summary'] ?? '')) !== ''):
	              $hasAction = true; ?>
	              <button class="btn btn-xs btn-default" type="button" onclick="openDiagnosticsDialog(<?=$id;?>)">診斷</button>
	          <?php endif;
	          if($isAdminUser && in_array($jobStatus, ['2','3'], true)):
	              $hasAction = true; ?>
	              <button class="btn btn-xs btn-warning" type="button" onclick="retryOpenMvsJob(this, <?=$id;?>)">重轉</button>
          <?php endif;
          if($isAdminUser && $jobStatus === '4'):
              $hasAction = true; ?>
              <button class="btn btn-xs btn-primary" type="button" onclick="startOpenMvsJob(this, <?=$id;?>)">啟動</button>
          <?php endif;
          if($isAdminUser && $jobStatus === '1'):
              $hasAction = true; ?>
              <button class="btn btn-xs btn-warning" type="button" onclick="pauseOpenMvsJob(this, <?=$id;?>)">暫停</button>
          <?php endif;
          if($isAdminUser && in_array($jobStatus, ['0','4','2','3'], true)):
              $hasAction = true; ?>
              <button class="btn btn-xs btn-danger" type="button" onclick="deleteOpenMvsJob(this, <?=$id;?>)">刪除</button>
          <?php endif;
          if(!$hasAction): ?>
              <span class="ovm-muted">-</span>
          <?php endif;
          return trim(ob_get_clean());
      }
  }

  if(!function_exists('ovm_job_delta_payload')){
      function ovm_job_delta_payload($rows){
          $estimateSeconds = ovm_average_completed_duration($rows);
          $hasActiveJobs = false;
          $failureReasons = [];
          $payloadRows = [];

          foreach($rows as $row){
              $id = (int)($row['id'] ?? 0);
              $active = in_array((string)($row['status'] ?? ''), ['0','1'], true) || ovm_job_has_active_products($id);
              if($active) $hasActiveJobs = true;

              $fullReason = trim((string)($row['reason'] ?? ''));
              if($fullReason !== '') $failureReasons[(string)$id] = ovm_json_safe_text($fullReason);

              $payloadRows[] = [
                  'id' => $id,
	                  'active' => $active,
	                  'thumb_html' => ovm_job_thumbnail_cell_html($row),
	                  'status_html' => ovm_job_status_cell_html($row),
	                  'quality_html' => ovm_job_quality_cell_html($row),
	                  'timing_html' => ovm_job_timing_cell_html($row, $estimateSeconds),
	                  'frames_html' => ovm_job_frames_cell_html($row),
	                  'artifacts_html' => ovm_job_artifacts_cell_html($row),
                  'products_html' => ovm_job_products_cell_html($row),
                  'actions_html' => ovm_job_actions_cell_html($row),
              ];
          }

          return [
              'estimate_seconds' => $estimateSeconds,
              'has_active_jobs' => $hasActiveJobs,
              'failure_reasons' => $failureReasons,
              'rows' => $payloadRows,
          ];
      }
  }
?>
