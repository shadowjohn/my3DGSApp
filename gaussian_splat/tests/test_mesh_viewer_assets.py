from pathlib import Path
import json
import subprocess
import textwrap


ROOT = Path(__file__).resolve().parents[1]


def compare_viewer_script() -> str:
    text = (ROOT / "viewer_compare_splat_mesh.html").read_text()
    return text.split("<script>", 1)[1].split("</script>", 1)[0]


def run_compare_viewer_assertions(tmp_path, assertions: str, search: str = "") -> subprocess.CompletedProcess:
    script = tmp_path / "compare_viewer_test.mjs"
    script.write_text(
        f"globalThis.window = {{ location: {{ search: {json.dumps(search)}, pathname: '/viewer_compare_splat_mesh.html', hash: '' }}, history: {{ replaceState() {{}} }} }};\n"
        "globalThis.document = { body: { dataset: {} }, querySelectorAll: () => [], querySelector: () => ({ textContent: '' }), getElementById: () => ({ textContent: '', src: '', href: '' }) };\n"
        + compare_viewer_script().replace("\n    main();\n", "\n")
        + "\n"
        + textwrap.dedent(assertions)
    )
    return subprocess.run(["node", str(script)], cwd=ROOT, text=True, capture_output=True, check=False)


def assert_node_ok(result: subprocess.CompletedProcess) -> None:
    assert result.returncode == 0, result.stderr + result.stdout


def test_mesh_viewer_loads_glb_and_controls():
    text = (ROOT / "viewer_mesh.html").read_text()
    assert "GLTFLoader" in text
    assert "OrbitControls" in text
    assert "wireframe" in text
    assert "線框" in text
    assert "opacity" in text
    assert "透明度" in text
    assert "triangle" in text
    assert "三角面" in text
    assert "file size" in text.lower()
    assert "檔案大小" in text
    assert "來源" in text
    assert "頂點" in text
    assert "URLSearchParams" in text
    assert 'const requestedSrc = params.get("src")' in text
    assert 'const requestedStudioJobId = params.get("studio_job_id")' in text
    assert "manifestPathFromEntrypoint" in text
    assert "../studio/api.php?mode=job_detail&id=" in text
    assert "Delivery manifest not found" in text
    assert "delivery_tracks missing" in text
    assert "mesh track missing" in text
    assert "primary_artifact missing" in text
    assert "Artifact not found" in text
    assert "legacy fallback" in text
    assert 'params.get("manifest")' in text
    assert "artifactPathFromManifest" in text
    assert "uploads/7/compare/mesh/cleaned_mesh.glb" in text
    assert "new THREE.Raycaster" in text
    assert "pickMeshPosition" in text
    assert "mesh-viewer-pick" in text
    assert "postMessage" in text
    assert 'addEventListener("pointerdown"' in text


def test_compare_viewer_embeds_splat_and_mesh_viewers():
    text = (ROOT / "viewer_compare_splat_mesh.html").read_text()
    assert "viewer_splat.php" in text
    assert "viewer_mesh.html" in text
    assert "splat.clean.ply" in text
    assert "cleaned_mesh.glb" in text
    assert "Gaussian Splat" in text
    assert "Mesh GLB" in text
    assert 'id="view-toggle"' in text
    assert "並排" in text
    assert 'data-view-mode="both"' in text
    assert 'data-view-mode="splat"' in text
    assert 'data-view-mode="mesh"' in text
    assert 'data-pane="splat"' in text
    assert 'data-pane="mesh"' in text
    assert 'params.get("view")' in text
    assert "function applyViewMode" in text
    assert 'body[data-view="splat"] [data-pane="mesh"]' in text
    assert "delivery_manifest.json" in text
    assert "loadManifest" in text
    assert 'params.get("studio_job_id")' in text
    assert "../studio/api.php?mode=job_detail&id=" in text
    assert "Delivery manifest not found" in text
    assert "legacy fallback" in text
    assert "delivery_tracks" in text
    assert 'manifestArtifactResult(manifest, "splat", manifestPath)' in text
    assert 'manifestArtifactResult(manifest, "mesh", manifestPath)' in text
    assert 'id="manifest-summary"' in text
    assert "交付清單" in text
    assert 'id="track-summary"' in text
    assert "軌道" in text
    assert "manifestSummaryText" in text
    assert "manifestTrackSummaries" in text
    assert "artifactHeadStatus" in text
    assert "schema_version=" in text
    assert "generated_at=" in text
    assert "delivery_capable=true" in text
    assert "delivery_capable=false" in text
    assert "Artifact not found" in text
    assert 'id="evidence-pick-summary"' in text
    assert "證據" in text
    assert "相機圖層" in text
    assert "稀疏點" in text
    assert "選取" in text
    assert "Evidence pick currently uses mesh/raycast position" in text
    assert "function loadSpatialIndex" in text
    assert "function gridTileIdForPosition" in text
    assert "function evidenceTileForPosition" in text
    assert "function evidencePickSummary" in text
    assert "function evidenceQueryUrl" in text
    assert "function queryEvidenceTile" in text
    assert "function handleEvidencePick" in text
    assert "mesh-viewer-pick" in text
    assert "coverage_score" in text
    assert "visible_camera_ids" in text
    assert "sample_sparse_points" in text
    assert "no evidence for picked area" in text


