# Gaussian Splat History

## 2026-06-30

### Studio Viewer / Reconvert Checkpoint

- `viewer_splat.html` 退場，Gaussian Splat 瀏覽入口統一改成 `viewer_splat.php`。
- `viewer_splat.php?id=...` 與數字型 `src=...` 會先解析成 Studio job artifact，再交給 `api.php?mode=getSplat&uuid=...` 下載，避免 viewer 把 job id 誤當檔案路徑。
- Splat viewer 下載資料時已加入進度條，比照 OpenMVS viewer 的使用感；若 response 沒有 `Content-Length`，會用 job artifact size 做進度 fallback。
- Viewer bootstrap 增加 artifact format / size metadata，並保留旋轉、上方向、alpha、scale 等檢視參數。
- Admin「重試」語意改成「重轉」，並在 modal 裡分成兩種流程：
  - 同編號重轉：保留 `input/`，清掉產物並用同一個 job id 重新排隊。
  - 新建編號重轉：複製來源影片到新 job，保留舊成果作版本對照。
- Admin running job 會顯示階段式進度條，讓轉檔中狀態更接近 OpenMVS 後台體驗。
- 詳細 / log lightbox 已限制在 viewport 內，長 log 改由內容區捲動，避免捲軸超出畫面不好滑。
- Gaussian mode 預設訓練 cap 調整為：
  - `fast = 10000`
  - `qa = 30000`
  - `premium = 60000`
- Mode-specific overrides 保留：
  - `GS_FAST_TRAIN_MAX_ITERATIONS`
  - `GS_QA_TRAIN_MAX_ITERATIONS`
  - `GS_PREMIUM_TRAIN_MAX_ITERATIONS`
- 已建立 signed-off local git checkpoint：
  - `b02f98f feat: checkpoint gaussian splat studio pipeline`
- Local bare remote：
  - `local -> ../gaussian_splat.git`
- Branch：
  - `codex/fix-transform-origin`
- Runtime artifacts 已排除版本控制：
  - `data/`
  - `downloads/`
  - `external/`
  - `outputs/`
  - `*.log`
  - `.superpowers/`
- Deferred：
  - 不做手機端 3DGS 訓練。
  - 不做原生 Viewer App。
  - 不做 public share token / 付款 / 帳號系統。
  - Gaussian cleanup / prune 與 delivery quality gate 留到後續 GS-Q1。

## 2026-06-05

### Viewer Calibration

- Viewer 初始角度調整後，以 `rx=0&ry=0&rz=0&up=view` 作為目前預設基準。
- Rotation debug UI 已可顯示並調整 `rx / ry / rz / up`。
- 修正 select 下拉選單白底白字問題。
- 目前判斷：自製 viewer 已可用來檢查結果，但正式品質判斷仍應優先用 Nerfstudio official viewer 對照。

### Quality Pipeline Direction

- 方向從「能否跑出 Gaussian Splat」轉為「品質是否可交付」。
- 決定先固定原始照片流程，暫緩 Real-ESRGAN，避免把增強影像引入 COLMAP 造成額外變因。
- MVP 品質主線：
  - Frame selector
  - COLMAP registration report
  - 30k splatfacto training
  - QA report
  - Low-confidence splat cleanup
  - Evidence report

### Implemented Development

- 新增/更新 Gaussian Splat 品質診斷計畫：
  - `docs/superpowers/plans/2026-06-05-gaussian-splat-quality-diagnostics.md`
  - `docs/frame-quality-runbook.md`
  - `docs/gaussian-splat-handoff-2026-06-05.md`
- 新增 A/B evidence report：
  - `scripts/build_ab_evidence_report.py`
  - `tests/test_ab_evidence_report.py`
- 新增 frame quality 與 COLMAP annotation：
  - `scripts/annotate_frame_quality_colmap.py`
  - `tests/test_annotate_frame_quality_colmap.py`
- 更新 pipeline timing / QA / cleanup：
  - `scripts/pipeline_timing.py`
  - `scripts/build_qa_report.py`
  - `scripts/filter_splat_ply.py`
  - `scripts/run_mvp_pipeline.sh`
- Evidence report 已加入結論欄：
  - Recommended Variant
  - Reason
  - Known Issues
  - Next Action

### selected_30k Run

Command:

