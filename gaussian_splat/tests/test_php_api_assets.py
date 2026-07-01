from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_migration_defines_job_schema_and_idempotent_column_repair():
    text = (ROOT / "migrate.php").read_text()

    assert 'require __DIR__ . "/../inc/config.php";' in text
    assert "php_sapi_name() !== 'cli'" in text
    assert 'CREATE TABLE IF NOT EXISTS `gaussian_splat_jobs`' in text
    assert "SHOW COLUMNS FROM `gaussian_splat_jobs`" in text
    assert "ALTER TABLE `gaussian_splat_jobs` ADD COLUMN" in text
    assert "MODIFY COLUMN `confidence_score` decimal(5,2)" in text
    assert "gaussian_splat_jobs migration complete" in text

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
        "camera_lon",
        "camera_lat",
        "camera_alt",
        "camera_heading",
        "camera_pitch",
        "camera_roll",
        "kind",
        "pipeline_mode",
        "email",
        "del",
        "process_log",
        "current_stage",
        "current_stage_label",
        "duration_seconds",
        "queue_seconds",
        "process_seconds",
        "frame_count",
        "registered_frame_count",
        "splat_file_size_mb",
        "confidence_score",
        "confidence_grade",
        "confidence_decision",
        "confidence_effective_decision",
        "confidence_gate_json",
        "confidence_override",
        "confidence_override_reason",
        "confidence_risk_count",
        "confidence_recommendation_count",
        "confidence_needs_override",
        "confidence_override_status",
        "confidence_updated_at",
    ]:
        assert f"`{column}`" in text
    assert "5 waiting_override" in text
    assert "`pipeline_mode` varchar(30) DEFAULT 'fast'" in text


def test_api_upload_creates_pending_mp4_or_zip_job_and_stages_input():
    text = (ROOT / "api.php").read_text()

    assert 'require __DIR__ . "/../inc/config.php";' in text
    assert "function gs_json" in text
    assert "case 'checkGD':" in text
    assert '$_SESSION[\'GD_CODE\']' in text
    assert "case 'upload':" in text
    assert "function gs_pipeline_mode_or_null" in text
    assert "['fast','qa','premium']" in text
    assert "$pipelineMode = gs_pipeline_mode_or_null" in text
    assert "模式錯誤" in text
    assert "'pipeline_mode' => $pipelineMode" in text
    assert "gdcode" in text
    assert "驗證碼錯誤" in text
    assert '$_SESSION[\'GD_CODE\'] = "囧";' in text
    assert "請輸入標題" in text
    assert "請選擇 MP4 影片或 ZIP 圖片包" in text
    assert "目前僅支援 MP4 影片或 ZIP 圖片包" in text
    assert "function gs_zip_image_entries" in text
    assert "function gs_extract_zip_images" in text
    assert "getimagesize" in text
    assert "ZIP 圖片至少需要" in text
    assert "$ext !== 'mp4' && $ext !== 'zip'" in text
    assert "if($ext === 'mp4')" in text
    assert "if($ext === 'zip')" in text
    assert "GS_MIN_VIDEO_SECONDS" in text
    assert "ffprobe" in text
    assert "gs_video_duration_reject_reason" in text
    assert "影片太短" in text
    assert "至少需要 3 秒影片" in text
    assert "建立上傳目錄失敗" in text
    assert "上傳後找不到檔案" in text
    assert "title is required" not in text
    assert "upload failed" not in text
    assert "only mp4 is supported in the MVP worker" not in text
    assert "insertSQL('gaussian_splat_jobs', $m)" in text
    assert '$root = __DIR__ . "/uploads/{$id}"' in text
    assert '$inputDir = "{$root}/input"' in text
    assert '$dest = "{$inputDir}/input.{$ext}"' in text
    assert "move_uploaded_file" in text
    assert 'gs_extract_zip_images($dest, "{$root}/images")' in text
    assert "updateSQL_SAFE('gaussian_splat_jobs'" in text


def test_api_log_transform_and_admin_actions():
    text = (ROOT / "api.php").read_text()

    assert "case 'get_log':" in text


