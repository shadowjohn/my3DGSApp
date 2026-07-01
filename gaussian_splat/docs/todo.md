# Photogrammetry Studio TODO

目標：把目前的 OpenMVS 與 Gaussian Splat demo，提升成一個可插拔 reconstruction engine、統一 validation、compare viewer、標準交付的 Photogrammetry Studio。

核心原則：

- Mode 是產品選擇，Engine 是平台能力。
- Fast 不等於 OpenMVS；Fast 等於 Default Reconstruction Engine。
- QA 改名為 Validation，因為它包含 coverage、registration、texture、hole、floating、camera、bbox、scale、alignment 等檢查。
- 每個 Engine 只負責產出 Artifact 與 Engine Contract。
- Validation 不知道 OpenMVS、3DGS、VGGT 或 SuGaR，它只讀標準 artifacts 與 contracts。
- Viewer 與 Delivery 不直接猜資料夾結構，只讀 manifest / contract。
- Evidence 第一來源是 COLMAP / SfM。OpenMVS 與 3DGS 第一版只提供 geometry / appearance 補充資料，不負責穩定 visibility。

## 產品模式

### A. Fast Reconstruction

80% 案件預設模式。

```text
Frames
  ↓
Default Reconstruction Engine
  ↓
Validation
  ↓
Delivery
```

目前 `defaultEngine = openmvs`。未來如果 VGGT Mesh 或其他 engine 更好，只換 default engine，不改 UI 與交付流程。

完成條件：

- 新上傳預設為 `fast`。
- Fast 只產主要交付 artifact。
- 使用者看到的是 Fast Reconstruction，不是 OpenMVS。
- Delivery manifest 能指出 primary artifact 與 readiness。

### B. QA Reconstruction

15% 案件使用。3DGS 不作正式交付，只作診斷。

```text
Frames
  ├─ Default Reconstruction Engine
  └─ Diagnostic Engine
      ↓
Validation Report
```

用途：

- Camera coverage
- floating artifacts 判斷
- capture gap 判斷
- 補拍建議
- 判斷問題是拍攝、mesh engine、splat engine、viewer 或 texture

完成條件：

- QA mode 跑 default engine + diagnostic engine。
- 3DGS artifacts 不出現在正式 delivery 裡。
- Validation report 可以回答問題來源。

### C. Premium Reconstruction

5% 高價值案件使用，最高品質交付模式。

```text
Frames / Masks
  ├─ Default Reconstruction Engine
  └─ Fidelity Engine
      ↓
Compare Viewer
Validation Gate
Delivery
```

價值：

- 同步產生 Textured GLB 與 Gaussian Splat。
- Mesh 可編輯，Splat 可高擬真預覽。
- Compare Viewer 可即時切換比對。
- Validation Gate 可快速判斷重建問題來源。

完成條件：

- Premium mode 產出雙成果。
- Compare Viewer 讀 delivery manifest，不寫死 OpenMVS / Gaussian。
- Delivery report 說明每個 artifact 的用途與限制。

## 標準資料結構

建議目標結構：

```text
project/
  input/
    frames/
    masks/
  pipelines/
    fast/
    qa/
    premium/
  engines/
    openmvs/
    gaussian_splat/
    vggt/
    sugar/
  artifacts/
    evidence/
      cameras.json
      points3d_tracks.jsonl
      coverage_summary.json
      geometry_summary.json
      appearance_summary.json
    camera_poses.json
    camera_graph.json
    registration.json
    coverage.json
    scene_stats.json
    sparse.ply
    dense.ply
    mesh.glb
    texture.png
    splat.ply
  validation/
    evidence_manifest.json
    validation_report.json
    coverage_report.json
    texture_report.json
    geometry_report.json
  delivery/
    viewer.html
    compare_viewer.html
    delivery_manifest.json
    report.html
```

第一階段不用一次搬成這個完整目錄。先在現有 `uploads/{id}/` 下產出相容的 manifest / contract，再逐步重構。

## Pipeline Contract

所有 Engine 必須輸出共同 contract。

```json
{
  "engine": "openmvs",
  "engineType": "mesh_reconstruction",
  "status": "completed",
  "mode": "fast",
  "input": {
    "type": "frames",
    "count": 120
  },
  "artifacts": [
    {
      "type": "mesh",
      "path": "artifacts/mesh.glb",
      "format": "glb",
      "engine": "openmvs"
    }
  ],
  "metrics": {
    "registeredFrames": 92,
    "registrationRatio": 0.93,
    "holes": 4,
    "textureBlackRatio": 0.02
  },
  "errors": []
}
```