```bash
GS_FRAME_CANDIDATE_FPS=12 GS_FRAME_TARGET_FPS=3 GS_FRAME_MAX_FRAMES=180 GS_TRAIN_MAX_ITERATIONS=30000 \
  bash scripts/run_mvp_pipeline.sh data/test001/input.mp4 uploads/eval-selected-30k
```

Key results:

| Metric | Value |
| --- | ---: |
| Candidate frames | 361 |
| Selected frames | 91 |
| Registered frames | 91 |
| Registered ratio | 1.00 |
| QA grade | A |
| Raw splats | 346,738 |
| Clean splats kept | 300,830 |
| Clean splats removed | 45,908 |
| Clean kept ratio | 0.87 |
| Total duration | 2,179.9 sec |

Stage timing:

| Stage | Duration |
| --- | ---: |
| Frame selection | 15.33 sec |
| COLMAP pose estimation | 1,084.34 sec |
| Frame COLMAP annotation | 0.08 sec |
| Splatfacto training | 1,040.65 sec |
| Splat export | 35.49 sec |
| Splat cleanup | 3.55 sec |
| Finalize QA | 0.11 sec |

Output files:

- `uploads/eval-selected-30k/evidence.md`
- `uploads/eval-selected-30k/evidence.json`
- `uploads/eval-selected-30k/qa_report.json`
- `uploads/eval-selected-30k/frame_quality_report.json`
- `uploads/eval-selected-30k/timing_report.json`
- `uploads/eval-selected-30k/exports/splat.ply`
- `uploads/eval-selected-30k/exports/splat.clean.ply`
- `uploads/eval-selected-30k/exports/splat.clean.viewer.json`

Viewer links:

```text
https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_splat.html?src=uploads%2Feval-selected-30k%2Fexports%2Fsplat.clean.ply&meta=uploads%2Feval-selected-30k%2Fexports%2Fsplat.clean.viewer.json&rx=0&ry=0&rz=0&up=view
```

```text
https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_splat.html?src=uploads%2Feval-selected-30k%2Fexports%2Fsplat.ply&rx=0&ry=0&rz=0&up=view
```

Evidence conclusion:

- Recommended Variant: `selected_30k`
- Reason: `registered_ratio = 1.00` and `quality_grade = A`
- Known Issues: PSNR is not computed until rendered eval images are available.
- Next Action: review clean viewer; if artifacts remain, tune cleanup clustering before Real-ESRGAN.

### Official Viewer Note

Official viewer command:

```bash
TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1 /park/conda_vm/gs_scene/bin/ns-viewer \
  --load-config uploads/eval-selected-30k/outputs/processed/splatfacto/2026-06-05_175720/config.yml \
  --viewer.websocket-port 7007 \
  --viewer.websocket-host 0.0.0.0
```

Observed issue:

- Checkpoint can load.
- Port `7007` showed `LISTEN`.
- HTTP connection still timed out in this session.
- Process was stopped.
- Needs a separate official viewer connectivity debug pass before treating official viewer URL as reliable.

### Verification

Ran after the evidence conclusion patch:

```bash
pytest -q
python3 -m py_compile scripts/build_ab_evidence_report.py scripts/annotate_frame_quality_colmap.py scripts/build_qa_report.py scripts/filter_splat_ply.py scripts/pipeline_timing.py scripts/prepare_enhanced_training_dataset.py
```

Result:

- Tests passed.
- Python compile check passed.

### Next Steps

1. Visually review `uploads/eval-selected-30k/exports/splat.clean.ply`.
2. If acceptable, run full A/B package:
   - `baseline_30k`
   - `selected`
   - `selected_30k`
3. If clean viewer still has many glass-shard artifacts, implement cleanup Phase 2:
   - KDTree/DBSCAN or similar spatial clustering.
   - Keep largest component.
   - Add `outlier_ratio` and `largest_component_ratio`.
   - Compare raw vs clean vs clustered-clean.
4. Keep Real-ESRGAN deferred until original-photo selected pipeline is visually stable.
5. After quality stabilizes, start Cesium/Easymap integration plan.

## 2026-06-06 Garden Vase Splat vs Mesh Extraction

Experiment:

- Garden Vase

Result:

- Gaussian Splat retains scene appearance and spatial context.
- Direct Poisson mesh extraction from cleaned splat is not visually acceptable.

Observation:

- Reality fidelity and geometric fidelity are different objectives.

Conclusion:

- Gaussian Splat should currently be treated as a Reality Layer, not as a replacement for BIM/GLB geometry.

