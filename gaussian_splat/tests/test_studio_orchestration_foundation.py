from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STUDIO = ROOT.parent / "studio"


def test_studio_migration_defines_project_job_and_engine_run_tables():
    text = (STUDIO / "migrate.php").read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS `studio_projects`" in text
    assert "CREATE TABLE IF NOT EXISTS `studio_jobs`" in text
    assert "`preflight_report_path`" in text
    assert "`attempts` int(11) NOT NULL DEFAULT 0" in text
    assert "`last_error` text DEFAULT NULL" in text
    assert "`worker_log_path` varchar(1024) DEFAULT NULL" in text
    assert "`last_heartbeat_at` datetime DEFAULT NULL" in text
    assert "ADD COLUMN" in text
    assert "CREATE TABLE IF NOT EXISTS `studio_engine_runs`" in text
    for field in (
        "`engine_name`",
        "`mode`",
        "`role`",
        "`status`",
        "`input_path`",
        "`output_contract_path`",
        "`artifact_manifest_path`",
        "`error_summary_path`",
        "`external_table`",
        "`external_job_id`",
        "`attempts`",
        "`last_error`",
        "`last_heartbeat_at`",
    ):
        assert field in text
    assert "studio_migrate_add_column(" in text


def test_studio_adapter_queues_existing_engines_without_direct_worker_calls():
    text = (STUDIO / "studio_lib.php").read_text(encoding="utf-8")

    for function in (
        "function studio_create_project",
        "function studio_create_job",
        "function studio_create_qa_job",
        "function studio_create_premium_job",
        "function studio_write_preflight_report",
        "function studio_preflight_report",
        "function studio_preflight_gate_decision",
        "function studio_job_detail",
        "function studio_enqueue_engine_run",
        "function studio_refresh_engine_run_status",
    ):
        assert function in text
    assert "openmvs_jobs" in text
    assert "gaussian_splat_jobs" in text
    assert "qa_validation_report" in text
    assert "preflight_report_path" in text
    assert "preflight_report" in text
    assert "preflight_report_error" in text
    assert "gate_decision" in text
    assert "malformed preflight_report.json" in text
    assert "capture_analyzer.py" in text
    assert "studio/jobs/\" . (int)$studioJobId . \"/preflight/preflight_report.json" in text
    for field in (
        "schema_version",
        "capture_summary",
        "confidence_score",
        "confidence_level",
        "blocking_issues",
        "warnings",
        "recommendations",
        "engine_recommendations",
        "generated_at",
    ):
        assert field in text
    for field in (
        "not_recommended",
        "recommended_modes",
        "discouraged_modes",
        "severity",
        "unavailable",
        "malformed",
    ):
        assert field in text
    assert "json_decode" in text
    assert "'web_dir' => 'openmvs'" in text
    assert "'web_dir' => 'gaussian_splat'" in text
    assert '"/uploads/"' in text
    assert "run_openmvs_pipeline.sh" not in text
    assert "run_mvp_pipeline.sh" not in text


def test_studio_preflight_is_written_for_qa_and_premium_create_paths():
    text = (STUDIO / "studio_lib.php").read_text(encoding="utf-8")

    assert "$preflightPath = studio_write_preflight_report($jobId" in text
    assert "'preflight_report_path' => $preflightPath" in text
    assert text.count("studio_write_preflight_report($jobId") >= 2


def test_studio_qa_trigger_api_creates_pending_job_without_running_workers():
    text = (STUDIO / "api.php").read_text(encoding="utf-8")

    assert "case 'create_qa_job':" in text
    assert "case 'create_premium_job':" in text
    assert "case 'evidence_query':" in text
    assert "case 'job_detail':" in text
    assert "studio_create_qa_job" in text
    assert "studio_create_premium_job" in text
    assert "studio_evidence_query" in text
    assert "studio_job_detail" in text
    assert "worker_command" in text
    assert "preflight_report_path" in text
    assert "qa_worker.php" in text
    assert "premium_worker.php" in text
    assert "--job-id=" in text
    for forbidden in ("studio_process_qa_job", "studio_process_premium_job", "run_openmvs_pipeline.sh", "run_mvp_pipeline.sh"):
        assert forbidden not in text


