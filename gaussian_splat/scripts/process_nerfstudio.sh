#!/usr/bin/env bash
set -euo pipefail

ENV_PATH="${GS_CONDA_ENV:-/DATA/conda_vm/gs_scene}"
COLMAP_ENV_PATH="${GS_COLMAP_ENV_PATH:-/DATA/conda_vm/openmvs}"
CUDA_ROOT="${GS_CUDA_ROOT:-$ENV_PATH}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGES_DIR=${1:?usage: process_nerfstudio.sh images_dir processed_dir}
PROCESSED_DIR=${2:?usage: process_nerfstudio.sh images_dir processed_dir}
SFM_MAPPER="${GS_SFM_MAPPER:-incremental}"
COLMAP_CMD="${GS_COLMAP_CMD:-$COLMAP_ENV_PATH/bin/colmap}"
SFM_MATCHER="${GS_SFM_MATCHER:-exhaustive}"
SFM_REPORT="$PROCESSED_DIR/sfm_report.json"

export PATH="$COLMAP_ENV_PATH/bin:$ENV_PATH/bin:$CUDA_ROOT/bin:$PATH"
if [ -d "$CUDA_ROOT/targets/x86_64-linux/lib" ]; then
  export LD_LIBRARY_PATH="$CUDA_ROOT/targets/x86_64-linux/lib:$ENV_PATH/lib:${LD_LIBRARY_PATH:-}"
else
  export LD_LIBRARY_PATH="$CUDA_ROOT/lib64:$CUDA_ROOT/lib:$ENV_PATH/lib:${LD_LIBRARY_PATH:-}"
fi
GS_COLMAP_USE_GPU="${GS_COLMAP_USE_GPU:-1}"

if [ ! -x "$ENV_PATH/bin/ns-process-data" ]; then
  echo "ns-process-data not found. Run scripts/install_gs_env.sh first." >&2
  exit 1
fi

mkdir -p "$PROCESSED_DIR"

