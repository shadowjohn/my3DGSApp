# COLMAP GPU Guide

本文件是「最後可用方法 + 為什麼變成這樣」。每天踩坑流水帳放在 [`history.md`](history.md)。

## Key Finding

COLMAP GPU acceleration can significantly reduce total reconstruction time.

Before enabling GPU, the pipeline bottleneck may appear to be OpenMVS or Gaussian Splatting, but the real bottleneck is often COLMAP Feature Extraction / Matching running on CPU.

After enabling:

- Feature Extraction: GPU accelerated
- Feature Matching: GPU accelerated
- Bundle Adjustment: still CPU-bound

Baseline from `uploads/9/logs/openmvs_pipeline.log` on 2026-06-27:

| Metric | Before GPU | After GPU |
| --- | ---: | ---: |
| Feature Extraction | TBD | 0.034 min |
| Feature Matching | TBD | 0.078 min |
| Mapper / Bundle Adjustment | TBD | 8.812 min |
| Total COLMAP | TBD | 9.003 min |

Benchmark context:

```text
GPU: NVIDIA GeForce RTX 5060 Ti 16GB
CPU: AMD Ryzen 3 4100 4-Core Processor (4C/8T)
Image count: 68
Image resolution: 1600 x 900
COLMAP command: scripts/run_openmvs_pipeline.sh with OVM_PIPELINE_MODE=colmap, COLMAP_GPU_MODE=gpu
```

Next CPU baseline command:

```bash
OVM_PIPELINE_MODE=colmap COLMAP_GPU_MODE=cpu bash scripts/run_openmvs_pipeline.sh <input> <job_dir> <lng> <lat> <alt>
```

## 1. Why（背景）

Photogrammetry 的前段瓶頸通常在特徵提取和匹配。這兩段如果用 CPU，影片抽出幾十到幾百張圖時會很慢；改用 CUDA COLMAP 後，SIFT feature extraction / matching 可以吃 GPU。

COLMAP 會用 GPU 的主要階段：

- `colmap feature_extractor --SiftExtraction.use_gpu 1`
- `colmap exhaustive_matcher --SiftMatching.use_gpu 1`

仍然主要是 CPU 的階段：

- `colmap mapper`
- `colmap image_undistorter`
- bundle adjustment / optimization
- model analysis / sparse model selection

OpenMVS 和 Gaussian 都依賴 COLMAP 的輸出。OpenMVS 的 `InterfaceCOLMAP` 需要 COLMAP dense workspace；Gaussian Splatting 通常也需要 COLMAP sparse reconstruction / camera poses。所以 COLMAP GPU 沒弄好，後面 OpenMVS / Gaussian 都是在等一個慢或不穩的前處理。

重點：COLMAP build 成功不等於 runtime 用到 GPU。一定要同時確認 binary 是 `with CUDA`，runtime 的 `nvidia-smi` 也有吃到 GPU。

## 2. Environment（固定環境）

本機目前確認到的環境：

```text
OS: Ubuntu 22.04.4 LTS (jammy)
GPU: NVIDIA GeForce RTX 5060 Ti
VRAM: 16311 MiB
CPU: AMD Ryzen 3 4100 4-Core Processor (4C/8T)
Driver: 580.159.03
Compute Capability: 12.0
CUDA Toolkit: 12.8 (/DATA/conda_vm/gs_scene)
nvcc: 12.8.61
gcc/g++: 11.4.0
cmake: 3.22.1
ninja: 1.10.1
CUDA COLMAP: /DATA/conda_vm/openmvs/bin/colmap 3.9.1 with CUDA
CPU-only COLMAP: /usr/bin/colmap 3.7 without CUDA
OpenMVS env: /DATA/conda_vm/openmvs
```

固定路徑：

```bash
export OPENMVS_CONDA_ENV=/DATA/conda_vm/openmvs
export COLMAP_BIN_DIR=/DATA/conda_vm/openmvs/bin
export OPENMVS_BIN_DIR=/DATA/conda_vm/openmvs/bin
export OVM_CUDA_ROOT=/DATA/conda_vm/gs_scene
export OVM_PREFERRED_CUDA_VERSION=12.8
export PATH="$COLMAP_BIN_DIR:$OPENMVS_BIN_DIR:$OPENMVS_CONDA_ENV/bin:$PATH"
```

先檢查不要吃到 `/usr/bin/colmap`：

```bash
command -v colmap
colmap -h | head -4
```

正確結果要看到：

```text
COLMAP 3.9.1 -- Structure-from-Motion and Multi-View Stereo
(Commit e9903641 on 2024-01-08 with CUDA)
```

