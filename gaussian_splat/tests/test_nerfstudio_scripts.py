from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def read_script(name: str) -> str:
    return (ROOT / "scripts" / name).read_text()


def test_scripts_use_strict_mode_and_argument_validation():
    expected_usage = {
        "process_nerfstudio.sh": [
            "${1:?usage: process_nerfstudio.sh images_dir processed_dir}",
            "${2:?usage: process_nerfstudio.sh images_dir processed_dir}",
        ],
        "train_splat.sh": [
            "${1:?usage: train_splat.sh processed_dir outputs_dir}",
            "${2:?usage: train_splat.sh processed_dir outputs_dir}",
        ],
        "export_splat.sh": [
            "${1:?usage: export_splat.sh config_yml exports_dir}",
            "${2:?usage: export_splat.sh config_yml exports_dir}",
        ],
        "run_mvp_pipeline.sh": [
            "${1:?usage: run_mvp_pipeline.sh input_video job_dir}",
            "${2:?usage: run_mvp_pipeline.sh input_video job_dir}",
        ],
    }

    for name, usage_patterns in expected_usage.items():
        text = read_script(name)
        assert "set -euo pipefail" in text
        for pattern in usage_patterns:
            assert pattern in text


def test_process_script_uses_ns_process_data_images():
    text = read_script("process_nerfstudio.sh")
    assert 'ENV_PATH="${GS_CONDA_ENV:-/DATA/conda_vm/gs_scene}"' in text
    assert 'COLMAP_ENV_PATH="${GS_COLMAP_ENV_PATH:-/DATA/conda_vm/openmvs}"' in text
    assert 'CUDA_ROOT="${GS_CUDA_ROOT:-$ENV_PATH}"' in text
    assert 'export PATH="$COLMAP_ENV_PATH/bin:$ENV_PATH/bin:$CUDA_ROOT/bin:$PATH"' in text
    assert 'export LD_LIBRARY_PATH="$CUDA_ROOT/targets/x86_64-linux/lib:$ENV_PATH/lib:${LD_LIBRARY_PATH:-}"' in text
    assert 'SFM_MAPPER="${GS_SFM_MAPPER:-incremental}"' in text
    assert 'COLMAP_CMD="${GS_COLMAP_CMD:-$COLMAP_ENV_PATH/bin/colmap}"' in text
    assert 'GS_COLMAP_USE_GPU="${GS_COLMAP_USE_GPU:-1}"' in text
    assert 'SFM_MATCHER="${GS_SFM_MATCHER:-exhaustive}"' in text
    assert '"$ENV_PATH/bin/ns-process-data" images' in text
    assert "--data" in text
    assert "--no-gpu" in text
    assert "--output-dir" in text
    assert "--skip-colmap" in text
    assert "--colmap-model-path colmap/sparse/0" in text
    assert 'transforms.json not found: $PROCESSED_DIR/transforms.json' in text


def test_process_script_supports_incremental_and_hierarchical_colmap_mappers():
    text = read_script("process_nerfstudio.sh")
    assert "run_colmap_reconstruction()" in text
    assert '"$COLMAP_CMD" feature_extractor' in text
    assert '"$COLMAP_CMD" exhaustive_matcher' in text
    assert '"$COLMAP_CMD" sequential_matcher' in text
    assert "Gaussian COLMAP GPU feature extraction failed; retrying CPU" in text
    assert "Gaussian COLMAP GPU matcher failed; retrying CPU" in text
    assert "--SiftExtraction.use_gpu 0" in text
    assert "--SiftMatching.use_gpu 0" in text
    assert '"$COLMAP_CMD" "${mapper_command[@]}"' in text
    assert 'incremental) mapper_command=(mapper) ;;' in text
    assert 'hierarchical) mapper_command=(hierarchical_mapper) ;;' in text
    assert 'nerfstudio)' in text
    assert 'write_sfm_report "$SFM_REPORT"' in text
    assert '"mapper": mapper' in text


