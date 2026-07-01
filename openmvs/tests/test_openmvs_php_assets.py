from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text()


def test_migration_defines_openmvs_job_schema():
    text = read("migrate.php")

    assert 'require __DIR__ . "/../inc/config.php";' in text
    assert "CREATE TABLE IF NOT EXISTS `openmvs_jobs`" in text
    assert "SHOW COLUMNS FROM `openmvs_jobs`" in text
    assert "ALTER TABLE `openmvs_jobs` ADD COLUMN" in text
    assert "openmvs_jobs migration complete" in text

    for column in [
        "id",
        "title",
        "orin_filename",
        "c_datetime",
        "IP",
        "status",
        "reason",
        "work_st_datetime",
        "work_et_datetime",
        "lon",
        "lat",
        "alt",
        "heading",
        "pitch",
        "roll",
        "scale",
        "kind",
        "email",
        "del",
        "process_log",
        "current_stage",
        "current_stage_label",
        "duration_seconds",
        "queue_seconds",
        "process_seconds",
        "input_frame_count",
        "registered_frame_count",
        "glb_file_size_mb",
        "mesh_file_size_mb",
        "texture_black_pixel_ratio",
        "texture_white_empty_pixel_ratio",
        "texture_width",
        "texture_height",
        "texture_patch_count",
        "mask_mode",
        "quality_preset",
        "capture_source_type",
        "capture_preset",
        "capture_quality_score",
        "capture_quality_grade",
        "capture_quality_decision",
        "capture_mask_status",
        "capture_frame_count",
        "capture_selected_frame_count",
        "capture_aligned_camera_count",
        "capture_registered_ratio",
        "capture_warning_count",
        "capture_updated_at",
    ]:
        assert f"`{column}`" in text


def test_migration_defines_openmvs_products_schema():
    text = read("migrate.php")

    assert "CREATE TABLE IF NOT EXISTS `openmvs_products`" in text
    assert "openmvs_products table ready" in text
    assert "$productColumns = [" in text
    assert "SHOW COLUMNS FROM `openmvs_products`" in text
    assert "ALTER TABLE `openmvs_products` ADD COLUMN" in text
    for column in [
        "id",
        "job_id",
        "product_type",
        "source_product_id",
        "texture_size",
        "status",
        "file_path",
        "file_size_mb",
        "reason",
        "error_message",
        "process_log",
        "current_stage",
        "createAt",
        "work_st_datetime",
        "work_et_datetime",
        "del",
    ]:
        assert f"`{column}`" in text
    assert "product column `{$name}` already exists" in text
    assert "product column `{$name}` added" in text
    for index in [
        "`idx_job_id` (`job_id`)",
        "`idx_product_type` (`product_type`)",
        "`idx_texture_size` (`texture_size`)",
        "`idx_status` (`status`)",
        "`idx_del` (`del`)",
    ]:
        assert index in text
    assert "$productIndexes = [" in text
    assert "SHOW INDEX FROM `openmvs_products`" in text
    assert "ALTER TABLE `openmvs_products` ADD INDEX `{$name}` {$definition}" in text
    assert "product index `{$name}` already exists" in text
    assert "product index `{$name}` added" in text


def test_job_view_defines_product_helpers():
    text = read("job_view.php")

    assert "function ovm_product_texture_sizes" in text
    assert "return [512, 2048, 4096, 8192]" in text
    assert "function ovm_product_texture_size_valid" in text
    assert "function ovm_product_status_text" in text
    assert "function ovm_product_file_size_mb" in text
    assert "function ovm_products_for_job" in text
    assert "FROM `openmvs_products`" in text
    assert "WHERE `job_id`=? AND `del`='0'" in text
    assert "ORDER BY `product_type`, `texture_size`" in text
    assert "function ovm_job_products_cell_html" in text
    assert "工作完成後可產製 GLB 產品" in text
    assert "createOpenMvsProduct" in text
    assert "deleteOpenMvsProduct" in text
    assert "openOpenMvsViewer(<?=$id;?>, <?=(int)$product['id'];?>)" in text
    assert "尚未產製" in text
    assert "重產" in text
    assert "$message = trim((string)($product['error_message'] ?? ''));" in text
    assert "if($message === '') $message = trim((string)($product['reason'] ?? ''));" in text
    assert "products_html" in text
    assert "ovm_job_has_active_products" in text