## 2026-06-15 Golden Benchmark Pack: uploads/3

Goal:

- Turn the Gaussian Splat work from "it ran" into a Golden Benchmark Pack that can prove whether the route is improving.
- Keep official-viewer and custom-viewer evidence separate.
- Track machine metrics, scorecard placeholders, capture diagnosis, and artifact mapping.

Implementation:

- Added `scripts/build_golden_benchmark_pack.py`.
- Added `tests/test_golden_benchmark_pack.py`.
- Added design spec: `docs/superpowers/specs/2026-06-15-golden-benchmark-pack-design.md`.
- Added implementation plan: `docs/superpowers/plans/2026-06-15-golden-benchmark-pack.md`.

Path note:

- Preferred benchmark path was `uploads/benchmark-uploads-3`.
- `uploads/` root was not writable by shell user because it is owned by `www-data`.
- Actual benchmark path is `uploads/3/benchmark-uploads-3`.

Run:

```bash
GS_FRAME_CANDIDATE_FPS=12 GS_FRAME_TARGET_FPS=3 GS_FRAME_MAX_FRAMES=180 GS_TRAIN_MAX_ITERATIONS=30000 \
  bash scripts/run_mvp_pipeline.sh uploads/3/input/input.mp4 uploads/3/benchmark-uploads-3/new-selected-30k
```

Result:

| Metric | Old uploads/3 | New selected_30k |
| --- | ---: | ---: |
| Frames | 32 | 48 |
| Registered frames | 25 | 41 |
| Registered ratio | 0.78 | 0.85 |
| Splat count | 118,696 | 204,477 |
| Clean splats kept |  | 180,390 |
| Clean kept ratio |  | 0.88 |
| QA grade |  | B |
| Total duration |  | 1,939.29 sec |

Stage timing:

| Stage | Duration |
| --- | ---: |
| Frame selection | 13.81 sec |
| COLMAP pose estimation | 216.09 sec |
| Frame COLMAP annotation | 0.12 sec |
| Splatfacto training | 1,676.47 sec |
| Splat export | 30.00 sec |
| Splat cleanup | 2.22 sec |
| Finalize QA | 0.19 sec |

Evidence:

- `uploads/3/benchmark-uploads-3/benchmark.md`
- `uploads/3/benchmark-uploads-3/benchmark.generated.md`
- `uploads/3/benchmark-uploads-3/benchmark.json`
- `uploads/3/benchmark-uploads-3/ab_evidence.md`
- `uploads/3/benchmark-uploads-3/ab_evidence.json`
- `uploads/3/benchmark-uploads-3/capture_diagnosis.md`
- `uploads/3/benchmark-uploads-3/scorecard.md`

Conclusion:

- Recommended Variant: `new_selected_30k_clean`.
- Reason: selected pipeline improved registration from `0.78` to `0.85`, reached QA grade `B`, and produced measurable cleanup evidence.
- Known Issues: selected frame count is only `48`; PSNR and published web-viewer screenshots are pending.
- Next Action: review clean splat through the 3wa web viewer, then tune cleanup Phase 2 if glass-shard artifacts remain. Nerfstudio official viewer remains useful for local diagnostics, but port `7007` may be blocked by firewall on the host.

## 2026-06-20 Outdoor Trench Technical Foundation Plan

Scope:

- Keep Phase 1 mobile web capture guide as the product direction.
- Implement server-side 3D processing foundations first.
- Add trench coverage QA, georef metadata, trench-focused splat delivery, engineering QA, and delivery manifest.
- Reserve oblique projection and GLB hybrid delivery modes for map-review alternatives.

Primary spec:

- `docs/superpowers/specs/2026-06-20-outdoor-trench-reality-layer-design.md`

Implementation plan:

- `docs/superpowers/plans/2026-06-20-outdoor-trench-technical-foundation.md`

Operational note:

- `GS_TRENCH_MODE=1` now extends the standard MVP pipeline after standard `qa_report.json` generation, producing `input_manifest.json`, `trench_coverage_report.json`, `georef.json`, `exports/splat.trench.ply`, `exports/splat.trench.viewer.json`, `trench_qa_report.json`, and `delivery_manifest.json`.

## 2026-06-21 Official Graphdeco Native Benchmark

Scope:

- Cloned the official `graphdeco-inria/gaussian-splatting` repository with submodules.
- Created isolated conda environment at `/park/conda_vm/graphdeco_native`.
- Installed official CUDA extensions: `diff_gaussian_rasterization`, `simple_knn`, and `fused_ssim`.
- Ran official `train.py` on official `tandt/train`.

Reference:

- Plan: `docs/superpowers/plans/2026-06-21-graphdeco-native-benchmark.md`
- Notes: `uploads/3/official-graphdeco-native/benchmark-notes.md`
- Official commit: `54c035f7834b564019656c3e3fcc3646292f727d`

Results:

- Smoke test: 100 iterations completed.
- Native 7k run completed.
- Train metric at iteration 7000: `L1 0.0663874477148056`, `PSNR 20.103558349609376`.
- Raw official PLY: `uploads/3/official-graphdeco-native/train-7k/model/point_cloud/iteration_7000/point_cloud.ply`
- Raw splats: `738963`, size `174.77 MB`.
- Auxiliary clean PLY: `uploads/3/official-graphdeco-native/train-7k/model/point_cloud/iteration_7000/point_cloud.clean.ply`
- Clean splats: `263810`, size `62.4 MB`.

Next action:

- Inspect raw official PLY in `viewer_splat.html`.
- Compare official 7k vs Nerfstudio 7k.
- If official 7k looks materially better, run official 30k as the Golden Benchmark baseline before adding our own cleanup or GIS value-adds.

### Official Render Truth Test

Ran official Graphdeco `render.py` against the native 7k model.

Artifacts:

- Render output: `uploads/3/official-graphdeco-native/train-7k/model/train/ours_7000/renders/`
- Ground truth output: `uploads/3/official-graphdeco-native/train-7k/model/train/ours_7000/gt/`
- Contact sheet: `uploads/3/official-graphdeco-native/train-7k/model/train/ours_7000/render_contact_sheet.jpg`
- Render/GT sheet: `uploads/3/official-graphdeco-native/train-7k/model/train/ours_7000/render_vs_gt_sheet.jpg`

Conclusion:

- Official renderer output is recognizable and close to the source train views.
- The severe blue fog / white shard artifacts seen in `viewer_splat.html` are not present in official renders.
- Current blocker is the custom web viewer/runtime interpretation of Graphdeco PLY, not the official native training result.

## 2026-06-21 SfM Mapper A/B Plumbing

Decision:

- RealityScan is not part of the open-source core pipeline.
- GLOMAP is now maintained inside COLMAP, but the installed `/usr/bin/colmap` is 3.7 and does not expose `global_mapper`.
- Start with A/B for `mapper` vs `hierarchical_mapper`, because both are available locally.

Implementation:

- `scripts/process_nerfstudio.sh` now supports `GS_SFM_MAPPER=incremental|hierarchical|nerfstudio`.
- `incremental` runs COLMAP `mapper`.
- `hierarchical` runs COLMAP `hierarchical_mapper`.
- `nerfstudio` preserves the legacy Nerfstudio-managed processing path.
- The pipeline stage label changed from `COLMAP pose estimation` to `SfM pose estimation`.
- `processed/sfm_report.json` records mapper, matcher, image count, registered count, registered ratio, sparse model path, database path, and COLMAP version.
- `qa_report.json` includes the `sfm` summary when `processed/sfm_report.json` exists.

Smoke test:

- Source: 12 selected frames from `uploads/3/benchmark-uploads-3/new-selected-30k/images`.
- Incremental output: `uploads/3/sfm-ab-smoke/incremental/transforms.json`.
- Incremental result: `12/12` registered, `registered_ratio = 1.0`.
- Hierarchical output: `uploads/3/sfm-ab-smoke/hierarchical/transforms.json`.
- Hierarchical result: `12/12` registered, `registered_ratio = 1.0`.

Next A/B command targets:

```bash
GS_SFM_MAPPER=incremental GS_SFM_MATCHER=exhaustive \
GS_FRAME_CANDIDATE_FPS=12 GS_FRAME_TARGET_FPS=3 GS_FRAME_MAX_FRAMES=180 GS_TRAIN_MAX_ITERATIONS=30000 \
  bash scripts/run_mvp_pipeline.sh uploads/3/input/input.mp4 uploads/3/benchmark-uploads-3/selected-30k-incremental

GS_SFM_MAPPER=hierarchical GS_SFM_MATCHER=exhaustive \
GS_FRAME_CANDIDATE_FPS=12 GS_FRAME_TARGET_FPS=3 GS_FRAME_MAX_FRAMES=180 GS_TRAIN_MAX_ITERATIONS=30000 \
  bash scripts/run_mvp_pipeline.sh uploads/3/input/input.mp4 uploads/3/benchmark-uploads-3/selected-30k-hierarchical
```