def test_compare_viewer_inline_script_syntax(tmp_path):
    script = tmp_path / "viewer_compare_inline.mjs"
    script.write_text(compare_viewer_script())

    assert_node_ok(subprocess.run(["node", "--check", str(script)], cwd=ROOT, text=True, capture_output=True, check=False))


def test_compare_viewer_summarizes_premium_and_qa_tracks(tmp_path):
    result = run_compare_viewer_assertions(
        tmp_path,
        """
        import assert from "node:assert/strict";

        const premium = {
          schema_version: "1.0",
          studio_job_id: 12,
          mode: "premium",
          generated_at: "2026-06-28T00:00:00+08:00",
          delivery_tracks: [
            { track: "mesh", engine: "openmvs", role: "delivery_capable", delivery_capable: true, primary_artifact: { type: "glb", path: "exports/model.glb" } },
            { track: "splat", engine: "gaussian_splat", role: "delivery_capable", delivery_capable: true, primary_artifact: { type: "splat", path: "exports/splat.clean.ply" } },
          ],
        };
        const qa = {
          schema_version: "1.0",
          studio_job_id: 13,
          mode: "qa",
          generated_at: "2026-06-28T00:05:00+08:00",
          delivery_tracks: [
            { track: "mesh", engine: "openmvs", role: "delivery_candidate", delivery_capable: true, primary_artifact: { type: "glb", path: "exports/model.glb" } },
            { track: "splat", engine: "gaussian_splat", role: "diagnostic", delivery_capable: false, primary_artifact: { type: "splat", path: "exports/splat.clean.ply" } },
          ],
        };

        assert.equal(manifestSummaryText(premium), "schema_version=1.0 mode=premium studio_job_id=12 generated_at=2026-06-28T00:00:00+08:00");
        assert.deepEqual(
          manifestTrackSummaries(premium, "fixtures/premium/delivery_manifest.json", {
            "fixtures/premium/exports/model.glb": "ok",
            "fixtures/premium/exports/splat.clean.ply": "ok",
          }),
          [
            "mesh/openmvs role=delivery_capable delivery_capable=true artifact=fixtures/premium/exports/model.glb status=ok",
            "splat/gaussian_splat role=delivery_capable delivery_capable=true artifact=fixtures/premium/exports/splat.clean.ply status=ok",
          ],
        );
        assert.equal(
          manifestTrackSummaries(qa, "fixtures/qa/delivery_manifest.json", {
            "fixtures/qa/exports/splat.clean.ply": "ok",
          })[1],
          "splat/gaussian_splat role=diagnostic delivery_capable=false artifact=fixtures/qa/exports/splat.clean.ply status=ok",
        );
        """,
    )

    assert_node_ok(result)


