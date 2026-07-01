# Photogrammetry Studio Task Breakdown

這份文件用來拆分可交給 subagent 共同執行的工作。核心策略是先凍結 shared contract，再讓 subagent 各自負責不同邊界，避免同時改同一批檔案。

## Subagent 分工原則

- 一個 subagent 只負責一個 bounded context。
- 同一 wave 內避免兩個 subagent 修改同一檔案。
- 所有 subagent 都必須先讀 `docs/todo.md`。
- 涉及資料表、API、worker、viewer 的任務要各自有測試。
- subagent 回報必須包含：修改檔案、測試指令、風險、下一步。

## 依賴圖

```text
Wave -1: Reconstruction Confidence
  ↓
Wave 0: Contract Freeze
  ↓
Wave 1: Independent Engine / Validation Work
  ├─ SfM Evidence Adapter
  ├─ OpenMVS Geometry Adapter
  ├─ 3DGS Appearance Adapter
  ├─ Validation Aggregator
  └─ UI Mode Copy / Fixtures
  ↓
Wave 2: Pipeline Orchestration
  ├─ Fast Pipeline
  ├─ QA Pipeline
  └─ Premium Pipeline
  ↓
Wave 3: Delivery / Viewer / Project UI
```

## Wave -1: Reconstruction Confidence

這一波優先於所有 heavy reconstruction。目標是上傳後先做 Capture Analyzer，產生 `confidence_report.json`，避免明顯不值得重建的資料直接進 COLMAP / OpenMVS / 3DGS。

### Task -1A: Capture Analyzer Core

Goal:

Create a standalone analyzer that scores input capture quality without running full reconstruction.

Likely files:

- Create: `scripts/capture_analyzer.py`
- Create: `tests/test_capture_analyzer.py`
- Modify: `docs/todo.md`

Expected implementation:

- Accept either a frame directory or video path.
- For a video path, sample frames cheaply with OpenCV or existing ffmpeg-based helpers if available.
- Compute:
  - frame count
  - blur estimate
  - brightness estimate
  - contrast estimate
  - duplicate / low-motion estimate
  - motion jump risk
- Emit a JSON report with:
  - `confidenceScore`
  - `grade`
  - `decision`
  - `estimatedRisk`
  - `metrics`
  - `recommendations`
- Do not call COLMAP, OpenMVS, 3DGS, or GPU tools in this task.

Checks:

- `pytest -q tests/test_capture_analyzer.py`
- `python3 -m py_compile scripts/capture_analyzer.py`
- Temp-dir tests create synthetic images and verify high/low confidence cases.

Can run as subagent: yes.

Isolation note:

- This subagent owns only `scripts/capture_analyzer.py` and `tests/test_capture_analyzer.py`.
- It must not edit upload UI, API, cron worker, or engine contract files.

### Task -1B: Confidence Queue Gate

Goal:

Integrate confidence reports into the upload / queue flow after Task -1A proves stable.

Likely files:

- Modify: `api.php`
- Modify: `crontab/1_run.php`
- Modify: `job_view.php`
- Modify: `tests/test_php_api_assets.py`
- Modify: `tests/test_cron_worker_assets.py`

Expected behavior:

- Upload or worker preflight creates `confidence_report.json`.
- Low-confidence jobs are marked paused / review-needed instead of immediately burning reconstruction time.
- Admin can override and run anyway.

Checks:

- Low-confidence fixture does not auto-run.
- Override requeues the job.
- Existing uploads without confidence report remain backward compatible.

Can run as subagent: later, after Task -1A.

### Task -1C: Registration Probe

Goal:

Add an optional lightweight registration estimate that is cheaper than full reconstruction.

Likely files:

- Create: `scripts/registration_probe.py`
- Create: `tests/test_registration_probe.py`
- Modify: `scripts/capture_analyzer.py`

Expected behavior:

- Run only when enabled.
- Estimate feature richness / likely registration ratio.
- Timeout aggressively.
- Never block the core cheap analyzer if probe fails.

Checks:

- Probe failure still produces confidence report.
- Timeout behavior is tested without running real COLMAP in unit tests.

Can run as subagent: later, after Task -1A.

## Wave 0: Coordinator Only

