# Viewer Evidence Stabilization

Task 9F freezes the current Evidence MVP as a lightweight viewer aid, not a full sparse reconstruction browser.

## Artifacts

- `evidence_manifest.json`: viewer/API entrypoint. It points to cameras, camera path, spatial index, and LOD sparse points.
- `cameras.json`: camera positions used by the Camera layer and camera path.
- `spatial_index.json`: grid/tile evidence for picked mesh positions.
- `lod_sparse_points.json`: small sparse point sample for the Sparse Points toggle.

The viewer must not fetch full `points3d_tracks.jsonl`. Full tracks stay backend/offline input for index building only.

## Smoke Links

- Compare viewer with Studio job: `viewer_compare_splat_mesh.html?studio_job_id=123`
- Compare viewer with a manifest: `viewer_compare_splat_mesh.html?manifest=docs/fixtures/premium_delivery_manifest.json`
- Compare viewer with evidence only: `viewer_compare_splat_mesh.html?evidence=docs/fixtures/evidence_manifest_colmap_openmvs_gaussian.json`

Fixture manifests can validate manifest parsing and error surfaces without burning reconstruction compute.

## Expected Error Surfaces

- Missing `evidence_manifest_path`: show `Camera evidence not available`.
- Missing cameras: keep spatial index / LOD paths when present, show camera evidence unavailable.
- Missing `spatial_index_path`: show `spatial index not available`.
- Missing `lod_sparse_points_path`: show `Sparse points not available`.
- Backend `evidence_query` failure: fallback to frontend spatial index when available.
- Malformed evidence JSON: show unavailable state, no blank viewer.
- Sparse LOD over cap: render at most `SPARSE_POINT_RENDER_CAP` points and show `capped`.

## Deliberate Non-goals

- No splat precise picking.
- No backend streaming.
- No full sparse point cloud rendering.
- No frontend loading of full point tracks.
