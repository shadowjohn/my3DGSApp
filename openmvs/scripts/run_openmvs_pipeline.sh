#!/usr/bin/env bash
set -euo pipefail

INPUT_FILE=${1:?usage: run_openmvs_pipeline.sh input_file job_dir}
JOB_DIR=${2:?usage: run_openmvs_pipeline.sh input_file job_dir}
INPUT_FILE="$(realpath -m "$INPUT_FILE")"
JOB_DIR="$(realpath -m "$JOB_DIR")"
ORIGIN_LNG="${3:-120.61022}"
ORIGIN_LAT="${4:-24.110946}"
ORIGIN_HEIGHT="${5:-0.0}"
OPENMVS_CONDA_ENV="${OPENMVS_CONDA_ENV:-/DATA/conda_vm/openmvs}"
OPENMVS_BIN_DIR="${OPENMVS_BIN_DIR:-$OPENMVS_CONDA_ENV/bin}"
COLMAP_BIN_DIR="${COLMAP_BIN_DIR:-$OPENMVS_CONDA_ENV/bin}"
OVM_PIPELINE_MODE="${OVM_PIPELINE_MODE:-}"
OPENMVS_NATIVE_ENV="${OPENMVS_NATIVE_ENV:-/DATA/conda_vm/openmvs}"
OPENMVS_NATIVE_BIN_DIR="${OPENMVS_NATIVE_BIN_DIR:-$OPENMVS_NATIVE_ENV/bin/OpenMVS}"
OPENMVS_NATIVE_LIB_DIR="${OPENMVS_NATIVE_LIB_DIR:-$OPENMVS_NATIVE_ENV/lib/OpenMVS}"
OPENMVS_NATIVE_DEPS_LIB_DIR="${OPENMVS_NATIVE_DEPS_LIB_DIR:-/DATA/conda_vm/openmvs_deps/lib}"
QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"
OVM_PREFERRED_CUDA_VERSION="${OVM_PREFERRED_CUDA_VERSION:-12.8}"
COLMAP_GPU_MODE="${COLMAP_GPU_MODE:-${COLMAP_USE_GPU:-auto}}"
COLMAP_GPU_PROBE="${COLMAP_GPU_PROBE:-1}"
OPENMVS_CUDA_DEVICE="${OPENMVS_CUDA_DEVICE:--1}"
OVM_TEXTURE_EMPTY_COLOR="${OVM_TEXTURE_EMPTY_COLOR:-16777215}"
OVM_TEXTURE_COST_SMOOTHNESS_RATIO="${OVM_TEXTURE_COST_SMOOTHNESS_RATIO:-1}"
OVM_TEXTURE_SHARPNESS_WEIGHT="${OVM_TEXTURE_SHARPNESS_WEIGHT:-0.35}"
OVM_TEXTURE_REPAIR_MODE="${OVM_TEXTURE_REPAIR_MODE:-auto}"
OVM_TEXTURE_REPAIR_TRIGGER_BLACK_RATIO="${OVM_TEXTURE_REPAIR_TRIGGER_BLACK_RATIO:-0.20}"
OVM_TEXTURE_REPAIR_MAX_WHITE_RATIO="${OVM_TEXTURE_REPAIR_MAX_WHITE_RATIO:-0.42}"
OVM_TEXTURE_REPAIR_BLACK_THRESHOLD="${OVM_TEXTURE_REPAIR_BLACK_THRESHOLD:-18}"
OVM_TEXTURE_REPAIR_INPAINT_RADIUS="${OVM_TEXTURE_REPAIR_INPAINT_RADIUS:-5}"
OVM_QUALITY_PRESET="${OVM_QUALITY_PRESET:-normal}"
COLMAP_DENSE_MAX_IMAGE_SIZE="${COLMAP_DENSE_MAX_IMAGE_SIZE:-2000}"
COLMAP_UNDISTORT_ROI_MIN_X="${COLMAP_UNDISTORT_ROI_MIN_X:-0}"
COLMAP_UNDISTORT_ROI_MIN_Y="${COLMAP_UNDISTORT_ROI_MIN_Y:-0}"
COLMAP_UNDISTORT_ROI_MAX_X="${COLMAP_UNDISTORT_ROI_MAX_X:-1}"
COLMAP_UNDISTORT_ROI_MAX_Y="${COLMAP_UNDISTORT_ROI_MAX_Y:-1}"
OVM_MASK_MODE="${OVM_MASK_MODE:-none}"
OVM_MASK_IGNORE_LABEL="${OVM_MASK_IGNORE_LABEL:-0}"
OVM_MASK_AUTO_RECT="${OVM_MASK_AUTO_RECT:-0.12,0.08,0.88,0.96}"
OVM_CREATE_STRUCTURE_DETECTOR_TYPE="${OVM_CREATE_STRUCTURE_DETECTOR_TYPE:-SIFT}"
OVM_CREATE_STRUCTURE_MAX_VIEWS_PER_CLUSTER="${OVM_CREATE_STRUCTURE_MAX_VIEWS_PER_CLUSTER:-0}"
OVM_CREATE_STRUCTURE_UNDISTORT_EXTENSION="${OVM_CREATE_STRUCTURE_UNDISTORT_EXTENSION:-.jpg}"
OVM_FRAME_FPS="${OVM_FRAME_FPS:-3}"
OVM_FRAME_WIDTH="${OVM_FRAME_WIDTH:-1600}"
OVM_MAX_FRAMES="${OVM_MAX_FRAMES:-240}"
OVM_MIN_FRAMES="${OVM_MIN_FRAMES:-8}"
OVM_REFINE_SCALES="${OVM_REFINE_SCALES:-1}"
OVM_REFINE_MAX_FACE_AREA="${OVM_REFINE_MAX_FACE_AREA:-16}"
OVM_OMP_NUM_THREADS="${OVM_OMP_NUM_THREADS:-16}"
OVM_PRODUCT_TEXTURE_SIZE="${OVM_PRODUCT_TEXTURE_SIZE:-}"
OVM_PRODUCT_OUTPUT_DIR="${OVM_PRODUCT_OUTPUT_DIR:-}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UPLOADS_DIR="$PROJECT_ROOT/uploads"
JOB_PARENT="$(dirname "$JOB_DIR")"
UPLOADS_REAL="$(realpath -m "$UPLOADS_DIR")"
JOB_PARENT_REAL="$(realpath -m "$JOB_PARENT")"
JOB_DIR_REAL="$(realpath -m "$JOB_DIR")"
IMAGES_DIR="$JOB_DIR/images"
COLMAP_DIR="$JOB_DIR/colmap"
SPARSE_DIR="$COLMAP_DIR/sparse"
DENSE_DIR="$COLMAP_DIR/dense"
MVS_DIR="$JOB_DIR/mvs"
EXPORTS_DIR="$JOB_DIR/exports"
SELECTED_SPARSE_DIR="$SPARSE_DIR/0"
PRIMARY_GLB_RELATIVE="exports/model.glb"
COLMAP_DATABASE="$COLMAP_DIR/database.db"
COLMAP_GPU_PROBE_LOG="$JOB_DIR/gpu_probe.log"
PIPELINE_MODE_FILE="$JOB_DIR/input/pipeline_mode.txt"
PIPELINE_FINISHED=0

