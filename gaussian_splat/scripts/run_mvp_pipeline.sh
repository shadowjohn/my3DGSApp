#!/usr/bin/env bash
set -euo pipefail

INPUT_VIDEO=${1:?usage: run_mvp_pipeline.sh input_video job_dir}
JOB_DIR=${2:?usage: run_mvp_pipeline.sh input_video job_dir}
ORIGIN_LNG="${3:-120.6647066}"
ORIGIN_LAT="${4:-24.1504731}"
ORIGIN_HEIGHT="${5:-0.0}"
FRAME_CANDIDATE_FPS="${GS_FRAME_CANDIDATE_FPS:-12}"
FRAME_TARGET_FPS="${GS_FRAME_TARGET_FPS:-3}"
FRAME_MAX_FRAMES="${GS_FRAME_MAX_FRAMES:-180}"
FRAME_WIDTH="${GS_FRAME_WIDTH:-1600}"
FRAME_MIN_FRAMES="${GS_FRAME_MIN_FRAMES:-8}"
FRAME_SELECTOR="${GS_FRAME_SELECTOR:-1}"
RESUME_MODE="${GS_RESUME:-0}"
PIPELINE_MODE="${GS_PIPELINE_MODE:-fast}"
PREMIUM_MESH_METHOD="${GS_PREMIUM_MESH_METHOD:-auto}"
PREMIUM_POINT_LIMIT="${GS_PREMIUM_POINT_LIMIT:-0}"
PREMIUM_TARGET_FACES="${GS_PREMIUM_TARGET_FACES:-100000}"
PREMIUM_SKIP_BLENDER="${GS_PREMIUM_SKIP_BLENDER:-0}"
TRENCH_MODE="${GS_TRENCH_MODE:-0}"
GEOREF_MODE="${GS_GEOREF_MODE:-none}"
GEOREF_CRS="${GS_GEOREF_CRS:-}"
GEOREF_LAT="${GS_GEOREF_LAT:-}"
GEOREF_LNG="${GS_GEOREF_LNG:-}"
GEOREF_HEIGHT="${GS_GEOREF_HEIGHT:-}"
GEOREF_HEADING="${GS_GEOREF_HEADING:-}"
GEOREF_SCALE="${GS_GEOREF_SCALE:-}"
GS_PYTHON="${GS_PYTHON:-/DATA/conda_vm/gs_scene/bin/python}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAGED_INPUT="$JOB_DIR/input/input.mp4"
INPUT_IS_IMAGE_DIR=0
TIMING_REPORT="$JOB_DIR/timing_report.json"
UPLOADS_DIR="$PROJECT_ROOT/uploads"
JOB_PARENT="$(dirname "$JOB_DIR")"
UPLOADS_REAL="$(realpath "$UPLOADS_DIR")"
JOB_PARENT_REAL="$(realpath -m "$JOB_PARENT")"
JOB_DIR_REAL="$(realpath -m "$JOB_DIR")"
PIPELINE_FINISHED=0

timing_event() {
  local command="$1"
  shift
  "$GS_PYTHON" "$PROJECT_ROOT/scripts/pipeline_timing.py" "$command" "$TIMING_REPORT" "$@"
}

timing_fail() {
  if [ "$PIPELINE_FINISHED" = "0" ]; then
    timing_event fail pipeline failed "Pipeline failed" || true
  fi
}

run_stage() {
  local key="$1"
  local label="$2"
  shift 2
  echo "[timing] START ${key} ${label}" >&2
  timing_event start "$key" "$label"
  set +e
  "$@"
  local exit_code=$?
  set -e
  if [ "$exit_code" -eq 0 ]; then
    timing_event finish "$key" success "OK"
    echo "[timing] END ${key} success" >&2
  else
    timing_event finish "$key" failed "exit ${exit_code}"
    echo "[timing] END ${key} failed" >&2
  fi
  return "$exit_code"
}

