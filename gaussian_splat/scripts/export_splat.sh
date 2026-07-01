#!/usr/bin/env bash
set -euo pipefail

ENV_PATH="${GS_CONDA_ENV:-/DATA/conda_vm/gs_scene}"
export TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1
export CUDA_HOME="$ENV_PATH"
export PATH="$ENV_PATH/bin:$PATH"
export CPATH="$ENV_PATH/targets/x86_64-linux/include:$ENV_PATH/include:${CPATH:-}"
export LIBRARY_PATH="$ENV_PATH/targets/x86_64-linux/lib:$ENV_PATH/lib:${LIBRARY_PATH:-}"
export LD_LIBRARY_PATH="$ENV_PATH/targets/x86_64-linux/lib:$ENV_PATH/lib:${LD_LIBRARY_PATH:-}"
CONFIG_PATH=${1:?usage: export_splat.sh config_yml exports_dir}
EXPORTS_DIR=${2:?usage: export_splat.sh config_yml exports_dir}

if [ ! -x "$ENV_PATH/bin/ns-export" ]; then
  echo "ns-export not found. Run scripts/install_gs_env.sh first." >&2
  exit 1
fi

mkdir -p "$EXPORTS_DIR"

"$ENV_PATH/bin/ns-export" gaussian-splat \
  --load-config "$CONFIG_PATH" \
  --output-dir "$EXPORTS_DIR" >&2

if [ ! -f "$EXPORTS_DIR/splat.ply" ]; then
  echo "splat.ply not found: $EXPORTS_DIR/splat.ply" >&2
  exit 1
fi

echo "$EXPORTS_DIR/splat.ply"
