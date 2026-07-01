# Gaussian Splat Frame Quality A/B Runbook

## Goal

用同一支來源影片比較三種 MVP 結果，避免只靠肉眼印象判斷品質：

1. `baseline_30k`: legacy fps=3/no frame selector 的低密度抽幀基準，訓練 30k iterations。
2. `selected`: dense candidate extraction + frame quality selector。
3. `selected_30k`: selected frame set，訓練 30k iterations。

先用 Nerfstudio 官方 viewer 看結果，再回到自製 `viewer_splat.html`。如果官方 viewer 清楚、自製 viewer 糊，問題才會落在 renderer、PLY parsing、camera scale 或 viewer metadata。

## Latest Result: selected_30k on 2026-06-05

這輪已先跑最有機會成為正式流程的 `selected_30k`：

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
| Clean kept ratio | 0.87 |
| Total duration | 2,179.9 sec |

Primary files:

- `uploads/eval-selected-30k/evidence.md`
- `uploads/eval-selected-30k/qa_report.json`
- `uploads/eval-selected-30k/frame_quality_report.json`
- `uploads/eval-selected-30k/timing_report.json`
- `uploads/eval-selected-30k/exports/splat.clean.ply`
- `uploads/eval-selected-30k/exports/splat.clean.viewer.json`

Clean viewer:

```text
https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_splat.html?src=uploads%2Feval-selected-30k%2Fexports%2Fsplat.clean.ply&meta=uploads%2Feval-selected-30k%2Fexports%2Fsplat.clean.viewer.json&rx=0&ry=0&rz=0&up=view
```

Current recommendation from evidence:

- Recommended Variant: `selected_30k`
- Reason: `registered_ratio = 1.00` and `quality_grade = A`
- Known Issues: PSNR is not computed until rendered eval images are available.
- Next Action: review clean viewer; if artifacts remain, tune cleanup clustering before Real-ESRGAN.

## Commands

### Golden benchmark pack: uploads/3 selected_30k

2026-06-15 ran the Golden Benchmark Pack for `uploads/3` under:

```text
uploads/3/benchmark-uploads-3
```

The original preferred output path was `uploads/benchmark-uploads-3`, but `uploads/` is owned by `www-data` and not writable by the shell user in this session. The benchmark was placed under `uploads/3/benchmark-uploads-3`, which is web-readable and writable.

Pipeline command:

```bash
GS_FRAME_CANDIDATE_FPS=12 GS_FRAME_TARGET_FPS=3 GS_FRAME_MAX_FRAMES=180 GS_TRAIN_MAX_ITERATIONS=30000 \
  bash scripts/run_mvp_pipeline.sh uploads/3/input/input.mp4 uploads/3/benchmark-uploads-3/new-selected-30k
```

Key results:

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

Stage timing for `new_selected_30k`:

| Stage | Duration |
| --- | ---: |
| Frame selection | 13.81 sec |
| COLMAP pose estimation | 216.09 sec |
| Frame COLMAP annotation | 0.12 sec |
| Splatfacto training | 1,676.47 sec |
| Splat export | 30.00 sec |
| Splat cleanup | 2.22 sec |
| Finalize QA | 0.19 sec |

Evidence files:

- `uploads/3/benchmark-uploads-3/benchmark.md`
- `uploads/3/benchmark-uploads-3/benchmark.generated.md`
- `uploads/3/benchmark-uploads-3/benchmark.json`
- `uploads/3/benchmark-uploads-3/ab_evidence.md`
- `uploads/3/benchmark-uploads-3/ab_evidence.json`
- `uploads/3/benchmark-uploads-3/capture_diagnosis.md`
- `uploads/3/benchmark-uploads-3/scorecard.md`

Viewer links:

```text
https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_splat.html?src=uploads%2F3%2Fbenchmark-uploads-3%2Fnew-selected-30k%2Fexports%2Fsplat.clean.ply&meta=uploads%2F3%2Fbenchmark-uploads-3%2Fnew-selected-30k%2Fexports%2Fsplat.clean.viewer.json&rx=0&ry=0&rz=0&up=view
```

Conclusion:

- Recommended Variant: `new_selected_30k_clean`
- Reason: registration improved from `0.78` to `0.85`, QA grade is `B`, and cleanup has measurable kept/removed splat evidence.
- Known Issues: selected frame count is only `48`, PSNR is not computed, and visual review still needs published web-viewer screenshots.
- Next Action: review the clean splat through the 3wa web viewer, then tune cleanup Phase 2 if glass-shard artifacts remain. Treat Nerfstudio official viewer as a local diagnostic tool; port `7007` may be blocked by firewall on the host.

### baseline_30k

這組是 legacy fps=3/no frame selector baseline。Task 2 的 `GS_FRAME_SELECTOR=0` 會讓 pipeline 跳過 frame quality selector，只用 fps=3 抽幀作為 30k baseline：