run_stage_capture() {
  local key="$1"
  local label="$2"
  shift 2
  echo "[timing] START ${key} ${label}" >&2
  timing_event start "$key" "$label"
  local output
  set +e
  output="$("$@")"
  local exit_code=$?
  set -e
  if [ "$exit_code" -eq 0 ]; then
    timing_event finish "$key" success "OK"
    echo "[timing] END ${key} success" >&2
  else
    timing_event finish "$key" failed "exit ${exit_code}"
    echo "[timing] END ${key} failed" >&2
  fi
  printf '%s\n' "$output"
  return "$exit_code"
}

reuse_stage() {
  local key="$1"
  local label="$2"
  local message="$3"
  echo "[timing] REUSE ${key} ${message}" >&2
  timing_event start "$key" "$label"
  timing_event finish "$key" success "$message"
}

run_trench_outputs() {
  run_stage trench_input "outdoor input manifest" "$GS_PYTHON" "$PROJECT_ROOT/scripts/outdoor_intake.py" "$STAGED_INPUT" "$JOB_DIR/input_manifest.json" >&2
  run_stage trench_coverage "trench coverage report" "$GS_PYTHON" "$PROJECT_ROOT/scripts/build_trench_coverage_report.py" "$JOB_DIR" >&2

  local georef_args=("$JOB_DIR/georef.json" "--mode" "$GEOREF_MODE")
  if [ -n "$GEOREF_CRS" ]; then georef_args+=("--crs" "$GEOREF_CRS"); fi
  if [ -n "$GEOREF_LAT" ]; then georef_args+=("--lat" "$GEOREF_LAT"); fi
  if [ -n "$GEOREF_LNG" ]; then georef_args+=("--lng" "$GEOREF_LNG"); fi
  if [ -n "$GEOREF_HEIGHT" ]; then georef_args+=("--height" "$GEOREF_HEIGHT"); fi
  if [ -n "$GEOREF_HEADING" ]; then georef_args+=("--heading" "$GEOREF_HEADING"); fi
  if [ -n "$GEOREF_SCALE" ]; then georef_args+=("--scale" "$GEOREF_SCALE"); fi

  run_stage georef "georef metadata" "$GS_PYTHON" "$PROJECT_ROOT/scripts/build_georef_metadata.py" "${georef_args[@]}" >&2
  run_stage trench_delivery "trench delivery export" "$GS_PYTHON" "$PROJECT_ROOT/scripts/build_trench_delivery.py" "$JOB_DIR" >&2
  run_stage trench_qa "trench engineering QA" "$GS_PYTHON" "$PROJECT_ROOT/scripts/build_trench_qa_report.py" "$JOB_DIR" >&2
}

run_premium_outputs() {
  local compare_args=(
    "--job-dir" "$JOB_DIR"
    "--mesh-method" "$PREMIUM_MESH_METHOD"
    "--point-limit" "$PREMIUM_POINT_LIMIT"
    "--target-faces" "$PREMIUM_TARGET_FACES"
  )
  if [ "$PREMIUM_SKIP_BLENDER" = "1" ]; then
    compare_args+=("--skip-blender")
  fi
  run_stage compare_bundle "premium compare bundle" "$GS_PYTHON" "$PROJECT_ROOT/scripts/build_compare_bundle.py" "${compare_args[@]}" >&2
}

finalize_outputs() {
  "$GS_PYTHON" "$PROJECT_ROOT/scripts/write_default_transform.py" "$(basename "$JOB_DIR")" "$JOB_DIR/transform.json" --lng "$ORIGIN_LNG" --lat "$ORIGIN_LAT" --height "$ORIGIN_HEIGHT" >&2 || return
  "$GS_PYTHON" "$PROJECT_ROOT/scripts/build_qa_report.py" "$(basename "$JOB_DIR")" "$JOB_DIR" >&2 || return
}

