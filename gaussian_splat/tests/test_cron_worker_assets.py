from pathlib import Path
import stat


ROOT = Path(__file__).resolve().parents[1]


def test_cron_helper_defines_logging_abort_and_failure_helpers():
    text = (ROOT / "crontab" / "inc" / "function.php").read_text()

    assert "function gs_run_cmd" in text
    assert "$timeout = max(1, (int)$timeout);" in text
    assert "proc_open" in text
    assert "0 => ['file', '/dev/null', 'r']" in text
    assert "proc_terminate" in text
    assert "pkill -TERM -P" in text
    assert "function gs_is_abort_requested" in text
    assert "is_callable($abortChecker)" in text
    assert "is_callable($lineCallback)" in text
    assert "function gs_append_log" in text
    assert "function gs_append_log_block" in text
    assert "RIGHT(CONCAT(IFNULL(`process_log`,''), ?), 60000)" in text
    assert "function gs_check_abort" in text
    assert "SELECT `status` FROM `gaussian_splat_jobs` WHERE `id`=? LIMIT 1" in text
    assert ".abort" in text
    assert "使用者中止" in text
    assert "function gs_fail" in text
    assert "'status'=>3" in text
    assert "function gs_parse_timing_stage_line" in text
    assert "function gs_update_timing_stage_from_line" in text
    assert "current_stage" in text
    assert "current_stage_label" in text
    assert "[timing] START" in text
    assert "function gs_seconds_between" in text
    assert "function gs_video_duration_seconds" in text
    assert "function gs_env_prefix" in text
    assert "ffprobe -v error -show_entries format=duration" in text


def test_cron_runner_claims_one_pending_job_and_runs_pipeline():
    text = (ROOT / "crontab" / "1_run.php").read_text()

    assert 'require __DIR__ . "/../../inc/config.php";' in text
    assert 'require __DIR__ . "/inc/function.php";' in text
    assert "1_run.lock" in text
    assert "flock($lockFp, LOCK_EX | LOCK_NB)" in text
    assert ".photogrammetry_worker.lock" in text
    assert "flock($globalLockFp, LOCK_EX | LOCK_NB)" in text
    assert "function gs_active_photogrammetry_job_exists" in text
    assert "SELECT `id` FROM `openmvs_jobs` WHERE `del`='0' AND `status`='1' LIMIT 1" in text
    assert "SELECT `id` FROM `gaussian_splat_jobs` WHERE `del`='0' AND `status`='1' LIMIT 1" in text
    assert "已有 Photogrammetry 轉檔程序在執行中" in text
    assert "$activeJobId" in text
    assert "worker exited before completion" in text
    assert "SELECT * FROM `gaussian_splat_jobs` WHERE `del`='0' AND `status`='0' ORDER BY `id` ASC LIMIT 1" in text
    assert "status'=>1" in text
    assert "input/input.{$kind}" in text
    assert "Gaussian worker accepts mp4 or zip input" in text
    assert "function gs_image_dir_count" in text
    assert "if($kind === 'zip')" in text
    assert '$pipelineInput = "{$jobDir}/images";' in text
    assert '$confidenceInput = $pipelineInput;' in text
    assert "scripts/confidence_gate.py" in text
    assert "confidence_gate.json" in text
    assert "confidence_effective_decision" in text
    assert "confidence_risk_count" in text
    assert "confidence_recommendation_count" in text
    assert "confidence_needs_override" in text
    assert "confidence_override_status" in text
    assert "confidence_updated_at" in text
    assert "json_encode($gate, JSON_UNESCAPED_UNICODE)" not in text
    assert "run_with_override" in text
    assert "'status'=>5" in text
    assert "--override" in text
    assert "--override-reason" in text
    assert text.index("scripts/confidence_gate.py") < text.index("scripts/run_mvp_pipeline.sh")
    assert "$originLon = is_numeric($row['lon'] ?? null) ? (float)$row['lon'] : 120.61022;" in text
    assert "$originLat = is_numeric($row['lat'] ?? null) ? (float)$row['lat'] : 24.110946;" in text
    assert "$originAlt = is_numeric($row['alt'] ?? null) ? (float)$row['alt'] : 0.0;" in text
    assert "scripts/run_mvp_pipeline.sh" in text
    assert "escapeshellarg($pipelineInput)" in text
    assert "escapeshellarg($jobDir)" in text
    assert "escapeshellarg((string)$originLon)" in text
    assert "escapeshellarg((string)$originLat)" in text
    assert "escapeshellarg((string)$originAlt)" in text
    assert "gs_run_cmd($cmd, $out, 86400, function() use($id)" in text
    assert "process.log" in text
    assert 'file_put_contents($logPath, $line . "\\n", FILE_APPEND)' in text
    assert "gs_append_log_block($id, $line)" in text
    assert "gs_abort($id)" in text
    assert "qa_report.json" in text
    assert "if($kind === 'mp4')" in text
    assert "$durationSeconds = gs_video_duration_seconds($input);" in text
    assert "$env['GS_FRAME_MIN_FRAMES'] = '1';" in text
    assert "$env['GS_FRAME_TARGET_FPS'] = '12';" in text
    assert "$pipelineMode = strtolower((string)($row['pipeline_mode'] ?? 'fast'));" in text
    assert "$env['GS_PIPELINE_MODE'] = $pipelineMode;" in text
    assert "短片實驗模式" in text
    assert "$cmd = gs_env_prefix($env) . escapeshellarg" in text
    assert "timing_report.json" in text
    assert "gs_seconds_between($row['c_datetime'] ?? null, $workStart)" in text
    assert "gs_seconds_between($workStart, $workEnd)" in text
    assert "gs_seconds_between($row['c_datetime'] ?? null, $workEnd)" in text
    assert "'current_stage'=>null" in text
    assert "'current_stage_label'=>'完成'" in text
    assert "'duration_seconds'=>$durationSeconds" in text
    assert "'queue_seconds'=>$queueSeconds" in text
    assert "'process_seconds'=>$processSeconds" in text
    assert "frame_count" in text
    assert "registered_frame_count" in text
    assert "splat_file_size_mb" in text
    assert "$upd['status'] = 2;" in text
    assert text.index('gs_append_log($id, "Gaussian Splat pipeline 完成")') < text.index("$upd['status'] = 2;")
    assert 'echo "Done.\\n";' in text