def test_studio_evidence_query_api_uses_safe_manifest_and_tile_helpers():
    text = (STUDIO / "studio_lib.php").read_text(encoding="utf-8")
    api = (STUDIO / "api.php").read_text(encoding="utf-8")

    assert "function studio_safe_json_path" in text
    assert "function studio_json_file" in text
    assert "function studio_evidence_manifest_path" in text
    assert "function studio_spatial_index_path" in text
    assert "function studio_spatial_tile_for_position" in text
    assert "function studio_evidence_query" in text
    assert "studio_job_detail($studioJobId)" in text
    assert "delivery_manifest_path" in text
    assert "evidence_manifest_path" in text
    assert "spatial_index_path" in text
    assert "coverage_score" in text
    assert "visible_camera_ids" in text
    assert "sample_sparse_points" in text
    assert "realpath" in text
    assert "studio_3d_root()" in text
    assert "path outside allowed root" in text
    assert "json file not found" in text
    assert "malformed json" in text
    assert "picked position required" in text
    assert "delivery_manifest_path not available" in text
    assert "evidence_manifest_path not available" in text
    assert "spatial_index_path not available" in text
    assert "no evidence for picked area" in text
    assert "pathinfo($real, PATHINFO_EXTENSION)" in text
    assert "$sampleLimit = 32" in text
    assert "array_slice" in text
    assert "catch(Throwable $e)" in api
    assert "studio_api_json(['status'=>'NO', 'reason'=>$e->getMessage()])" in api


def test_studio_qa_trigger_cli_creates_pending_job_without_running_workers():
    text = (STUDIO / "create_qa_job.php").read_text(encoding="utf-8")

    assert "studio_create_qa_job" in text
    assert "studio_job_detail" in text
    assert "--title" in text
    assert "--input" in text
    assert "studio_job_id" in text
    assert "preflight_report_path" in text
    for forbidden in ("studio_process_qa_job", "qa_worker.php", "run_openmvs_pipeline.sh", "run_mvp_pipeline.sh"):
        assert forbidden not in text


def test_studio_premium_trigger_cli_creates_pending_job_without_running_workers():
    text = (STUDIO / "create_premium_job.php").read_text(encoding="utf-8")

    assert "studio_create_premium_job" in text
    assert "studio_job_detail" in text
    assert "--title" in text
    assert "--input" in text
    assert "--source-type" in text
    assert "studio_job_id" in text
    assert "preflight_report_path" in text
    assert "premium_worker.php" in text
    for forbidden in ("studio_process_premium_job", "premium_worker.php --job-id", "run_openmvs_pipeline.sh", "run_mvp_pipeline.sh"):
        assert forbidden not in text