case "$JOB_PARENT_REAL" in
  "$UPLOADS_REAL"|"$UPLOADS_REAL"/*) ;;
  *)
    echo "job_dir must be under $UPLOADS_DIR: $JOB_DIR" >&2
    exit 1
    ;;
esac

case "$JOB_DIR_REAL" in
  "$UPLOADS_REAL"/*) ;;
  *)
    echo "job_dir must be under $UPLOADS_DIR: $JOB_DIR" >&2
    exit 1
    ;;
esac

case "$PIPELINE_MODE" in
  fast|qa)
    if [ -z "${GS_TRAIN_MAX_ITERATIONS:-}" ]; then
      echo "GS_PIPELINE_MODE=$PIPELINE_MODE requires GS_TRAIN_MAX_ITERATIONS; refusing uncapped preview/diagnostic training." >&2
      exit 2
    fi
    ;;
  premium) ;;
  *)
    echo "unsupported GS_PIPELINE_MODE: $PIPELINE_MODE" >&2
    exit 2
    ;;
esac
if [ ! -x "$GS_PYTHON" ]; then
  echo "GS_PYTHON not executable: $GS_PYTHON" >&2
  exit 2
fi
if [ -n "${GS_TRAIN_MAX_ITERATIONS:-}" ]; then
  if ! [[ "$GS_TRAIN_MAX_ITERATIONS" =~ ^[1-9][0-9]*$ ]]; then
    echo "invalid GS_TRAIN_MAX_ITERATIONS: $GS_TRAIN_MAX_ITERATIONS" >&2
    exit 2
  fi
  echo "[config] GS_TRAIN_MAX_ITERATIONS=$GS_TRAIN_MAX_ITERATIONS" >&2
fi

mkdir -p "$JOB_DIR/input" "$JOB_DIR/images" "$JOB_DIR/processed" "$JOB_DIR/outputs" "$JOB_DIR/exports"
chmod a+rx "$JOB_PARENT"
chmod a+rx "$JOB_DIR" "$JOB_DIR/exports"
timing_event init pipeline "Gaussian Splat pipeline"
trap timing_fail ERR
if [ -d "$INPUT_VIDEO" ]; then
  INPUT_IS_IMAGE_DIR=1
  STAGED_INPUT="$INPUT_VIDEO"
fi
if [ "$INPUT_IS_IMAGE_DIR" = "0" ] && { [ ! -e "$STAGED_INPUT" ] || [ "$(realpath "$INPUT_VIDEO")" != "$(realpath "$STAGED_INPUT")" ]; }; then
  cp "$INPUT_VIDEO" "$STAGED_INPUT"
fi

if [ "$INPUT_IS_IMAGE_DIR" = "1" ]; then
  IMAGE_COUNT="$(find "$JOB_DIR/images" -maxdepth 1 -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' \) | wc -l)"
  if [ "$IMAGE_COUNT" -lt "$FRAME_MIN_FRAMES" ]; then
    echo "uploaded image set has fewer than $FRAME_MIN_FRAMES JPG/PNG files" >&2
    exit 2
  fi
  rm -f "$JOB_DIR/frame_quality_report.json"
  reuse_stage frame_select "uploaded image set" "using $IMAGE_COUNT uploaded images"
elif [ "$FRAME_SELECTOR" = "0" ]; then
  find "$JOB_DIR/images" -maxdepth 1 -type f -regextype posix-extended -regex ".*/frame_[0-9]{5}\.(jpg|jpeg|png)" -delete
  rm -f "$JOB_DIR/frame_quality_report.json"
  run_stage legacy_extract "legacy fps frame extraction" "$GS_PYTHON" "$PROJECT_ROOT/scripts/extract_frames.py" "$STAGED_INPUT" "$JOB_DIR/images" --fps "$FRAME_TARGET_FPS" --width "$FRAME_WIDTH" --max-frames "$FRAME_MAX_FRAMES" >&2