def test_process_script_can_use_hloc_lightglue_matching():
    text = read_script("process_nerfstudio.sh")
    helper_path = ROOT / "scripts" / "run_hloc_reconstruction.py"
    helper = helper_path.read_text() if helper_path.exists() else ""

    assert "hloc_lightglue)" in text
    assert 'run_hloc_lightglue_reconstruction "$sparse_root"' in text
    assert "run_hloc_reconstruction.py" in text
    assert "Unsupported GS_SFM_MATCHER: $SFM_MATCHER (use exhaustive, sequential, or hloc_lightglue)" in text
    assert '"superpoint+lightglue"' in helper
    assert 'device = "cuda" if torch.cuda.is_available() else "cpu"' in helper
    assert "GS_HLOC_MATCH_WINDOW" in helper
    assert "hloc_lightglue requires hloc, pycolmap, and torch" in helper


def test_run_pipeline_labels_sfm_stage_generically():
    text = read_script("run_mvp_pipeline.sh")
    assert 'TRANSFORMS_PATH="$(run_stage_capture sfm "SfM pose estimation" bash "$PROJECT_ROOT/scripts/process_nerfstudio.sh"' in text
    assert 'run_stage frame_colmap "frame SfM annotation"' in text


def test_run_pipeline_requires_training_cap_for_fast_and_qa_modes():
    text = read_script("run_mvp_pipeline.sh")

    assert 'case "$PIPELINE_MODE" in' in text
    assert "fast|qa)" in text
    assert "GS_PIPELINE_MODE=$PIPELINE_MODE requires GS_TRAIN_MAX_ITERATIONS" in text
    assert "premium) ;;" in text
    assert "unsupported GS_PIPELINE_MODE: $PIPELINE_MODE" in text
    assert "exit 2" in text
    assert 'echo "[config] GS_TRAIN_MAX_ITERATIONS=$GS_TRAIN_MAX_ITERATIONS" >&2' in text


def test_train_script_uses_splatfacto():
    text = read_script("train_splat.sh")
    assert 'export CUDA_HOME="$ENV_PATH"' in text
    assert 'export PATH="$ENV_PATH/bin:$PATH"' in text
    assert 'export MAX_JOBS="${GS_TORCH_EXT_MAX_JOBS:-${MAX_JOBS:-2}}"' in text
    assert 'export GS_TORCH_MATMUL_PRECISION="${GS_TORCH_MATMUL_PRECISION:-high}"' in text
    assert 'TRAIN_VIS="${GS_TRAIN_VIS:-tensorboard}"' in text
    assert "GS_TRAIN_MAX_ITERATIONS" in text
    assert "--max-num-iterations" in text
    assert '"$ENV_PATH/bin/python" - splatfacto' in text
    assert "torch.set_float32_matmul_precision" in text
    assert 'os.environ["GS_TORCH_MATMUL_PRECISION"]' in text
    assert "from nerfstudio.scripts.train import entrypoint" in text
    assert '--vis "$TRAIN_VIS"' in text
    assert "--viewer.quit-on-train-completion True" in text
    assert "--data" in text
    assert "--output-dir" in text
    assert "--output-dir \"$OUTPUTS_DIR\" >&2" in text
    assert "config.yml not found under: $OUTPUTS_DIR" in text


def test_export_script_exports_gaussian_splat_ply():
    text = read_script("export_splat.sh")
    assert "TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1" in text
    assert '"$ENV_PATH/bin/ns-export" gaussian-splat' in text
    assert "--load-config" in text
    assert "--output-dir" in text
    assert "--output-dir \"$EXPORTS_DIR\" >&2" in text
    assert "splat.ply" in text
    assert "splat.ply not found: $EXPORTS_DIR/splat.ply" in text