def test_studio_project_mode_surface_uses_api_and_shows_job_detail_sections():
    text = (STUDIO / "index.php").read_text(encoding="utf-8")
    css = (STUDIO / "assets" / "studio.css").read_text(encoding="utf-8")

    assert 'require "{$base_dir}/inc/checkpassword.php";' in text
    assert '<link rel="stylesheet" href="assets/studio.css">' in text
    assert "Photogrammetry Studio" in text
    assert 'class="studio-shell"' in text
    assert 'class="studio-header"' in text
    assert 'class="summary-grid"' in text
    assert 'class="studio-toolbar"' in text
    assert 'class="section-card"' in text
    assert 'function chip' in text
    assert "Recent Jobs" in text
    assert "近期任務" in text
    assert "ID" in text
    assert "Title / Input" in text
    assert "標題 / 輸入" in text
    assert "Mode" in text
    assert "模式" in text
    assert "Status" in text
    assert "狀態" in text
    assert "Confidence" in text
    assert "信心" in text
    assert "Gate" in text
    assert "閘門" in text
    assert "Delivery" in text
    assert "交付" in text
    assert "Updated" in text
    assert "更新時間" in text
    assert "Actions" in text
    assert "操作" in text
    assert "job-list-table" in text
    assert "job-list-empty" in text
    assert "studio_recent_jobs" in text
    assert "studio_list_preflight" in text
    assert "studio_list_delivery_status" in text
    assert "studio_list_gate_decision" in text
    assert "Detail" in text
    assert "明細" in text
    assert "Viewer" in text
    assert "檢視" in text
    assert "Manifest" in text
    assert "清單" in text
    assert "unavailable" in text
    assert "is-disabled" in text
    assert "api.php?mode=create_qa_job" in text
    assert "api.php?mode=create_premium_job" in text
    assert "api.php?mode=job_detail" in text
    assert 'name="mode"' in text
    assert 'value="qa"' in text
    assert 'value="premium"' in text
    assert "createMode" in text
    assert "createEndpoint" in text
    assert "next_worker" in text
    assert "worker_command" in text
    assert "studio_job_id" in text
    assert "engine_runs" in text
    assert "Job Summary" in text
    assert "任務摘要" in text
    assert "Preflight" in text
    assert "前置檢查" in text
    assert "preflight_report_path" in text
    assert "preflight_report" in text
    assert "preflight_report_error" in text
    assert "confidence_score" in text
    assert "confidence_level" in text
    assert "blocking_issues" in text
    assert "warnings" in text
    assert "recommendations" in text
    assert "engine_recommendations" in text
    assert "Gate Decision" in text
    assert "閘門判斷" in text
    assert "gate_decision" in text
    assert "function gateDecisionSummary" in text
    assert "chip(\"gate\"" in text
    assert "recommended_modes" in text
    assert "discouraged_modes" in text
    assert "not_recommended" in text
    assert "unavailable" in text
    assert "preflight_report.json" in text
    assert "not available" in text
    assert "malformed preflight_report.json" in text
    assert "malformed evidence_manifest.json" in text
    assert "malformed delivery_manifest.json" in text
    assert "function preflightSummary" in text
    assert "function listText" in text
    assert "Validation" in text
    assert "驗證摘要" in text
    assert "Delivery Manifest" in text
    assert "交付清單" in text
    assert "Evidence / Viewer Links" in text
    assert "證據 / 檢視連結" in text
    assert "delivery_manifest_path" in text
    assert "schema_version" in text
    assert "generated_at" in text
    assert "delivery_tracks" in text
    assert "primary_artifact" in text
    assert "camera layer" in text
    assert "spatial index" in text
    assert "sparse LOD" in text
    assert "viewer_compare_splat_mesh.html?studio_job_id=" in text
    assert "Compare Viewer" in text
    assert "比對檢視" in text
    assert "mesh viewer" in text
    assert "Mesh 檢視" in text
    assert "function pathDetails" in text
    assert "function pathCell" in text
    assert "function deliveryTrackRows" in text
    assert "function deliveryManifestDetail" in text
    assert "function loadDeliveryManifestDetail" in text
    assert "function evidenceLinksSummary" in text
    assert "created_at" in text
    assert "updated_at" in text
    assert "attempts" in text
    assert "last_heartbeat_at" in text
    assert "last_error" in text
    assert "worker_log_path" in text
    assert "input_path" in text
    assert "error_summary_path" in text
    assert "capture_issue" in text
    assert "mesh_issue" in text
    assert "splat_issue" in text
    assert "conclusion" in text
    assert "recommendation" in text
    assert "進階設定" in text
    assert "預設引擎" in text
    assert "診斷引擎" in text
    assert "delivery_candidate" in text
    assert "delivery_capable" in text
    assert "diagnostic" in text
    assert "role-chip" in text
    assert "mode-chip" in text
    assert "status-chip" in text
    assert "confidence-chip" in text
    assert "qa_validation_report.json" in text
    assert "OpenMVS" in text
    assert "Gaussian" in text
    assert "Premium" in text
    for css_token in (
        ":root",
        "--bg",
        "--panel",
        "--border",
        "--text",
        "--muted",
        "--success",
        "--warning",
        "--danger",
        "--info",
        ".studio-shell",
        ".studio-header",
        ".summary-grid",
        ".studio-toolbar",
        ".section-card",
        ".status-chip",
        ".mode-chip",
        ".role-chip",
        ".confidence-chip",
        ".quality-badge",
        ".action-button",
        ".alert-box",
        ".job-list-table",
        ".is-disabled",
        ".detail-card",
        ".engine-run-grid",
        ".path-details",
    ):
        assert css_token in css
    for forbidden in ("studio_process_qa_job", "studio_process_premium_job", "qa_worker.php", "premium_worker.php --job-id", "mode=list_jobs"):
        assert forbidden not in text