```bash
rm -rf uploads/eval-baseline-30k
mkdir -p uploads/eval-baseline-30k
GS_FRAME_SELECTOR=0 GS_TRAIN_MAX_ITERATIONS=30000 GS_FRAME_TARGET_FPS=3 GS_FRAME_MAX_FRAMES=180 bash scripts/run_mvp_pipeline.sh data/test001/input.mp4 uploads/eval-baseline-30k
```

### selected

```bash
rm -rf uploads/eval-selected
mkdir -p uploads/eval-selected
GS_FRAME_CANDIDATE_FPS=12 GS_FRAME_TARGET_FPS=3 GS_FRAME_MAX_FRAMES=180 bash scripts/run_mvp_pipeline.sh data/test001/input.mp4 uploads/eval-selected
```

### selected_30k

```bash
rm -rf uploads/eval-selected-30k
mkdir -p uploads/eval-selected-30k
GS_TRAIN_MAX_ITERATIONS=30000 GS_FRAME_CANDIDATE_FPS=12 GS_FRAME_TARGET_FPS=3 GS_FRAME_MAX_FRAMES=180 bash scripts/run_mvp_pipeline.sh data/test001/input.mp4 uploads/eval-selected-30k
```

### Evidence report

```bash
python3 scripts/build_ab_evidence_report.py \
  --variant baseline_30k=uploads/eval-baseline-30k \
  --variant selected=uploads/eval-selected \
  --variant selected_30k=uploads/eval-selected-30k \
  --output uploads/eval-ab-quality/evidence.json \
  --markdown uploads/eval-ab-quality/evidence.md \
  --viewer-base-url https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_splat.html
```

## Viewer Checks

每組訓練完先看官方 viewer：

```bash
ns-viewer --load-config uploads/eval-selected/outputs/processed/splatfacto/<date>/config.yml
```

再看 web viewer：

```text
https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_splat.html?src=uploads/eval-selected/exports/splat.ply
```

## Scorecard

| Variant | Registered ratio | Splats kept after filter | Glass shards | Main object texture | Training time | Customer-ready? |
| --- | ---: | ---: | --- | --- | ---: | --- |
| baseline_30k |  |  |  |  |  |  |
| selected |  |  |  |  |  |  |
| selected_30k |  |  |  |  |  |  |

Useful files:

- `uploads/<job>/qa_report.json`
- `uploads/<job>/timing_report.json`
- `uploads/<job>/frame_quality_report.json`
- `uploads/<job>/exports/splat.ply`
- `uploads/<job>/exports/splat.viewer.json` when viewer metadata is generated

## Outdoor Trench Reality Layer Mode

Use this mode for outdoor road excavation and sewer construction benchmarks. It keeps the standard Gaussian Splat pipeline, then adds trench-oriented coverage, georef, delivery, and engineering QA files for map-review handoff.

```bash
GS_TRENCH_MODE=1 GS_FRAME_CANDIDATE_FPS=12 GS_FRAME_TARGET_FPS=3 GS_FRAME_MAX_FRAMES=180 GS_TRAIN_MAX_ITERATIONS=30000 \
  bash scripts/run_mvp_pipeline.sh uploads/<job>/input/input.mp4 uploads/<job>-trench
```

Expected additional files:

- `input_manifest.json`
- `trench_coverage_report.json`
- `georef.json`
- `exports/splat.trench.ply`
- `exports/splat.trench.viewer.json`
- `trench_qa_report.json`
- `delivery_manifest.json`

Viewer link pattern:

```text
https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_splat.html?src=uploads%2F<job>-trench%2Fexports%2Fsplat.trench.ply&meta=uploads%2F<job>-trench%2Fexports%2Fsplat.trench.viewer.json&rx=0&ry=0&rz=0&up=view
```

Decision fields:

- `trench_coverage_report.json`: use `registered_ratio`, `camera_path_span`, warnings, and `coverage_decision` to decide whether the capture is usable or needs supplemental photos.
- `trench_qa_report.json`: use `delivery_grade` and `decision` as the frontstage/customer-facing quality gate.
- `delivery_manifest.json`: records whether the review layer is `gaussian_splat`, `oblique_projection`, `glb_hybrid`, or `mixed`.

The first version uses `splat.clean.ply` as the trench-focused delivery source. True corridor filtering, oblique projection, and GLB hybrid delivery are later improvements after the Gaussian Splat evidence loop is stable.

## MVP Decision Rules

- Use `baseline_30k` vs `selected_30k` to decide whether frame selection helps this capture style.
- Treat `registered_ratio < 0.65` as retake territory even when a viewer output exists.
- Treat `quality_grade A/B` as frontstage acceptable, `C` as internal review, and `D` as retake.
- Do not enable Real-ESRGAN in the MVP evidence loop. It is a later experiment after frame selection, COLMAP, training, and cleanup are stable.
- Use cleanup stats to explain shard reduction: report source splat count, kept splat count, kept ratio, and filters.