def test_run_pipeline_wires_all_steps_in_order():
    text = read_script("run_mvp_pipeline.sh")
    assert "scripts/frame_quality_select.py" in text
    assert 'FRAME_CANDIDATE_FPS="${GS_FRAME_CANDIDATE_FPS:-12}"' in text
    assert 'FRAME_TARGET_FPS="${GS_FRAME_TARGET_FPS:-3}"' in text
    assert 'FRAME_MAX_FRAMES="${GS_FRAME_MAX_FRAMES:-180}"' in text
    assert 'FRAME_WIDTH="${GS_FRAME_WIDTH:-1600}"' in text
    assert 'FRAME_MIN_FRAMES="${GS_FRAME_MIN_FRAMES:-8}"' in text
    assert "scripts/process_nerfstudio.sh" in text
    assert "scripts/train_splat.sh" in text
    assert "scripts/export_splat.sh" in text
    assert "scripts/write_default_transform.py" in text
    assert "scripts/build_qa_report.py" in text
    assert 'STAGED_INPUT="$JOB_DIR/input/input.mp4"' in text
    assert 'ORIGIN_LNG="${3:-120.6647066}"' in text
    assert 'ORIGIN_LAT="${4:-24.1504731}"' in text
    assert 'ORIGIN_HEIGHT="${5:-0.0}"' in text
    assert 'realpath "$INPUT_VIDEO"' in text
    assert 'realpath "$STAGED_INPUT"' in text
    assert '"$STAGED_INPUT" \\' in text
    assert '"$JOB_DIR/candidates" \\' in text
    assert '"$JOB_DIR/images" \\' in text
    assert '--report "$JOB_DIR/frame_quality_report.json" \\' in text
    assert '--candidate-fps "$FRAME_CANDIDATE_FPS" \\' in text
    assert '--target-fps "$FRAME_TARGET_FPS" \\' in text
    assert '--max-frames "$FRAME_MAX_FRAMES" \\' in text
    assert '--min-candidates "$FRAME_MIN_FRAMES" \\' in text
    assert '--min-selected "$FRAME_MIN_FRAMES" \\' in text
    assert '--width "$FRAME_WIDTH" >&2' in text
    assert 'python3 "$PROJECT_ROOT/scripts/extract_frames.py" "$STAGED_INPUT" "$JOB_DIR/images" >&2' not in text
    assert '"$JOB_DIR/transform.json" --lng "$ORIGIN_LNG" --lat "$ORIGIN_LAT" --height "$ORIGIN_HEIGHT" >&2' in text
    assert '"$JOB_DIR" >&2' in text
    assert 'JOB_PARENT="$(dirname "$JOB_DIR")"' in text
    assert 'UPLOADS_DIR="$PROJECT_ROOT/uploads"' in text
    assert 'UPLOADS_REAL="$(realpath "$UPLOADS_DIR")"' in text
    assert 'JOB_PARENT_REAL="$(realpath -m "$JOB_PARENT")"' in text
    assert 'JOB_DIR_REAL="$(realpath -m "$JOB_DIR")"' in text
    assert 'case "$JOB_PARENT_REAL" in' in text
    assert 'case "$JOB_DIR_REAL" in' in text
    assert 'echo "job_dir must be under $UPLOADS_DIR: $JOB_DIR" >&2' in text
    assert 'chmod a+rx "$JOB_PARENT"' in text
    assert 'chmod a+rx "$JOB_DIR" "$JOB_DIR/exports"' in text
    assert 'chmod a+r "$SPLAT_PATH" "$JOB_DIR/transform.json" "$JOB_DIR/qa_report.json"' in text
    assert 'TRANSFORMS_PATH="$(run_stage_capture sfm "SfM pose estimation" bash "$PROJECT_ROOT/scripts/process_nerfstudio.sh"' in text
    assert 'CONFIG_PATH="$(run_stage_capture train "splatfacto training" bash "$PROJECT_ROOT/scripts/train_splat.sh"' in text
    assert 'SPLAT_PATH="$(run_stage_capture export "splat export" bash "$PROJECT_ROOT/scripts/export_splat.sh"' in text
    assert 'echo "$SPLAT_PATH"' in text
    assert text.index("scripts/frame_quality_select.py") < text.index("scripts/process_nerfstudio.sh")