## 2026-06-21 SfM Mapper A/B Result

Completed full selected-30k A/B for `uploads/3/input/input.mp4`.

Result:

- Incremental mapper: `41 / 48` registered, `registered_ratio = 0.85`, QA grade `B`, `220,129` exported splats.
- Hierarchical mapper: `41 / 48` registered, `registered_ratio = 0.85`, QA grade `B`, `223,358` exported splats.
- Incremental total duration: `2,096.65s`.
- Hierarchical total duration: `2,176.31s`.
- Incremental SfM duration: `146.50s`.
- Hierarchical SfM duration: `153.67s`.

Decision:

- Keep `GS_SFM_MAPPER=incremental` as the default for the current small/medium selected-frame workflow.
- Keep `GS_SFM_MAPPER=hierarchical` available for larger captures and future outdoor roadwork/drainage benchmarks.
- This A/B does not show a quality or speed win for hierarchical on the 48-frame `uploads/3` selected dataset.

Report:

- `uploads/3/benchmark-uploads-3/sfm_mapper_ab.md`

## 2026-06-21 - Blender Photogrammetry QA Pack Plan

- Approved G1.8 design.
- First implementation generates `blender-pack` for `selected-30k-hierarchical`.
- 3wa server generates `blender_qa_manifest.json`, COLMAP-derived `sparse_points.ply`, proxy frames, `camera_path.json`, initial `blender_qa_report.json`, and `README.md`.
- Blender inspection happens on a Windows/GUI engineering machine.
- Blender is not a replacement for 3DGS, not a server dependency, and not the 3wa viewer.
- First command:

```bash
python3 scripts/generate_blender_pack.py uploads/3/benchmark-uploads-3/selected-30k-hierarchical
```

## 2026-06-21 - First Blender QA Pack Artifact

- Generated first Blender QA Pack:
  - `uploads/3/benchmark-uploads-3/selected-30k-hierarchical/blender-pack`
- Use `README.md` inside the pack for Blender import steps.
- Use `blender_qa_report.json` and `blender_qa_notes.md` to classify whether artifacts are capture, SfM, training, cleanup, or viewer-related.

## 2026-06-22 - Runtime ROI / Low-Confidence Region Metadata

- Added `scripts/build_confidence_regions.py`.
- Added `tests/test_confidence_regions.py`.
- Purpose: generate `roi_candidates.json` and `low_confidence_regions.json` for future viewer fade/remove and cleanup experiments.
- Important finding: Blender/COLMAP sparse points and Nerfstudio exported splat PLY do not share the same runtime coordinate space. Sparse ROI is useful for Blender diagnostics, but should not directly crop web splats.
- Current runtime recommendation uses `splat.clean.ply` positions to build `splat-clean-robust-bbox`.

Generated for `uploads/3/benchmark-uploads-3/selected-30k-hierarchical`:

- `exports/roi_candidates.json`
- `exports/low_confidence_regions.json`

Key result:

| Metric | Value |
| --- | ---: |
| Sparse points | 6,333 |
| Cameras | 41 |
| Clean splats | 199,065 |
| Recommended ROI | `splat-clean-robust-bbox` |
| Inside runtime ROI | 178,602 |
| Outside runtime ROI | 20,463 |
| Outside ratio | 0.1028 |

Diagnostic note:

- `sparse-core-robust-bbox` covers only `15 / 199,065` runtime splats, proving direct sparse-to-splat filtering would incorrectly remove the visible subject.

Verification:

```bash
pytest -q tests/test_confidence_regions.py tests/test_blender_qa_pack.py tests/test_georef_metadata.py tests/test_trench_coverage_report.py
python3 -m py_compile scripts/build_confidence_regions.py
python3 -m json.tool uploads/3/benchmark-uploads-3/selected-30k-hierarchical/exports/roi_candidates.json >/dev/null
python3 -m json.tool uploads/3/benchmark-uploads-3/selected-30k-hierarchical/exports/low_confidence_regions.json >/dev/null
```

Next action:

- Wire `low_confidence_regions.json` into a viewer-side fade test or generate a derived ROI-filtered PLY variant before Cesium/Three.js integration.