## 3. Build History（累積）

### Build #1：使用 apt / system COLMAP

原因：

- 先確認系統內建工具能不能直接跑。

失敗：

```bash
/usr/bin/colmap -h | head -4
```

結果：

```text
COLMAP 3.7 ... without CUDA
```

原因分析：

- apt 裝到的是 CPU-only COLMAP。
- 就算機器有 NVIDIA GPU，這支 binary 也不會跑 CUDA SIFT。

修正：

- 不再用 `/usr/bin/colmap`。
- 明確把 `/DATA/conda_vm/openmvs/bin` 放在 PATH 前面。

結果：

- 需要自己 build CUDA-enabled COLMAP。

### Build #2：建立專案專用 COLMAP CUDA build

原因：

- OpenMVS 和 Gaussian 都需要同一套可靠的 CUDA COLMAP。
- 避免每個專案各自吃到不同 `colmap`。

使用腳本：

```bash
OVM_CUDA_ROOT=/DATA/conda_vm/gs_scene \
OPENMVS_CONDA_ENV=/DATA/conda_vm/openmvs \
bash scripts/install_colmap_cuda.sh
```

關鍵 CMake：

```bash
-DCMAKE_INSTALL_PREFIX=/DATA/conda_vm/openmvs
-DCMAKE_CUDA_COMPILER=/DATA/conda_vm/gs_scene/bin/nvcc
-DCMAKE_CUDA_ARCHITECTURES=<nvidia-smi compute cap>
-DCUDA_ENABLED=ON
-DGUI_ENABLED=OFF
-DTESTS_ENABLED=OFF
```

失敗防線：

```bash
"/DATA/conda_vm/openmvs/bin/colmap" -h | grep "without CUDA"
```

如果還是 `without CUDA`，腳本直接失敗。

結果：

```text
/DATA/conda_vm/openmvs/bin/colmap
COLMAP 3.9.1 ... with CUDA
```

### Build #3：OpenMVS CUDA build

原因：

- COLMAP GPU 只處理前段特徵與匹配。
- OpenMVS 自己的 densify/refine/texture 若要 GPU，OpenMVS 也要 CUDA build。

使用腳本：

```bash
OVM_CUDA_ROOT=/DATA/conda_vm/gs_scene \
OPENMVS_CONDA_ENV=/DATA/conda_vm/openmvs \
OpenMVS_USE_CUDA=ON \
bash scripts/install_openmvs_env.sh
```

關鍵 CMake：

```bash
-DOpenMVS_USE_CUDA=ON
-DCMAKE_CUDA_COMPILER=/DATA/conda_vm/gs_scene/bin/nvcc
-DCMAKE_CUDA_ARCHITECTURES=<nvidia-smi compute cap>
```

確認：

```bash
/DATA/conda_vm/openmvs/bin/DensifyPointCloud --help | grep -- --cuda-device
ldd /DATA/conda_vm/openmvs/bin/DensifyPointCloud | grep -Ei 'cuda|cudart|curand'
```

結果：

- `/DATA/conda_vm/openmvs/bin/DensifyPointCloud` 支援 `--cuda-device`。
- OpenMVS stage 可以用 `OPENMVS_CUDA_DEVICE=-1`，失敗時 fallback `--cuda-device -2`。

### Build #4：runtime fallback 設計

原因：

- GPU build 成功仍可能 runtime 失敗，例如 driver / CUDA runtime / image data / memory 問題。
- 不能讓整個轉檔因 GPU 一次失敗就死掉。

修正：

- pipeline 開始時先跑 COLMAP GPU probe。
- COLMAP feature / matcher 真實 GPU stage 失敗時，自動重建 database 並 fallback CPU。
- OpenMVS GPU stage 失敗時，自動 retry `--cuda-device -2`。

結果：

- 能優先用 GPU。
- GPU 失敗時仍能完成重建，不讓 job 直接死。

## 4. Final Working Commands

### Build CUDA COLMAP

```bash
cd /var/www/html/demo/php/map/3D/openmvs

OVM_CUDA_ROOT=/DATA/conda_vm/gs_scene \
OPENMVS_CONDA_ENV=/DATA/conda_vm/openmvs \
bash scripts/install_colmap_cuda.sh
```

最後變成這樣的原因：

- `/usr/bin/colmap` 是 `without CUDA`，不能用。
- `/DATA/conda_vm/gs_scene` 有 CUDA 12.8 toolkit。
- `/DATA/conda_vm/openmvs/bin` 是專案可控安裝位置，OpenMVS / Gaussian 都能共用。