export PATH="$COLMAP_BIN_DIR:$OPENMVS_BIN_DIR:$OPENMVS_CONDA_ENV/bin:$PATH"
export QT_QPA_PLATFORM
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-$OVM_OMP_NUM_THREADS}"

function prepend_env_path() {
  local var_name="$1"
  local dir="$2"
  local current="${!var_name-}"
  if [ ! -d "$dir" ]; then
    return 1
  fi
  case ":$current:" in
    *":$dir:"*) ;;
    *) export "$var_name=$dir${current:+:$current}" ;;
  esac
}

function configure_cuda_runtime() {
  local candidates=()
  local cuda_root=""
  local fallback_root=""
  if [ -n "${OVM_CUDA_ROOT:-}" ]; then
    candidates+=("$OVM_CUDA_ROOT")
  fi
  candidates+=(
    "/usr/local/cuda-${OVM_PREFERRED_CUDA_VERSION}"
    "$OPENMVS_CONDA_ENV"
    "/DATA/conda_vm/gs_scene"
    "/usr/local/cuda"
    "/usr"
  )

  for cuda_root in "${candidates[@]}"; do
    [ -d "$cuda_root" ] || continue
    [ -x "$cuda_root/bin/nvcc" ] || continue
    if [ -z "$fallback_root" ]; then
      fallback_root="$cuda_root"
    fi

    local version_text=""
    if [ -x "$cuda_root/bin/nvcc" ]; then
      version_text="$("$cuda_root/bin/nvcc" --version 2>/dev/null || true)"
    fi

    if [ -n "${OVM_CUDA_ROOT:-}" ] && [ "$cuda_root" = "$OVM_CUDA_ROOT" ]; then
      break
    fi
    if [ "$cuda_root" = "/usr/local/cuda-${OVM_PREFERRED_CUDA_VERSION}" ]; then
      break
    fi
    if printf '%s' "$version_text" | grep -q "release ${OVM_PREFERRED_CUDA_VERSION}"; then
      break
    fi
    if find "$cuda_root" -maxdepth 3 -name "libcudart.so*${OVM_PREFERRED_CUDA_VERSION}*" -print -quit 2>/dev/null | grep -q .; then
      break
    fi
    cuda_root=""
  done

  if [ -z "$cuda_root" ] && [ -n "$fallback_root" ]; then
    cuda_root="$fallback_root"
  fi
  if [ -z "$cuda_root" ]; then
    echo "[env-check] CUDA runtime not found; COLMAP will use CPU" >&2
    return 1
  fi

  prepend_env_path PATH "$cuda_root/bin" || true
  if [ -d "$cuda_root/targets/x86_64-linux/lib" ]; then
    prepend_env_path LD_LIBRARY_PATH "$cuda_root/targets/x86_64-linux/lib" || true
  else
    prepend_env_path LD_LIBRARY_PATH "$cuda_root/lib64" || true
    prepend_env_path LD_LIBRARY_PATH "$cuda_root/lib" || true
  fi
  export OVM_SELECTED_CUDA_ROOT="$cuda_root"
  echo "[env-check] CUDA runtime selected: $cuda_root" >&2
}

function normalize_pipeline_mode() {
  local mode="$1"
  mode="$(printf '%s' "$mode" | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')"
  case "$mode" in
    native|openmvs_native|openmvs-native|createstructure|create_structure) echo "openmvs_native" ;;
    "") echo "openmvs_native" ;;
    standard|colmap|interface_colmap|interface-colmap) echo "colmap" ;;
    *)
      echo "[env-check] Unknown OVM_PIPELINE_MODE=$1; using openmvs_native" >&2
      echo "openmvs_native"
      ;;
  esac
}

function load_pipeline_mode() {
  local mode="$OVM_PIPELINE_MODE"
  if [ -z "$mode" ] && [ -f "$PIPELINE_MODE_FILE" ]; then
    mode="$(head -n 1 "$PIPELINE_MODE_FILE" 2>/dev/null || true)"
  fi
  OVM_PIPELINE_MODE="$(normalize_pipeline_mode "$mode")"
  export OVM_PIPELINE_MODE
  echo "[env-check] OpenMVS pipeline mode: $OVM_PIPELINE_MODE" >&2
}