def test_api_defines_product_action_foundation():
    text = read("api.php")

    assert "function ovm_product_dir" in text
    assert 'return "uploads/{$jobId}/products/glb_{$textureSize}"' in text
    assert "function ovm_product_model_path" in text
    assert 'model.glb' in text
    assert "function ovm_remove_product_dir_for_row" in text
    assert "function ovm_product_dir_is_safe_for_row" in text
    assert "realpath(__DIR__ . '/uploads')" in text
    assert "case 'product_action':" in text
    assert 'require "{$base_dir}/inc/checkpassword.php";' in text
    assert "action === 'create_glb'" in text
    assert "ovm_product_texture_size_valid" in text
    assert "SELECT `id`,`status`,`del` FROM `openmvs_jobs` WHERE `id`=? LIMIT 1" in text
    assert "LOCK TABLES `openmvs_products` WRITE" in text
    assert "UNLOCK TABLES" in text
    assert "$response = null" in text
    assert "產品佇列鎖定失敗" in text
    assert "ovm_json($response)" in text
    assert "SELECT `id` FROM `openmvs_products` WHERE `job_id`=? AND `product_type`='glb' AND `texture_size`=? AND `del`='0' LIMIT 1" in text
    assert "insertSQL('openmvs_products'" in text
    assert "action === 'delete'" in text
    assert "SELECT * FROM `openmvs_products` WHERE `id`=? AND `del`='0' LIMIT 1" in text
    assert "ovm_remove_product_dir_for_row" in text
    assert "if(!ovm_product_dir_is_safe_for_row($products[0]))" in text
    assert "UPDATE `openmvs_products` SET `del`='1' WHERE `id`=? AND `del`='0' AND `status` IN ('0','2','3','4')" in text
    assert "$deleteStmt->rowCount() <= 0" in text
    assert "產品狀態已變更，請重新整理" in text
    assert "if(!ovm_remove_product_dir_for_row($failed[0]))" in text
    assert "產品目錄不安全，已略過重產" in text
    assert "in_array((string)($products[0]['status'] ?? ''), ['0','2','3','4'], true)" in text
    assert "產製中不能刪除" in text
    assert "AND `status`='3'" in text
    assert "'status'=>0" in text
    assert "'error_message'=>''" in text
    assert "'file_path'=>''" in text
    assert "products/glb_(?:512|2048|4096|8192)/model\\.glb" in text
    assert text.index("if(!ovm_product_dir_is_safe_for_row($products[0]))") < text.index("$deleteStmt = $pdo->prepare")


def test_api_accepts_mp4_and_zip_uploads_and_queues_background_job():
    text = read("api.php")

    assert 'require __DIR__ . "/../inc/config.php";' in text
    assert "case 'upload':" in text
    assert "checkGD" in text
    assert "驗證碼錯誤" in text
    assert "請選擇 MP4 影片或圖片 ZIP" in text
    assert "目前僅支援 MP4 影片或 ZIP 圖片包" in text
    assert "OVM_MIN_VIDEO_SECONDS" in text
    assert "ffprobe" in text
    assert "影片太短" in text
    assert "至少需要 3 秒影片" in text
    assert "ovm_zip_contains_usable_images" in text
    assert "ZIP 內沒有可用圖片" in text
    assert "mask_mode" in text
    assert "ovm_normalize_mask_mode" in text
    assert "quality_preset" in text
    assert "ovm_normalize_quality_preset" in text
    assert "ovm_zip_contains_masks" in text
    assert "ZIP 內沒有 .mask.png" in text
    assert "function ovm_existing_artifact_url" in text
    assert "insertSQL('openmvs_jobs', $m)" in text
    assert '$root = __DIR__ . "/uploads/{$id}"' in text
    assert '$dest = "{$inputDir}/input.{$ext}"' in text
    assert '@file_put_contents("{$inputDir}/pipeline_mode.txt", "openmvs_native\\n")' in text
    assert "move_uploaded_file" in text
    assert "case 'jobs_delta':" in text
    assert "ovm_job_delta_payload($rows)" in text
    assert "engine_contract_url" in text
    assert "validation_report_url" in text
    assert "delivery_manifest_url" in text
    assert "failure_summary_url" in text
    assert "case 'admin_action':" in text
    assert "action === 'retry'" in text
    assert "action === 'abort'" in text
    assert ".abort" in text


