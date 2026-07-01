#!/usr/bin/env bash
set -euo pipefail

CONDA_ROOT="${CONDA_ROOT:-/DATA/conda_vm/miniforge3}"
CONDA="${CONDA:-$CONDA_ROOT/bin/conda}"
ENV_PATH="${OPENMVS_CONDA_ENV:-/DATA/conda_vm/openmvs}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONDA_ENV_FILE="${CONDA_ENV_FILE:-$PROJECT_ROOT/requirements/conda-openmvs.yml}"
WORK_ROOT="${OPENMVS_BUILD_ROOT:-/DATA/conda_vm/openmvs_src}"
OPENMVS_SRC="$WORK_ROOT/openMVS"
VCG_SRC="$WORK_ROOT/VCG"
BUILD_DIR="$WORK_ROOT/openmvs_build"
OVM_PREFERRED_CUDA_VERSION="${OVM_PREFERRED_CUDA_VERSION:-12.8}"
OpenMVS_USE_CUDA="${OpenMVS_USE_CUDA:-ON}"
OVM_CUDA_ARCHITECTURES="${OVM_CUDA_ARCHITECTURES:-120}"

if [ ! -x "$CONDA" ]; then
  echo "conda not found at $CONDA" >&2
  exit 1
fi

if [ ! -x "$ENV_PATH/bin/python" ]; then
  echo "Creating conda environment at $ENV_PATH"
  if [ -f "$CONDA_ENV_FILE" ]; then
    "$CONDA" env create -y -p "$ENV_PATH" -f "$CONDA_ENV_FILE"
  else
    "$CONDA" create -y -p "$ENV_PATH" python=3.10
  fi
fi

CMAKE_COMPILER_ARGS=()
if [ "${OpenMVS_USE_CUDA}" = "OFF" ] && command -v gcc >/dev/null 2>&1 && command -v g++ >/dev/null 2>&1; then
  export CC="$(command -v gcc)"
  export CXX="$(command -v g++)"
  export CUDAHOSTCXX="$CXX"
  CMAKE_COMPILER_ARGS+=("-DCMAKE_C_COMPILER=$CC" "-DCMAKE_CXX_COMPILER=$CXX")
elif command -v gcc-13 >/dev/null 2>&1 && command -v g++-13 >/dev/null 2>&1; then
  export CC="$(command -v gcc-13)"
  export CXX="$(command -v g++-13)"
  export CUDAHOSTCXX="$CXX"
  CMAKE_COMPILER_ARGS+=("-DCMAKE_C_COMPILER=$CC" "-DCMAKE_CXX_COMPILER=$CXX" "-DCMAKE_CUDA_HOST_COMPILER=$CXX")
elif [ -x "$ENV_PATH/bin/x86_64-conda-linux-gnu-gcc" ] && [ -x "$ENV_PATH/bin/x86_64-conda-linux-gnu-g++" ]; then
  export CC="$ENV_PATH/bin/x86_64-conda-linux-gnu-gcc"
  export CXX="$ENV_PATH/bin/x86_64-conda-linux-gnu-g++"
  export CUDAHOSTCXX="$CXX"
  CMAKE_COMPILER_ARGS+=("-DCMAKE_C_COMPILER=$CC" "-DCMAKE_CXX_COMPILER=$CXX" "-DCMAKE_CUDA_HOST_COMPILER=$CXX")
fi

CMAKE_BOOST_ARGS=("-DBoost_NO_BOOST_CMAKE=ON" "-DBOOST_LIBRARYDIR=/usr/lib/x86_64-linux-gnu")
BOOST_CONFIG_DIR="$(find "$ENV_PATH/lib/cmake" -maxdepth 1 -type d -name 'Boost-*' | sort | tail -n 1 || true)"
if [ -n "$BOOST_CONFIG_DIR" ]; then
  CMAKE_BOOST_ARGS+=("-DBoost_DIR=$BOOST_CONFIG_DIR")
fi

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
CMAKE_CUDA_ARGS=()
if [ "${OpenMVS_USE_CUDA}" = "ON" ] && [ -n "$CUDA_ROOT" ]; then
  export PATH="$CUDA_ROOT/bin:$PATH"
  if [ -d "$CUDA_ROOT/targets/x86_64-linux/lib" ]; then
    export LD_LIBRARY_PATH="$CUDA_ROOT/targets/x86_64-linux/lib:${LD_LIBRARY_PATH:-}"
  elif [ "$CUDA_ROOT" = "/usr" ]; then
    export LD_LIBRARY_PATH="/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}"
  else
    export LD_LIBRARY_PATH="$CUDA_ROOT/lib64:$CUDA_ROOT/lib:${LD_LIBRARY_PATH:-}"
  fi
  if [ -z "$OVM_CUDA_ARCHITECTURES" ] && command -v nvidia-smi >/dev/null 2>&1; then
    OVM_CUDA_ARCHITECTURES="$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader 2>/dev/null | head -n 1 | tr -d '.' | tr -cd '0-9')"
  fi
  CMAKE_CUDA_ARGS+=("-DCMAKE_CUDA_COMPILER=$CUDA_ROOT/bin/nvcc")
  if [ -n "$OVM_CUDA_ARCHITECTURES" ]; then
    CMAKE_CUDA_ARGS+=("-DCMAKE_CUDA_ARCHITECTURES=$OVM_CUDA_ARCHITECTURES")
    echo "Using CUDA architectures for OpenMVS build: $OVM_CUDA_ARCHITECTURES"
  fi
  echo "Using CUDA root for OpenMVS build: $CUDA_ROOT"