function apply_quality_preset() {
  OVM_QUALITY_PRESET="$(printf '%s' "$OVM_QUALITY_PRESET" | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')"
  case "$OVM_QUALITY_PRESET" in
    fast)
      OVM_FRAME_FPS=2
      OVM_FRAME_WIDTH=1400
      OVM_MAX_FRAMES=160
      COLMAP_DENSE_MAX_IMAGE_SIZE=1600
      OVM_REFINE_SCALES=1
      OVM_REFINE_MAX_FACE_AREA=24
      OVM_TEXTURE_SHARPNESS_WEIGHT=0.25
      ;;
    normal)
      OVM_FRAME_FPS=3
      OVM_FRAME_WIDTH=1600
      OVM_MAX_FRAMES=240
      COLMAP_DENSE_MAX_IMAGE_SIZE=2000
      OVM_REFINE_SCALES=1
      OVM_REFINE_MAX_FACE_AREA=16
      OVM_TEXTURE_SHARPNESS_WEIGHT=0.35
      ;;
    high)
      OVM_FRAME_FPS=4
      OVM_FRAME_WIDTH=2200
      OVM_MAX_FRAMES=240
      COLMAP_DENSE_MAX_IMAGE_SIZE=3200
      OVM_REFINE_SCALES=2
      OVM_REFINE_MAX_FACE_AREA=8
      OVM_TEXTURE_SHARPNESS_WEIGHT=0.55
      ;;
    *)
      echo "[env-check] Unknown OVM_QUALITY_PRESET=$OVM_QUALITY_PRESET; using normal" >&2
      OVM_QUALITY_PRESET=normal
      apply_quality_preset
      return
      ;;
  esac
  export OVM_QUALITY_PRESET OVM_FRAME_FPS OVM_FRAME_WIDTH OVM_MAX_FRAMES COLMAP_DENSE_MAX_IMAGE_SIZE
  export OVM_REFINE_SCALES OVM_REFINE_MAX_FACE_AREA OVM_TEXTURE_SHARPNESS_WEIGHT
  echo "[env-check] quality preset: $OVM_QUALITY_PRESET" >&2
}

function configure_openmvs_native_runtime() {
  prepend_env_path PATH "$OPENMVS_NATIVE_BIN_DIR" || true
  prepend_env_path PATH "$OPENMVS_NATIVE_ENV/bin" || true
  prepend_env_path LD_LIBRARY_PATH "$OPENMVS_NATIVE_LIB_DIR" || true
  prepend_env_path LD_LIBRARY_PATH "$OPENMVS_NATIVE_DEPS_LIB_DIR" || true
  prepend_env_path LD_LIBRARY_PATH "$OPENMVS_NATIVE_ENV/targets/x86_64-linux/lib" || true
  prepend_env_path LD_LIBRARY_PATH "$OPENMVS_NATIVE_ENV/lib/gcc/x86_64-conda-linux-gnu/14.3.0" || true
  prepend_env_path LD_LIBRARY_PATH "$OPENMVS_NATIVE_ENV/lib" || true
  echo "[env-check] OpenMVS native env selected: $OPENMVS_NATIVE_ENV" >&2
}

run_stage() {
  local key="$1"
  local label="$2"
  shift 2
  echo "[timing] START ${key} ${label}" >&2
  set +e
  if [ -x /usr/bin/time ]; then
    /usr/bin/time -v "$@"
  else
    echo "[timing] /usr/bin/time -v unavailable; resource usage will not be logged" >&2
    "$@"
  fi
  local exit_code=$?
  set -e
  if [ "$exit_code" -eq 0 ]; then
    echo "[timing] END ${key} success" >&2
  else
    echo "[timing] END ${key} failed" >&2
  fi
  return "$exit_code"
}

function colmap_supports_gpu_options() {
  colmap feature_extractor -h 2>&1 | grep -q -- "--SiftExtraction.use_gpu" &&
    colmap exhaustive_matcher -h 2>&1 | grep -q -- "--SiftMatching.use_gpu"
}

function log_colmap_binary_status() {
  local colmap_path=""
  local version_text=""
  colmap_path="$(command -v colmap || true)"
  if [ -z "$colmap_path" ]; then
    echo "[env-check] COLMAP binary selected: missing" >&2
    return 1
  fi
  version_text="$(colmap -h 2>&1 | head -n 2 | tr '\n' ' ' || true)"
  echo "[env-check] COLMAP binary selected: $colmap_path ${version_text}" >&2
}

function nvidia_gpu_visible() {
  command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1
}

function openmvs_binary_cuda_enabled() {
  local densify_path=""
  densify_path="$(command -v DensifyPointCloud || true)"
  [ -n "$densify_path" ] || return 1
  if ldd "$densify_path" 2>/dev/null | grep -Eiq 'cuda|cudart|curand'; then
    return 0
  fi
  strings "$densify_path" 2>/dev/null | grep -Eiq 'gpu-device|cuda-device|CUDA device|DensifyPointCloudCUDA|RefineMeshCUDA'
}

function reset_colmap_database() {
  rm -f "$COLMAP_DATABASE" "$COLMAP_DATABASE-shm" "$COLMAP_DATABASE-wal"
}

function run_colmap_gpu_probe() {
  local probe_dir="$JOB_DIR/.gpu_probe"
  rm -rf "$probe_dir"
  mkdir -p "$probe_dir/images"
  : > "$COLMAP_GPU_PROBE_LOG"

  echo "[env-check] Running COLMAP GPU probe" >&2
  if ! ffmpeg -v error -f lavfi -i "testsrc=size=320x240:rate=1" -frames:v 2 "$probe_dir/images/probe_%02d.jpg" >>"$COLMAP_GPU_PROBE_LOG" 2>&1; then
    echo "[env-check] GPU probe image generation failed; falling back to CPU" >&2
    return 1
  fi
  if ! colmap feature_extractor \
    --database_path "$probe_dir/database.db" \
    --image_path "$probe_dir/images" \
    --ImageReader.single_camera 1 \
    --SiftExtraction.use_gpu 1 \
    --SiftExtraction.max_num_features 256 >>"$COLMAP_GPU_PROBE_LOG" 2>&1; then
    echo "[env-check] COLMAP GPU feature probe failed; falling back to CPU" >&2
    return 1
  fi
  if ! colmap exhaustive_matcher \
    --database_path "$probe_dir/database.db" \
    --SiftMatching.use_gpu 1 >>"$COLMAP_GPU_PROBE_LOG" 2>&1; then
    echo "[env-check] COLMAP GPU matcher probe failed; falling back to CPU" >&2
    return 1
  fi

  rm -rf "$probe_dir"
  echo "[env-check] COLMAP GPU probe passed" >&2
}