## Evidence Model v1.0.3

第一版 Evidence Model 以 COLMAP 作為共同根資料源，因為 OpenMVS 與 3DGS 通常都從同一份 SfM workspace 延伸。

```text
COLMAP cameras / images / points3D / tracks
  ↓
SfM Evidence Adapter
  ├─ cameras.json
  ├─ points3d_tracks.jsonl
  └─ coverage_summary.json

OpenMVS mesh / dense cloud / texture
  ↓
Geometry Adapter
  ├─ geometry_summary.json
  └─ geometry_regions.json

3DGS splat / training logs / render metrics
  ↓
Appearance Adapter
  ├─ appearance_summary.json
  └─ splat_summary.json

Validation Aggregator
  ↓
validation_report.json
evidence_manifest.json
```

Contract split:

- `engine_contract.json`: 描述 job 有哪些引擎產物與來源。
- `evidence_manifest.json`: 給 Viewer / API 查 evidence asset 與能力。
- `validation_report.json`: 存判斷結果、分數、原因與補拍建議。

Coordinate rule:

- Base coordinate system is `colmap_world`.
- OpenMVS / 3DGS 第一版若共用同一份 COLMAP workspace，可視為同座標系。
- Viewer 做過 center / scale / rotate 時，必須保存 `viewer_transform`，避免點擊查 evidence 時座標錯位。

OpenMVS adapter v1 should not require per-vertex camera visibility. Visibility 先從 COLMAP tracks 建。

3DGS adapter v1 should avoid strong floater / overfit claims from density alone. Conservative rule: geometry low + COLMAP coverage low + 3DGS appearance pass = suspected appearance overfit / geometry risk.

## Validation Categories

- Registration
- Coverage
- Camera Graph
- Reprojection Error
- Texture
- Mesh Holes
- Floating Artifacts
- Black Area
- Bounding Box
- Scale
- Alignment
- Delivery Readiness

## Roadmap

### Phase -1: Reconstruction Confidence

這一階段排在所有重建流程前面。目的不是開始重建，而是上傳後先判斷值不值得重建，避免花數小時跑 COLMAP / OpenMVS / 3DGS 後才發現結果不可用。

```text
Upload
  ↓
Capture Analyzer
  ├─ Frame Count
  ├─ Blur
  ├─ Coverage
  ├─ Motion
  ├─ Registration Estimate
  ├─ Lighting / Rain / Reflection Risk
  └─ Expected Quality
  ↓
Confidence Score
  ↓
Run / Warn / Require Override / Recommend Recapture
```

Output:

```json
{
  "confidenceScore": 0.45,
  "grade": "C-",
  "decision": "recapture_recommended",
  "estimatedRisk": {
    "blur": "medium",
    "coverage": "low",
    "motion": "high",
    "registration": "low"
  },
  "recommendations": [
    "補拍左後方",
    "補拍車底",
    "補拍油箱附近",
    "建議增加約 8 張"
  ]
}
```

Gate policy:

- [x] `80%+`: 直接進 Fast / QA / Premium。
- [x] `60-79%`: 允許跑，但提示可能需要人工檢查。
- [x] `40-59%`: 預設暫停，建議補拍，可手動 override。
- [x] `<40%`: 不建議重建，避免浪費 GPU / 時間。

First implementation should be conservative:

- [x] Build a local `capture_analyzer` script that reads selected frames or a video.
- [x] Compute cheap metrics first: frame count, blur, brightness, contrast, duplicate/motion estimate.
- [x] Emit `confidence_report.json` with score, grade, risks, and recommendations.
- [x] Add a conservative `confidence_gate` helper with hold/reject/override behavior.
- [x] Later add lightweight COLMAP registration probe as a separate task.
- [x] Add Studio shared `preflight_report.json` for QA / Premium job creation without gating.
- [x] Show Studio preflight summary in job detail without gating.
- [x] Add advisory preflight gate decision in job detail without enforcement.

### Phase 0: Baseline Safety

- [x] Record current OpenMVS and Gaussian Splat upload, worker, viewer, QA behavior.
- [x] Add tests that freeze current critical URLs and admin actions.
- [x] Confirm existing jobs still render after new files are added.

