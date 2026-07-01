# Blender Photogrammetry QA Pack Design

## Purpose

We need a reliable way to inspect and explain why a Gaussian Splat job looks good in the main subject area but fails around the background with glass-shard artifacts, floaters, stretched splats, or transparent geometry.

The current pipeline can run FFmpeg frame extraction, frame selection, COLMAP or hierarchical SfM, Nerfstudio/Graphdeco-style training, cleanup, QA reports, and web viewer publication. What it still lacks is a clear intermediate review layer between SfM and final splat delivery.

This design adds a Blender Photogrammetry QA Pack:

```text
SfM camera tracking + point cloud + image context + ROI diagnosis
```

The pack is not meant to replace Gaussian Splatting. It is a diagnostic and bridge layer that lets us inspect camera paths, sparse points, image planes, ground planes, regions of interest, low-confidence areas, and future mesh/GLB delivery candidates in Blender.

## Context

Recent benchmark work showed that changing SfM mapper strategy from incremental to hierarchical did not materially solve the visual artifact problem. Both routes can register enough frames and train a recognizable result, but low-confidence peripheral regions still create distracting fragments.

The current visible pattern is:

- the main subject can be acceptable;
- the outer background often looks broken;
- strict cleanup can reduce data size but may make the main subject transparent;
- web viewer tuning helps presentation but does not explain the reconstruction;
- direct mesh extraction from cleaned splats is not yet visually acceptable.

This means the next useful layer is not another blind training run. We need a way to see what the camera solver and point cloud believe happened before the splats are rendered.

The Polyfjord-style workflow and the Blender Photogrammetry Importer suggest a practical route:

```text
video
-> frames
-> COLMAP feature extraction / matching / mapping
-> Blender import
-> animated camera + point cloud + background frames
-> visual QA / cleanup planning / compositing bridge
```

## Goals

- Create a repeatable Blender QA Pack for a completed job.
- Use the existing frame and SfM outputs instead of introducing a separate reconstruction pipeline at first.
- Keep the 3wa server responsible for generating portable inspection assets, not for running Blender.
- Keep Blender inspection on a Windows workstation or GUI engineering machine in the first phase.
- Import camera poses, sparse point cloud, selected frames, and job metadata into Blender for inspection.
- Provide proxy assets so Blender remains usable on large jobs.
- Identify whether visual artifacts are likely caused by capture coverage, SfM alignment, training, cleanup, or viewer behavior.
- Support indoor object/desk scans and outdoor construction scans with the same basic QA structure.
- Prepare a future route for GLB, image projection, shadow-catcher planes, and Cesium/Easymap metadata without building those integrations in this phase.
- Preserve the 3wa website as the normal result review surface while using Blender as an engineering inspection surface.

## Non-Goals

- Do not replace the existing Gaussian Splat pipeline in this phase.
- Do not make Blender the production web viewer.
- Do not implement Cesium, Easymap, Unreal, or Three.js runtime delivery in this design.
- Do not promise survey-grade accuracy from Blender inspection alone.
- Do not require manual tracking markers.
- Do not require a Windows `.bat` workflow on the server.
- Do not run Blender headless as a server dependency in the first implementation.
- Do not solve full mesh extraction or texture baking in the first implementation.
- Do not use Real-ESRGAN, diffusion view synthesis, or frame blending as part of this QA pack.

## First Target

The first QA pack should target the current benchmark case:

```text
uploads/3
```

Preferred first source variant:

```text
uploads/3/benchmark-uploads-3/selected-30k-hierarchical
```

Fallback source variant:

```text
uploads/3/benchmark-uploads-3/selected-30k-incremental
```

This job is useful because it has a recognizable main subject and severe peripheral artifacts. It can prove whether Blender inspection helps explain the exact problem we are seeing.

## Pipeline Position

The Blender QA Pack sits after frame selection and SfM, and before final delivery decisions:

```text
input video or photos
-> frame extraction / frame selector
-> SfM pose estimation
-> Blender Photogrammetry QA Pack
-> splat training / cleanup review
-> delivery decision
```

For already trained jobs, the QA pack can be generated retroactively from existing processed outputs:

```text
existing processed frames + COLMAP model + reports
-> blender-pack
```

## Server And Workstation Boundary

The first implementation must draw a hard boundary:

```text
3wa server
-> generate blender-pack assets
-> publish manifest, PLY, proxy frames, camera path, report, README

GUI engineering workstation
-> open Blender
-> import COLMAP / PLY / images
-> inspect camera path, ROI, artifacts, ground plane, and delivery candidates
-> write human review notes
```

This avoids making Blender, OpenGL, Vulkan, add-on loading, and display-driver behavior part of the production server pipeline.

The phased position is:

```text
Phase 1: server generates QA Pack only
Phase 2: engineer manually performs Blender inspection
Phase 3: optional headless Blender automation after the manual workflow is proven stable
```

The first script should therefore be a pack generator, not a Blender runner.

## Output Structure

Each job variant should be able to produce this server-generated Phase 1 pack:

```text
<job-or-variant>/
  blender-pack/
    README.md
    blender_qa_manifest.json
    blender_qa_report.json
    blender_qa_notes.md
    import/
      colmap/
      images/
      sparse_points.ply
      camera_path.json
      image_manifest.json
    proxies/
      frames_50/
      frames_25/
      sparse_points_preview.ply
```

Manual workstation review may later add optional files such as `.blend` scenes and screenshots, but the server must not require those files for the first acceptance pass.

## Manifest

`blender_qa_manifest.json` should map existing job artifacts to Blender-friendly inputs:

```json
{
  "jobId": "uploads/3/benchmark-uploads-3/selected-30k-hierarchical",
  "sourceVideo": "uploads/3/input/input.mp4",
  "imagesDir": "processed/images",
  "colmapSparseModel": "processed/colmap/sparse/0",
  "database": "processed/colmap/database.db",
  "splatRaw": "exports/splat.ply",
  "splatClean": "exports/splat.clean.ply",
  "qaReport": "qa_report.json",
  "frameReport": "frame_report.json",
  "sfmReport": "processed/sfm_report.json",
  "proxyPolicy": {
    "frameScales": [50, 25],
    "maxPreviewPoints": 250000
  },
  "blender": {
    "targetVersion": "4.x",
    "displayBackend": "OpenGL",
    "importer": "SBCV/Blender-Addon-Photogrammetry-Importer"
  }
}
```

Paths may be stored relative to the job variant folder when possible. Website URLs should continue to be generated separately by the existing viewer/report tooling.

## Blender Import Strategy

The first route should prefer the existing Blender Photogrammetry Importer because it already supports COLMAP-style outputs and can visualize cameras, image planes, and point clouds.

Expected manual import flow:

1. Install the Blender Photogrammetry Importer add-on.
2. Set Blender display backend to OpenGL when point cloud display is unstable under Vulkan.
3. Import the COLMAP model or workspace from `blender-pack/import/colmap`.
4. Import or link selected images as camera background frames.
5. Load the sparse or preview point cloud.
6. Create an animated camera from the imported frame cameras.
7. Use proxy frames at 50% or 25% when playback is slow.

Expected automated support:

- generate folders and manifests;
- convert COLMAP binary models to text or PLY when needed;
- create preview point clouds;
- generate a Blender Python bootstrap script for repeatable import;
- build 50% and 25% proxy frames when useful.

The first version must not run Blender headless. A pack that opens cleanly in Blender by following `README.md` is acceptable for the first benchmark.

## QA Report

`blender_qa_report.json` should summarize what Blender inspection is expected to reveal:

```json
{
  "cameraPath": {
    "registeredFrames": 41,
    "selectedFrames": 48,
    "registeredRatio": 0.85,
    "pathContinuity": "good",
    "suspectedJumps": []
  },
  "coverage": {
    "subjectCoverage": "medium",
    "peripheryCoverage": "low",
    "singleSidedRisk": "medium",
    "lowTextureRisk": "medium"
  },
  "artifactDiagnosis": {
    "mainSubject": "usable",
    "periphery": "poor",
    "likelyCauses": [
      "low peripheral overlap",
      "background not intended as ROI",
      "large unstable splats after training"
    ]
  },
  "recommendedAction": "keep subject ROI, fade or remove low-confidence periphery before delivery"
}
```

The report should combine existing machine metrics with explicit human-review fields filled during Blender inspection. It should avoid claiming certainty where the system only has a visual diagnosis.