function detect_colmap_gpu_mode() {
  local mode
  mode="$(printf '%s' "$COLMAP_GPU_MODE" | tr '[:upper:]' '[:lower:]')"
  case "$mode" in
    0|false|cpu|off)
      echo "[env-check] COLMAP GPU disabled by COLMAP_GPU_MODE=$COLMAP_GPU_MODE; using CPU" >&2
      echo "0"
      return 0
      ;;
    1|true|gpu|on|auto|"") ;;
    *)
      echo "[env-check] Unknown COLMAP_GPU_MODE=$COLMAP_GPU_MODE; using auto" >&2
      mode="auto"
      ;;
  esac

  if ! nvidia_gpu_visible; then
    echo "[env-check] No visible NVIDIA GPU; using COLMAP CPU" >&2
    echo "0"
    return 0
  fi
  if ! colmap_supports_gpu_options; then
    echo "[env-check] COLMAP GPU options are unavailable; using CPU" >&2
    echo "0"
    return 0
  fi
  if [ "$COLMAP_GPU_PROBE" = "0" ]; then
    echo "[env-check] COLMAP GPU probe disabled; using GPU because NVIDIA GPU is visible" >&2
    echo "1"
    return 0
  fi
  if run_colmap_gpu_probe; then
    echo "1"
    return 0
  fi

  echo "0"
}

function log_openmvs_cuda_status() {
  if openmvs_binary_cuda_enabled; then
    echo "[env-check] OpenMVS binary appears CUDA-enabled" >&2
  else
    echo "[env-check] OpenMVS binary appears CPU-only; OpenMVS CUDA requires rebuild" >&2
  fi
}

function detect_openmvs_cuda_device() {
  local requested
  requested="$(printf '%s' "$OPENMVS_CUDA_DEVICE" | tr '[:upper:]' '[:lower:]')"
  case "$requested" in
    -2|cpu|off|false)
      echo "[env-check] OpenMVS CUDA disabled by OPENMVS_CUDA_DEVICE=$OPENMVS_CUDA_DEVICE; using CPU" >&2
      echo "-2"
      return 0
      ;;
  esac

  if ! nvidia_gpu_visible; then
    echo "[env-check] No visible NVIDIA GPU; using OpenMVS CPU" >&2
    echo "-2"
    return 0
  fi
  if ! openmvs_binary_cuda_enabled; then
    echo "[env-check] OpenMVS CUDA runtime not linked; using CPU" >&2
    echo "-2"
    return 0
  fi

  echo "[env-check] OpenMVS CUDA enabled: $OPENMVS_CUDA_DEVICE" >&2
  echo "$OPENMVS_CUDA_DEVICE"
}

function openmvs_cuda_args_for() {
  local tool="$1"
  local tool_path=""
  local help_text=""
  OPENMVS_TOOL_CUDA_ARGS=()
  OPENMVS_TOOL_GPU_OPTION=""
  help_text="$("$tool" --help 2>&1 || true)"
  if printf '%s' "$help_text" | grep -q -- "--gpu-device"; then
    OPENMVS_TOOL_GPU_OPTION="--gpu-device"
    OPENMVS_TOOL_CUDA_ARGS=("$OPENMVS_TOOL_GPU_OPTION" "$OPENMVS_EFFECTIVE_CUDA_DEVICE")
    return
  fi
  if printf '%s' "$help_text" | grep -q -- "--cuda-device"; then
    OPENMVS_TOOL_GPU_OPTION="--cuda-device"
    OPENMVS_TOOL_CUDA_ARGS=("$OPENMVS_TOOL_GPU_OPTION" "$OPENMVS_EFFECTIVE_CUDA_DEVICE")
    return
  fi
  tool_path="$(command -v "$tool" || true)"
  if [ -n "$tool_path" ] && strings "$tool_path" 2>/dev/null | grep -q -- "gpu-device"; then
    OPENMVS_TOOL_GPU_OPTION="--gpu-device"
    OPENMVS_TOOL_CUDA_ARGS=("$OPENMVS_TOOL_GPU_OPTION" "$OPENMVS_EFFECTIVE_CUDA_DEVICE")
  elif [ -n "$tool_path" ] && strings "$tool_path" 2>/dev/null | grep -q -- "cuda-device"; then
    OPENMVS_TOOL_GPU_OPTION="--cuda-device"
    OPENMVS_TOOL_CUDA_ARGS=("$OPENMVS_TOOL_GPU_OPTION" "$OPENMVS_EFFECTIVE_CUDA_DEVICE")
  fi
}

function run_openmvs_stage() {
  local key="$1"
  local label="$2"
  local tool="$3"
  shift 3
  openmvs_cuda_args_for "$tool"

  if [ "${#OPENMVS_TOOL_CUDA_ARGS[@]}" -eq 0 ]; then
    run_stage "$key" "$label" "$tool" "$@"
    return
  fi

  if [ "$OPENMVS_EFFECTIVE_CUDA_DEVICE" != "-2" ]; then
    if run_stage "$key" "$label (GPU)" "$tool" "$@" "${OPENMVS_TOOL_CUDA_ARGS[@]}"; then
      return 0
    fi
    echo "[env-check] $tool GPU stage failed; retrying with CPU" >&2
    run_stage "$key" "$label (CPU fallback)" "$tool" "$@" "$OPENMVS_TOOL_GPU_OPTION" -2
    return
  fi

  run_stage "$key" "$label (CPU)" "$tool" "$@" "${OPENMVS_TOOL_CUDA_ARGS[@]}"
}