elif [ "${OpenMVS_USE_CUDA}" = "ON" ]; then
  echo "CUDA root not found; CMake will try its default CUDA discovery."
fi

echo "System packages may still be required:"
echo "  sudo apt-get install -y build-essential git cmake ninja-build libboost-all-dev libeigen3-dev libopencv-dev libcgal-dev libceres-dev libglew-dev libglfw3-dev freeglut3-dev libnanoflann-dev"
echo "This script never stores sudo credentials; run the package command manually if prompted."

mkdir -p "$WORK_ROOT"
if [ ! -d "$OPENMVS_SRC" ]; then
  git clone --recurse-submodules --branch v2.4.0 https://github.com/cdcseacave/openMVS.git "$OPENMVS_SRC"
fi
if [ ! -d "$VCG_SRC" ]; then
  git clone https://github.com/cdcseacave/VCG.git "$VCG_SRC"
fi

python3 - "$OPENMVS_SRC" <<'PY'
from pathlib import Path
import sys

root = Path(sys.argv[1])
patches = {
    root / "CMakeLists.txt": [
        ("CMAKE_POLICY(SET CMP0167 NEW)", "CMAKE_POLICY(SET CMP0167 OLD)"),
        ("FIND_PACKAGE(Boost REQUIRED COMPONENTS iostreams program_options system serialization OPTIONAL_COMPONENTS ${Boost_EXTRA_COMPONENTS})",
         "FIND_PACKAGE(Boost REQUIRED COMPONENTS iostreams program_options serialization OPTIONAL_COMPONENTS ${Boost_EXTRA_COMPONENTS})"),
    ],
    root / "libs/IO/CMakeLists.txt": [
        ("pkg_check_modules(${PREFIX} REQUIRED IMPORTED_TARGET ${MODULE_NAME})",
         "pkg_check_modules(${PREFIX} IMPORTED_TARGET ${MODULE_NAME})"),
    ],
    root / "libs/Common/Types.inl": [
        ("compression_params.push_back(cv::IMWRITE_JPEGXL_QUALITY);\n\t\tcompression_params.push_back(95);",
         "return false;"),
    ],
    root / "libs/Common/OBB.inl": [
        ("nanoflann::SearchParams()", "nanoflann::SearchParameters()"),
    ],
    root / "libs/MVS/Scene.cpp": [
        ("nanoflann::SearchParams searchParams(0, 0, false)",
         "nanoflann::SearchParameters searchParams(0, false)"),
    ],
    root / "libs/MVS/SceneReconstruct.cpp": [
        ("#include <CGAL/AABB_traits_3.h>", "#include <CGAL/AABB_traits.h>"),
        ("#include <CGAL/AABB_triangle_primitive_3.h>", "#include <CGAL/AABB_triangle_primitive.h>"),
    ],
}

for path, replacements in patches.items():
    text = path.read_text()
    original = text
    for old, new in replacements:
        text = text.replace(old, new)
    if text != original:
        path.write_text(text)
PY

rm -f "$BUILD_DIR/CMakeCache.txt"

cmake -S "$OPENMVS_SRC" -B "$BUILD_DIR" \
  -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="$ENV_PATH" \
  -DCMAKE_POLICY_DEFAULT_CMP0167=OLD \
  -DOpenMVS_USE_CUDA="${OpenMVS_USE_CUDA}" \
  -DOpenMVS_USE_PYTHON=OFF \
  "${CMAKE_BOOST_ARGS[@]}" \
  -DCGAL_DIR=/usr/lib/x86_64-linux-gnu/cmake/CGAL \
  -DGMP_INCLUDE_DIR=/usr/include/x86_64-linux-gnu \
  -DGMP_LIBRARIES=/usr/lib/x86_64-linux-gnu/libgmp.so \
  -DMPFR_INCLUDE_DIR=/usr/include \
  -DMPFR_LIBRARIES=/usr/lib/x86_64-linux-gnu/libmpfr.so \
  -DOpenCV_DIR=/usr/lib/x86_64-linux-gnu/cmake/opencv4 \
  -DVCG_ROOT="$VCG_SRC" \
  "${CMAKE_COMPILER_ARGS[@]}" \
  "${CMAKE_CUDA_ARGS[@]}"

cmake --build "$BUILD_DIR" -j "${OPENMVS_BUILD_JOBS:-4}"
cmake --install "$BUILD_DIR"

for tool in InterfaceCOLMAP DensifyPointCloud ReconstructMesh RefineMesh TextureMesh TransformScene Tests InterfaceMetashape InterfaceMVSNet InterfacePolycam; do
  if [ -x "$ENV_PATH/bin/OpenMVS/$tool" ]; then
    ln -sf "OpenMVS/$tool" "$ENV_PATH/bin/$tool"
  fi
done

echo "OpenMVS installed under $ENV_PATH"
echo "Use: OPENMVS_BIN_DIR=$ENV_PATH/bin"