### Phase 1: Contract Foundation

- [x] Define `engine_contract.json` schema.
- [x] Define `evidence_manifest.json` schema.
- [x] Define artifact type vocabulary.
- [x] Define `validation_report.json` schema.
- [x] Define `delivery_manifest.json` schema.
- [x] Define coordinate system fields: `base=colmap_world`, transform chain, and `viewer_transform`.
- [x] Add sample fixtures for Fast, QA, and Premium modes.
- [x] Add COLMAP / SfM Evidence Adapter task before OpenMVS and Gaussian adapters.

### Phase 2: Mode Model

- [x] Add pipeline mode field: `fast`, `qa`, `premium`.
- [x] Make new upload default to `fast`.
- [x] Show mode in index/admin tables and admin detail modal.
- [x] Add guarded admin actions for rerun by mode.

### Phase 3: OpenMVS As Default Engine

- [x] Wrap existing OpenMVS pipeline output as `OpenMVSEngine`.
- [x] Generate `engine_contract.json` from OpenMVS job artifacts.
- [x] Generate `geometry_summary.json` from mesh / dense cloud / texture.
- [x] Map old OpenMVS QA values into validation metrics.
- [x] Do not require per-vertex camera visibility from OpenMVS `.ply`.
- [x] Keep current `model.glb` viewer compatibility.

### Phase 4: Gaussian As Diagnostic / Fidelity Engine

- [x] Generate `engine_contract.json` from Gaussian Splat job artifacts.
- [x] Generate `appearance_summary.json` from splat / training logs / render metrics.
- [x] Add splat validation metrics: black ratio, transparent ratio, opacity, bbox outliers, floating risk.
- [x] Mark Gaussian artifacts as diagnostic-only in QA validation contract.
- [x] Persist/run Gaussian diagnostic artifacts from QA orchestration.
- [x] Mark Gaussian artifacts as delivery-capable only in Premium mode.

### Phase 5: Orchestration

- [x] Implement Fast orchestration: default engine only.
- [x] Add QA contract report builder: `validation/qa_validation_report.json`.
- [x] Add Studio orchestration foundation: project/job/engine_runs data model and engine queue adapters.
- [x] Implement QA orchestration: default engine + diagnostic engine.
  - Implemented by Studio QA worker aggregator; API/UI trigger remains a later product slice.
  - Do not invoke OpenMVS directly from Gaussian worker because OpenMVS runner owns its upload path, DB, and lock semantics.
- [x] Add Studio QA Trigger API/CLI entry.
- [x] Implement Premium orchestration: default engine + fidelity engine + compare viewer.
- [x] Make orchestration resumable and rerunnable.

### Phase 6: Validation Gate

- [x] Build validation aggregation from engine contracts.
- [x] Emit one decision: `deliverable`, `review_needed`, `recapture_recommended`, or `engine_failed`.
- [x] Explain likely root cause: capture, engine, texture, viewer, or unknown.
- [x] Add human-readable report text.

### Phase 7: Delivery

- [x] Generate delivery manifest for each mode.
- [x] Update viewers to read delivery manifest where possible.
- [x] Premium compare viewer switches between Textured GLB and Splat.
- [x] Fast delivery stays simple and quick.

### Phase 8: Project UI

- [x] Make homepage start from Project + Mode.
- [x] Keep Engine selection as advanced option.
- [x] Add Project Detail: pipeline, engine runs, artifacts, validation, delivery.
- [x] Preserve existing direct OpenMVS / Gaussian URLs during transition.

### Phase 9: Studio Project UI

- [x] Add minimal Studio QA surface: create QA job and inspect engine runs.
- [x] Add Studio QA background worker wrapper for cron.
- [x] Add Studio job detail contract/artifact/validation surface.
- [x] Add minimal QA advanced engine options surface.
- [x] Consolidate Studio Project + Mode UI for QA / Premium job creation and detail viewing.

### Phase 10: Delivery Manifest Unification

- [x] Add delivery_manifest.json schema v1.0 with delivery_tracks.
- [x] Align OpenMVS Fast delivery_manifest.json with schema v1.0 while preserving legacy fields.
- [x] Align Gaussian pipeline-mode delivery_manifest.json with schema v1.0 while preserving legacy artifacts.
- [x] Make Studio QA completion write aggregated delivery_manifest.json.
- [x] Make existing viewers read delivery_tracks as the primary path source with legacy artifacts fallback.
- [x] Add studio_job_id viewer entrypoint and explicit missing-manifest / missing-track / missing-artifact UI.
- [ ] Add stronger Studio viewer landing page links for each completed QA job.

