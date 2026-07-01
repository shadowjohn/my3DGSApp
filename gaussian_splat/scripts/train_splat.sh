#!/usr/bin/env bash
set -euo pipefail

ENV_PATH="${GS_CONDA_ENV:-/DATA/conda_vm/gs_scene}"
export CUDA_HOME="$ENV_PATH"
export PATH="$ENV_PATH/bin:$PATH"
export CPATH="$ENV_PATH/targets/x86_64-linux/include:$ENV_PATH/include:${CPATH:-}"
export LIBRARY_PATH="$ENV_PATH/targets/x86_64-linux/lib:$ENV_PATH/lib:${LIBRARY_PATH:-}"
export LD_LIBRARY_PATH="$ENV_PATH/targets/x86_64-linux/lib:$ENV_PATH/lib:${LD_LIBRARY_PATH:-}"
export MAX_JOBS="${GS_TORCH_EXT_MAX_JOBS:-${MAX_JOBS:-2}}"
export GS_TORCH_MATMUL_PRECISION="${GS_TORCH_MATMUL_PRECISION:-high}"
TRAIN_VIS="${GS_TRAIN_VIS:-tensorboard}"
PROCESSED_DIR=${1:?usage: train_splat.sh processed_dir outputs_dir}
OUTPUTS_DIR=${2:?usage: train_splat.sh processed_dir outputs_dir}

if [ ! -x "$ENV_PATH/bin/ns-train" ]; then
  echo "ns-train not found. Run scripts/install_gs_env.sh first." >&2
  exit 1
fi

mkdir -p "$OUTPUTS_DIR"

TRAIN_ARGS=()
if [ -n "${GS_TRAIN_MAX_ITERATIONS:-}" ]; then
  TRAIN_ARGS+=(--max-num-iterations "$GS_TRAIN_MAX_ITERATIONS")
fi

"$ENV_PATH/bin/python" - splatfacto \
  --data "$PROCESSED_DIR" \
  "${TRAIN_ARGS[@]}" \
  --vis "$TRAIN_VIS" \
  --viewer.quit-on-train-completion True \
  --output-dir "$OUTPUTS_DIR" >&2 <<'PY'
import os
import sys

import torch
from nerfstudio.scripts.train import entrypoint

torch.set_float32_matmul_precision(os.environ["GS_TORCH_MATMUL_PRECISION"])
sys.argv[0] = "ns-train"
raise SystemExit(entrypoint())
PY

CONFIG_PATH="$(find "$OUTPUTS_DIR" -path '*/splatfacto/*/config.yml' -type f | sort | tail -n 1)"
if [ ! -f "$CONFIG_PATH" ]; then
  echo "config.yml not found under: $OUTPUTS_DIR" >&2
  exit 1
fi

echo "$CONFIG_PATH"