def test_run_pipeline_can_disable_frame_selector_for_legacy_fps_baseline():
    text = read_script("run_mvp_pipeline.sh")
    assert 'FRAME_SELECTOR="${GS_FRAME_SELECTOR:-1}"' in text
    assert 'if [ "$FRAME_SELECTOR" = "0" ]; then' in text
    assert 'find "$JOB_DIR/images" -maxdepth 1 -type f -regextype posix-extended -regex ".*/frame_[0-9]{5}\\.(jpg|jpeg|png)" -delete' in text
    assert 'rm -f "$JOB_DIR/frame_quality_report.json"' in text
    assert 'run_stage legacy_extract "legacy fps frame extraction"' in text
    assert '"$GS_PYTHON" "$PROJECT_ROOT/scripts/extract_frames.py" "$STAGED_INPUT" "$JOB_DIR/images"' in text
    assert '--width "$FRAME_WIDTH" --max-frames "$FRAME_MAX_FRAMES" >&2' in text
    assert 'else' in text
    assert 'run_stage frame_select "frame quality selection"' in text
    assert text.index('find "$JOB_DIR/images"') < text.index('run_stage legacy_extract "legacy fps frame extraction"')
    assert text.index('rm -f "$JOB_DIR/frame_quality_report.json"') < text.index('run_stage legacy_extract "legacy fps frame extraction"')


def test_run_pipeline_accepts_prepared_image_directory_input():
    text = read_script("run_mvp_pipeline.sh")

    assert "INPUT_IS_IMAGE_DIR=0" in text
    assert 'if [ -d "$INPUT_VIDEO" ]; then' in text
    assert 'INPUT_IS_IMAGE_DIR=1' in text
    assert 'STAGED_INPUT="$INPUT_VIDEO"' in text
    assert 'IMAGE_COUNT="$(find "$JOB_DIR/images" -maxdepth 1 -type f' in text
    assert 'reuse_stage frame_select "uploaded image set" "using $IMAGE_COUNT uploaded images"' in text
    assert 'if [ "$INPUT_IS_IMAGE_DIR" = "1" ]; then' in text
    assert text.index('if [ "$INPUT_IS_IMAGE_DIR" = "1" ]; then') < text.index('TRANSFORMS_PATH="$(run_stage_capture sfm')


def test_run_pipeline_optionally_enhances_selected_frames_after_colmap_pose_estimation():
    text = read_script("run_mvp_pipeline.sh")
    assert 'TRAIN_PROCESSED_DIR="$JOB_DIR/processed"' in text
    assert 'if [ "${GS_FRAME_ENHANCE:-0}" = "1" ]; then' in text
    assert '"$GS_PYTHON" "$PROJECT_ROOT/scripts/enhance_frames_realesrgan.py" \\' in text
    assert '"$JOB_DIR/images" \\' in text
    assert '"$JOB_DIR/enhanced_images" \\' in text
    assert '--scale "${GS_FRAME_ENHANCE_SCALE:-2}" \\' in text
    assert '--model-name "${GS_FRAME_ENHANCE_MODEL:-realesrgan-x4plus}" >&2' in text
    assert 'TRANSFORMS_PATH="$(run_stage_capture sfm "SfM pose estimation" bash "$PROJECT_ROOT/scripts/process_nerfstudio.sh" "$JOB_DIR/images" "$JOB_DIR/processed")"' in text
    assert '"$GS_PYTHON" "$PROJECT_ROOT/scripts/prepare_enhanced_training_dataset.py" \\' in text
    assert '"$JOB_DIR/processed" \\' in text
    assert '"$JOB_DIR/enhanced_images" \\' in text
    assert '"$JOB_DIR/processed_enhanced" >&2' in text
    assert 'TRAIN_PROCESSED_DIR="$JOB_DIR/processed_enhanced"' in text
    assert 'CONFIG_PATH="$(run_stage_capture train "splatfacto training" bash "$PROJECT_ROOT/scripts/train_splat.sh" "$TRAIN_PROCESSED_DIR" "$JOB_DIR/outputs")"' in text
    assert text.index("scripts/process_nerfstudio.sh") < text.index("scripts/enhance_frames_realesrgan.py")
    assert text.index("scripts/enhance_frames_realesrgan.py") < text.index("scripts/prepare_enhanced_training_dataset.py")
    assert text.index("scripts/prepare_enhanced_training_dataset.py") < text.index("scripts/train_splat.sh")