def test_studio_delivery_page_reads_manifest_without_exposing_internal_paths():
    text = (STUDIO / "delivery.php").read_text(encoding="utf-8")

    assert 'require "{$base_dir}/inc/checkpassword.php";' in text
    assert "studio_job_detail" in text
    assert "delivery_manifest_path" in text
    assert "Delivery Page MVP" in text
    assert "交付頁" in text
    assert "交付狀態" in text
    assert "信心" in text
    assert "閘門判斷" in text
    assert "驗證摘要" in text
    assert "交付軌道" in text
    assert "檢視成果" in text
    assert "證據狀態" in text
    assert "Compare Viewer" in text
    assert "Mesh Viewer" in text
    assert "Splat Viewer" in text
    assert "viewer_compare_splat_mesh.html?studio_job_id=" in text
    assert "viewer_mesh.html?studio_job_id=" in text
    assert "viewer_splat.php?studio_job_id=" in text
    assert "diagnostic only" in text
    assert "delivery capable" in text
    assert "交付清單尚未就緒" in text
    assert "交付清單 JSON 格式錯誤" in text
    assert "不顯示 raw worker log / internal absolute path" in text
    assert "source_path" not in text
    assert "engine_runs" not in text
    assert "output_contract_path" not in text
    assert "artifact_manifest_path" not in text
    assert "error_summary_path" not in text
    assert "studio_3d_root()" not in text
    assert "/var/www" not in text
    for forbidden in ("studio_process_qa_job", "studio_process_premium_job", "CREATE TABLE", "ALTER TABLE", "delivery_manifest.schema"):
        assert forbidden not in text


def test_studio_worker_log_page_is_protected_tail_viewer():
    text = (STUDIO / "log.php").read_text(encoding="utf-8")
    index = (STUDIO / "index.php").read_text(encoding="utf-8")

    assert 'require "{$base_dir}/inc/checkpassword.php";' in text
    assert "studio_job_detail" in text
    assert "worker_log_path" in text
    assert "realpath" in text
    assert "pathinfo($full, PATHINFO_EXTENSION) !== 'log'" in text
    assert "array_slice($lines, -200)" in text
    assert "最近 200 行" in text
    assert "log.php?job_id=" in index
    assert "查看 log" in index
    assert "/var/www" not in text
    for forbidden in ("studio_process_qa_job", "studio_process_premium_job", "unlink(", "DELETE FROM"):
        assert forbidden not in text


def test_studio_crontab_runs_qa_worker_with_lock_only():
    runner = (STUDIO / "crontab" / "1_run.php").read_text(encoding="utf-8")
    shell = (STUDIO / "crontab" / "1min.sh").read_text(encoding="utf-8")

    assert "flock" in runner
    assert "1_run.lock" in runner
    assert "qa_worker.php" in runner
    assert "--limit=5" in runner
    assert "php 1_run.php" in shell
    for forbidden in ("run_openmvs_pipeline.sh", "run_mvp_pipeline.sh", "studio_process_qa_job"):
        assert forbidden not in runner
        assert forbidden not in shell