def test_index_job_view_and_js_wire_glb_viewer_actions():
    index = read("index.php")
    job_view = read("job_view.php")
    js = read("js/function.js")
    viewer = read("viewer_mesh.php")

    assert "OpenMVS 轉檔" in index
    assert 'accept=".mp4,.zip"' in index
    assert "MP4 影片或圖片 ZIP" in index
    assert "遮罩 / 主體隔離" not in index
    assert 'name="mask_mode"' in index
    assert 'type="hidden" name="mask_mode" id="mask_mode" value="none"' in index
    assert 'value="provided"' not in index
    assert 'value="auto"' not in index
    assert 'name="quality_preset"' in index
    assert 'value="fast"' in index
    assert 'value="normal" selected' in index
    assert 'value="high"' in index
    assert "api.php?mode=upload" in index
    assert "api.php?mode=jobs_delta" in index
    assert "viewer_mesh.php" in index
    assert "ovm-job-list" in index
    assert "ovm-job-card" in index
    assert "ovm-job-card-body" in index
    assert "ovm-job-actions" in index
    assert "ovm-job-empty" in index
    assert 'data-refresh-cell="thumb"' in index
    assert 'data-refresh-cell="status"' in index
    assert 'data-refresh-cell="quality"' in index
    assert 'data-refresh-cell="timing"' in index
    assert 'data-refresh-cell="frames"' in index
    assert 'data-refresh-cell="artifacts"' in index
    assert 'data-refresh-cell="products"' in index
    assert 'data-refresh-cell="actions"' in index
    assert '$include_mode = "easymap7115|threejs155"' in index
    assert 'from "three/addons/loaders/GLTFLoader.js"' in index
    assert "function initOpenMvsThumbs" in index
    assert "saveOpenMvsThumb" in index
    assert "ovm_job_search_form_html" in index
    assert "ovm_job_pagination_html" in index
    assert "ovm_job_list_state(15)" in index

    assert "function ovm_pipeline_stage_map" in job_view
    assert "OVM_LIST_PER_PAGE" in job_view
    assert "function ovm_job_list_state" in job_view
    assert "function ovm_job_search_form_html" in job_view
    assert "function ovm_job_pagination_html" in job_view
    assert "function ovm_job_search_suggestions" in job_view
    assert 'name="q"' in job_view
    assert 'list="ovmJobSearchList"' in job_view
    assert "'prepare_images'" in job_view
    assert "'prepare_masks'" in job_view
    assert "'colmap_mapper'" in job_view
    assert "'openmvs_texture'" in job_view
    assert "ovm_job_glb_path" in job_view
    assert "ovm_job_thumb_cache_url" in job_view
    assert "ovm_job_thumbnail_cell_html" in job_view
    assert "function ovm_job_source_preview_path" in job_view
    assert "ovm-thumb-pair" in job_view
    assert "原始" in job_view
    assert "成果" in job_view
    assert "model-thumb-pending" in job_view
    assert "thumb_html" in job_view
    assert "products_html" in job_view
    assert "openOpenMvsViewer" in job_view
    assert "glb_file_size_mb" in job_view
    assert "texture_black_pixel_ratio" in job_view
    assert "texture_white_empty_pixel_ratio" in job_view
    assert "texture_patch_count" in job_view
    assert "mask_mode" in job_view
    assert "ovm_mask_mode_label($row" not in job_view
    assert "拍攝模式" in job_view
    assert "註冊比例" in job_view
    assert "capture_quality_decision" in job_view
    assert "ovm_contract_summary_lines" in job_view
    assert "ovm_job_validation_summary_html" in job_view
    assert "ovm_job_failure_summary_html" in job_view
    assert "Validation " in job_view
    assert "Failure " in job_view
    assert "建議補拍" in job_view
    assert "ovm_job_standard_artifact_links" in job_view
    assert "engine_contract.json" in job_view
    assert "validation/validation_report.json" in job_view
    assert "delivery_manifest.json" in job_view
    assert "failure_summary.json" in job_view
    assert "引擎合約" in job_view
    assert "驗證報告" in job_view
    assert "交付清單" in job_view
    assert "失敗摘要" in job_view

    assert "最近 50 筆" not in index
    assert "LIMIT 50" not in index

    assert "function openOpenMvsViewer" in js
    assert "product_id" in js
    assert "function createOpenMvsProduct" in js
    assert "function deleteOpenMvsProduct" in js
    assert "api.php?mode=product_action" in js
    assert 'viewer_mesh.php?id=' in js
    assert 'viewer_mesh.html?src=' not in js
    assert "filter_input(INPUT_GET, 'id'" in viewer
    assert "filter_input(INPUT_GET, 'product_id'" in viewer
    assert "SELECT * FROM `openmvs_products` WHERE `id`=? AND `job_id`=? AND `del`='0' LIMIT 1" in viewer
    assert "GLB {$viewerProductSize}" in viewer
    assert "VIEWER_RESOLVED_SRC" in viewer
    assert "api.php?mode=getGLB&uuid=" in viewer
    assert "VIEWER_FILE_SIZE_BYTES" in viewer
    assert "filesize($viewerPath)" in viewer
    assert "getimagesize" in viewer
    assert "VIEWER_PORTRAIT_CAPTURE" in viewer
    assert "case 'getGLB':" in read("api.php")
    assert "openmvs_glb_tokens" in read("api.php")
    assert "cacheKey" in viewer
    assert "setURLModifier" in viewer
    assert "modelResourceBase" in viewer
    assert "function resolveModelResourceUrl" in viewer
    assert "loader.setResourcePath(modelResourceBase)" in viewer
    assert "ovm_cache=" in viewer
    assert "下載 GLB" in viewer
    assert "載入 GLB" in viewer
    assert "ovm-load-progress" in viewer
    assert "function downloadGlb" in viewer
    assert "new XMLHttpRequest()" in viewer
    assert 'request.getResponseHeader("Content-Length")' in viewer
    assert "fallbackTotal" in viewer
    assert "progressDetail" in viewer


