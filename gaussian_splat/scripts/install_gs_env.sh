#!/usr/bin/env bash
set -euo pipefail

CONDA_ROOT="${CONDA_ROOT:-/DATA/conda_vm/miniforge3}"
CONDA="${CONDA:-$CONDA_ROOT/bin/conda}"
ENV_PATH="${GS_CONDA_ENV:-/DATA/conda_vm/gs_scene}"

if [ ! -x "$CONDA" ]; then
  echo "conda not found at $CONDA" >&2
  exit 1
fi

if [ ! -d "$ENV_PATH" ]; then
  "$CONDA" create -y -p "$ENV_PATH" -c conda-forge python=3.10 c-compiler cxx-compiler
fi

if ! "$ENV_PATH/bin/nvcc" --version 2>/dev/null | grep -q "release 12.8"; then
  "$CONDA" install -y -p "$ENV_PATH" -c nvidia/label/cuda-12.8.0 cuda-toolkit=12.8.0
fi

export CUDA_HOME="$ENV_PATH"
export PATH="$ENV_PATH/bin:$PATH"
export LD_LIBRARY_PATH="$ENV_PATH/lib:${LD_LIBRARY_PATH:-}"
export CPATH="$ENV_PATH/targets/x86_64-linux/include:$ENV_PATH/include:${CPATH:-}"
export LIBRARY_PATH="$ENV_PATH/targets/x86_64-linux/lib:$ENV_PATH/lib:${LIBRARY_PATH:-}"
export CC="$ENV_PATH/bin/x86_64-conda-linux-gnu-gcc"
export CXX="$ENV_PATH/bin/x86_64-conda-linux-gnu-g++"
export CUDAHOSTCXX="$CXX"
export MAX_JOBS="${MAX_JOBS:-1}"

"$ENV_PATH/bin/python" -m pip install --upgrade pip wheel
"$ENV_PATH/bin/pip" install setuptools==80.10.2

"$ENV_PATH/bin/pip" install \
  torch==2.10.0 \
  torchvision==0.25.0 \
  torchaudio==2.10.0 \
  --index-url https://download.pytorch.org/whl/cu128

"$ENV_PATH/bin/pip" install ninja

CUDA_ARCH="$("$ENV_PATH/bin/python" - <<'PY'
import torch
if torch.cuda.is_available():
    major, minor = torch.cuda.get_device_capability(0)
    print(f"{major}{minor}")
PY
)"

if [ -n "$CUDA_ARCH" ]; then
  export TCNN_CUDA_ARCHITECTURES="$CUDA_ARCH"
fi

"$ENV_PATH/bin/nvcc" --version
"$ENV_PATH/bin/pip" install --no-build-isolation git+https://github.com/NVlabs/tiny-cuda-nn/#subdirectory=bindings/torch
"$ENV_PATH/bin/pip" install nerfstudio
"$ENV_PATH/bin/pip" install gsplat

"$ENV_PATH/bin/python" - <<'PY'
import torch
print("torch", torch.__version__)
print("cuda available", torch.cuda.is_available())
print("torch cuda", torch.version.cuda)
if not torch.cuda.is_available():
    raise SystemExit("CUDA is not available to PyTorch")
PY

"$ENV_PATH/bin/ns-train" --help >/dev/null
"$ENV_PATH/bin/ns-process-data" --help >/dev/null
"$ENV_PATH/bin/ns-export" --help >/dev/null

echo "Gaussian Splat environment ready: $ENV_PATH"