def test_run_pipeline_annotates_frame_quality_after_colmap():
    text = read_script("run_mvp_pipeline.sh")
    assert "scripts/annotate_frame_quality_colmap.py" in text
    assert 'run_stage frame_colmap "frame SfM annotation"' in text
    assert text.index("scripts/process_nerfstudio.sh") < text.index("scripts/annotate_frame_quality_colmap.py")
    assert text.index("scripts/annotate_frame_quality_colmap.py") < text.index("scripts/train_splat.sh")


def test_run_pipeline_supports_trench_mode_outputs_after_standard_qa():
    text = read_script("run_mvp_pipeline.sh")
    assert 'TRENCH_MODE="${GS_TRENCH_MODE:-0}"' in text
    assert 'GEOREF_MODE="${GS_GEOREF_MODE:-none}"' in text
    assert 'GEOREF_CRS="${GS_GEOREF_CRS:-}"' in text
    assert 'GEOREF_LAT="${GS_GEOREF_LAT:-}"' in text
    assert 'GEOREF_LNG="${GS_GEOREF_LNG:-}"' in text
    assert 'GEOREF_HEIGHT="${GS_GEOREF_HEIGHT:-}"' in text
    assert 'GEOREF_HEADING="${GS_GEOREF_HEADING:-}"' in text
    assert 'GEOREF_SCALE="${GS_GEOREF_SCALE:-}"' in text
    assert 'if [ "$TRENCH_MODE" = "1" ]; then' in text
    assert "scripts/outdoor_intake.py" in text
    assert "scripts/build_trench_coverage_report.py" in text
    assert "scripts/build_georef_metadata.py" in text
    assert "scripts/build_trench_delivery.py" in text
    assert "scripts/build_trench_qa_report.py" in text
    assert "scripts/build_delivery_manifest.py" in text
    assert 'PIPELINE_MODE="${GS_PIPELINE_MODE:-fast}"' in text
    assert '--pipeline-mode "$PIPELINE_MODE"' in text
    assert 'local georef_args=("$JOB_DIR/georef.json" "--mode" "$GEOREF_MODE")' in text
    assert 'georef_args+=("--crs" "$GEOREF_CRS")' in text
    assert 'georef_args+=("--lat" "$GEOREF_LAT")' in text
    assert 'georef_args+=("--lng" "$GEOREF_LNG")' in text
    assert 'georef_args+=("--height" "$GEOREF_HEIGHT")' in text
    assert 'georef_args+=("--heading" "$GEOREF_HEADING")' in text
    assert 'georef_args+=("--scale" "$GEOREF_SCALE")' in text
    assert '"$JOB_DIR/input_manifest.json"' in text
    assert '"$JOB_DIR/trench_coverage_report.json"' in text
    assert '"$JOB_DIR/georef.json"' in text
    assert '"$JOB_DIR/trench_qa_report.json"' in text
    assert '"$JOB_DIR/delivery_manifest.json"' in text
    assert 'chmod a+r "$JOB_DIR/input_manifest.json"' in text
    assert 'chmod a+r "$JOB_DIR/trench_coverage_report.json"' in text
    assert 'chmod a+r "$JOB_DIR/georef.json"' in text
    assert 'chmod a+r "$JOB_DIR/trench_qa_report.json"' in text
    assert 'chmod a+r "$JOB_DIR/delivery_manifest.json"' in text
    assert 'chmod a+r "$JOB_DIR/exports/splat.trench.ply"' in text
    assert 'chmod a+r "$JOB_DIR/exports/splat.trench.viewer.json"' in text
    assert 'if [ -f "$JOB_DIR/input_manifest.json" ]; then' in text
    assert 'if [ -f "$JOB_DIR/trench_coverage_report.json" ]; then' in text
    assert 'if [ -f "$JOB_DIR/georef.json" ]; then' in text
    assert 'if [ -f "$JOB_DIR/trench_qa_report.json" ]; then' in text
    assert 'if [ -f "$JOB_DIR/delivery_manifest.json" ]; then' in text
    assert 'if [ -f "$JOB_DIR/exports/splat.trench.ply" ]; then' in text
    assert 'if [ -f "$JOB_DIR/exports/splat.trench.viewer.json" ]; then' in text
    assert text.index('run_stage finalize "viewer metadata and QA" finalize_outputs') < text.index(
        'if [ "$TRENCH_MODE" = "1" ]; then\n  run_trench_outputs'
    )
    assert text.index("scripts/outdoor_intake.py") < text.index("scripts/build_trench_coverage_report.py")
    assert text.index("scripts/build_trench_coverage_report.py") < text.index("scripts/build_georef_metadata.py")
    assert text.index("scripts/build_georef_metadata.py") < text.index("scripts/build_trench_delivery.py")
    assert text.index("scripts/build_trench_delivery.py") < text.index("scripts/build_trench_qa_report.py")
    assert text.index("scripts/build_trench_qa_report.py") < text.index("scripts/build_delivery_manifest.py")