image_count() {
  find "$1" -maxdepth 1 -type f \( \
    -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' \
  \) | wc -l
}

copy_input_images() {
  local source_dir="$1"
  local target_dir="$2"
  rm -rf "$target_dir"
  mkdir -p "$target_dir"
  while IFS= read -r -d '' image_path; do
    cp -p "$image_path" "$target_dir/$(basename "$image_path")"
  done < <(find "$source_dir" -maxdepth 1 -type f \( \
    -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' \
  \) -print0 | sort -z)
}

write_sfm_report() {
  local report_path="$1"
  local mapper="$2"
  local matcher="$3"
  local source_images="$4"
  local sparse_model="$5"
  local transforms_path="$6"
  local database_path="$7"
  local colmap_command="$8"

  python3 - "$report_path" "$mapper" "$matcher" "$source_images" "$sparse_model" "$transforms_path" "$database_path" "$colmap_command" <<'PY'
import json
import subprocess
import sys
from pathlib import Path

report_path = Path(sys.argv[1])
mapper = sys.argv[2]
matcher = sys.argv[3]
source_images = Path(sys.argv[4])
sparse_model = sys.argv[5]
transforms_path = Path(sys.argv[6])
database_path = sys.argv[7]
colmap_command = sys.argv[8]

image_count = len([
    path for path in source_images.iterdir()
    if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png"}
]) if source_images.is_dir() else 0

registered_count = 0
if transforms_path.is_file():
    try:
        data = json.loads(transforms_path.read_text())
        frames = data.get("frames", []) if isinstance(data, dict) else []
        registered_count = len(frames) if isinstance(frames, list) else 0
    except json.JSONDecodeError:
        registered_count = 0

try:
    version = subprocess.run(
        [colmap_command, "-h"],
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    ).stdout.splitlines()[0]
except (OSError, subprocess.SubprocessError, IndexError):
    version = None

report = {
    "mapper": mapper,
    "matcher": matcher,
    "image_count": image_count,
    "registered_count": registered_count,
    "registered_ratio": round(registered_count / image_count, 2) if image_count else 0.0,
    "sparse_model_path": sparse_model,
    "database_path": database_path,
    "colmap_command": colmap_command,
    "colmap_version": version,
}
report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
PY
}

normalise_sparse_model() {
  local sparse_root="$1"
  local sparse_model="$sparse_root/0"

  if [ -f "$sparse_model/cameras.bin" ] && [ -f "$sparse_model/images.bin" ] && [ -f "$sparse_model/points3D.bin" ]; then
    printf '%s\n' "$sparse_model"
    return 0
  fi

  if [ -f "$sparse_root/cameras.bin" ] && [ -f "$sparse_root/images.bin" ] && [ -f "$sparse_root/points3D.bin" ]; then
    mkdir -p "$sparse_model"
    mv "$sparse_root/cameras.bin" "$sparse_root/images.bin" "$sparse_root/points3D.bin" "$sparse_model/"
    for optional_model_file in frames.bin rigs.bin; do
      if [ -f "$sparse_root/$optional_model_file" ]; then
        mv "$sparse_root/$optional_model_file" "$sparse_model/"
      fi
    done
    if [ -f "$sparse_root/project.ini" ]; then
      mv "$sparse_root/project.ini" "$sparse_model/"
    fi
    printf '%s\n' "$sparse_model"
    return 0
  fi

  local found_model
  found_model="$(find "$sparse_root" -mindepth 1 -maxdepth 2 -type f -name cameras.bin -printf '%h\n' | sort | head -n 1)"
  if [ -n "$found_model" ] && [ -f "$found_model/images.bin" ] && [ -f "$found_model/points3D.bin" ]; then
    if [ "$found_model" != "$sparse_model" ]; then
      rm -rf "$sparse_model"
      mkdir -p "$(dirname "$sparse_model")"
      cp -a "$found_model" "$sparse_model"
    fi
    printf '%s\n' "$sparse_model"
    return 0
  fi

  echo "COLMAP sparse model not found under: $sparse_root" >&2
  return 1
}

run_matcher() {
  local database_path="$1"
  local use_gpu="$GS_COLMAP_USE_GPU"
  case "$SFM_MATCHER" in
    exhaustive)
      if "$COLMAP_CMD" exhaustive_matcher \
        --database_path "$database_path" \
        --SiftMatching.use_gpu "$use_gpu" >&2; then
        return 0
      fi
      ;;
    sequential)
      if "$COLMAP_CMD" sequential_matcher \
        --database_path "$database_path" \
        --SiftMatching.use_gpu "$use_gpu" >&2; then
        return 0
      fi
      ;;
    *)
      echo "Unsupported GS_SFM_MATCHER: $SFM_MATCHER (use exhaustive, sequential, or hloc_lightglue)" >&2
      return 1
      ;;
  esac

  if [ "$use_gpu" = "1" ]; then
    echo "[env-check] Gaussian COLMAP GPU matcher failed; retrying CPU" >&2
    case "$SFM_MATCHER" in
      exhaustive)
        "$COLMAP_CMD" exhaustive_matcher \
          --database_path "$database_path" \
          --SiftMatching.use_gpu 0 >&2
        ;;
      sequential)
        "$COLMAP_CMD" sequential_matcher \
          --database_path "$database_path" \
          --SiftMatching.use_gpu 0 >&2
        ;;
    esac
    return
  fi

  return 1
}

convert_existing_colmap_model() {
  local sparse_model="$1"
  "$ENV_PATH/bin/ns-process-data" images \
    --data "$PROCESSED_DIR/images" \
    --no-gpu \
    --skip-colmap \
    --skip-image-processing \
    --colmap-model-path colmap/sparse/0 \
    --output-dir "$PROCESSED_DIR" >&2

  write_sfm_report "$SFM_REPORT" "$SFM_MAPPER" "$SFM_MATCHER" "$PROCESSED_DIR/images" "$sparse_model" "$PROCESSED_DIR/transforms.json" "$PROCESSED_DIR/colmap/database.db" "$COLMAP_CMD"
}

run_hloc_lightglue_reconstruction() {
  local sparse_root="$1"
  "$ENV_PATH/bin/python" "$SCRIPT_DIR/run_hloc_reconstruction.py" "$PROCESSED_DIR/images" "$sparse_root" >&2
  if [ -f "$sparse_root/database.db" ]; then
    mv "$sparse_root/database.db" "$PROCESSED_DIR/colmap/database.db"
  fi
}

