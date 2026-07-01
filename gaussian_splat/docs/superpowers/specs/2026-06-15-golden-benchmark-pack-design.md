# Golden Benchmark Pack Design

## Purpose

We need to verify whether the current Gaussian Splat direction is technically sound before adding more product features or map integrations.

The existing pipeline can already produce splats, QA reports, timing reports, cleanup metadata, and viewer links. However, those artifacts mostly prove that the workflow runs. They do not yet prove that the visual quality is comparable to a strong demo or customer-ready reference.

This design introduces a Golden Benchmark Pack: a repeatable evidence bundle that compares old results, newly generated results, and optional external reference outputs from the same source video.

The first benchmark target is:

```text
uploads/3
```

This job is useful because it is not a total failure. It has a visible office scene and recognizable subjects, but also obvious glass-shard artifacts and an imperfect registration ratio. It is exactly the kind of case that can reveal whether the current route is improving the right problem.

## Goals

- Compare the old `uploads/3` output against a new run from the same `uploads/3/input/input.mp4`.
- Separate capture problems from pipeline problems.
- Separate official Nerfstudio quality from custom viewer quality.
- Keep human visual judgment alongside machine metrics.
- Produce a `benchmark.md` that can be reviewed without re-reading raw logs.
- Create a repeatable structure for future benchmark jobs.

## Non-Goals

- Do not tune the pipeline in this design.
- Do not implement Cesium, Easymap, MapLibre, or placement features.
- Do not introduce Real-ESRGAN into the first benchmark pass.
- Do not treat `registered_ratio` as a complete quality score.
- Do not replace human review with automated visual scoring in the first version.

## Benchmark Location

For `uploads/3`, the benchmark bundle should be created at:

```text
uploads/benchmark-uploads-3/
```

Recommended structure:

```text
uploads/benchmark-uploads-3/
  benchmark.json
  benchmark.md
  scorecard.md
  capture_diagnosis.md
  source/
    input.mp4
  old/
    qa_report.json
    transform.json
    viewer_links.md
  new-selected-30k/
    evidence.json
    evidence.md
    qa_report.json
    frame_quality_report.json
    timing_report.json
    official-viewer/
      screenshots/
      notes.md
    custom-viewer/
      screenshots/
      notes.md
    exports/
      splat.ply
      splat.clean.ply
      splat.clean.viewer.json
  references/
    external-demo/
      notes.md
      screenshots/
  screenshots/
    old/
    new-raw/
    new-clean/
    official-viewer/
```

Files may be copied or referenced. Large artifacts such as `.ply` and `.mp4` should be copied only when the benchmark needs to be portable. Otherwise, `benchmark.json` can store source paths.

The default artifact policy is non-portable:

```json
{
  "portableMode": false
}
```

This prevents benchmark folders from growing uncontrollably. In non-portable mode, large files may be referenced by path instead of copied into the benchmark bundle.

## Source Case: uploads/3

Known current metrics:

| Metric | Value |
| --- | ---: |
| Frame count | 32 |
| Registered frames | 25 |
| Registered ratio | 0.78 |
| Warning | registered_ratio lower than 0.8 |
| Current splat size | about 29MB |

Known artifacts:

- `uploads/3/input/input.mp4`
- `uploads/3/qa_report.json`
- `uploads/3/transform.json`
- `uploads/3/processed/transforms.json`
- `uploads/3/exports/splat.ply`
- `uploads/3/exports/splat.viewer.json`
- `uploads/3/exports/splat.core-20260605-1100.ply`
- `uploads/3/exports/splat.core-20260605-1100.viewer.json`

## Variants

The first benchmark should include these variants:

| Variant | Source | Purpose |
| --- | --- | --- |
| `old_uploads_3_raw` | `uploads/3/exports/splat.ply` | Current online result that motivated the concern |
| `old_uploads_3_core` | `uploads/3/exports/splat.core-20260605-1100.ply` | Previously cleaned/core result, if still viewable |
| `new_selected_30k_raw` | new pipeline output | Tests whether current selector + 30k training improves the old job |
| `new_selected_30k_clean` | new cleanup output | Tests whether current cleanup reduces glass-shard artifacts |
| `official_viewer_new` | Nerfstudio config from new run | Distinguishes reconstruction quality from custom viewer quality |
| `external_reference` | optional third-party/demo output | Checks whether our route is behind a stronger reference implementation |

The minimum useful benchmark is old raw vs new raw vs new clean. The stronger benchmark adds official viewer and external reference.

Official viewer and custom viewer evidence must stay separated:

```text
new-selected-30k/
  official-viewer/
    screenshots/
    notes.md
  custom-viewer/
    screenshots/
    notes.md
```