def test_run_pipeline_always_writes_studio_delivery_manifest_after_optional_trench_outputs():
    text = read_script("run_mvp_pipeline.sh")

    assert 'run_stage delivery_manifest "delivery manifest" "$GS_PYTHON" "$PROJECT_ROOT/scripts/build_delivery_manifest.py" "$JOB_DIR" --pipeline-mode "$PIPELINE_MODE" >&2' in text
    assert 'run_stage appearance_summary "Gaussian appearance summary" "$GS_PYTHON" "$PROJECT_ROOT/scripts/build_gaussian_appearance_summary.py" "$JOB_DIR" >&2' in text
    assert 'run_stage engine_contract "Gaussian engine contract" "$GS_PYTHON" "$PROJECT_ROOT/scripts/build_gaussian_engine_contract.py" "$JOB_DIR" --mode "$PIPELINE_MODE" >&2' in text
    assert 'run_stage validation_report "validation report" "$GS_PYTHON" "$PROJECT_ROOT/scripts/build_validation_report.py" "$JOB_DIR" >&2' in text
    assert 'if [ "$PIPELINE_MODE" = "qa" ]; then' in text
    assert 'run_stage qa_validation_report "QA validation report" "$GS_PYTHON" "$PROJECT_ROOT/scripts/build_qa_validation_report.py" "$JOB_DIR" >&2' in text
    assert 'if [ "$PIPELINE_MODE" = "premium" ]; then' in text
    assert 'run_premium_outputs' in text
    assert 'run_stage compare_bundle "premium compare bundle" "$GS_PYTHON" "$PROJECT_ROOT/scripts/build_compare_bundle.py" "${compare_args[@]}" >&2' in text
    assert text.index('if [ "$TRENCH_MODE" = "1" ]; then') < text.index('run_stage delivery_manifest "delivery manifest"')
    assert text.index('run_stage appearance_summary "Gaussian appearance summary"') < text.index('run_stage engine_contract "Gaussian engine contract"')
    assert text.index('run_stage engine_contract "Gaussian engine contract"') < text.index('run_stage validation_report "validation report"')
    assert text.index('run_stage validation_report "validation report"') < text.index('run_stage qa_validation_report "QA validation report"')
    assert text.index('run_stage validation_report "validation report"') < text.index('if [ "$PIPELINE_MODE" = "premium" ]; then\n  run_premium_outputs\nfi')
    assert text.index('if [ "$PIPELINE_MODE" = "premium" ]; then\n  run_premium_outputs\nfi') < text.index('run_stage delivery_manifest "delivery manifest"')
    assert text.index('run_stage validation_report "validation report"') < text.index('run_stage delivery_manifest "delivery manifest"')