else
  run_stage frame_select "frame quality selection" "$GS_PYTHON" "$PROJECT_ROOT/scripts/frame_quality_select.py" \
    "$STAGED_INPUT" \
    "$JOB_DIR/candidates" \
    "$JOB_DIR/images" \
    --report "$JOB_DIR/frame_quality_report.json" \
    --candidate-fps "$FRAME_CANDIDATE_FPS" \
    --target-fps "$FRAME_TARGET_FPS" \
    --max-frames "$FRAME_MAX_FRAMES" \
    --min-candidates "$FRAME_MIN_FRAMES" \
    --min-selected "$FRAME_MIN_FRAMES" \
    --width "$FRAME_WIDTH" >&2
fi
if [ "$RESUME_MODE" = "1" ] && [ -f "$JOB_DIR/processed/transforms.json" ]; then
  TRANSFORMS_PATH="$JOB_DIR/processed/transforms.json"
  reuse_stage sfm "SfM pose estimation" "reused processed/transforms.json"
else
  TRANSFORMS_PATH="$(run_stage_capture sfm "SfM pose estimation" bash "$PROJECT_ROOT/scripts/process_nerfstudio.sh" "$JOB_DIR/images" "$JOB_DIR/processed")"
fi
test -f "$TRANSFORMS_PATH"
if [ -f "$JOB_DIR/frame_quality_report.json" ]; then
  run_stage frame_colmap "frame SfM annotation" "$GS_PYTHON" "$PROJECT_ROOT/scripts/annotate_frame_quality_colmap.py" "$JOB_DIR/frame_quality_report.json" "$TRANSFORMS_PATH" >&2
fi
TRAIN_PROCESSED_DIR="$JOB_DIR/processed"
if [ "${GS_FRAME_ENHANCE:-0}" = "1" ]; then
  run_stage enhance "Real-ESRGAN frame enhancement" "$GS_PYTHON" "$PROJECT_ROOT/scripts/enhance_frames_realesrgan.py" \
    "$JOB_DIR/images" \
    "$JOB_DIR/enhanced_images" \
    --scale "${GS_FRAME_ENHANCE_SCALE:-2}" \
    --model-name "${GS_FRAME_ENHANCE_MODEL:-realesrgan-x4plus}" >&2
  run_stage prepare_training_images "prepare enhanced training images" "$GS_PYTHON" "$PROJECT_ROOT/scripts/prepare_enhanced_training_dataset.py" \
    "$JOB_DIR/processed" \
    "$JOB_DIR/enhanced_images" \
    "$JOB_DIR/processed_enhanced" >&2
  TRAIN_PROCESSED_DIR="$JOB_DIR/processed_enhanced"
fi
if [ "$RESUME_MODE" = "1" ] && [ -f "$JOB_DIR/exports/splat.ply" ]; then
  SPLAT_PATH="$JOB_DIR/exports/splat.ply"
  reuse_stage train "splatfacto training" "reused exports/splat.ply"
  reuse_stage export "splat export" "reused exports/splat.ply"
else
  CONFIG_PATH="$(run_stage_capture train "splatfacto training" bash "$PROJECT_ROOT/scripts/train_splat.sh" "$TRAIN_PROCESSED_DIR" "$JOB_DIR/outputs")"
  SPLAT_PATH="$(run_stage_capture export "splat export" bash "$PROJECT_ROOT/scripts/export_splat.sh" "$CONFIG_PATH" "$JOB_DIR/exports")"
fi
if [ "$RESUME_MODE" = "1" ] && [ -f "$JOB_DIR/exports/splat.clean.ply" ] && [ -f "$JOB_DIR/exports/splat.clean.viewer.json" ]; then
  reuse_stage cleanup "splat cleanup" "reused exports/splat.clean.ply"
else
  run_stage cleanup "splat cleanup" "$GS_PYTHON" "$PROJECT_ROOT/scripts/filter_splat_ply.py" "$SPLAT_PATH" "$JOB_DIR/exports/splat.clean.ply" --meta "$JOB_DIR/exports/splat.clean.viewer.json" >&2