This prevents a common ambiguity: whether the Gaussian reconstruction is poor, or whether the custom renderer, PLY parsing, alpha handling, splat scale, sorting, camera defaults, or viewer metadata are creating the perceived quality problem.

## Artifact Mapping

`benchmark.json` should include a stable artifact map so later reports can be generated without hard-coded paths.

Suggested shape:

```json
{
  "benchmarkId": "benchmark-uploads-3",
  "sourceJob": "uploads/3",
  "artifactPolicy": {
    "portableMode": false
  },
  "cases": {
    "old": {
      "jobDir": "uploads/3",
      "rawSplat": "uploads/3/exports/splat.ply",
      "coreSplat": "uploads/3/exports/splat.core-20260605-1100.ply",
      "qaReport": "uploads/3/qa_report.json",
      "transform": "uploads/3/transform.json"
    },
    "newSelected30k": {
      "jobDir": "uploads/benchmark-uploads-3/new-selected-30k",
      "rawSplat": "uploads/benchmark-uploads-3/new-selected-30k/exports/splat.ply",
      "cleanSplat": "uploads/benchmark-uploads-3/new-selected-30k/exports/splat.clean.ply",
      "cleanViewerMeta": "uploads/benchmark-uploads-3/new-selected-30k/exports/splat.clean.viewer.json",
      "qaReport": "uploads/benchmark-uploads-3/new-selected-30k/qa_report.json",
      "frameReport": "uploads/benchmark-uploads-3/new-selected-30k/frame_quality_report.json",
      "timingReport": "uploads/benchmark-uploads-3/new-selected-30k/timing_report.json",
      "officialViewer": "uploads/benchmark-uploads-3/new-selected-30k/official-viewer",
      "customViewer": "uploads/benchmark-uploads-3/new-selected-30k/custom-viewer"
    },
    "reference": {
      "externalDemo": "uploads/benchmark-uploads-3/references/external-demo"
    }
  }
}
```

The exact paths may change during implementation, but the top-level concepts should stay stable: `benchmarkId`, `sourceJob`, `artifactPolicy`, and `cases`.

## New Run Command

The first new run should use the current recommended route:

```bash
GS_FRAME_CANDIDATE_FPS=12 GS_FRAME_TARGET_FPS=3 GS_FRAME_MAX_FRAMES=180 GS_TRAIN_MAX_ITERATIONS=30000 \
  bash scripts/run_mvp_pipeline.sh uploads/3/input/input.mp4 uploads/benchmark-uploads-3/new-selected-30k
```

Expected outputs:

- `uploads/benchmark-uploads-3/new-selected-30k/qa_report.json`
- `uploads/benchmark-uploads-3/new-selected-30k/frame_quality_report.json`
- `uploads/benchmark-uploads-3/new-selected-30k/timing_report.json`
- `uploads/benchmark-uploads-3/new-selected-30k/exports/splat.ply`
- `uploads/benchmark-uploads-3/new-selected-30k/exports/splat.clean.ply`
- `uploads/benchmark-uploads-3/new-selected-30k/exports/splat.clean.viewer.json`

## Viewer URLs

All viewer URLs should include explicit view parameters so reviewers compare similar starting conditions.

Current old raw:

```text
https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_splat.html?src=uploads%2F3%2Fexports%2Fsplat.ply&rx=0&ry=0&rz=0&up=view
```

Current old core:

```text
https://3wa.tw/demo/php/map/3D/gaussian_splat/viewer_splat.html?src=uploads%2F3%2Fexports%2Fsplat.core-20260605-1100.ply&meta=uploads%2F3%2Fexports%2Fsplat.core-20260605-1100.viewer.json&rx=0&ry=0&rz=0&up=view
```

New raw and new clean URLs should be generated after the new run.

## Scorecard

Human review remains required. The scorecard must be fixed, not free-form, so benchmarks can be compared across cases.

| Field | Scale | Meaning |
| --- | --- | --- |
| Geometry | 1-5 | Does the reconstructed space hold together as 3D structure? |
| Recognizability | 1-5 | Can a viewer understand the main subject/scene? |
| Floaters | 1-5 | Higher means fewer floating shards, spikes, and disconnected splats. |
| Registration | 1-5 | Do camera poses and view transitions feel stable? |
| Viewer Quality | 1-5 | Does this viewer appear to render the same model faithfully? |
| Overall | 1-5 | Overall delivery quality for this variant. |

The benchmark should also collect reviewer notes:

```text
Recommended Variant:
Reason:
Known Issues:
Next Action:
```

## Machine Metrics

The benchmark should read and display:

- frame count
- selected frame count
- registered frame count
- registered ratio
- splat count
- clean kept count
- clean kept ratio
- total duration
- stage durations
- QA grade
- warnings

These metrics are diagnostic, not final quality truth.

## Capture Diagnosis

