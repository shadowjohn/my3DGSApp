# Gaussian Splat Handoff - 2026-06-05

## Current State

這輪已從「能不能跑出 Gaussian Splat」推進到「品質是否可交付」。目前 `selected_30k` 已完整跑完，並產出 clean PLY、QA report、timing report、frame quality report、evidence report。

主要成果：

- Viewer 預設角度目前以 `rx=0&ry=0&rz=0&up=view` 為基準。
- Frame selector 已可用，這輪從 361 張候選中選 91 張。
- COLMAP 註冊結果很好：91/91 registered，`registered_ratio = 1.00`。
- `splatfacto` 30k training 完成。
- Cleanup 已產出 `splat.clean.ply`，用於降低低信心碎片。
- Evidence report 已新增結論欄位：Recommended Variant、Reason、Known Issues、Next Action。

## Latest Run

Command:

```bash
GS_FRAME_CANDIDATE_FPS=12 GS_FRAME_TARGET_FPS=3 GS_FRAME_MAX_FRAMES=180 GS_TRAIN_MAX_ITERATIONS=30000 \
  bash scripts/run_mvp_pipeline.sh data/test001/input.mp4 uploads/eval-selected-30k
```

Output files:

- `uploads/eval-selected-30k/qa_report.json`
- `uploads/eval-selected-30k/frame_quality_report.json`
- `uploads/eval-selected-30k/timing_report.json`
- `uploads/eval-selected-30k/evidence.md`
- `uploads/eval-selected-30k/evidence.json`
- `uploads/eval-selected-30k/exports/splat.ply`
- `uploads/eval-selected-30k/exports/splat.clean.ply`
- `uploads/eval-selected-30k/exports/splat.clean.viewer.json`

Key metrics:

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

## Viewer Links

Clean viewer:

```text
https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_splat.html?src=uploads%2Feval-selected-30k%2Fexports%2Fsplat.clean.ply&meta=uploads%2Feval-selected-30k%2Fexports%2Fsplat.clean.viewer.json&rx=0&ry=0&rz=0&up=view
```

Raw viewer:

```text
https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_splat.html?src=uploads%2Feval-selected-30k%2Fexports%2Fsplat.ply&rx=0&ry=0&rz=0&up=view
```

Official viewer command:

```bash
TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1 /park/conda_vm/gs_scene/bin/ns-viewer \
  --load-config uploads/eval-selected-30k/outputs/processed/splatfacto/2026-06-05_175720/config.yml \
  --viewer.websocket-port 7007 \
  --viewer.websocket-host 0.0.0.0
```

Note: official viewer loaded the checkpoint, but during this session port `7007` showed `LISTEN` while HTTP connection timed out. The process was stopped. This needs a separate viewer connectivity debug pass before treating the official viewer URL as reliable.

## Development Saved

Implemented pipeline pieces:

- `scripts/build_ab_evidence_report.py`: builds JSON/Markdown evidence reports and now emits a conclusion block.
- `scripts/annotate_frame_quality_colmap.py`: annotates selected frames with COLMAP registration and camera position.
- `scripts/build_qa_report.py`: emits canonical quality metrics and A-D quality grade.
- `scripts/filter_splat_ply.py`: writes cleanup metadata including kept/removed counts and filters.
- `scripts/run_mvp_pipeline.sh`: supports selector toggle, COLMAP annotation, timing, cleanup, and finalize.
- `scripts/pipeline_timing.py`: records pipeline and stage durations.
- `scripts/prepare_enhanced_training_dataset.py`: supports the later selected-pose/original-COLMAP plus enhanced-training experiment.
- `viewer_splat.html` and `js/gaussian_splat_viewer.js`: viewer defaults and rotation/debug UI were adjusted during this round.
- `docs/frame-quality-runbook.md`: A/B runbook and decision rules.
- `docs/superpowers/plans/2026-06-05-gaussian-splat-quality-diagnostics.md`: implementation plan.

Verification already run:

```bash
pytest -q
python3 -m py_compile scripts/build_ab_evidence_report.py scripts/annotate_frame_quality_colmap.py scripts/build_qa_report.py scripts/filter_splat_ply.py scripts/pipeline_timing.py scripts/prepare_enhanced_training_dataset.py
```

Both passed on 2026-06-05 after the evidence conclusion patch.

## Current Interpretation

`selected_30k` is the current recommended variant by metrics:

- `registered_ratio = 1.00` means the selected frames did not hurt COLMAP.
- QA grade `A` means the pipeline evidence is strong enough for internal review.
- Remaining customer-readiness depends on the visual check of `splat.clean.ply`.

If clean viewer still shows serious glass-shard artifacts, the next bottleneck is likely low-confidence splat cleanup, not Real-ESRGAN.

## Next Steps

1. Review the clean viewer visually.
2. If clean viewer is acceptable, run full A/B package:

```bash
GS_FRAME_SELECTOR=0 GS_FRAME_TARGET_FPS=3 GS_FRAME_MAX_FRAMES=180 GS_TRAIN_MAX_ITERATIONS=30000 \
  bash scripts/run_mvp_pipeline.sh data/test001/input.mp4 uploads/eval-baseline-30k

GS_FRAME_CANDIDATE_FPS=12 GS_FRAME_TARGET_FPS=3 GS_FRAME_MAX_FRAMES=180 \
  bash scripts/run_mvp_pipeline.sh data/test001/input.mp4 uploads/eval-selected

python3 scripts/build_ab_evidence_report.py \
  --variant baseline_30k=uploads/eval-baseline-30k \
  --variant selected=uploads/eval-selected \
  --variant selected_30k=uploads/eval-selected-30k \
  --output uploads/eval-ab-quality/evidence.json \
  --markdown uploads/eval-ab-quality/evidence.md \
  --viewer-base-url https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_splat.html
```

3. If clean viewer still has many shards, implement cleanup Phase 2:

- Position clustering with KDTree/DBSCAN.
- Keep largest connected component.
- Report `outlier_ratio` and `largest_component_ratio` in `qa_report.json`.
- Add a cleanup preview/evidence comparison for raw vs clean vs clustered-clean.

4. Defer Real-ESRGAN until the baseline selected/original-photo pipeline is visually stable.
5. After quality stabilizes, start Cesium/Easymap integration plan with model origin, scale, heading/pitch/roll, and metadata handoff.

## Git Note

This handoff records the current development state in files, but it does not create a git commit. The working tree contains multiple modified and untracked files from this development round plus generated data under `uploads/`, `outputs/`, and `data/`.