### Build CUDA OpenMVS

```bash
cd /var/www/html/demo/php/map/3D/openmvs

OVM_CUDA_ROOT=/DATA/conda_vm/gs_scene \
OPENMVS_CONDA_ENV=/DATA/conda_vm/openmvs \
OpenMVS_USE_CUDA=ON \
bash scripts/install_openmvs_env.sh
```

### Current Pipeline Mode Status

- `openmvs_native` 是目前可用基準：實測轉出的 viewer 畫面正確。
- `colmap` 仍未通過：流程可拿來測 COLMAP GPU / CUDA 環境，但目前轉出的畫面不對，不能當正式輸出路徑。
- upload / cron 預設保留 `openmvs_native`，等 `colmap` 視覺結果修正後再切換。
- `high` preset 尚未穩定：#27 長 MP4 抽滿 360 張後，`CreateStructure` 在 GPU 與 CPU fallback 都 segfault；長影片先用 `normal` / 較低 frame 上限驗證。
- #27 目前 evidence 不像 OOM：kernel log 是 `CreateStructure` segfault，沒有 OOM killer；後續 stage log 已加 `/usr/bin/time -v` 追 Max RSS / signal / exit status。
- 不建議把單一模型直接切成無重疊批次跑：SfM 需要全局 camera pose 與 track，切段會變成多個座標系；若要降風險，先用 frame cap / smart sampling，或把分段 GLB 當多模型輸出再另行對齊。

### Run OpenMVS pipeline with COLMAP GPU

注意：OpenMVS upload 預設 `openmvs_native`，會跳過 COLMAP。要測 COLMAP GPU 必須用 `OVM_PIPELINE_MODE=colmap`。

```bash
cd /var/www/html/demo/php/map/3D/openmvs

env \
  OVM_PIPELINE_MODE=colmap \
  COLMAP_GPU_MODE=gpu \
  COLMAP_GPU_PROBE=1 \
  OPENMVS_CUDA_DEVICE=-1 \
  OVM_CUDA_ROOT=/DATA/conda_vm/gs_scene \
  COLMAP_BIN_DIR=/DATA/conda_vm/openmvs/bin \
  OPENMVS_BIN_DIR=/DATA/conda_vm/openmvs/bin \
  OPENMVS_CONDA_ENV=/DATA/conda_vm/openmvs \
  bash scripts/run_openmvs_pipeline.sh \
    uploads/1/input/input.mp4 \
    uploads/1 \
    120.61022 24.110946 0
```

Cron worker 版：

```bash
cd /var/www/html/demo/php/map/3D/openmvs
printf 'colmap\n' > uploads/<job_id>/input/pipeline_mode.txt

env \
  COLMAP_GPU_MODE=gpu \
  COLMAP_GPU_PROBE=1 \
  OPENMVS_CUDA_DEVICE=-1 \
  OVM_CUDA_ROOT=/DATA/conda_vm/gs_scene \
  COLMAP_BIN_DIR=/DATA/conda_vm/openmvs/bin \
  OPENMVS_BIN_DIR=/DATA/conda_vm/openmvs/bin \
  OPENMVS_CONDA_ENV=/DATA/conda_vm/openmvs \
  php crontab/1_run.php
```

## 5. Verify

### Binary verify

```bash
command -v colmap
colmap -h | head -4
```

必須是：

```text
/DATA/conda_vm/openmvs/bin/colmap
... with CUDA
```

檢查 COLMAP GPU options：

```bash
/DATA/conda_vm/openmvs/bin/colmap feature_extractor -h | grep -E 'SiftExtraction.use_gpu|SiftExtraction.gpu_index'
/DATA/conda_vm/openmvs/bin/colmap exhaustive_matcher -h | grep -E 'SiftMatching.use_gpu|SiftMatching.gpu_index'
```

應該看到：

```text
--SiftExtraction.use_gpu arg (=1)
--SiftExtraction.gpu_index arg (=-1)
--SiftMatching.use_gpu arg (=1)
--SiftMatching.gpu_index arg (=-1)
```

### Minimal command verify

```bash
colmap feature_extractor \
  --database_path database.db \
  --image_path images \
  --ImageReader.single_camera 1 \
  --SiftExtraction.use_gpu 1

colmap exhaustive_matcher \
  --database_path database.db \
  --SiftMatching.use_gpu 1
```

## 6. Runtime Verification

開另一個 terminal：

```bash
watch -n 0.5 nvidia-smi
```

正常現象：