function openmvs_refine_args() {
  OPENMVS_REFINE_ARGS=(scene_dense.mvs -m scene_dense_mesh.ply -o scene_dense_mesh_refine.mvs --scales "$OVM_REFINE_SCALES" --max-face-area "$OVM_REFINE_MAX_FACE_AREA")
}

function openmvs_texture_args() {
  OPENMVS_TEXTURE_ARGS=(
    --empty-color "$OVM_TEXTURE_EMPTY_COLOR"
    --cost-smoothness-ratio "$OVM_TEXTURE_COST_SMOOTHNESS_RATIO"
    --sharpness-weight "$OVM_TEXTURE_SHARPNESS_WEIGHT"
  )
}

function normalize_mask_mode() {
  local mode
  mode="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
  case "$mode" in
    none|off|false|0|"") echo "none" ;;
    provided|mask|masks) echo "provided" ;;
    auto|automatic|subject) echo "auto" ;;
    *)
      echo "[env-check] Unknown OVM_MASK_MODE=$1; using none" >&2
      echo "none"
      ;;
  esac
}

function openmvs_mask_args() {
  OPENMVS_DENSIFY_MASK_ARGS=()
  OPENMVS_TEXTURE_MASK_ARGS=()
  if [ "$OVM_MASK_MODE" = "none" ]; then
    return
  fi
  OPENMVS_DENSIFY_MASK_ARGS=(--mask-path "$DENSE_DIR/images/" --ignore-mask-label "$OVM_MASK_IGNORE_LABEL")
  OPENMVS_TEXTURE_MASK_ARGS=(--ignore-mask-label "$OVM_MASK_IGNORE_LABEL")
}

function run_colmap_feature_with_fallback() {
  local use_gpu="$1"
  if [ "$use_gpu" = "1" ]; then
    if run_stage colmap_feature "COLMAP feature extraction (GPU)" colmap feature_extractor \
      --database_path "$COLMAP_DATABASE" \
      --image_path "$IMAGES_DIR" \
      --ImageReader.single_camera 1 \
      --SiftExtraction.use_gpu 1; then
      return 0
    fi

    echo "[env-check] COLMAP GPU feature extraction failed; falling back to CPU" >&2
    COLMAP_USE_GPU=0
    reset_colmap_database
  fi

  run_stage colmap_feature "COLMAP feature extraction (CPU)" colmap feature_extractor \
    --database_path "$COLMAP_DATABASE" \
    --image_path "$IMAGES_DIR" \
    --ImageReader.single_camera 1 \
    --SiftExtraction.use_gpu 0
}

function run_colmap_matcher_with_fallback() {
  local use_gpu="$1"
  if [ "$use_gpu" = "1" ]; then
    if run_stage colmap_matcher "COLMAP exhaustive matching (GPU)" colmap exhaustive_matcher \
      --database_path "$COLMAP_DATABASE" \
      --SiftMatching.use_gpu 1; then
      return 0
    fi

    echo "[env-check] COLMAP GPU matcher failed; falling back to CPU and rebuilding COLMAP database" >&2
    COLMAP_USE_GPU=0
    reset_colmap_database
    run_colmap_feature_with_fallback 0
  fi

  run_stage colmap_matcher "COLMAP exhaustive matching (CPU)" colmap exhaustive_matcher \
    --database_path "$COLMAP_DATABASE" \
    --SiftMatching.use_gpu 0
}

function colmap_model_metric() {
  local metric="$1"
  awk -F': ' -v metric="$metric" '$0 ~ metric ":" {print $NF; exit}' | tr -dc '0-9.'
}