def test_viewer_prefers_2048_webp_glb_when_available():
    viewer = read("viewer_mesh.php")

    assert "model_2048_webp.glb" in viewer
    assert "foreach($viewerSrcCandidates as $viewerSrc)" in viewer


def test_get_glb_api_allows_2048_webp_variant():
    api = read("api.php")

    assert "model(?:_2048_webp)?\\.glb" in api


def test_viewer_rotates_portrait_capture_counterclockwise():
    viewer = read("viewer_mesh.php")

    assert "Math.PI - (VIEWER_PORTRAIT_CAPTURE ? Math.PI / 2 : 0)" in viewer


def test_viewer_keyboard_moves_camera_forward_and_back():
    viewer = read("viewer_mesh.php")

    assert 'window.addEventListener("keydown", handleViewerKeyDown)' in viewer
    for code in ["KeyW", "KeyA", "KeyS", "KeyD", "KeyF", "KeyB"]:
        assert code in viewer
    assert "moveCameraAlongView(" in viewer
    assert "moveCameraSideways(" in viewer
    assert 'id="reset-view"' in viewer
    assert "controls.reset()" in viewer


def test_viewer_shows_one_line_keyboard_help():
    viewer = read("viewer_mesh.php")

    assert 'id="viewer-help"' in viewer
    assert "W/F 前進" in viewer
    assert "S/B 後退" in viewer
    assert "A/D 左右" in viewer
    assert "white-space: nowrap" in viewer


