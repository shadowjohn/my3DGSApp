# Outdoor Trench Reality Layer Design

## Purpose

We need to move the Gaussian Splat work from small-object demos and office experiments into engineering-site reality capture.

The first target domain is outdoor road excavation and sewer construction: workers may record a trench, a manhole, pipes, culverts, road surfaces, materials, and the surrounding work zone. The output does not need survey-grade mesh geometry in the first version. It must let reviewers visually return to the site with convincing photographic texture, identify the main construction surfaces, and later support overlays with maps, oblique imagery, utility drawings, or project annotations.

This design treats Gaussian Splat as a Reality Layer:

```text
photorealistic site memory + coarse spatial context + QA evidence
```

It is not a replacement for RTK survey, BIM, CAD, or precise pipe as-built geometry.

## Context

Recent benchmarks showed that the current pipeline can reconstruct recognizable subjects, but uncontrolled background regions create glass-shard artifacts, floaters, and low-confidence splats. For engineering scenes, this means the product should not promise that every background pixel becomes a clean 3D model.

The product direction should instead focus on:

- realistic texture on the trench, pavement, pipe, manhole, culvert, and construction surface;
- suppressing low-confidence background that distracts from the work zone;
- preserving enough pose, scale, and geo metadata for future map and projection workflows;
- producing clear QA that says whether a capture is deliverable, needs supplemental photos, or should be retaken.

## Goals

- Support two common field inputs:
  - A: walk-video mode, where a worker slowly walks along the trench with a phone.
  - C: photo-set mode, where the site only has separate still photos.
- Keep the design compatible with a future mobile capture app that records videos/photos, uploads them to the server, and shows processed reality layers in a map viewer.
- Produce one consistent evidence/output structure regardless of input type.
- Prioritize visual readability of road surface, trench, pipe, manhole, culvert, and immediate work zone.
- Keep geometric expectations honest: coarse surface structure is acceptable if texture is convincing.
- Add engineering-scene QA fields that are more useful than generic splat count alone.
- Prepare metadata boundaries for future Easymap, Cesium, projection, and oblique imagery overlay.

## Non-Goals

- Do not integrate Diffuman4D directly in the first engineering MVP.
- Do not use diffusion-generated views as production input in this phase.
- Do not claim survey-grade accuracy without GCP, RTK, or independent measurement.
- Do not build Cesium, Easymap, 3D Tiles, or GIS overlay in this design.
- Do not require drone input for the first benchmark.
- Do not force all outdoor background to reconstruct cleanly.

## Target Scene

The first golden benchmark should be an outdoor road excavation or sewer construction scene with at least one of:

- open trench;
- exposed pipe or utility conduit;
- manhole or culvert opening;
- road surface cut line;
- construction materials or safety cones;
- worker activity near the work zone.

The first benchmark should prefer a scene where the trench or work zone is the obvious centerline. This lets the cleanup and viewer default focus on a corridor instead of a small object.

## Input Modes

### A. Walk-Video Mode

Walk-video mode is the preferred MVP route.

Expected capture:

- one `input.mp4`;
- worker walks slowly along one side of the trench, then optionally returns along the other side;
- camera points diagonally down into the work zone, not only straight ahead;
- each area appears in multiple frames with strong overlap;
- avoid fast pans, sudden turns, and autofocus hunting.

Processing route:

```text
input.mp4
↓
dense candidate extraction
↓
frame quality selection
↓
COLMAP pose estimation
↓
splatfacto training
↓
trench-focused cleanup
↓
engineering QA + viewer metadata
```

This mode should be the first target for a complete benchmark because video provides temporal continuity and gives COLMAP more chances to register a stable path.

### C. Photo-Set Mode

Photo-set mode is common in field practice and must be supported, but the first version should be stricter about diagnostics.

Expected capture:

- `images/*.jpg`;
- photos should overlap by at least 70%;
- photos should include both oblique views and a few wider context shots;
- EXIF timestamp and GPS should be preserved when available;
- repeated viewpoints without coverage should be warned about.

Processing route:

```text
images/*.jpg
↓
photo quality + EXIF + overlap diagnostics
↓
COLMAP pose estimation
↓
splatfacto training when coverage is sufficient
↓
trench-focused cleanup
↓
engineering QA + viewer metadata
```

For MVP, photo-set mode may stop early with a "needs more coverage" report instead of forcing a poor reconstruction.

## Output Structure

Each job should produce a consistent outdoor reality layer folder:

```text
uploads/<job>/
  input/
    input.mp4 or images/
  processed/
  outputs/
  exports/
    splat.ply
    splat.clean.ply
    splat.trench.ply
    splat.trench.viewer.json
  frame_report.json
  trench_qa_report.json
  georef.json
  capture_diagnosis.md
  evidence.md
```