## Notes

- Do not judge final quality from the custom viewer first. Confirm in Nerfstudio official viewer before debugging web rendering.
- Do not blend adjacent frames in this runbook. Naive temporal averaging can look smoother, but it can destroy view-consistent features and hurt COLMAP registration.
- Real-ESRGAN is a later experiment outside this MVP evidence loop; do not include Enhanced/Real-ESRGAN runs in the primary A/B report.

## SfM Mapper A/B

Use this benchmark when the capture has many frames or long corridor-like motion, such as road excavation, sewer work, pipe trench inspection, or a long indoor walk-through.

Available mapper modes:

- `GS_SFM_MAPPER=incremental`: COLMAP incremental mapper. This is the stable baseline and the current 3DGS community default.
- `GS_SFM_MAPPER=hierarchical`: COLMAP hierarchical mapper. This is the speed candidate for larger frame sets.
- `GS_SFM_MAPPER=nerfstudio`: legacy Nerfstudio-managed COLMAP processing. Keep this as a fallback if custom mapper plumbing fails.

Smoke test commands:

```bash
GS_SFM_MAPPER=incremental GS_SFM_MATCHER=exhaustive \
  bash scripts/process_nerfstudio.sh uploads/3/sfm-ab-smoke/images uploads/3/sfm-ab-smoke/incremental

GS_SFM_MAPPER=hierarchical GS_SFM_MATCHER=exhaustive \
  bash scripts/process_nerfstudio.sh uploads/3/sfm-ab-smoke/images uploads/3/sfm-ab-smoke/hierarchical
```

Full selected 30k A/B commands:

```bash
GS_SFM_MAPPER=incremental GS_SFM_MATCHER=exhaustive \
GS_FRAME_CANDIDATE_FPS=12 GS_FRAME_TARGET_FPS=3 GS_FRAME_MAX_FRAMES=180 GS_TRAIN_MAX_ITERATIONS=30000 \
  bash scripts/run_mvp_pipeline.sh uploads/3/input/input.mp4 uploads/3/benchmark-uploads-3/selected-30k-incremental

GS_SFM_MAPPER=hierarchical GS_SFM_MATCHER=exhaustive \
GS_FRAME_CANDIDATE_FPS=12 GS_FRAME_TARGET_FPS=3 GS_FRAME_MAX_FRAMES=180 GS_TRAIN_MAX_ITERATIONS=30000 \
  bash scripts/run_mvp_pipeline.sh uploads/3/input/input.mp4 uploads/3/benchmark-uploads-3/selected-30k-hierarchical
```

Read these files first:

- `processed/sfm_report.json`
- `qa_report.json`
- `frame_quality_report.json`
- `timing_report.json`
- `exports/splat.clean.ply`

Compare:

- SfM time
- registered images and `registered_ratio`
- sparse model success/failure
- training time
- splat count
- official render or viewer screenshots
- floaters, glass shards, holes, and subject quality

## Blender Photogrammetry QA Pack

Use this pack when the web viewer shows recognizable subject detail but severe peripheral glass-shard artifacts. It is an inspection handoff pack, not a retraining step.

It does not retrain, does not run Blender on the server, and does not make Blender a server dependency. The 3wa server only prepares artifacts for Blender inspection on a Windows or GUI engineering workstation:

- source frame references and proxy frames
- COLMAP sparse model outputs
- COLMAP-derived sparse point clouds
- camera path JSON
- initial manifest, QA report, README, and notes

First command:

```bash
python3 scripts/generate_blender_pack.py uploads/3/benchmark-uploads-3/selected-30k-hierarchical
```

Expected output path:

```text
uploads/3/benchmark-uploads-3/selected-30k-hierarchical/blender-pack
```

On the workstation:

- Open `blender-pack/README.md` first.
- Install or enable `SBCV/Blender-Addon-Photogrammetry-Importer`.
- Import COLMAP from `blender-pack/import/colmap`.
- Load `blender-pack/import/sparse_points.ply` for the full sparse point cloud, or `blender-pack/proxies/sparse_points_preview.ply` for a lighter sparse preview.
- Use the sparse preview to check camera path, ROI coverage, and whether shards are peripheral instead of subject geometry.
- Use `blender-pack/proxies/frames_50` and `blender-pack/proxies/frames_25` as proxy image backgrounds.
- Use `blender-pack/import/camera_path.json` to review registered camera centers and path continuity.

Capture notes:

- Move around or along the subject; avoid rotating in place.
- Disable stabilization when possible because it can warp frame-to-frame geometry.
- Lock exposure and focus before the capture pass.
- For trenches, capture the corridor path plus cross-angle shots across the trench or work area.