- `Feature Extraction` / SIFT extraction：GPU 使用率會拉高。
- `Exhaustive Matching`：GPU 也可能拉高。
- `Mapper` / Bundle Adjustment：CPU 高是正常的。
- `Image Undistortion`：不要期待 GPU 長時間高載。

pipeline log 要看到：

```text
[env-check] CUDA runtime selected: /DATA/conda_vm/gs_scene
[env-check] COLMAP binary selected: /DATA/conda_vm/openmvs/bin/colmap ... with CUDA
[env-check] Running COLMAP GPU probe
[env-check] COLMAP GPU probe passed
[timing] START colmap_feature COLMAP feature extraction (GPU)
[timing] START colmap_matcher COLMAP exhaustive matching (GPU)
```

看 probe：

```bash
cat uploads/<job_id>/gpu_probe.log
```

看 worker raw log：

```bash
tail -f uploads/<job_id>/logs/openmvs_pipeline.log
```

## 7. Common Errors

### Error: `without CUDA`

症狀：

```bash
colmap -h | head -4
# ... without CUDA
```

原因：

- 吃到 `/usr/bin/colmap`。
- 或 COLMAP build 沒吃到 `-DCUDA_ENABLED=ON`。

修法：

```bash
export PATH=/DATA/conda_vm/openmvs/bin:$PATH
command -v colmap
```

不行就重建：

```bash
OVM_CUDA_ROOT=/DATA/conda_vm/gs_scene \
OPENMVS_CONDA_ENV=/DATA/conda_vm/openmvs \
bash scripts/install_colmap_cuda.sh
```

### Error: 找不到 CUDA / `nvcc`

症狀：

```text
CUDA toolkit not found. Set OVM_CUDA_ROOT...
```

原因：

- 沒有 `/usr/local/cuda-12.8`。
- 但本機 CUDA 12.8 在 `/DATA/conda_vm/gs_scene`。

修法：

```bash
export OVM_CUDA_ROOT=/DATA/conda_vm/gs_scene
$OVM_CUDA_ROOT/bin/nvcc --version
```

### Error: Ceres / build dependency

症狀：

- CMake 找不到 Ceres / Eigen / Boost / CGAL。

原因：

- 系統 build dependency 不完整。

修法：

```bash
sudo apt-get install -y \
  build-essential git cmake ninja-build \
  libboost-all-dev libeigen3-dev libopencv-dev \
  libcgal-dev libceres-dev libglew-dev libglfw3-dev \
  freeglut3-dev libnanoflann-dev
```

### Error: Qt / display

症狀：

- headless server 跑 COLMAP / OpenMVS 時 Qt display 相關錯誤。

原因：

- CLI 在 server 上不應該找 X display。

修法：

```bash
export QT_QPA_PLATFORM=offscreen
```

pipeline 已預設：

```bash
QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"
```

### Error: GPU probe failed

症狀：

```text
[env-check] COLMAP GPU feature probe failed; falling back to CPU
```

原因：

- CUDA runtime / driver / binary / image probe 任一環節失敗。

修法：

```bash
cat uploads/<job_id>/gpu_probe.log
command -v colmap
colmap -h | head -4
nvidia-smi -L
```

必要時暫時跳過 probe：

```bash
COLMAP_GPU_MODE=gpu COLMAP_GPU_PROBE=0 ...
```

但這只是測試，不是最終穩定方案。

## 8. Lessons Learned（重要）

### Lesson 1

不要相信 apt 的 COLMAP。很多發行版套件是 `without CUDA`，有 GPU 也不會用。

### Lesson 2

先確認 COLMAP GPU build，再花時間調 OpenMVS / Gaussian。前段沒 GPU，後面都只是等。

### Lesson 3

Bundle Adjustment 本來就是 CPU。看到 CPU 100% 不代表 GPU 壞掉。

### Lesson 4

Build 成功不等於 runtime 用到 GPU。一定要看 `nvidia-smi`。

### Lesson 5

`command -v colmap` 比你以為的重要。PATH 順序錯，一切都會看起來「有裝」，但其實跑錯 binary。

### Lesson 6

GPU fallback 要保留。正式服務要完成 job，不要因一次 GPU stage fail 就整條死掉。

## 9. TODO

- benchmark RTX 5060 Ti：feature / matching / mapper / total time
- benchmark old GPU，例如 RTX 1080
- 比較 CUDA 12.8 和其他 CUDA runtime
- 記錄多 GPU `gpu_index` / `OPENMVS_CUDA_DEVICE` 策略
- 把 Gaussian 專案實際套用結果補回 [`history.md`](history.md)
- 若 OpenMVS / Gaussian 共用需求變多，再抽一支共用 env loader