def test_compare_viewer_smokes_existing_premium_fixture(tmp_path):
    manifest = json.loads((ROOT / "docs" / "fixtures" / "premium_delivery_manifest.json").read_text())
    result = run_compare_viewer_assertions(
        tmp_path,
        f"""
        import assert from "node:assert/strict";

        const manifest = {json.dumps(manifest)};
        const lines = manifestTrackSummaries(manifest, "docs/fixtures/premium_delivery_manifest.json", {{
          "docs/fixtures/artifacts/openmvs/model.glb": "ok",
          "docs/fixtures/artifacts/gaussian/splat.ply": "ok",
        }});
        assert.equal(manifestSummaryText(manifest), "schema_version=1.0 mode=premium studio_job_id=fixture-premium generated_at=2026-06-28T00:00:00+08:00");
        assert.equal(lines[0], "mesh/openmvs role=delivery_capable delivery_capable=true artifact=docs/fixtures/artifacts/openmvs/model.glb status=ok");
        assert.equal(lines[1], "splat/gaussian_splat role=delivery_capable delivery_capable=true artifact=docs/fixtures/artifacts/gaussian/splat.ply status=ok");
        """,
    )

    assert_node_ok(result)


def test_compare_viewer_smokes_existing_qa_fixture(tmp_path):
    manifest = json.loads((ROOT / "docs" / "fixtures" / "qa_delivery_manifest.json").read_text())
    result = run_compare_viewer_assertions(
        tmp_path,
        f"""
        import assert from "node:assert/strict";

        const manifest = {json.dumps(manifest)};
        const lines = manifestTrackSummaries(manifest, "docs/fixtures/qa_delivery_manifest.json", {{
          "docs/fixtures/artifacts/openmvs/model.glb": "ok",
          "docs/fixtures/artifacts/gaussian/splat.ply": "ok",
        }});
        assert.equal(manifestSummaryText(manifest), "schema_version=1.0 mode=qa studio_job_id=fixture-qa generated_at=2026-06-28T00:10:00+08:00");
        assert.equal(lines[0], "mesh/openmvs role=delivery_candidate delivery_capable=true artifact=docs/fixtures/artifacts/openmvs/model.glb status=ok");
        assert.equal(lines[1], "splat/gaussian_splat role=diagnostic delivery_capable=false artifact=docs/fixtures/artifacts/gaussian/splat.ply status=ok");
        """,
    )

    assert_node_ok(result)


def test_compare_viewer_reports_artifact_head_failure(tmp_path):
    result = run_compare_viewer_assertions(
        tmp_path,
        """
        import assert from "node:assert/strict";

        globalThis.fetch = async () => ({ ok: false, status: 404 });
        assert.equal(await artifactHeadStatus("missing.glb"), "missing (404)");
        assert.equal(artifactFailureMessage({ "mesh.glb": "ok", "splat.ply": "missing (404)" }), "Artifact not found: splat.ply (missing (404))");
        """,
    )

    assert_node_ok(result)