### Phase 11: Gaussian Engine Normalization

- [x] Normalize Gaussian engine_contract.json with schema_version, engine_name, pipeline_mode, role, delivery_capable, diagnostics, and validation_summary.
- [x] Keep QA Gaussian role diagnostic and delivery_capable=false.
- [x] Allow Premium Gaussian contract role delivery_capable without implementing Premium orchestration.
- [x] Make Gaussian delivery manifest prefer engine_contract role and delivery_capable values.

### Phase 12: Premium Reconstruction

- [x] Implement Premium dual-engine Studio orchestration lifecycle.
- [x] Enqueue OpenMVS as delivery_capable mesh run through Studio adapter.
- [x] Enqueue Gaussian Splat as delivery_capable splat run through Studio adapter.
- [x] Keep Premium worker idempotent and adapter-only; do not call engine workers directly.
- [x] Generate Premium dual-track delivery manifest.
- [x] Update `studio_jobs.delivery_manifest_path` after Premium terminal aggregation.
- [x] Add Premium compare viewer polish.
- [x] Add Premium trigger API / CLI for pending Studio jobs.
- [x] Add Compare Viewer camera evidence layer foundation without loading full point tracks.
- [x] Add lightweight evidence spatial index builder and manifest contract.
- [x] Add Compare Viewer mesh pick evidence query MVP using spatial index tiles.
- [x] Add Studio evidence query API for per-tile coverage lookup with viewer fallback.
- [x] Add Compare Viewer Sparse Point LOD visualization with lazy loading and render cap.
- [x] Stabilize Viewer Evidence error surfaces, safety checks, fixture smoke, and docs.
- [x] Add Studio QA/Premium E2E smoke harness and runbook without starting workers.
- [x] Run controlled QA/Premium E2E smoke over existing completed engine outputs and record results.
- [x] Add Studio visual system and admin shell styling without changing worker/API/schema behavior.
- [x] Polish Studio job list columns and actions without adding API/search/pagination.
- [x] Polish Studio job detail sections, manifest summary, and evidence links without changing data flow.
- [x] Add protected Studio delivery page MVP without exposing raw worker logs or internal paths.
- [x] Add Worker Ops 10B-1 status fields: attempts, heartbeat, last_error, and worker log path.
- [x] Add Worker Ops 10B-2A stuck running job recovery CLI with dry-run/apply guard.
- [x] Add Worker Ops 10B-2B failed / partial_failed retry policy guard without mutating engine_runs.
- [x] Add Worker Ops 10B-3 protected worker log tail surface.
- [x] Add Worker Ops 10B-4 retention audit CLI without deleting artifacts.
- [x] Add Studio Worker Ops runbook for worker commands, logs, recovery, retention, and troubleshooting.
- [x] Run controlled true rebuild QA smoke: OpenMVS pass, Studio partial aggregation pass, Gaussian diagnostic aborted to avoid uncapped training.
- [x] Add Gaussian QA diagnostic training cap guard before re-running full dual-engine smoke.
- [x] Run capped Gaussian true rebuild QA smoke full pass with Studio job #10, OpenMVS #23, and Gaussian diagnostic #15.
- [x] Freeze Studio QA full-pass baseline in smoke docs and worker ops runbook.

## First Implementation Slice

Do these first:

1. Add `capture_analyzer` and `confidence_report.json` as Phase -1 preflight.
2. Add mode vocabulary and docs fixtures.
3. Freeze `engine_contract.json`, `evidence_manifest.json`, and `validation_report.json`.
4. Add COLMAP / SfM Evidence Adapter for `cameras.json`, `points3d_tracks.jsonl`, and `coverage_summary.json`.
5. Generate OpenMVS geometry summary from existing outputs.
6. Generate Gaussian appearance summary from existing outputs.
7. [x] Add validation report aggregator that reads evidence summaries and contracts.
8. [x] Surface mode + validation summary in the Gaussian Splat admin/index pages.

This slice proves the platform abstraction without rewriting the heavy reconstruction pipelines yet.