def test_run_pipeline_writes_timing_report_and_stage_markers():
    text = read_script("run_mvp_pipeline.sh")

    assert 'TIMING_REPORT="$JOB_DIR/timing_report.json"' in text
    assert 'timing_event init pipeline "Gaussian Splat pipeline"' in text
    assert 'echo "[timing] START ${key} ${label}" >&2' in text
    assert 'echo "[timing] END ${key} success" >&2' in text
    assert 'timing_event finish pipeline success "Pipeline complete"' in text
    assert 'timing_event fail pipeline failed "Pipeline failed"' in text
    assert 'run_stage frame_select "frame quality selection"' in text
    assert 'run_stage enhance "Real-ESRGAN frame enhancement"' in text
    assert 'run_stage prepare_training_images "prepare enhanced training images"' in text
    assert 'run_stage_capture sfm "SfM pose estimation"' in text
    assert 'run_stage_capture train "splatfacto training"' in text
    assert 'run_stage_capture export "splat export"' in text
    assert 'run_stage cleanup "splat cleanup"' in text
    assert '"$GS_PYTHON" "$PROJECT_ROOT/scripts/filter_splat_ply.py"' in text
    assert '"$SPLAT_PATH" "$JOB_DIR/exports/splat.clean.ply"' in text
    assert '--meta "$JOB_DIR/exports/splat.clean.viewer.json" >&2' in text
    assert 'run_stage finalize "viewer metadata and QA"' in text
    assert "write_default_transform.py" in text
    assert "build_qa_report.py" in text
    assert '>&2 || return' in text
    assert text.index('run_stage_capture export "splat export"') < text.index('run_stage cleanup "splat cleanup"')
    assert text.index('run_stage cleanup "splat cleanup"') < text.index('run_stage finalize "viewer metadata and QA"')
    assert '"$JOB_DIR/exports/splat.clean.ply"' in text
    assert '"$JOB_DIR/exports/splat.clean.viewer.json"' in text
    assert 'chmod a+r "$JOB_DIR/exports/splat.clean.ply"' in text
    assert 'chmod a+r "$JOB_DIR/exports/splat.clean.viewer.json"' in text
    assert 'chmod a+r "$JOB_DIR/engine_contract.json"' in text
    assert 'chmod a+r "$JOB_DIR/evidence/appearance_summary.json"' in text
    assert 'chmod a+r "$JOB_DIR/evidence/splat_summary.json"' in text
    assert 'chmod a+r "$JOB_DIR/validation/validation_report.json"' in text
    assert 'chmod a+r "$JOB_DIR/validation/qa_validation_report.json"' in text
    assert 'chmod a+r "$JOB_DIR/compare/compare_report.json"' in text


def test_run_pipeline_resume_reuses_existing_heavy_outputs_only_when_requested():
    text = read_script("run_mvp_pipeline.sh")

    assert 'RESUME_MODE="${GS_RESUME:-0}"' in text
    assert "reuse_stage()" in text
    assert 'if [ "$RESUME_MODE" = "1" ] && [ -f "$JOB_DIR/processed/transforms.json" ]; then' in text
    assert 'reused processed/transforms.json' in text
    assert 'if [ "$RESUME_MODE" = "1" ] && [ -f "$JOB_DIR/exports/splat.ply" ]; then' in text
    assert 'reused exports/splat.ply' in text
    assert 'if [ "$RESUME_MODE" = "1" ] && [ -f "$JOB_DIR/exports/splat.clean.ply" ] && [ -f "$JOB_DIR/exports/splat.clean.viewer.json" ]; then' in text
    assert 'reused exports/splat.clean.ply' in text


def test_run_pipeline_rejects_symlink_job_dir_outside_uploads(tmp_path):
    outside = tmp_path / "outside-job-target"
    outside.mkdir()
    project = tmp_path / "fake-project"
    scripts = project / "scripts"
    uploads = project / "uploads"
    scripts.mkdir(parents=True)
    uploads.mkdir()
    pipeline = scripts / "run_mvp_pipeline.sh"
    pipeline.write_text(read_script("run_mvp_pipeline.sh"))
    input_file = project / "README.md"
    input_file.write_text("fake input")
    job_link = uploads / "pytest-symlink-job"
    if job_link.exists() or job_link.is_symlink():
        job_link.unlink()
    job_link.symlink_to(outside, target_is_directory=True)

    try:
        result = subprocess.run(
            [
                "bash",
                str(pipeline),
                str(input_file),
                str(job_link),
            ],
            cwd=project,
            text=True,
            capture_output=True,
            check=False,
        )
    finally:
        if job_link.exists() or job_link.is_symlink():
            job_link.unlink()

    assert result.returncode == 1
    assert "job_dir must be under" in result.stderr