def test_compare_viewer_camera_evidence_layer_without_loading_tracks(tmp_path):
    text = (ROOT / "viewer_compare_splat_mesh.html").read_text()
    assert 'id="camera-layer-toggle"' in text
    assert 'id="evidence-summary"' in text
    assert 'id="camera-path-svg"' in text
    assert 'id="sparse-points-toggle"' in text
    assert 'id="sparse-points-summary"' in text
    assert 'id="sparse-points-svg"' in text
    assert 'params.get("evidence")' in text
    assert "function evidenceManifestPath" in text
    assert "function cameraEvidenceAssetPath" in text
    assert "function spatialIndexPath" in text
    assert "function lodSparsePointsPath" in text
    assert "function cameraPathPoints" in text
    assert "function sparsePointRows" in text
    assert "function sparsePointSummary" in text
    assert "function sparsePointsSvg" in text
    assert "function loadSparsePoints" in text
    assert "function renderSparsePoints" in text
    assert "SPARSE_POINT_RENDER_CAP" in text
    assert "function cameraEvidenceSummary" in text
    assert "function renderCameraEvidence" in text
    assert "Camera evidence not available" in text
    assert "spatial index not available" in text
    assert "Sparse points not available" in text
    assert "capped" in text
    assert "points3d_tracks" not in text

    evidence_manifest = json.loads((ROOT / "docs" / "fixtures" / "evidence_manifest_colmap_openmvs_gaussian.json").read_text())
    result = run_compare_viewer_assertions(
        tmp_path,
        f"""
        import assert from "node:assert/strict";

        const deliveryManifest = {{ evidence_manifest_path: "evidence/evidence_manifest.json" }};
        const evidenceManifest = {json.dumps(evidence_manifest)};
        const cameras = {{
          cameras: [
            {{ name: "frame_0001.jpg", position: [0, 0, 0] }},
            {{ name: "frame_0002.jpg", tvec: [1, 2, 3] }},
            {{ name: "bad.jpg", tvec: ["x", 0, 0] }},
          ],
        }};

        assert.equal(
          evidenceManifestPath(deliveryManifest, "studio/jobs/42/delivery_manifest.json"),
          "studio/jobs/42/evidence/evidence_manifest.json",
        );
        assert.equal(
          cameraEvidenceAssetPath(evidenceManifest, "studio/jobs/42/evidence_manifest.json"),
          "studio/jobs/42/artifacts/evidence/cameras.json",
        );
        assert.equal(
          spatialIndexPath({{ spatial_index_path: "spatial_index.json" }}, "studio/jobs/42/evidence_manifest.json"),
          "studio/jobs/42/spatial_index.json",
        );
        assert.equal(
          lodSparsePointsPath({{ lod_sparse_points_path: "lod_sparse_points.json" }}, "studio/jobs/42/evidence_manifest.json"),
          "studio/jobs/42/lod_sparse_points.json",
        );
        assert.equal(cameraEvidenceSummary(cameras, ""), "2 cameras; spatial index not available");
        assert.equal(cameraEvidenceSummary(cameras, "spatial_index.json"), "2 cameras; spatial index ready");
        assert.deepEqual(cameraPathPoints(cameras).map((point) => point.name), ["frame_0001.jpg", "frame_0002.jpg"]);
        assert.match(cameraPathSvg(cameraPathPoints(cameras)), /polyline/);
        assert.match(cameraPathSvg([{{ name: "<bad>", x: 0, y: 0, z: 0 }}]), /&lt;bad&gt;/);
        assert.doesNotMatch(cameraPathSvg([{{ name: "<bad>", x: 0, y: 0, z: 0 }}]), /<bad>/);
        """,
    )

    assert_node_ok(result)


def test_compare_viewer_handles_incomplete_and_malformed_evidence_without_blank_state(tmp_path):
    result = run_compare_viewer_assertions(
        tmp_path,
        """
        import assert from "node:assert/strict";

        globalThis.fetch = async (path) => {
          if (path.endsWith("evidence_manifest.json")) {
            return {
              ok: true,
              json: async () => ({
                spatial_index_path: "spatial_index.json",
                lod_sparse_points_path: "lod_sparse_points.json",
              }),
            };
          }
          throw new Error(`unexpected fetch: ${path}`);
        };

        const missingCameras = await loadCameraEvidence(
          { evidence_manifest_path: "evidence/evidence_manifest.json" },
          "studio/jobs/9/delivery_manifest.json",
        );
        assert.equal(missingCameras.error, "Camera evidence not available");
        assert.equal(missingCameras.indexPath, "studio/jobs/9/evidence/spatial_index.json");
        assert.equal(missingCameras.lodPath, "studio/jobs/9/evidence/lod_sparse_points.json");

        globalThis.fetch = async () => ({
          ok: true,
          json: async () => { throw new Error("bad json"); },
        });
        const malformed = await loadCameraEvidence(
          { evidence_manifest_path: "evidence/evidence_manifest.json" },
          "studio/jobs/9/delivery_manifest.json",
        );
        assert.equal(malformed.error, "Camera evidence not available");

        currentSpatialIndexPath = "spatial_index.json";
        assert.equal(await queryEvidenceTile([1, 0, 1]), undefined);
        """,
    )

    assert_node_ok(result)