不要開 subagent。這一波要先固定命名與 schema，否則後面會互相打架。

### Task 0.1: Contract Schema Freeze

Scope:

- Define canonical mode names: `fast`, `qa`, `premium`.
- Define canonical engine contract fields.
- Define canonical evidence manifest fields.
- Define canonical artifact types.
- Define canonical validation categories.
- Define coordinate system fields with `base=colmap_world` and explicit viewer transforms.

Files:

- Create or modify: `docs/todo.md`
- Create: `docs/schemas/engine_contract.schema.json`
- Create: `docs/schemas/evidence_manifest.schema.json`
- Create: `docs/schemas/validation_report.schema.json`
- Create: `docs/schemas/delivery_manifest.schema.json`
- Create: `docs/fixtures/fast_engine_contract.json`
- Create: `docs/fixtures/evidence_manifest_colmap_openmvs_gaussian.json`
- Create: `docs/fixtures/cross_engine_validation_report.json`
- Create: `docs/fixtures/qa_engine_contract.json`
- Create: `docs/fixtures/premium_delivery_manifest.json`

Checks:

- JSON fixtures parse with `python3 -m json.tool`.
- Schema files contain no engine-specific hardcoding except example values.
- `fast` is described as Default Reconstruction Engine, not OpenMVS.
- Evidence files make COLMAP / SfM the first source for cameras, tracks, and coverage.

Subagent: no.

Reason:

- This is shared state. It should be done once by coordinator.

## Wave 1: Parallel Work After Contract Freeze

These tasks can run in parallel after Wave 0 is complete.

### Task 1A: Mode Model And Admin/API Wiring

Goal:

Add mode awareness to the existing Gaussian Splat management surface without changing reconstruction behavior yet.

Likely files:

- Modify: `migrate.php`
- Modify: `api.php`
- Modify: `index.php`
- Modify: `admin.php`
- Modify: `job_view.php`
- Modify: `tests/test_php_api_assets.py`
- Modify: `tests/test_php_page_assets.py`

Expected implementation:

- Add a DB column such as `pipeline_mode varchar(30) DEFAULT 'fast'`.
- Upload creates jobs with `pipeline_mode='fast'` unless user chooses another mode.
- Admin/index pages display Fast / QA / Premium.
- API validates mode values with a helper.
- Existing jobs without mode display as Fast.

Checks:

- `pytest -q tests/test_php_api_assets.py tests/test_php_page_assets.py`
- Manual upload still works.
- Existing rows without `pipeline_mode` do not break list rendering.

Can run as subagent: yes.

Isolation note:

- This subagent should not edit reconstruction scripts.

### Task 1A+: COLMAP / SfM Evidence Adapter

Goal:

Build the root Evidence adapter from COLMAP outputs. This is the first source for camera coverage, visible camera counts, track length, reprojection error, and sparse density.

Likely files:

- Create: `scripts/build_sfm_evidence.py`
- Create: `tests/test_sfm_evidence.py`
- Reference only: existing COLMAP outputs under `uploads/{id}/processed/colmap` or OpenMVS job workspaces.

Expected implementation:

- Read COLMAP `cameras`, `images`, and `points3D` from text export first; binary support can be added later if no text export exists.
- Emit:
  - `evidence/cameras.json`
  - `evidence/points3d_tracks.jsonl`
  - `evidence/coverage_summary.json`
- Use `colmap_world` as the base coordinate system.
- Include enough track data to answer which images see each sparse point.
- Keep output small enough for API / viewer previews by writing detailed tracks as JSONL, not one giant JSON blob.

Checks:

- Unit test with tiny fake COLMAP text files.
- Coverage summary includes camera count, sparse point count, average track length, and reprojection error summary.
- Malformed or missing COLMAP files fail with a clear message.

Can run as subagent: yes.

Isolation note:

- This subagent should not edit OpenMVS, Gaussian, PHP pages, or viewers.

### Task 1B: OpenMVS Geometry Adapter

Goal:

Convert existing OpenMVS outputs into standard Geometry Evidence Summary. Do not require per-vertex camera visibility from OpenMVS `.ply`; visibility comes from Task 1A+ COLMAP tracks.

Likely files:

- Create: `scripts/build_openmvs_geometry_summary.py`
- Create: `tests/test_openmvs_geometry_summary.py`
- Reference only: `/var/www/html/demo/php/map/3D/openmvs/scripts/build_qa_report.py`

Expected implementation:

- Read known OpenMVS-style artifacts from a job dir.
- Emit:
  - `evidence/geometry_summary.json`
  - `evidence/geometry_regions.json` when cheap region data is available
- Include mesh path, dense point cloud path, texture path, bounding box, vertex count, face count, dense point count, normal availability, texture availability, hole risk summary, thin geometry risk, and density summary.
- If `engine_contract.json` is available, reference these geometry evidence files from it.
- Do not invent camera visibility from dense `.ply` files.

Checks:

- Unit test with a temp job dir containing fake `exports/model.glb`, fake dense cloud, and `qa_report.json`.
- Summary emits useful values even when dense cloud or texture is missing.
- Output does not contain per-vertex visibility fields.

Can run as subagent: yes.

Isolation note:

- This subagent should not edit PHP pages or COLMAP evidence scripts.

### Task 1C: 3DGS Appearance Adapter

Goal:

Convert existing Gaussian Splat outputs into standard Appearance Evidence Summary. Keep v1 conservative across GraphDECO, gsplat, PostShot, SuperSplat, and Nerfstudio format differences.

Likely files:

- Create: `scripts/build_gaussian_appearance_summary.py`
- Create: `tests/test_gaussian_appearance_summary.py`
- Reference only: `scripts/build_qa_report.py`

Expected implementation:

- Emit:
  - `evidence/appearance_summary.json`
  - `evidence/splat_summary.json`
- Include cameras source / COLMAP workspace, splat path, splat count, bounding box, opacity summary if available, scale summary if available, training iterations, training time, final loss / PSNR / SSIM if available.
- Do not classify floaters or overfit from splat density alone.
- Leave cross-engine diagnosis to Task 1D.

Checks:

- Unit test with fake `exports/splat.ply` and `qa_report.json`.
- Summary still emits if training logs are missing.
- Output marks unavailable opacity / scale / render metrics as unknown instead of failing.

Can run as subagent: yes.

Isolation note:

- This subagent should not edit OpenMVS geometry scripts, PHP pages, or viewers.

### Task 1D: Validation Aggregator

Goal:

Build a validation layer that reads SfM, geometry, and appearance evidence summaries plus engine contracts, then produces a platform-level `validation_report.json`.

Likely files:

- Create: `scripts/build_validation_report.py`
- Create: `tests/test_validation_report.py`

Expected implementation:

- Input: `engine_contract.json`, `evidence_manifest.json`, `coverage_summary.json`, `geometry_summary.json`, and `appearance_summary.json` when present.
- Output: validation summary with categories:
  - registration
  - coverage
  - texture
  - geometry
  - splat_health
  - delivery_readiness
- Cross-validation MVP matrix:
  - coverage high + geometry high + appearance high -> Good Dataset
  - coverage low + geometry low + appearance high -> Mesh Risk / Possible 3DGS Overfit
  - coverage high + geometry high + appearance low -> Texture / Lighting / Appearance Issue
  - coverage low + geometry low + appearance low -> Capture Failure
- Decision values:
  - `deliverable`
  - `review_needed`
  - `recapture_recommended`
  - `engine_failed`
- Root cause values:
  - `capture`
  - `engine`
  - `texture`
  - `viewer`
  - `unknown`

Checks:

- Test good coverage + good geometry + good appearance -> deliverable.
- Test low coverage + low geometry + good appearance -> review_needed with possible overfit / mesh risk.
- Test good coverage + good geometry + low appearance -> appearance issue.
- Test low coverage + low geometry + low appearance -> recapture_recommended.

Can run as subagent: yes.

Isolation note:

- This subagent should not edit current worker scripts yet.

### Task 1E: Documentation And UX Copy

Goal:

Make the public planning/demo text align with Photogrammetry Studio vocabulary.

Likely files:

- Modify: `openmvs_rework_plan.html`
- Modify: `docs/todo.md`
- Optional: create `docs/photogrammetry-studio-overview.md`