def test_cron_runner_caps_gaussian_training_by_pipeline_mode_and_logs_it():
    text = (ROOT / "crontab" / "1_run.php").read_text()

    assert "function gs_training_cap_for_mode" in text
    assert "'fast' => ['GS_FAST_TRAIN_MAX_ITERATIONS', '10000']" in text
    assert "'qa' => ['GS_QA_TRAIN_MAX_ITERATIONS', '30000']" in text
    assert "'premium' => ['GS_PREMIUM_TRAIN_MAX_ITERATIONS', '60000']" in text
    assert "GS_FAST_TRAIN_MAX_ITERATIONS" in text
    assert "GS_QA_TRAIN_MAX_ITERATIONS" in text
    assert "GS_PREMIUM_TRAIN_MAX_ITERATIONS" in text
    assert "$trainingCap = gs_training_cap_for_mode($pipelineMode);" in text
    assert "$env['GS_TRAIN_MAX_ITERATIONS'] = $trainingCap;" in text
    assert "Gaussian {$pipelineMode} training cap: GS_TRAIN_MAX_ITERATIONS={$trainingCap}" in text
    assert "QA diagnostic training cap" not in text
    assert "invalid {$envName}: {$cap}" in text


def test_cron_runner_passes_optional_sfm_matcher_to_pipeline():
    text = (ROOT / "crontab" / "1_run.php").read_text()

    assert "function gs_sfm_matcher_from_env" in text
    assert "function gs_sfm_matcher_for_job" in text
    assert "input/sfm_matcher.txt" in text
    assert "GS_SFM_MATCHER" in text
    assert "['exhaustive','sequential','hloc_lightglue']" in text
    assert "$sfmMatcher = gs_sfm_matcher_for_job($jobDir);" in text
    assert "$env['GS_SFM_MATCHER'] = $sfmMatcher;" in text
    assert "GS_HLOC_MATCH_WINDOW" in text
    assert "$env['GS_HLOC_MATCH_WINDOW'] = $hlocMatchWindow;" in text
    assert "Gaussian SfM matcher: {$sfmMatcher}" in text


def test_one_minute_wrapper_is_executable_and_runs_php_runner():
    path = ROOT / "crontab" / "1min.sh"
    text = path.read_text()

    assert text.startswith("#!/usr/bin/env bash\n")
    assert "set -euo pipefail" in text
    assert 'cd "$(dirname "$0")"' in text
    assert "php 1_run.php" in text
    assert path.stat().st_mode & stat.S_IXUSR


def test_gitignore_excludes_runtime_cron_locks():
    text = (ROOT / ".gitignore").read_text()

    assert "crontab/*.lock" in text