Each benchmark must include `capture_diagnosis.md`.

This file records input-video conditions that can explain why one case succeeds and another fails under the same pipeline.

Suggested checklist:

```markdown
# Capture Diagnosis

## Scene Conditions

- Reflective surfaces:
- Moving people / moving objects:
- Low-texture walls or floors:
- Repeated patterns:
- Thin structures:
- Transparent or glossy objects:
- Background clutter:

## Camera Conditions

- Camera path:
- Approximate overlap:
- Motion speed:
- Shake:
- Focus stability:
- Exposure stability:
- Lighting level:
- Rolling shutter risk:

## Diagnosis

Capture Risk: low / medium / high
Primary Capture Issues:
Expected Pipeline Impact:
Retake Recommendation:
```

This diagnosis is required because future cases may show opposite results with the same code: one capture may be excellent while another fails due to reflections, fast-moving people, low texture, unstable exposure, or insufficient overlap.

## Decision Rules

Use these rules when reading the benchmark:

- If old and new are both poor, prioritize capture quality and dataset suitability.
- If old is poor and new is clearly better, the current pipeline direction is validated.
- If new raw is poor but new clean is better, cleanup is a meaningful part of the route.
- If official viewer is good but custom viewer is poor, focus on `viewer_splat.html`, renderer settings, PLY parsing, alpha, scale, sorting, and camera defaults.
- If official viewer is also poor, focus on capture, COLMAP pose quality, Nerfstudio training config, or low-confidence splat generation.
- If registered ratio is high but visual quality is low, add pose/path quality and visual score to the QA model.
- If an external reference is much better on the same input, inspect which stage it likely improves: masking, segmentation, pose estimation, training configuration, cleanup, or rendering.

## Evidence Report

`benchmark.md` should be readable by a non-implementer. It should contain:

- source video path
- benchmark date
- compared variants
- viewer links
- machine metric table
- human scorecard
- screenshots or screenshot placeholders
- conclusion
- next action

Suggested conclusion format:

```markdown
## Conclusion

Recommended Variant:
Reason:
Known Issues:
Next Action:
Route Confidence:
```

`Route Confidence` should be one of:

- `validated`
- `promising`
- `uncertain`
- `pivot_needed`

## External Reference Handling

The external reference is optional in the first implementation because it may require manual operation. If used, it should be recorded as:

```text
uploads/benchmark-uploads-3/references/external-demo/
```

Minimum contents:

- `notes.md`
- screenshots or screen recordings
- input settings, if known
- output settings, if known
- date/time captured

The benchmark must clearly label external reference evidence as manual and non-reproducible unless the process can be automated.

## Open Questions

- Which external high-quality demo should become the actual golden algorithm reference?
- Should screenshots be manual in version one, or should Playwright/browser automation capture fixed views?
- Should the benchmark include a small viewer state file that fixes camera pose across variants?

## Proposed First Pass

For the first pass, use the conservative route:

1. Create `uploads/benchmark-uploads-3/`.
2. Record the old `uploads/3` metrics and viewer links.
3. Re-run the current selected 30k pipeline into `uploads/benchmark-uploads-3/new-selected-30k`.
4. Build `benchmark.json` with artifact mapping and `portableMode: false`.
5. Build `benchmark.md`.
6. Fill `capture_diagnosis.md`.
7. Separately record official-viewer and custom-viewer screenshots/notes.
8. Manually review old raw, old core, new raw, and new clean.
9. Fill out the fixed `scorecard.md`.
10. Decide whether the current route is `validated`, `promising`, `uncertain`, or `pivot_needed`.

## Roadmap Position

This benchmark is Phase G1.5.

Recommended roadmap:

| Phase | Name | Status |
| --- | --- | --- |
| G1 | Baseline Pipeline | Completed |
| G1.5 | Golden Benchmark Pack | Current |
| G1.6 | Viewer Compare: official vs custom | Next |
| G1.7 | Benchmark Automation | Later |
| G2 | Mesh Extraction | Deferred |
| G3 | GLB Export | Deferred |
| G4 | 3D Tiles | Deferred |
| G5 | GIS Integration | Deferred |

Do not start Mesh Extraction, GLB Export, 3D Tiles, MapLibre, Cesium, or GIS Integration until the benchmark evidence shows Gaussian Splat is worth further investment for the target use cases.

## Self-Review

- No implementation details are required before approval.
- The design separates product-flow proof from reconstruction-quality proof.
- The design does not rely only on `registered_ratio`.
- The design keeps Real-ESRGAN and map integration out of the first benchmark pass.
- The first benchmark has a concrete source case: `uploads/3`.
- The design separates official-viewer evidence from custom-viewer evidence.
- The design includes artifact mapping, fixed scorecard fields, capture diagnosis, and non-portable artifact policy.