Expected implementation:

- Replace OpenMVS-first wording with mode-first wording.
- Rename C to Premium Reconstruction.
- Use Validation, not QA, for platform-level reports.
- Explain Engine as pluggable implementation detail.

Checks:

- `curl -I https://3wa.tw/demo/php/map/3D/gaussian_splat/openmvs_rework_plan.html` returns 200 after permission is set to 644.
- Screenshot first viewport if visual layout changes.

Can run as subagent: yes.

Isolation note:

- This subagent should not edit PHP/API/worker code.

## Wave 2: Pipeline Orchestration

Run these after Wave 1 contracts and validation helper are merged.

### Task 2A: Fast Pipeline

Goal:

Make Fast mode call the default reconstruction engine and generate delivery manifest.

Likely files:

- Modify: `crontab/1_run.php`
- Modify: `scripts/run_mvp_pipeline.sh`
- Modify: `tests/test_cron_worker_assets.py`
- Create or modify: `scripts/build_delivery_manifest.py`

Expected behavior:

- `fast` resolves to current default engine.
- Current default engine can remain Gaussian for this folder during transition, or call OpenMVS from the unified project later.
- Worker writes engine contract and validation report.

Checks:

- Pending Fast job is picked by cron.
- Contract and validation report exist after completion.
- Existing upload flow still succeeds.

Can run as subagent: yes, but only after contract helpers exist.

### Task 2B-0: QA Pipeline Contract (Current Task 3A)

Status: contract slice implemented.

Files:

- `scripts/build_qa_validation_report.py`
- `tests/test_qa_pipeline_contract.py`

Done:

- QA report mode is `qa`.
- Default engine is marked `delivery_candidate`.
- Gaussian Splat is marked `diagnostic` and `delivery=false`.
- Report writes `validation/qa_validation_report.json`.
- Decision classifies `capture_issue`, `mesh_issue`, `splat_issue`, or `none`.

Not done in this slice:

- No worker orchestration changes yet.
- No Premium changes.
- No Viewer changes.
- No Project UI changes.

### Task 2B: QA Pipeline

Goal:

Run default engine plus diagnostic engine and produce validation report without delivering diagnostic artifacts.

Likely files:

- Modify: `crontab/1_run.php`
- Modify: `api.php`
- Modify: `job_view.php`
- Modify: `tests/test_cron_worker_assets.py`
- Modify: `tests/test_php_api_assets.py`

Expected behavior:

- QA mode stores diagnostic engine outputs but marks them as non-delivery.
- Validation report includes compare logic.
- UI does not show 3DGS as a formal deliverable in QA mode.

Checks:

- QA mode job has at least two engine contracts.
- Delivery manifest excludes diagnostic splat as primary delivery.
- Validation report includes diagnostic findings.

Can run as subagent: yes, but it will touch orchestration and UI. Do not run in parallel with Task 2C unless file ownership is split.

### Task 2C: Premium Pipeline

Goal:

Run default engine plus fidelity engine and produce compare viewer plus dual delivery manifest.

Likely files:

- Modify: `viewer_compare_splat_mesh.html`
- Modify: `scripts/build_compare_bundle.py`
- Modify: `scripts/build_delivery_manifest.py`
- Modify: `tests/test_mesh_extraction_scripts.py`
- Modify: `tests/test_mesh_viewer_assets.py`

Expected behavior:

- Premium delivery manifest includes mesh and splat.
- Compare viewer reads manifest or generated URLs.
- Validation gate explains whether issues are capture or engine related.

Checks:

- Compare viewer opens with job-specific assets.
- Delivery manifest lists both artifact families.
- Existing compare viewer URLs still work during transition.

Can run as subagent: yes, preferably after Task 2B or with clear file locks.

## Wave 3: UI And Delivery

### Task 3A: Project Detail Page

Goal:

Create a project detail view centered on Project, Pipeline, Engine Runs, Artifacts, Validation, and Delivery.

Likely files:

- Create or modify: `project.php`
- Modify: `index.php`
- Modify: `job_view.php`
- Modify: `tests/test_php_page_assets.py`

Checks:

- User can open a job/project detail page.
- Engine runs and artifacts are grouped by contract.
- Validation decision is visible.