Existing files such as `qa_report.json`, `timing_report.json`, and `frame_quality_report.json` should remain compatible. `trench_qa_report.json` can either extend `qa_report.json` or be produced as a separate engineering-domain report.

## End-to-End Product Shape

The long-term product should be an end-to-end capture and map-review workflow:

```text
mobile app
↓
record video or take photos
↓
upload to server
↓
server-side Gaussian Splat / photogrammetry processing
↓
QA + georef + reality-layer exports
↓
map platform review and overlay
```

Mobile app responsibilities:

- capture walk-video and photo-set jobs;
- preserve EXIF, timestamps, GPS, compass heading, and device orientation when available;
- guide the field user with short capture prompts;
- upload original media without destructive compression;
- show upload and processing status.

Server responsibilities:

- normalize video/photo inputs into a common frame set;
- run reconstruction, cleanup, QA, and evidence generation;
- produce web-viewer links and map-layer metadata;
- keep raw, clean, and trench-focused variants available for comparison.

Map platform responsibilities:

- open the trench-focused reality layer from the job record;
- overlay approximate location, project drawings, utility lines, and annotations;
- support before/during/after comparison;
- support later Cesium/Easymap integration without changing the capture contract.

The first MVP does not need to build the mobile app, but the server-side job schema should not assume that uploads only come from a desktop browser.

## Trench-Focused Cleanup

The existing cleanup is too generic for engineering scenes. Outdoor trench cleanup should keep the work corridor and suppress distracting low-confidence surroundings.

The first implementation should produce:

```text
exports/splat.trench.ply
exports/splat.trench.viewer.json
```

Conceptual filters:

- opacity and scale filters to remove obvious unstable splats;
- spatial filtering around the main registered camera path and reconstruction density;
- low-confidence background transparency or removal;
- optional sky/high-background suppression when the camera path and splat distribution indicate an outdoor scene;
- preservation bias for ground-like and trench-corridor regions.

This is not semantic segmentation yet. It is a corridor-focused delivery policy. Semantic masks can be added later when the basic route is stable.

## Viewer Mode

The web viewer should support an engineering review mode:

```text
viewer_splat.html?src=...splat.trench.ply&meta=...splat.trench.viewer.json&mode=trench
```

Expected defaults:

- start near the trench or work-corridor centroid;
- use a field-view and camera distance suitable for inspection;
- hide or reduce low-confidence background if metadata requests it;
- expose raw, clean, and trench-focused variants in admin/evidence links;
- keep the current web viewer path as the primary online review route.

Nerfstudio official viewer remains useful for local diagnostics, but it should not be treated as the normal 3wa online review path because host firewall rules may block its local port.

## Georeference Metadata

The first version does not need full GIS integration, but it must reserve metadata fields for it.

`georef.json` should support:

```json
{
  "mode": "none | exif | manual | gcp | rtk",
  "crs": null,
  "origin": {
    "lat": null,
    "lng": null,
    "height": null
  },
  "headingDegrees": null,
  "scaleMetersPerUnit": null,
  "controlPoints": [],
  "confidence": "none | low | medium | high",
  "notes": []
}
```

For early jobs, `mode` may be `none` or `exif`. The important part is that downstream Cesium/Easymap work will have a stable place to read positioning confidence.

## Engineering QA

Generic metrics are not enough. Outdoor trench jobs should include engineering-specific quality fields.

Suggested `trench_qa_report.json` fields:

```json
{
  "input_mode": "walk_video | photo_set",
  "frame_count": 0,
  "selected_count": 0,
  "registered_count": 0,
  "registered_ratio": 0.0,
  "splat_count": 0,
  "trench_splat_count": 0,
  "trench_kept_ratio": 0.0,
  "surface_readability": "unknown | poor | fair | good",
  "texture_realism": "unknown | poor | fair | good",
  "background_artifact_score": 0,
  "georef_confidence": "none | low | medium | high",
  "delivery_grade": "A | B | C | D",
  "decision": "deliverable | review_needed | supplemental_capture_needed | retake",
  "warnings": []
}
```

Decision guidance:

| Decision | Meaning |
| --- | --- |
| `deliverable` | Main work zone is readable and artifacts do not distract from review. |
| `review_needed` | Main work zone is partially usable but requires human inspection. |
| `supplemental_capture_needed` | Core route worked, but missing views or weak overlap require additional photos/video. |
| `retake` | Registration, texture, or artifacts are too poor for engineering review. |

## Evidence Pack

The first outdoor benchmark should produce an evidence bundle similar to the Golden Benchmark Pack:

