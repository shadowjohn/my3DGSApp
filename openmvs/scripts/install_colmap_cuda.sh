#!/usr/bin/env bash
set -euo pipefail

ENV_PATH="${OPENMVS_CONDA_ENV:-/DATA/conda_vm/openmvs}"
WORK_ROOT="${COLMAP_BUILD_ROOT:-/DATA/conda_vm/openmvs_src}"
COLMAP_SRC="$WORK_ROOT/colmap"
BUILD_DIR="$WORK_ROOT/colmap_build"
COLMAP_VERSION="${COLMAP_VERSION:-3.9.1}"
OVM_PREFERRED_CUDA_VERSION="${OVM_PREFERRED_CUDA_VERSION:-12.8}"
OVM_CUDA_ARCHITECTURES="${OVM_CUDA_ARCHITECTURES:-}"

select_cuda_root() {
  local candidates=()
  local cuda_root=""
  local fallback_root=""
  if [ -n "${OVM_CUDA_ROOT:-}" ]; then
    candidates+=("$OVM_CUDA_ROOT")
  fi
  candidates+=(
    "/usr/local/cuda-${OVM_PREFERRED_CUDA_VERSION}"
    "$ENV_PATH"
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
    version_text="$("$cuda_root/bin/nvcc" --version 2>/dev/null || true)"

    if [ -n "${OVM_CUDA_ROOT:-}" ] && [ "$cuda_root" = "$OVM_CUDA_ROOT" ]; then
      echo "$cuda_root"
      return 0
    fi
    if [ "$cuda_root" = "/usr/local/cuda-${OVM_PREFERRED_CUDA_VERSION}" ]; then
      echo "$cuda_root"
      return 0
    fi
    if printf '%s' "$version_text" | grep -q "release ${OVM_PREFERRED_CUDA_VERSION}"; then
      echo "$cuda_root"
      return 0
    fi
    if find "$cuda_root" -maxdepth 3 -name "libcudart.so*${OVM_PREFERRED_CUDA_VERSION}*" -print -quit 2>/dev/null | grep -q .; then
      echo "$cuda_root"
      return 0
    fi
  done

  if [ -n "$fallback_root" ]; then
    echo "$fallback_root"
  fi
}

CUDA_ROOT="$(select_cuda_root || true)"
if [ -z "$CUDA_ROOT" ] || [ ! -x "$CUDA_ROOT/bin/nvcc" ]; then
  echo "CUDA toolkit not found. Set OVM_CUDA_ROOT to a CUDA ${OVM_PREFERRED_CUDA_VERSION} toolkit." >&2
  exit 1
fi

export PATH="$CUDA_ROOT/bin:$ENV_PATH/bin:$PATH"
if [ -d "$CUDA_ROOT/targets/x86_64-linux/lib" ]; then
  export LD_LIBRARY_PATH="$CUDA_ROOT/targets/x86_64-linux/lib:${LD_LIBRARY_PATH:-}"
elif [ "$CUDA_ROOT" = "/usr" ]; then
  export LD_LIBRARY_PATH="/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}"
else
  export LD_LIBRARY_PATH="$CUDA_ROOT/lib64:$CUDA_ROOT/lib:${LD_LIBRARY_PATH:-}"
fi

CMAKE_COMPILER_ARGS=()
if [ -x "$ENV_PATH/bin/x86_64-conda-linux-gnu-gcc" ] && [ -x "$ENV_PATH/bin/x86_64-conda-linux-gnu-g++" ]; then
  export CC="$ENV_PATH/bin/x86_64-conda-linux-gnu-gcc"
  export CXX="$ENV_PATH/bin/x86_64-conda-linux-gnu-g++"
  export CUDAHOSTCXX="$CXX"
  CMAKE_COMPILER_ARGS+=("-DCMAKE_C_COMPILER=$CC" "-DCMAKE_CXX_COMPILER=$CXX" "-DCMAKE_CUDA_HOST_COMPILER=$CXX")
fi

if [ -z "$OVM_CUDA_ARCHITECTURES" ] && command -v nvidia-smi >/dev/null 2>&1; then
  OVM_CUDA_ARCHITECTURES="$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader 2>/dev/null | head -n 1 | tr -d '.' | tr -cd '0-9')"
fi
if [ -z "$OVM_CUDA_ARCHITECTURES" ]; then
  OVM_CUDA_ARCHITECTURES="120"
fi

echo "Using CUDA root for COLMAP build: $CUDA_ROOT"
echo "Using CUDA architectures for COLMAP build: $OVM_CUDA_ARCHITECTURES"
echo "COLMAP install prefix: $ENV_PATH"

mkdir -p "$WORK_ROOT"
if [ ! -d "$COLMAP_SRC/.git" ]; then
  git clone --recursive https://github.com/colmap/colmap.git "$COLMAP_SRC"
fi

git -C "$COLMAP_SRC" fetch --tags --recurse-submodules=no
git -C "$COLMAP_SRC" checkout "$COLMAP_VERSION"
git -C "$COLMAP_SRC" submodule update --init --recursive

cmake -S "$COLMAP_SRC" -B "$BUILD_DIR" \
  -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="$ENV_PATH" \
  -DCMAKE_CUDA_COMPILER="$CUDA_ROOT/bin/nvcc" \
  -DCMAKE_CUDA_ARCHITECTURES="$OVM_CUDA_ARCHITECTURES" \
  "${CMAKE_COMPILER_ARGS[@]}" \
  -DCUDA_ENABLED=ON \
  -DGUI_ENABLED=OFF \
  -DTESTS_ENABLED=OFF

cmake --build "$BUILD_DIR" -j "${COLMAP_BUILD_JOBS:-4}"
cmake --install "$BUILD_DIR"

"$ENV_PATH/bin/colmap" -h | head -n 4
if "$ENV_PATH/bin/colmap" -h 2>&1 | grep -q "without CUDA"; then
  echo "COLMAP was installed without CUDA; inspect $BUILD_DIR/CMakeCache.txt" >&2
  exit 1
fi

echo "CUDA-enabled COLMAP installed under $ENV_PATH/bin/colmap"