def test_upload_progress_reports_http_status_for_non_json_response():
    index = read("index.php")

    assert "function uploadResponseErrorMessage" in index
    assert "xhr.status" in index
    assert "\" (HTTP \"" in index


def test_upload_checks_captcha_before_large_file_upload():
    index = read("index.php")

    assert "function checkUploadCaptcha" in index
    assert "api.php?mode=checkGD" in index
    precheck = index.index('checkUploadCaptcha($("#gdcode").val()).then')
    show_dialog = index.index("showUploadProgressDialog(file);", precheck)
    upload = index.index("return uploadWithProgress(formData);", show_dialog)
    assert precheck < show_dialog < upload


def test_thumbnail_api_saves_png_cache_and_retry_clears_old_thumb():
    api = read("api.php")

    assert "case 'save_thumb':" in api
    assert "ovm_thumb_cache_dir" in api
    assert "ovm_thumb_cache_path($id)" in api
    assert "uploads/_thumbs" in api
    assert "data:image/png;base64" in api
    assert "base64_decode" in api
    assert "1024 * 1024" in api
    assert "ovm_job_glb_path($id)" in api
    assert "thumb dir not writable" in api
    assert "ovm_delete_thumb_cache($id)" in api


def test_index_and_admin_have_search_pagination_and_large_thumbnails():
    index = read("index.php")
    admin = read("admin.php")

    for text in [index, admin]:
        assert "ovm_job_search_form_html" in text
        assert "ovm_job_pagination_html" in text
        assert 'data-refresh-cell="products"' in text
        assert "ovm_job_products_cell_html" in text

    job_view = read("job_view.php")
    assert 'name="q"' in job_view
    assert 'list="ovmJobSearchList"' in job_view
    assert "每頁 15 筆" in job_view

    assert ".ovm-thumb-pair{display:grid;grid-template-columns:1fr 1fr;gap:8px;width:200px;}" in index
    assert ".ovm-model-thumb{position:relative;width:96px;height:154px;" in index
    assert ".ovm-thumb-cell{width:200px;}" in index
    assert ".ovm-job-main{display:grid;grid-template-columns:200px minmax(0,1fr);" in index


def test_job_status_labels_are_the_requested_five_states():
    job_view = read("job_view.php")
    migrate = read("migrate.php")

    assert "case '0': return '待處理';" in job_view
    assert "case '1': return '轉檔中';" in job_view
    assert "case '2': return '已完成';" in job_view
    assert "case '3': return '失敗';" in job_view
    assert "case '4': return '暫停';" in job_view
    assert "return '等待轉檔'" not in job_view
    assert "return '已中止'" not in job_view
    assert "'label'=>'待處理'" in job_view
    assert "'label'=>'暫停'" in job_view
    assert "'label'=>'已完成'" in job_view
    assert "'step'=>'已停止'" not in job_view

    assert "0 pending 1 running 2 ready 3 failed 4 paused" in migrate