```text
uploads/<benchmark>/
  benchmark.json
  benchmark.md
  capture_diagnosis.md
  scorecard.md
  screenshots/
    raw/
    clean/
    trench/
    top-down/
```

The scorecard should use engineering-scene categories:

| Field | Scale | Meaning |
| --- | --- | --- |
| Work Zone Recognizability | 1-5 | Can reviewers understand the road/trench/pipe/manhole context? |
| Surface Texture | 1-5 | Does pavement/trench/pipe texture look realistic enough for visual review? |
| Background Artifacts | 1-5 | Higher means fewer distracting floaters and glass shards outside the work zone. |
| Camera Stability | 1-5 | Does movement through the scene feel stable enough? |
| Geo/Scale Confidence | 1-5 | Are position and scale good enough for the stated use? |
| Overall Delivery | 1-5 | Can this be shown to a customer for the intended review purpose? |

## Capture Guidance

The field guidance should be short and operational:

- walk slowly;
- keep trench/work zone large in frame;
- record both sides when safe;
- keep at least 70% overlap;
- include a few wide context shots;
- avoid pointing mostly at sky or far background;
- avoid rapid pans and sudden turns;
- keep focus/exposure stable;
- include a known scale marker when possible;
- preserve original image/video files and EXIF metadata.

For photo-set mode:

- take sequential photos along the trench;
- include oblique left/right views;
- avoid only taking isolated close-ups;
- include start/end context photos;
- avoid deleting "boring" overlap photos because COLMAP needs them.

## Diffuman4D Positioning

Diffuman4D is useful as a research signal, not as an immediate dependency.

Its lesson is that sparse or incomplete observations can create noisy 3D Gaussian results, and that view-completion can improve reconstruction when the domain model is strong. However, Diffuman4D is focused on dynamic humans, not construction trenches or GIS reality layers.

For this project:

- do not run diffusion-generated frames through production pose estimation in this phase;
- do not use generated detail as engineering evidence;
- use the idea to justify future research on missing-view detection and supplemental capture recommendations;
- consider diffusion-assisted view completion only after capture QA, trench cleanup, and georef metadata are stable.

## Future GIS And Projection Path

After the outdoor trench MVP is stable, the likely integration sequence is:

1. top-down review screenshot from the trench-focused splat;
2. manual scale/origin placement;
3. overlay with map, utility drawing, or oblique imagery;
4. `georef.json` upgraded from `manual` to `gcp` or `rtk`;
5. Cesium/Easymap reality layer integration;
6. time-series comparison for before/during/after construction.

This design intentionally stops before those integrations so the first benchmark can prove that the reality layer is worth carrying downstream.

## Oblique Imagery And GLB Hybrid Option

Some engineering scenes may not need a fully dense 3D reconstruction to look convincing in the map platform. A hybrid layer can combine:

- oblique imagery or projected photos for realistic appearance;
- a coarse surface, trench corridor, or local mesh for spatial placement;
- small GLB anchor objects for obvious local features such as manholes, pipes, culvert mouths, barriers, or equipment;
- Gaussian Splat reality layers where free-viewpoint review is valuable.

This hybrid approach is acceptable when the goal is visual evidence and spatial context rather than survey-grade geometry. It can also reduce pressure on Gaussian Splat to reconstruct every low-confidence background region.

The QA report should record which delivery mode was used:

```json
{
  "delivery_mode": "gaussian_splat | oblique_projection | glb_hybrid | mixed"
}
```

For the first outdoor trench MVP, Gaussian Splat remains the main route. Oblique projection and GLB hybrid are reserved as downstream alternatives when they produce a clearer map-review experience.

## Success Criteria

The first benchmark is successful if:

- walk-video mode produces a viewable `splat.trench.ply`;
- road surface, trench, pipe/manhole/culvert, and immediate construction context are recognizable;
- background artifacts are less distracting than the raw splat;
- `trench_qa_report.json` clearly says deliverable, review needed, supplemental capture needed, or retake;
- `georef.json` exists even when confidence is `none` or `low`;
- evidence links can be opened through the 3wa web viewer.

## Open Implementation Questions

- Should `trench_qa_report.json` be a separate file or an extension of `qa_report.json`?
- Should trench corridor detection start as automatic-only, or allow an admin-drawn ROI polygon?
- Should photo-set mode initially block training when overlap is weak, or allow an explicit "force reconstruction" option?
- Which first real-world benchmark footage should become the outdoor golden case?
- What metadata must the future mobile app send on day one: GPS only, or GPS + compass + device orientation?
- Which map-review delivery should be treated as primary after the first benchmark: Gaussian Splat layer, oblique projection, or GLB hybrid?