Can run as subagent: yes.

### Task 3B-1: Viewer Evidence Camera Layer

Goal:

Add a lightweight Evidence camera layer to viewers.

Likely files:

- Modify: `viewer_splat.html`
- Modify: `viewer_mesh.html`
- Modify: `viewer_compare_splat_mesh.html`
- Modify: `js/gaussian_splat_viewer.js`
- Modify: `tests/test_viewer_assets.py`
- Modify: `tests/test_mesh_viewer_assets.py`

Checks:

- Existing `?src=` URLs still work.
- New evidence camera layer can load `evidence/cameras.json`.
- Viewer can draw camera positions, frustums, and camera path.
- Cache busting remains active for reruns.

Can run as subagent: yes, but do not run in parallel with Task 2C if both edit compare viewer.

### Task 3B-2: Viewer Click Evidence

Goal:

Let operators click a suspicious region and see nearby evidence without loading the full `points3D` track set into the browser.

Likely files:

- Modify: `viewer_splat.html`
- Modify: `viewer_mesh.html`
- Modify: `viewer_compare_splat_mesh.html`
- Modify: `api.php`
- Modify: `tests/test_viewer_assets.py`
- Modify: `tests/test_php_api_assets.py`

Expected behavior:

- Raycast the clicked viewer point.
- Convert viewer coordinates back through `viewer_transform` into `colmap_world`.
- Call a small API such as `get_evidence_at`.
- Return nearby coverage, visible camera count, sparse point count, and recommendations.
- Highlight selected camera cones and show an evidence panel.

Checks:

- Existing `?src=` URLs still work.
- API returns a clear error when evidence assets are missing.
- Viewer does not directly download the full `points3d_tracks.jsonl`.

Can run as subagent: yes, after Task 3B-1 and Task 1A+.

### Task 3C: Public Documentation

Goal:

Publish the Photogrammetry Studio concept and operator workflow.

Likely files:

- Create: `docs/photogrammetry-studio-operator-guide.md`
- Modify: `README.md`
- Modify: `openmvs_rework_plan.html`

Checks:

- Operator can understand when to choose Fast, QA, or Premium.
- Documentation says Fast uses Default Reconstruction Engine.
- No wording implies OpenMVS is permanently hardcoded as Fast.

Can run as subagent: yes.

## Suggested First Parallel Dispatch

First dispatch one implementation subagent for Task -1A. After Task -1A is reviewed and merged, continue with Wave 0.

After Wave 0 contract files are created, open five subagents:

1. **Mode Model Agent**
   - Scope: PHP mode fields, upload validation, list display.
   - No script changes.

2. **SfM Evidence Agent**
   - Scope: COLMAP cameras / points3D tracks / coverage summary.
   - No PHP changes.

3. **OpenMVS Geometry Agent**
   - Scope: OpenMVS geometry summary and tests.
   - No PHP changes.

4. **3DGS Appearance Agent**
   - Scope: Gaussian appearance summary and tests.
   - No PHP page changes.

5. **Validation Agent**
   - Scope: validation aggregator and tests using fixture contracts / evidence summaries.
   - No worker or viewer changes.

Coordinator then integrates:

- Resolve any shared helper naming conflict.
- Run the full Python/PHP asset test subset.
- Decide whether Wave 2 orchestration should be inline or subagent-driven.

## Subagent Prompt Template

Use this shape when launching a subagent:

```text
You are working in /var/www/html/demo/php/map/3D/gaussian_splat.

Read docs/todo.md and docs/task.md first.

Your assigned task is: <task name>.

Scope:
- <allowed files or directory>

Do not edit:
- <files owned by other agents>

Required checks:
- <exact pytest or shell commands>

Return:
- Summary of changes
- Files modified
- Commands run and results
- Risks or follow-up work
```

## Coordination Rules

- Freeze schemas before opening subagents.
- If two agents need the same file, split by wave instead of parallelizing.
- Prefer additive helpers over large refactors in the first slice.
- Preserve existing upload, cron, viewer, and direct URL behavior.
- Every engine adapter must have temp-dir unit tests with fake artifacts.
- Every UI/API change must have asset tests or a browser smoke test.