def test_studio_qa_worker_aggregates_engine_runs_without_direct_worker_calls():
    text = (STUDIO / "qa_worker.php").read_text(encoding="utf-8")
    lib = (STUDIO / "studio_lib.php").read_text(encoding="utf-8")

    assert "studio_enqueue_engine_run" in text
    assert "'openmvs'" in text
    assert "'delivery_candidate'" in text
    assert "'gaussian_splat'" in text
    assert "'diagnostic'" in text
    assert "studio_refresh_engine_run_status" in text
    assert "qa_validation_report.json" in text
    assert "studio_write_delivery_manifest" in text
    assert "delivery_manifest.json" in lib
    assert "function studio_manifest_path" in lib
    assert "\"../../../\"" in lib
    assert "delivery_manifest_path" in text
    assert "delivery_tracks" in lib
    assert "capture_issue" in text
    assert "mesh_issue" in text
    assert "splat_issue" in text
    assert "partial_failed" in text
    assert "studio_worker_log(" in text
    assert "'qa_worker'" in text
    assert "attempts" in text
    assert "'worker_log_path' =>" in text
    assert "'last_heartbeat_at' =>" in text
    assert "'last_error' =>" in text
    assert "run_openmvs_pipeline.sh" not in text
    assert "run_mvp_pipeline.sh" not in text


def test_studio_premium_worker_orchestrates_delivery_capable_engine_runs_only():
    text = (STUDIO / "premium_worker.php").read_text(encoding="utf-8")
    lib = (STUDIO / "studio_lib.php").read_text(encoding="utf-8")

    assert "studio_enqueue_engine_run" in text
    assert "'openmvs'" in text
    assert "'gaussian_splat'" in text
    assert "'delivery_capable'" in text
    assert "'premium'" in text
    assert "studio_refresh_engine_run_status" in text
    assert "studio_process_premium_job" in text
    assert "studio_premium_jobs" in text
    assert "partial_failed" in text
    assert "studio_write_delivery_manifest" in text
    assert "delivery_manifest_path" in text
    assert "delivery_manifest.json" in lib
    assert "function studio_delivery_artifact_from_manifest" in lib
    assert "primaryArtifact" in lib
    assert "delivery_tracks" in lib
    assert "artifact_manifest_path" in lib
    assert "'mode' => (string)($job['pipeline_mode'] ?? 'qa')" in lib
    assert "'delivery_capable' => $role !== 'diagnostic'" in lib
    assert "'qa_report_path' => $qaReportPath" in lib
    assert "studio_worker_log(" in text
    assert "'premium_worker'" in text
    assert "attempts" in text
    assert "'worker_log_path' =>" in text
    assert "'last_heartbeat_at' =>" in text
    assert "'last_error' =>" in text
    assert "qa_validation_report" not in text
    for forbidden in ("run_openmvs_pipeline.sh", "run_mvp_pipeline.sh", "build_compare_bundle.py"):
        assert forbidden not in text


def test_studio_stuck_recovery_cli_is_dry_run_and_does_not_run_workers():
    text = (STUDIO / "recover_stuck_jobs.php").read_text(encoding="utf-8")

    assert "CLI only" in text
    assert "--apply" in text
    assert "--older-than-minutes" in text
    assert "--mode" in text
    assert "--limit" in text
    assert "--include-failed" in text
    assert "Dry-run only" in text
    assert "BLOCKED-RETRY" in text
    assert "terminal engine_runs need replacement policy" in text
    assert "last_heartbeat_at" in text
    assert "work_st_datetime" in text
    assert "status`=1" in text
    assert "status` IN (3,5)" in text
    assert "'status' => 0" in text
    assert "manual_recovery: stuck" in text
    assert "studio_worker_log(" in text
    for forbidden in (
        "studio_process_qa_job",
        "studio_process_premium_job",
        "run_openmvs_pipeline.sh",
        "run_mvp_pipeline.sh",
        "unlink(",
        "rm -rf",
        "DELETE FROM",
    ):
        assert forbidden not in text


def test_studio_retention_audit_reports_without_deleting_artifacts():
    text = (STUDIO / "retention_audit.php").read_text(encoding="utf-8")

    assert "CLI only" in text
    assert "--older-than-days" in text
    assert "--limit" in text
    assert "retention_audit" in text
    assert "json_encode" in text
    assert "studio_jobs" in text
    assert "studio_engine_runs" in text
    assert "candidate_count" in text
    assert "dry_run_only" in text
    assert "artifact cleanup requires explicit policy" in text
    for forbidden in ("--apply", "unlink(", "rmdir(", "DELETE FROM", "DROP TABLE", "rm -rf"):
        assert forbidden not in text