def test_failed_and_completed_jobs_can_be_retried_from_index_actions():
    api = read("api.php")
    index = read("index.php")
    job_view = read("job_view.php")
    js = read("js/function.js")

    assert "action === 'retry'" in api
    assert "retry_mode" in api
    assert "retry_clone" in api
    assert "ovm_clone_job_for_retry" in api
    assert "quality_preset" in api
    assert "只有失敗或已完成的工作可以重轉" in api
    assert "'input_frame_count'=>null" in api
    assert "'registered_frame_count'=>null" in api
    assert "'glb_file_size_mb'=>null" in api
    assert "'mesh_file_size_mb'=>null" in api
    assert "'texture_black_pixel_ratio'=>null" in api
    assert "'texture_white_empty_pixel_ratio'=>null" in api
    assert "'texture_patch_count'=>null" in api
    assert "'capture_source_type'=>null" in api
    assert "'capture_quality_decision'=>null" in api
    assert "'capture_updated_at'=>null" in api
    assert "engine_contract.json" in api
    assert "delivery_manifest.json" in api
    assert "failure_summary.json" in api
    assert "ovm_remove_path(\"{$jobDir}/validation\")" in api

    assert "retryOpenMvsJob" in job_view
    assert "重轉" in job_view
    assert "in_array($jobStatus, ['2','3'], true)" in job_view

    assert "retryOpenMvsDialog" in index
    assert 'id="retryQualityPreset"' in index
    assert 'id="retryMode"' in index
    assert 'value="clone"' in index
    assert "confirmRetryOpenMvsJob" in index

    assert "function retryOpenMvsJob" in js
    assert "function confirmRetryOpenMvsJob" in js
    assert "function closeRetryOpenMvsDialog" in js
    assert "window.prompt" not in js
    assert "quality_preset" in js
    assert "retry_mode" in js
    assert "clone" in js
    assert "api.php?mode=admin_action" in js
    assert 'postOpenMvsAdminAction(button, id, "retry"' in js
    assert "window.location.reload()" in js


def test_index_admin_actions_are_guarded_by_status():
    api = read("api.php")
    job_view = read("job_view.php")
    js = read("js/function.js")

    assert "ovm_clear_generated_outputs($id)" in api
    assert "function ovm_job_has_running_products" in api
    assert "function ovm_clear_products_for_job" in api
    assert "SELECT `id` FROM `openmvs_products` WHERE `job_id`=? AND `del`='0' AND `status`='1' LIMIT 1" in api
    assert "updateSQL_SAFE('openmvs_products', ['del'=>1], \"`job_id`=? AND `del`='0' AND `status`<>'1'\", [$id])" in api
    assert "ovm_remove_path(__DIR__ . \"/uploads/{$id}/products\")" in api
    assert "if(!ovm_clear_products_for_job($id)) ovm_json(['status'=>'NO','reason'=>'產品產製中，請稍後重轉'])" in api
    assert "if(!ovm_clear_products_for_job($id)) ovm_json(['status'=>'NO','reason'=>'產品產製中，請稍後啟動'])" in api
    assert "action === 'start'" in api
    assert "action === 'delete'" in api
    assert "只能啟動暫停中的工作" in api
    assert "轉檔中才能暫停" in api
    assert "這個狀態不能刪除" in api
    assert "['0','4','2','3']" in api
    assert "'del'=>1" in api

    assert "startOpenMvsJob" in job_view
    assert "pauseOpenMvsJob" in job_view
    assert "deleteOpenMvsJob" in job_view
    assert "$jobStatus === '4'" in job_view
    assert "$jobStatus === '1'" in job_view
    assert "in_array($jobStatus, ['0','4','2','3'], true)" in job_view
    assert "啟動" in job_view
    assert "暫停" in job_view
    assert "刪除" in job_view

    assert "function startOpenMvsJob" in js
    assert "function pauseOpenMvsJob" in js
    assert "function deleteOpenMvsJob" in js
    assert 'postOpenMvsAdminAction(button, id, "start"' in js
    assert 'postOpenMvsAdminAction(button, id, "abort"' in js
    assert 'postOpenMvsAdminAction(button, id, "delete"' in js
    assert "確定要啟動這筆暫停工作嗎" in js
    assert "確定要暫停目前轉檔嗎" in js
    assert "刪除後列表將不再顯示" in js