## Capture Rules Added To QA

The Blender workflow highlights one important capture rule that should become part of our field checklist:

```text
disable video stabilization when possible
```

Capture guidance should include:

- turn off digital or optical stabilization when the capture app allows it;
- lock exposure;
- lock focus;
- enable lens correction when the capture app supports it;
- move slowly;
- do not rotate in place as the main capture motion;
- keep at least 70% overlap;
- keep the subject large in frame;
- avoid heavy autofocus hunting;
- for trenches or roadwork, capture along the corridor and add cross-angle supplemental shots.

These rules belong in future mobile web capture guidance and in any `capture_diagnosis.md` generated for failed jobs.

## Indoor Scene Use

For indoor desk or object scans, the Blender QA Pack should help answer:

- Did the camera actually move around the subject, or mostly pan in place?
- Is the main subject covered from enough angles?
- Are background fragments outside the intended ROI?
- Does the sparse point cloud agree with the visually recognizable subject?
- Is the cleanup too strict and making the subject transparent?

The likely first delivery policy for indoor scenes is:

```text
preserve trusted subject ROI + remove/fade low-confidence periphery
```

## Outdoor Construction Use

For road excavation, sewer construction, culverts, pipes, and trench scenes, the Blender QA Pack should help answer:

- Is the camera path aligned with the trench or work corridor?
- Are both sides of the trench captured, or only one side?
- Is there enough downward oblique coverage for the ground and pipe surfaces?
- Can a ground plane or trench axis be estimated visually?
- Which areas are only texture context and should not be treated as reliable geometry?
- Which areas are good candidates for future GLB or texture projection output?

The likely first delivery policy for construction scenes is:

```text
photorealistic reality layer for the work zone + coarse spatial frame + honest QA
```

## Relationship To Existing Web Viewer

The existing 3wa web viewer remains the customer-visible review path. Blender is for engineering inspection and asset preparation.

The QA pack should link back to web viewer URLs for:

- raw splat;
- clean splat;
- ROI or trench-focused splat when available;
- official render screenshots when available.

Blender screenshots can be used inside benchmark reports to explain why a viewer result looks broken, but they should not replace the online viewer link.

## Future Extensions

After the QA pack proves useful, the following extensions become reasonable:

1. Blender cleanup guide:
   - select and hide bad point regions;
   - define ROI boxes;
   - save clipping metadata for splat filtering.

2. GLB bridge:
   - generate a simple proxy mesh;
   - project selected images or bake textures;
   - export a client-friendly GLB for local feature objects.

3. Ground plane and shadow catcher:
   - fit or manually place a plane;
   - support VFX-style overlays and visual context.

4. Cesium/Easymap metadata:
   - add origin, heading, scale, and ROI bounding boxes;
   - keep splat/GLB placement reproducible in a map scene.

5. Mobile capture feedback:
   - show warnings for stabilization, blur, focus hunting, coverage gaps, and single-sided paths.

These are intentionally future work. The first implementation should focus on generating a useful Blender inspection bundle.

## Acceptance Criteria

- A design-compatible `blender-pack` can be generated for the selected `uploads/3` benchmark variant.
- The pack includes a manifest that points to frames, COLMAP model, sparse point data, and existing QA reports.
- The pack includes a human-readable README explaining how to open it in Blender with the Photogrammetry Importer.
- The pack includes or can generate a preview point cloud suitable for Blender inspection.
- The pack documents whether the current artifact problem appears to be capture coverage, SfM, training, cleanup, or viewer-related.
- No existing customer-facing pipeline behavior changes merely by generating the pack.

## Implementation Notes

The first implementation should be small:

- add a script that builds the folder structure and manifest;
- name the first server-side script `generate_blender_pack.py`;
- reuse existing processed outputs instead of recomputing SfM;
- convert sparse points to PLY if necessary;
- optionally build 50% and 25% proxy frames;
- write `README.md` and `blender_qa_notes.md`;
- update the benchmark or history notes with the generated pack path.

Only after Phase 1 and manual workstation inspection are useful should we consider optional Blender headless automation or GLB export.

## Decision

Proceed with the Blender Photogrammetry QA Pack as the next diagnostic layer. Treat it as a bridge between reconstruction evidence and future delivery formats, not as a replacement for Gaussian Splatting.