run_colmap_reconstruction() {
  local mapper_command=()
  case "$SFM_MAPPER" in
    incremental) mapper_command=(mapper) ;;
    hierarchical) mapper_command=(hierarchical_mapper) ;;
    *)
      echo "Unsupported GS_SFM_MAPPER: $SFM_MAPPER (use incremental, hierarchical, or nerfstudio)" >&2
      return 1
      ;;
  esac

  if ! command -v "$COLMAP_CMD" >/dev/null 2>&1; then
    echo "COLMAP command not found: $COLMAP_CMD" >&2
    return 1
  fi

  local image_total
  image_total="$(image_count "$IMAGES_DIR")"
  if [ "$image_total" -eq 0 ]; then
    echo "No images found in: $IMAGES_DIR" >&2
    return 1
  fi

  rm -rf "$PROCESSED_DIR/colmap" "$PROCESSED_DIR/transforms.json" "$PROCESSED_DIR/sparse_pc.ply"
  copy_input_images "$IMAGES_DIR" "$PROCESSED_DIR/images"

  local database_path="$PROCESSED_DIR/colmap/database.db"
  local sparse_root="$PROCESSED_DIR/colmap/sparse"
  mkdir -p "$PROCESSED_DIR/colmap" "$sparse_root"

  case "$SFM_MATCHER" in
    hloc_lightglue)
      run_hloc_lightglue_reconstruction "$sparse_root"
      local sparse_model
      sparse_model="$(normalise_sparse_model "$sparse_root")"
      convert_existing_colmap_model "$sparse_model"
      return
      ;;
    exhaustive|sequential) ;;
    *)
      echo "Unsupported GS_SFM_MATCHER: $SFM_MATCHER (use exhaustive, sequential, or hloc_lightglue)" >&2
      return 1
      ;;
  esac

  if ! "$COLMAP_CMD" feature_extractor \
    --database_path "$database_path" \
    --image_path "$PROCESSED_DIR/images" \
    --ImageReader.single_camera 1 \
    --ImageReader.camera_model OPENCV \
    --SiftExtraction.use_gpu "$GS_COLMAP_USE_GPU" >&2; then
    if [ "$GS_COLMAP_USE_GPU" != "1" ]; then
      return 1
    fi
    echo "[env-check] Gaussian COLMAP GPU feature extraction failed; retrying CPU" >&2
    rm -f "$database_path" "$database_path-shm" "$database_path-wal"
    "$COLMAP_CMD" feature_extractor \
      --database_path "$database_path" \
      --image_path "$PROCESSED_DIR/images" \
      --ImageReader.single_camera 1 \
      --ImageReader.camera_model OPENCV \
      --SiftExtraction.use_gpu 0 >&2
  fi

  run_matcher "$database_path"

  "$COLMAP_CMD" "${mapper_command[@]}" \
    --database_path "$database_path" \
    --image_path "$PROCESSED_DIR/images" \
    --output_path "$sparse_root" >&2

  local sparse_model
  sparse_model="$(normalise_sparse_model "$sparse_root")"
  convert_existing_colmap_model "$sparse_model"
}

run_nerfstudio_process() {
  "$ENV_PATH/bin/ns-process-data" images \
    --data "$IMAGES_DIR" \
    --no-gpu \
    --output-dir "$PROCESSED_DIR" >&2
  write_sfm_report "$SFM_REPORT" "nerfstudio" "nerfstudio-default" "$IMAGES_DIR" "$PROCESSED_DIR/colmap/sparse/0" "$PROCESSED_DIR/transforms.json" "$PROCESSED_DIR/colmap/database.db" "$COLMAP_CMD"
}

case "$SFM_MAPPER" in
  nerfstudio)
    run_nerfstudio_process
    ;;
  incremental|hierarchical)
    run_colmap_reconstruction
    ;;
  *)
    echo "Unsupported GS_SFM_MAPPER: $SFM_MAPPER (use incremental, hierarchical, or nerfstudio)" >&2
    exit 1
    ;;
esac

if [ ! -f "$PROCESSED_DIR/transforms.json" ]; then
  echo "transforms.json not found: $PROCESSED_DIR/transforms.json" >&2
  exit 1
fi

echo "$PROCESSED_DIR/transforms.json"