fi
run_stage finalize "viewer metadata and QA" finalize_outputs
if [ "$TRENCH_MODE" = "1" ]; then
  run_trench_outputs
fi
run_stage appearance_summary "Gaussian appearance summary" "$GS_PYTHON" "$PROJECT_ROOT/scripts/build_gaussian_appearance_summary.py" "$JOB_DIR" >&2
run_stage engine_contract "Gaussian engine contract" "$GS_PYTHON" "$PROJECT_ROOT/scripts/build_gaussian_engine_contract.py" "$JOB_DIR" --mode "$PIPELINE_MODE" >&2
run_stage validation_report "validation report" "$GS_PYTHON" "$PROJECT_ROOT/scripts/build_validation_report.py" "$JOB_DIR" >&2
if [ "$PIPELINE_MODE" = "qa" ]; then
  run_stage qa_validation_report "QA validation report" "$GS_PYTHON" "$PROJECT_ROOT/scripts/build_qa_validation_report.py" "$JOB_DIR" >&2
fi
if [ "$PIPELINE_MODE" = "premium" ]; then
  run_premium_outputs
fi
run_stage delivery_manifest "delivery manifest" "$GS_PYTHON" "$PROJECT_ROOT/scripts/build_delivery_manifest.py" "$JOB_DIR" --pipeline-mode "$PIPELINE_MODE" >&2
timing_event finish pipeline success "Pipeline complete"
chmod a+r "$SPLAT_PATH" "$JOB_DIR/transform.json" "$JOB_DIR/qa_report.json" "$JOB_DIR/timing_report.json"
if [ -f "$JOB_DIR/exports/splat.clean.ply" ]; then
  chmod a+r "$JOB_DIR/exports/splat.clean.ply"
fi
if [ -f "$JOB_DIR/exports/splat.clean.viewer.json" ]; then
  chmod a+r "$JOB_DIR/exports/splat.clean.viewer.json"
fi
if [ -f "$JOB_DIR/input_manifest.json" ]; then
  chmod a+r "$JOB_DIR/input_manifest.json"
fi
if [ -f "$JOB_DIR/trench_coverage_report.json" ]; then
  chmod a+r "$JOB_DIR/trench_coverage_report.json"
fi
if [ -f "$JOB_DIR/georef.json" ]; then
  chmod a+r "$JOB_DIR/georef.json"
fi
if [ -f "$JOB_DIR/trench_qa_report.json" ]; then
  chmod a+r "$JOB_DIR/trench_qa_report.json"
fi
if [ -f "$JOB_DIR/delivery_manifest.json" ]; then
  chmod a+r "$JOB_DIR/delivery_manifest.json"
fi
if [ -f "$JOB_DIR/engine_contract.json" ]; then
  chmod a+r "$JOB_DIR/engine_contract.json"
fi
if [ -f "$JOB_DIR/evidence/appearance_summary.json" ]; then
  chmod a+r "$JOB_DIR/evidence/appearance_summary.json"
fi
if [ -f "$JOB_DIR/evidence/splat_summary.json" ]; then
  chmod a+r "$JOB_DIR/evidence/splat_summary.json"
fi
if [ -f "$JOB_DIR/validation/validation_report.json" ]; then
  chmod a+r "$JOB_DIR/validation/validation_report.json"
fi
if [ -f "$JOB_DIR/validation/qa_validation_report.json" ]; then
  chmod a+r "$JOB_DIR/validation/qa_validation_report.json"
fi
if [ -f "$JOB_DIR/compare/compare_report.json" ]; then
  chmod a+r "$JOB_DIR/compare/compare_report.json"
fi
if [ -f "$JOB_DIR/exports/splat.trench.ply" ]; then
  chmod a+r "$JOB_DIR/exports/splat.trench.ply"
fi
if [ -f "$JOB_DIR/exports/splat.trench.viewer.json" ]; then
  chmod a+r "$JOB_DIR/exports/splat.trench.viewer.json"
fi
PIPELINE_FINISHED=1

echo "$SPLAT_PATH"
