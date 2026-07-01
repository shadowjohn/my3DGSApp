# Photogrammetry GPU History

這份是踩坑時間線。SOP 放 [`colmap_gpu_guide.md`](colmap_gpu_guide.md)。

## 2026-06-24

開始整理 OpenMVS upload queue，需要 MP4 / ZIP 進來後能跑 COLMAP + OpenMVS，再輸出 GLB viewer。

初始問題：

- pipeline 可以排隊，但本機工具鏈還不穩。
- 要確認 COLMAP / OpenMVS 安裝位置。
- 要避免 job 失敗時只留一堆 raw log。

## 2026-06-25

建立 OpenMVS pipeline：

- `scripts/run_openmvs_pipeline.sh`
- `scripts/install_openmvs_env.sh`
- `scripts/install_colmap_cuda.sh`
- `scripts/build_qa_report.py`
- GLB viewer / upload queue / cron worker

GPU 相關發現：

- `/usr/bin/colmap` 存在，但它是 `COLMAP 3.7 ... without CUDA`。
- 不能靠系統 COLMAP。
- 需要專案自己的 CUDA COLMAP。

決策：

- 使用 `/park/conda_vm/openmvs` 當 OpenMVS / COLMAP install prefix。
- 使用 `/park/conda_vm/gs_scene` 的 CUDA 12.8 toolkit。
- `COLMAP_BIN_DIR` 預設指向 `$OPENMVS_CONDA_ENV/bin`。

## 2026-06-26

整理 GPU fallback 與診斷：

- COLMAP GPU mode 預設 `auto`。
- 加入 `COLMAP_GPU_PROBE=1`，先跑小 probe。
- GPU feature / matcher 失敗時 fallback CPU。
- OpenMVS CUDA 透過 `OPENMVS_CUDA_DEVICE=-1`，CPU fallback 是 `-2`。
- raw log 改寫到 filesystem，DB 只存 diagnostic summary。

重要教訓：

- GPU build 成功和 runtime 真正吃 GPU是兩件事。
- 一定要保留 raw log path 和 compact diagnostics，不然很難回頭查。

## 2026-06-27

確認本機環境：

```text
Ubuntu 22.04.4 LTS
NVIDIA GeForce RTX 5060 Ti 16GB
Driver 580.159.03
CUDA Toolkit 12.8 at /park/conda_vm/gs_scene
/park/conda_vm/openmvs/bin/colmap 3.9.1 with CUDA
/usr/bin/colmap 3.7 without CUDA
```

整理文件：

- `docs/colmap_gpu_guide.md`：最終 SOP + 原因
- `docs/history.md`：踩坑時間線

目前穩定結論：

- OpenMVS 預設 native mode 會跳過 COLMAP。
- 要測 COLMAP GPU 必須 `OVM_PIPELINE_MODE=colmap`。
- Gaussian 要抄的是 `/park/conda_vm/openmvs/bin/colmap` 和 `/park/conda_vm/gs_scene` 這組環境，不要抄 `/usr/bin/colmap`。

## 2026-06-30

整理專案版本控制：

- 在 `openmvs` 目錄建立 Git repository。
- 第一版納入 PHP 頁面、cron worker、pipeline scripts、測試與文件。
- `.gitignore` 排除 `uploads/`、`*.log`、`test-results/`、`wiki_runs/`，避免把大型輸入、模型產物、測試輸出和執行 log 放進版控。

pipeline 實測狀態：

- `openmvs_native` 目前轉出的 viewer 畫面正確，先當正式路徑。
- `colmap` 模式仍未成功，轉出畫面不對；暫時只作 GPU / CUDA debug 路徑。
- #27 使用 `openmvs_native` + `high` preset，從 158 秒 MP4 抽滿 360 張；`CreateStructure` 在 feature / match 後出現大量 `Linear solver failure`，GPU 與 CPU fallback 都 segfault，沒有進到 Densify。
- #27 kernel log 顯示 `CreateStructure` signal 11 / segfault，未看到 OOM killer；目前不像單純 RAM 不夠，比較像高影格數讓 native SfM solver 不穩。
- pipeline stage runner 已加 `/usr/bin/time -v`，後續每個 stage log 會留下 Max RSS / signal / exit status，方便判斷是不是記憶體峰值造成。
- 先把 `high` 視為未通過長影片驗證；長 MP4 優先用 `normal` 或降低 frame 上限重跑。
- 單一 SfM 模型不容易直接「分批」：分段會得到不同座標系的子模型；若要分批，較實際的是先降採樣 / 限 frame，或接受多個分段 GLB 後再另做對齊合併。

簽章狀態：

- 本機尚未設定 GPG secret key / `user.signingkey`。
- initial commit 先保留未簽章狀態；日後設定 key 後可用 `git commit --amend -S --no-edit` 補簽。

## 待補

- Gaussian 實際接上後的 build/run log。
- RTX 5060 Ti benchmark。
- 多 GPU / 指定 gpu index 策略。
- CUDA 12.8 對 OpenMVS densify/refine/texture 的實測差異。