function select_colmap_sparse_model() {
  local candidate=""
  local best_dir=""
  local best_images=-1
  local best_points=-1

  for candidate in "$SPARSE_DIR"/*; do
    [ -d "$candidate" ] || continue
    local analysis=""
    local images=""
    local points=""
    analysis="$(colmap model_analyzer --path "$candidate" 2>&1 || true)"
    images="$(printf '%s\n' "$analysis" | colmap_model_metric "Registered images")"
    points="$(printf '%s\n' "$analysis" | colmap_model_metric "Points")"
    images="${images:-0}"
    points="${points:-0}"
    echo "[env-check] COLMAP sparse model candidate: $candidate registered_images=$images points=$points" >&2
    if [ "$images" -gt "$best_images" ] || { [ "$images" -eq "$best_images" ] && [ "$points" -gt "$best_points" ]; }; then
      best_dir="$candidate"
      best_images="$images"
      best_points="$points"
    fi
  done

  if [ -z "$best_dir" ] || [ "$best_images" -le 0 ]; then
    echo "no usable COLMAP sparse model found under $SPARSE_DIR" >&2
    return 1
  fi

  SELECTED_SPARSE_DIR="$best_dir"
  export SELECTED_SPARSE_DIR
  echo "[env-check] COLMAP sparse model selected: $SELECTED_SPARSE_DIR registered_images=$best_images points=$best_points" >&2
}

# Stage contract examples consumed by the PHP worker:
# [timing] START prepare_images prepare input images
# [timing] START colmap_mapper COLMAP sparse reconstruction
# [timing] START openmvs_texture OpenMVS mesh texturing

require_tool() {
  local tool="$1"
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "missing required tool: $tool. Install OpenMVS into /DATA/conda_vm/openmvs or set OPENMVS_BIN_DIR." >&2
    exit 127
  fi
}

copy_if_exists() {
  local src="$1"
  local dst="$2"
  if [ -f "$src" ]; then
    cp "$src" "$dst"
  fi
}

function copy_texture_sidecars() {
  local src_dir="$1"
  local dst_dir="$2"
  local texture_prefix="$3"
  local texture_path=""

  shopt -s nullglob
  for texture_path in "$src_dir/${texture_prefix}"*.png "$src_dir/${texture_prefix}"*.jpg "$src_dir/${texture_prefix}"*.jpeg; do
    [ -f "$texture_path" ] || continue
    cp "$texture_path" "$dst_dir/$(basename "$texture_path")"
  done
  shopt -u nullglob
}

function product_mode_requested() {
  [ -n "$OVM_PRODUCT_TEXTURE_SIZE" ] || [ -n "$OVM_PRODUCT_OUTPUT_DIR" ]
}

function validate_product_texture_size() {
  case "$OVM_PRODUCT_TEXTURE_SIZE" in
    512|2048|4096|8192) ;;
    *)
      echo "invalid OVM_PRODUCT_TEXTURE_SIZE: $OVM_PRODUCT_TEXTURE_SIZE" >&2
      exit 2
      ;;
  esac
}

function validate_product_env() {
  local expected_output_dir=""
  local expected_output_real=""
  local product_output_real=""
  product_mode_requested || return 0
  if [ -z "$OVM_PRODUCT_TEXTURE_SIZE" ] || [ -z "$OVM_PRODUCT_OUTPUT_DIR" ]; then
    echo "incomplete OVM product env: OVM_PRODUCT_TEXTURE_SIZE and OVM_PRODUCT_OUTPUT_DIR are required" >&2
    exit 2
  fi
  validate_product_texture_size
  expected_output_dir="$JOB_DIR/products/glb_${OVM_PRODUCT_TEXTURE_SIZE}"
  expected_output_real="$(realpath -m "$expected_output_dir")"
  product_output_real="$(realpath -m "$OVM_PRODUCT_OUTPUT_DIR")"
  case "$product_output_real" in
    "$expected_output_real"|"$expected_output_real"/*) ;;
    *)
      echo "invalid OVM_PRODUCT_OUTPUT_DIR: must be under $expected_output_dir" >&2
      exit 2
      ;;
  esac
  OVM_PRODUCT_OUTPUT_DIR="$product_output_real"
  export OVM_PRODUCT_OUTPUT_DIR
}

function run_product_glb_export() {
  test -f "$MVS_DIR/scene_dense.mvs"
  test -f "$MVS_DIR/scene_dense_mesh_refine.ply"
  mkdir -p "$OVM_PRODUCT_OUTPUT_DIR" "$JOB_DIR/.npm-cache"
  openmvs_texture_args

  (
    cd "$MVS_DIR"
    run_openmvs_stage product_glb "OpenMVS product GLB export" TextureMesh scene_dense.mvs -m scene_dense_mesh_refine.ply -o "product_glb_${OVM_PRODUCT_TEXTURE_SIZE}.glb" --export-type glb --max-texture-size "$OVM_PRODUCT_TEXTURE_SIZE" "${OPENMVS_TEXTURE_ARGS[@]}"
    if command -v npx >/dev/null 2>&1; then
      run_stage product_embed_glb "embed product GLB textures" env npm_config_cache="$JOB_DIR/.npm-cache" npx --yes @gltf-transform/cli copy "product_glb_${OVM_PRODUCT_TEXTURE_SIZE}.glb" "embedded_product_glb_${OVM_PRODUCT_TEXTURE_SIZE}.glb"
    fi
  )

  if [ -f "$MVS_DIR/embedded_product_glb_${OVM_PRODUCT_TEXTURE_SIZE}.glb" ]; then
    cp "$MVS_DIR/embedded_product_glb_${OVM_PRODUCT_TEXTURE_SIZE}.glb" "$OVM_PRODUCT_OUTPUT_DIR/model.glb"
  else
    cp "$MVS_DIR/product_glb_${OVM_PRODUCT_TEXTURE_SIZE}.glb" "$OVM_PRODUCT_OUTPUT_DIR/model.glb"
  fi
  copy_texture_sidecars "$MVS_DIR" "$OVM_PRODUCT_OUTPUT_DIR" "product_glb_${OVM_PRODUCT_TEXTURE_SIZE}"
  chmod -R a+rX "$OVM_PRODUCT_OUTPUT_DIR"
  PIPELINE_FINISHED=1
  echo "$OVM_PRODUCT_OUTPUT_DIR/model.glb"
}

function write_registered_frame_manifest() {
  local images_dir="$1"
  local report_path="$2"
  python3 - "$images_dir" "$report_path" <<'PY'
import json
import sys
from pathlib import Path

images_dir = Path(sys.argv[1])
report = Path(sys.argv[2])
count = len([p for p in images_dir.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".tif", ".tiff"}]) if images_dir.is_dir() else None
report.write_text(json.dumps({"registered_frame_count": count}, ensure_ascii=False, indent=2) + "\n")
PY
}

function write_native_mask_manifest() {
  python3 - "$JOB_DIR/mask_manifest.json" "$OVM_MASK_MODE" <<'PY'
import json
import sys
from pathlib import Path

Path(sys.argv[1]).write_text(json.dumps({
    "mode": sys.argv[2],
    "mask_count": 0,
    "note": "OpenMVS native CreateStructure mode does not use COLMAP undistorted masks."
}, ensure_ascii=False, indent=2) + "\n")
PY
}

function run_openmvs_native_pipeline() {
  if [ "$OVM_MASK_MODE" != "none" ]; then
    echo "[env-check] OpenMVS native mode ignores mask mode '$OVM_MASK_MODE'; use COLMAP mode for masks" >&2
  fi
  write_native_mask_manifest

  (
    cd "$MVS_DIR"
    OPENMVS_DENSIFY_MASK_ARGS=()
    OPENMVS_TEXTURE_MASK_ARGS=()
    run_openmvs_stage openmvs_create_structure "OpenMVS native SfM" CreateStructure -s "$IMAGES_DIR" -o scene.sfm --export-mvs scene.mvs --extract-colors 1 --detector-type "$OVM_CREATE_STRUCTURE_DETECTOR_TYPE" --max-views-per-cluster "$OVM_CREATE_STRUCTURE_MAX_VIEWS_PER_CLUSTER" --undistort-extension "$OVM_CREATE_STRUCTURE_UNDISTORT_EXTENSION"
    write_registered_frame_manifest "$MVS_DIR/undistorted" "$JOB_DIR/colmap_manifest.json"
    run_openmvs_stage openmvs_densify "OpenMVS dense point cloud" DensifyPointCloud scene.mvs
    run_openmvs_stage openmvs_reconstruct "OpenMVS mesh reconstruction" ReconstructMesh scene_dense.mvs -p scene_dense.ply -o scene_dense_mesh.ply
    openmvs_refine_args
    openmvs_texture_args
    run_openmvs_stage openmvs_refine "OpenMVS mesh refinement" RefineMesh "${OPENMVS_REFINE_ARGS[@]}"
    run_openmvs_stage openmvs_texture "OpenMVS mesh texturing" TextureMesh scene_dense.mvs -m scene_dense_mesh_refine.ply -o scene_dense_mesh_refine_texture.mvs "${OPENMVS_TEXTURE_ARGS[@]}"
    run_openmvs_stage export_glb "OpenMVS GLB export" TextureMesh scene_dense.mvs -m scene_dense_mesh_refine.ply -o scene_dense_mesh_refine_texture.glb --export-type glb "${OPENMVS_TEXTURE_ARGS[@]}"
    if command -v npx >/dev/null 2>&1; then
      mkdir -p "$JOB_DIR/.npm-cache"
      run_stage embed_glb "embed GLB textures" env npm_config_cache="$JOB_DIR/.npm-cache" npx --yes @gltf-transform/cli copy scene_dense_mesh_refine_texture.glb embedded_model.glb
    fi
  )
}

function run_colmap_openmvs_pipeline() {
  run_colmap_feature_with_fallback "$COLMAP_USE_GPU"
  run_colmap_matcher_with_fallback "$COLMAP_USE_GPU"

  run_stage colmap_mapper "COLMAP sparse reconstruction" colmap mapper \
    --database_path "$COLMAP_DATABASE" \
    --image_path "$IMAGES_DIR" \
    --output_path "$SPARSE_DIR"

  select_colmap_sparse_model
  test -d "$SELECTED_SPARSE_DIR"

  run_stage colmap_undistort "COLMAP image undistortion" colmap image_undistorter \
    --image_path "$IMAGES_DIR" \
    --input_path "$SELECTED_SPARSE_DIR" \
    --output_path "$DENSE_DIR" \
    --output_type COLMAP \
    --roi_min_x "$COLMAP_UNDISTORT_ROI_MIN_X" \
    --roi_min_y "$COLMAP_UNDISTORT_ROI_MIN_Y" \
    --roi_max_x "$COLMAP_UNDISTORT_ROI_MAX_X" \
    --roi_max_y "$COLMAP_UNDISTORT_ROI_MAX_Y" \
    --max_image_size "$COLMAP_DENSE_MAX_IMAGE_SIZE"

  run_stage prepare_masks "prepare OpenMVS masks" python3 "$PROJECT_ROOT/scripts/prepare_masks.py" \
    --mode "$OVM_MASK_MODE" \
    --manifest "$JOB_DIR/input_manifest.json" \
    --raw-images "$IMAGES_DIR" \
    --dense-images "$DENSE_DIR/images" \
    --report "$JOB_DIR/mask_manifest.json" \
    --auto-rect "$OVM_MASK_AUTO_RECT"

  write_registered_frame_manifest "$DENSE_DIR/images" "$JOB_DIR/colmap_manifest.json"

  run_stage openmvs_interface "OpenMVS import COLMAP" InterfaceCOLMAP -i "$DENSE_DIR" -o "$MVS_DIR/scene.mvs" --image-folder "$DENSE_DIR/images"

  (
    cd "$MVS_DIR"
    openmvs_mask_args
    run_openmvs_stage openmvs_densify "OpenMVS dense point cloud" DensifyPointCloud scene.mvs "${OPENMVS_DENSIFY_MASK_ARGS[@]}"
    run_openmvs_stage openmvs_reconstruct "OpenMVS mesh reconstruction" ReconstructMesh scene_dense.mvs -p scene_dense.ply -o scene_dense_mesh.ply
    openmvs_refine_args
    openmvs_texture_args
    run_openmvs_stage openmvs_refine "OpenMVS mesh refinement" RefineMesh "${OPENMVS_REFINE_ARGS[@]}"
    run_openmvs_stage openmvs_texture "OpenMVS mesh texturing" TextureMesh scene_dense.mvs -m scene_dense_mesh_refine.ply -o scene_dense_mesh_refine_texture.mvs "${OPENMVS_TEXTURE_ARGS[@]}" "${OPENMVS_TEXTURE_MASK_ARGS[@]}"
    run_openmvs_stage export_glb "OpenMVS GLB export" TextureMesh scene_dense.mvs -m scene_dense_mesh_refine.ply -o scene_dense_mesh_refine_texture.glb --export-type glb "${OPENMVS_TEXTURE_ARGS[@]}" "${OPENMVS_TEXTURE_MASK_ARGS[@]}"
  )
}

function copy_openmvs_artifacts() {
  copy_if_exists "$MVS_DIR/scene_dense_mesh.ply" "$EXPORTS_DIR/scene_dense_mesh.ply"
  copy_if_exists "$MVS_DIR/scene_dense_mesh_refine.ply" "$EXPORTS_DIR/scene_dense_mesh_refine.ply"
  copy_if_exists "$MVS_DIR/scene_dense_mesh_refine_texture.ply" "$EXPORTS_DIR/scene_dense_mesh_refine_texture.ply"
  if [ -f "$MVS_DIR/embedded_model.glb" ]; then
    cp "$MVS_DIR/embedded_model.glb" "$EXPORTS_DIR/model.glb"
  elif [ -f "$MVS_DIR/scene_dense_mesh_refine_texture.glb" ]; then
    cp "$MVS_DIR/scene_dense_mesh_refine_texture.glb" "$EXPORTS_DIR/model.glb"
  fi
  copy_texture_sidecars "$MVS_DIR" "$EXPORTS_DIR" "scene_dense_mesh_refine_texture"
  test -f "$EXPORTS_DIR/model.glb"
}

function repair_export_textures() {
  run_stage repair_textures "repair texture atlas" python3 "$PROJECT_ROOT/scripts/repair_texture_atlas.py" \
    "$EXPORTS_DIR" \
    --mode "$OVM_TEXTURE_REPAIR_MODE" \
    --trigger-black-ratio "$OVM_TEXTURE_REPAIR_TRIGGER_BLACK_RATIO" \
    --max-white-ratio "$OVM_TEXTURE_REPAIR_MAX_WHITE_RATIO" \
    --black-threshold "$OVM_TEXTURE_REPAIR_BLACK_THRESHOLD" \
    --inpaint-radius "$OVM_TEXTURE_REPAIR_INPAINT_RADIUS" \
    --report "$JOB_DIR/texture_repair_report.json"
}

function finalize_openmvs_job() {
  run_stage finalize "viewer metadata and QA" python3 "$PROJECT_ROOT/scripts/write_default_transform.py" \
    "$(basename "$JOB_DIR")" \
    "$JOB_DIR/transform.json" \
    --lng "$ORIGIN_LNG" \
    --lat "$ORIGIN_LAT" \
    --height "$ORIGIN_HEIGHT"

  repair_export_textures
  python3 "$PROJECT_ROOT/scripts/build_qa_report.py" "$(basename "$JOB_DIR")" "$JOB_DIR" --output "$JOB_DIR/qa_report.json"
  chmod -R a+rX "$EXPORTS_DIR" "$JOB_DIR/qa_report.json" "$JOB_DIR/transform.json" "$JOB_DIR/input_manifest.json" "$JOB_DIR/colmap_manifest.json" "$JOB_DIR/texture_repair_report.json"
  if [ -f "$JOB_DIR/mask_manifest.json" ]; then
    chmod a+r "$JOB_DIR/mask_manifest.json"
  fi
  PIPELINE_FINISHED=1
  echo "$EXPORTS_DIR/model.glb"
}

finalize_failure() {
  if [ "$PIPELINE_FINISHED" = "0" ]; then
    echo "OpenMVS pipeline failed" >&2
  fi
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

validate_product_env
mkdir -p "$JOB_DIR/input" "$MVS_DIR"
if ! product_mode_requested; then
  mkdir -p "$IMAGES_DIR" "$SPARSE_DIR" "$DENSE_DIR" "$EXPORTS_DIR"
fi
chmod a+rx "$JOB_PARENT" "$JOB_DIR"
if ! product_mode_requested; then
  chmod a+rx "$EXPORTS_DIR"
fi
trap finalize_failure ERR

load_pipeline_mode
apply_quality_preset
configure_cuda_runtime || true
if [ "$OVM_PIPELINE_MODE" = "openmvs_native" ] || product_mode_requested; then
  configure_openmvs_native_runtime
fi

if product_mode_requested; then
  require_tool TextureMesh
  log_openmvs_cuda_status
  OPENMVS_EFFECTIVE_CUDA_DEVICE="$(detect_openmvs_cuda_device)"
  export OPENMVS_EFFECTIVE_CUDA_DEVICE
  run_product_glb_export
  exit 0
fi

require_tool ffmpeg
require_tool ffprobe
if [ "$OVM_PIPELINE_MODE" = "openmvs_native" ]; then
  require_tool CreateStructure
  require_tool npx
else
  require_tool colmap
  require_tool InterfaceCOLMAP
fi
require_tool DensifyPointCloud
require_tool ReconstructMesh
require_tool RefineMesh
require_tool TextureMesh

if [ "$OVM_PIPELINE_MODE" = "colmap" ]; then
  log_colmap_binary_status || true
else
  echo "[env-check] COLMAP skipped for OpenMVS native mode" >&2
fi
OVM_MASK_MODE="$(normalize_mask_mode "$OVM_MASK_MODE")"
export OVM_MASK_MODE
if [ "$OVM_PIPELINE_MODE" = "colmap" ]; then
  COLMAP_USE_GPU="$(detect_colmap_gpu_mode)"
else
  COLMAP_USE_GPU=0
fi
export COLMAP_USE_GPU
log_openmvs_cuda_status
OPENMVS_EFFECTIVE_CUDA_DEVICE="$(detect_openmvs_cuda_device)"
export OPENMVS_EFFECTIVE_CUDA_DEVICE

run_stage prepare_images "prepare input images" python3 "$PROJECT_ROOT/scripts/prepare_images.py" \
  "$INPUT_FILE" \
  "$IMAGES_DIR" \
  --report "$JOB_DIR/input_manifest.json" \
  --fps "$OVM_FRAME_FPS" \
  --width "$OVM_FRAME_WIDTH" \
  --max-frames "$OVM_MAX_FRAMES" \
  --min-frames "$OVM_MIN_FRAMES"

if [ "$OVM_PIPELINE_MODE" = "openmvs_native" ]; then
  run_openmvs_native_pipeline
else
  run_colmap_openmvs_pipeline
fi

copy_openmvs_artifacts
finalize_openmvs_job