def test_cron_worker_runs_pipeline_and_updates_metrics():
    helper = read("crontab/inc/function.php")
    runner = read("crontab/1_run.php")
    wrapper = read("crontab/1min.sh")

    assert "function ovm_run_cmd" in helper
    assert "proc_open" in helper
    assert "pkill -TERM -P" in helper
    assert "function ovm_is_abort_requested" in helper
    assert "SELECT `status` FROM `openmvs_jobs` WHERE `id`=? LIMIT 1" in helper
    assert "[timing] START" in helper
    assert "function ovm_normalize_pipeline_mode" in helper
    assert "interface_colmap" in helper
    assert "return 'colmap';" in helper
    assert "function ovm_capture_source_type" in helper
    assert "function ovm_capture_summary_fields" in helper
    assert "openmvs.qa_report_missing" in helper
    assert "openmvs.qa_report_malformed" in helper
    assert "openmvs.contract_artifact_failed" in helper

    assert 'require __DIR__ . "/../../inc/config.php";' in runner
    assert "1_run.lock" in runner
    assert "flock($lockFp, LOCK_EX | LOCK_NB)" in runner
    assert ".photogrammetry_worker.lock" in runner
    assert "flock($globalLockFp, LOCK_EX | LOCK_NB)" in runner
    assert "function ovm_active_photogrammetry_job_exists" in runner
    assert "SELECT `id` FROM `openmvs_jobs` WHERE `del`='0' AND `status`='1' LIMIT 1" in runner
    assert "SELECT `id` FROM `gaussian_splat_jobs` WHERE `del`='0' AND `status`='1' LIMIT 1" in runner
    assert "已有 Photogrammetry 轉檔程序在執行中" in runner
    assert "$activeJobId" in runner
    assert "worker exited before completion" in runner
    assert "SELECT * FROM `openmvs_jobs` WHERE `del`='0' AND `status`='0' ORDER BY `id` ASC LIMIT 1" in runner
    assert "scripts/run_openmvs_pipeline.sh" in runner
    assert "scripts/build_engine_contract.py" in runner
    assert "scripts/build_validation_report.py" in runner
    assert "scripts/build_delivery_manifest.py" in runner
    assert "standard_artifacts" in runner
    assert "openmvs.contract_artifact_failed" in runner
    assert "input/input.{$kind}" in runner
    assert "qa_report.json" in runner
    assert "is_file($qaPath)" in runner
    assert "json_last_error()" in runner
    assert "openmvs.qa_report_missing" in runner
    assert "openmvs.qa_report_malformed" in runner
    assert "input_frame_count" in runner
    assert "registered_frame_count" in runner
    assert "glb_file_size_mb" in runner
    assert "OVM_MASK_MODE" in runner
    assert "env OVM_MASK_MODE=" in runner
    assert "OVM_QUALITY_PRESET" in runner
    assert "quality preset:" in runner
    assert "escapeshellarg($maskMode)" in runner
    assert "frames_(\\d+)" in runner
    assert "OVM_MAX_FRAMES=" in runner
    assert "ovm_normalize_pipeline_mode" in runner
    assert "$pipelineMode = 'openmvs_native';" in runner
    assert "$pipelineMode = ovm_normalize_pipeline_mode($candidateMode);" in runner
    assert "texture_black_pixel_ratio" in runner
    assert "texture_white_empty_pixel_ratio" in runner
    assert "texture_patch_count" in runner
    assert "capture_registered_ratio" in runner
    assert "capture_quality_decision" in runner
    assert "$upd['status'] = 2;" in runner

    assert wrapper.startswith("#!/usr/bin/env bash\n")
    assert "php 1_run.php" in wrapper