def test_compare_viewer_evidence_api_failure_falls_back_to_frontend_spatial_index(tmp_path):
    result = run_compare_viewer_assertions(
        tmp_path,
        """
        import assert from "node:assert/strict";

        const index = {
          grid: { size: 2, min_x: 0, max_x: 10, min_z: 0, max_z: 10 },
          tiles: [{ tile_id: "0_0", coverage_score: 0.88, point_count: 4, visible_camera_ids: [7], sample_sparse_points: [] }],
        };
        const calls = [];
        globalThis.fetch = async (path) => {
          calls.push(path);
          if (String(path).startsWith("../studio/api.php?mode=evidence_query")) return { ok: false, status: 503 };
          if (path === "spatial_index.json") return { ok: true, json: async () => index };
          throw new Error(`unexpected fetch: ${path}`);
        };
        currentSpatialIndexPath = "spatial_index.json";

        const tile = await queryEvidenceTile([1, 0, 1]);
        assert.equal(tile.coverage_score, 0.88);
        assert.match(calls[0], /mode=evidence_query/);
        assert.equal(calls[1], "spatial_index.json");
        """,
        search="?studio_job_id=42",
    )

    assert_node_ok(result)


def test_compare_viewer_queries_spatial_index_tile_for_mesh_pick(tmp_path):
    result = run_compare_viewer_assertions(
        tmp_path,
        """
        import assert from "node:assert/strict";

        const index = {
          grid: { size: 2, min_x: 0, max_x: 10, min_z: 0, max_z: 10 },
          tiles: [
            {
              tile_id: "0_0",
              bbox: [0, 0, 0, 5, 1, 5],
              coverage_score: 0.75,
              point_count: 2,
              visible_camera_ids: [1, 2],
              sample_sparse_points: [
                { point3d_id: 10, xyz: [1, 0, 1] },
                { point3d_id: 11, xyz: [2, 0, 2] },
              ],
            },
          ],
        };

        assert.equal(gridTileIdForPosition(index, [1, 0, 1]), "0_0");
        assert.equal(evidenceTileForPosition(index, [1, 0, 1]).coverage_score, 0.75);
        assert.equal(evidenceTileForPosition(index, [9, 0, 9]), null);
        assert.equal(
          evidenceQueryUrl("42", [1, 2, 3]),
          "../studio/api.php?mode=evidence_query&id=42&x=1&y=2&z=3",
        );
        assert.equal(
          evidencePickSummary([1.234, 0, 2.345], index.tiles[0]),
          "picked=[1.23,0.00,2.35] tile=0_0 bbox=[0,0,0,5,1,5] coverage_score=0.75 point_count=2 visible_camera_ids=1,2 sample_sparse_points=10,11",
        );
        assert.equal(
          evidencePickSummary([9, 0, 9], null),
          "picked=[9.00,0.00,9.00] no evidence for picked area",
        );
        """,
    )

    assert_node_ok(result)


def test_compare_viewer_renders_capped_sparse_lod_and_highlights_tile_samples(tmp_path):
    result = run_compare_viewer_assertions(
        tmp_path,
        """
        import assert from "node:assert/strict";

        const data = {
          point_count: 3,
          points: [
            { point3d_id: 10, xyz: [0, 0, 0], rgb: [255, 0, 0] },
            { point3d_id: 11, xyz: [1, 0, 1], rgb: [0, 255, 0] },
            { point3d_id: 12, xyz: [2, 0, 2], rgb: [0, 0, 255] },
          ],
        };
        const rows = sparsePointRows(data, 2);

        assert.equal(rows.length, 2);
        assert.equal(sparsePointSummary(data, rows), "sparse points: total=3 rendered=2 capped");
        assert.match(sparsePointsSvg(rows, new Set([11])), /data-point-id="11"/);
        assert.match(sparsePointsSvg(rows, new Set([11])), /stroke="#ffdf6e"/);
        assert.doesNotMatch(sparsePointsSvg(rows, new Set([11])), /data-point-id="12"/);
        assert.equal(sparsePointSummary(null, []), "Sparse points not available");
        """,
    )

    assert_node_ok(result)