def test_api_saves_gaussian_thumbnail_cache():
    text = (ROOT / "api.php").read_text()
    job_view = (ROOT / "job_view.php").read_text()

    assert "case 'save_thumb':" in text
    assert "gs_thumb_cache_dir" in text
    assert "gs_job_thumb_cache_path($id)" in text
    assert "uploads/_thumbs" in job_view
    assert "output_{$id}.png" in job_view
    assert "data:image/png;base64" in text
    assert "base64_decode" in text
    save_thumb_block = text[text.index("case 'save_thumb':"):text.index("case 'save_transform':")]
    assert "gs_splat_artifact_for_job($id)" in save_thumb_block
    assert "gs_job_splat_path($id)" not in save_thumb_block
    assert "(string)($rows[0]['status'] ?? '') !== '2'" in save_thumb_block
    assert "is_file($thumbPath)" in save_thumb_block
    assert "gs_delete_thumb_cache($id)" not in save_thumb_block
    assert "找不到 Splat，不能儲存成果縮圖" in text
    assert "thumb dir not writable" in text
    assert "function gs_job_thumbnail_cell_html" in job_view
    assert "thumb_html" in job_view
    assert "SELECT * FROM `gaussian_splat_jobs` WHERE `id`=? LIMIT 1" in text
    assert 'require_once __DIR__ . "/job_view.php";' in text
    assert '$row = $rows[0] ?? [];' in text
    assert "'reason'=>$row['reason'] ?? ''" in text
    assert "'log'=>$row['process_log'] ?? ''" in text
    assert "'pipeline_mode'=>(string)($row['pipeline_mode'] ?? 'fast')" in text
    assert "'pipeline_mode_label'=>gs_pipeline_mode_label($row['pipeline_mode'] ?? 'fast')" in text
    assert "'confidence_gate'=>gs_confidence_gate_from_row($row)" in text
    assert "'confidence_summary'=>gs_confidence_summary_from_row($row)" in text
    assert "'confidence_report_url'=>gs_job_confidence_report_url($id)" in text
    assert "'confidence_gate_url'=>gs_job_confidence_gate_url($id)" in text
    assert "'artifact_links'=>gs_job_artifact_links($id)" in text
    assert "case 'jobs_delta':" in text
    assert 'require_once __DIR__ . "/job_view.php";' in text
    assert "gs_job_list_state(15)" in text
    assert "gs_job_delta_payload($rows)" in text
    assert "'has_active_jobs'=>$payload['has_active_jobs']" in text
    assert "'rows'=>$payload['rows']" in text
    assert "'failure_reasons'=>$payload['failure_reasons']" in text
    assert "case 'save_transform':" in text
    assert 'require "{$base_dir}/inc/checkpassword.php";' in text
    assert "base64_decode" in text
    assert "transform.json" in text
    assert "JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT" in text
    assert "case 'admin_action':" in text
    assert "action === 'reconvert'" in text
    assert "$reconvertAllowedStatuses = ['2','3','4','5'];" in text
    assert "$reconvertPipelineMode = gs_pipeline_mode_or_null" in text
    assert "$reconvertTarget = ($_POST['reconvert_target'] ?? 'new') === 'same' ? 'same' : 'new';" in text
    assert "重轉模式錯誤" in text
    assert "不能重轉執行中或排隊中的工作" in text
    assert "function gs_reset_reconvert_job" in text
    assert "function gs_delete_reconvert_path" in text
    assert "gs_reset_reconvert_job($sourceRow, $reconvertPipelineMode)" in text
    assert "gs_create_reconvert_job($sourceRow, $reconvertPipelineMode)" in text
    assert "insertSQL('gaussian_splat_jobs', $m)" in text
    assert "copy($sourceInput, $dest)" in text
    assert "'source_job_id'=>$sourceId" in text
    assert "'version'=>$version" in text
    assert "action === 'retry'" not in text
    assert "gs_delete_generated_dir" not in text
    assert "RecursiveDirectoryIterator" not in text
    assert "action === 'confidence_override'" in text
    assert "`status`='5'" in text
    assert "'confidence_override'=>1" in text
    assert "'confidence_override_reason'=>$overrideReason" in text
    assert "'status'=>0" in text
    assert "action === 'abort'" in text
    assert "$abortAllowedStatuses = ['0','1'];" in text
    assert "不能中止已完成、失敗或等待覆核的工作" in text
    assert "if($currentStatus === '1')" in text
    assert "`id`=? AND `status` IN (0,1)" in text
    assert "'current_stage'=>null" in text
    assert "'current_stage_label'=>null" in text
    assert ".abort" in text
    assert "定位資料格式錯誤" in text
    assert "建立工作目錄失敗" in text
    assert "儲存定位資料失敗" in text
    assert "工作編號錯誤" in text
    assert "未知的操作" in text
    assert "未知模式" in text


def test_api_streams_splat_by_uuid_instead_of_client_path():
    text = (ROOT / "api.php").read_text()

    assert "case 'resolveSplat':" in text
    assert "case 'getSplat':" in text
    assert 'require_once __DIR__ . "/job_view.php";' in text
    assert "gs_splat_artifact_for_job($id)" in text
    assert "gs_splat_artifact_from_uuid($uuid)" in text
    assert "gs_stream_splat_artifact($artifact)" in text
    assert "Content-Length: " in text
    assert "Accept-Ranges: bytes" in text
    assert "HTTP_RANGE" in text
    assert "REQUEST_METHOD'] ?? 'GET') === 'HEAD'" in text
    assert "unsupported splat extension" in text
    assert "artifact not found" in text