def test_cron_worker_runs_queued_glb_products():
    runner = read("crontab/1_run.php")

    assert "FROM `openmvs_products`" in runner
    assert "$activeProductId" in runner
    assert "$activeProductId = $productId;" in runner
    assert "$activeProductId = null;" in runner
    assert "SELECT `status` FROM `openmvs_products` WHERE `id`=? LIMIT 1" in runner
    assert "product worker exited before completion" in runner
    assert "`product_type`='glb' AND `status`='0' AND `del`='0' ORDER BY `id` ASC LIMIT 1" in runner
    assert "'openmvs_products'," in runner
    assert "'status'=>1" in runner
    assert "UPDATE `openmvs_products` SET" in runner
    assert "WHERE `id`=? AND `status`='0' AND `del`='0'" in runner
    assert "$claimStmt->rowCount() <= 0" in runner
    assert "continue;" in runner
    assert "'status'=>2" in runner
    assert "'status'=>3" in runner
    assert "`current_stage`='product_start'" in runner
    assert "`error_message`=''" in runner
    assert "'error_message'=>$reason" in runner
    assert "'current_stage'=>'failed'" in runner
    assert "OVM_PRODUCT_TEXTURE_SIZE=" in runner
    assert "OVM_PRODUCT_OUTPUT_DIR=" in runner
    assert "input/input.{$kind}" in runner
    assert "products/glb_{$textureSize}/model.glb" in runner
    assert "'file_path'=>$productFilePath" in runner
    assert "'file_size_mb'=>$productFileSizeMb" in runner
    assert "`process_log` = RIGHT(CONCAT(IFNULL(`process_log`,''), ?), 60000)" in runner


def test_openmvs_diagnostics_summary_surface():
    migrate = read("migrate.php")
    helper = read("crontab/inc/function.php")
    runner = read("crontab/1_run.php")
    api = read("api.php")
    index = read("index.php")
    job_view = read("job_view.php")
    js = read("js/function.js")

    assert "CREATE TABLE IF NOT EXISTS `openmvs_job_diagnostics`" in migrate
    assert "UNIQUE KEY `uq_job_stage_pattern`" in migrate
    for column in [
        "diagnostic_status",
        "diagnostic_score",
        "diagnostic_summary",
        "diagnostic_log_path",
        "diagnostic_category",
        "diagnostic_code",
        "diagnostic_severity",
        "diagnostic_count",
        "diagnostic_value",
        "diagnostic_message",
        "diagnostic_source",
    ]:
        assert f"`{column}`" in migrate

    assert "function ovm_parse_log_diagnostics" in helper
    assert "function ovm_upsert_job_diagnostics" in helper
    assert "function ovm_finalize_job_diagnostics" in helper
    assert "function ovm_write_failure_contract" in helper
    assert "openmvs.linear_solver_failure" in helper
    assert "openmvs.texture_patch_rejected" in helper
    assert "openmvs.cpu_fallback" in helper
    assert "openmvs.out_of_memory" in helper
    assert "openmvs.missing_scene" in helper
    assert "openmvs.process_timeout" in helper
    assert "openmvs.nonzero_exit" in helper
    assert "scripts/build_failure_summary.py" in helper
    assert "failure_summary.json" in helper

    assert 'uploads/{$id}/logs/openmvs_pipeline.log' in runner
    assert "process_log = RIGHT(CONCAT" not in runner
    assert "ovm_finalize_job_diagnostics" in runner

    assert "case 'get_diagnostics':" in api
    assert "DELETE FROM `openmvs_job_diagnostics` WHERE `job_id`=?" in api
    assert '<div class="ovm-job-section-title">品質</div>' in index
    assert 'data-refresh-cell="quality"' in index
    assert "jobDiagnosticsDialog" in index
    assert "ovm_job_quality_cell_html" in job_view
    assert "openDiagnosticsDialog" in job_view
    assert "quality_html" in job_view
    assert "function openDiagnosticsDialog" in js


def test_diagnostics_table_cells_keep_dark_background():
    index = read("index.php")
    js = read("js/function.js")

    assert ".ovm-diagnostics-body .ovm-table > tbody > tr > td" in index
    assert "background:#0f1722!important" in index
    assert "class=\"table table-condensed ovm-table\"" in js
