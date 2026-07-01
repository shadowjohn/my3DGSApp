from pathlib import Path
import subprocess
import textwrap


ROOT = Path(__file__).resolve().parents[1]


def run_viewer_module_assertions(tmp_path, assertions: str) -> subprocess.CompletedProcess:
    text = (ROOT / "js" / "gaussian_splat_viewer.js").read_text()
    text = text.replace(
        'import * as GaussianSplats3D from "@mkkellogg/gaussian-splats-3d";',
        "const GaussianSplats3D = { SceneFormat: { Ply: 'ply', Splat: 'splat', KSplat: 'ksplat', Spz: 'spz' } };",
    )
    text = text.replace("\nmain();\n", "\n")
    script = tmp_path / "viewer_scene_options_test.mjs"
    script.write_text(
        "globalThis.window = { location: { search: '' } };\n"
        "globalThis.document = { getElementById: () => ({ textContent: '' }) };\n"
        + text
        + "\n"
        + textwrap.dedent(assertions)
    )
    return subprocess.run(
        ["node", str(script)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def assert_node_ok(result: subprocess.CompletedProcess) -> None:
    assert result.returncode == 0, result.stderr + result.stdout


def test_viewer_php_loads_module_script_and_canvas_root():
    assert not (ROOT / "viewer_splat.html").exists()
    text = (ROOT / "viewer_splat.php").read_text()

    assert '<div id="viewer-root">' in text
    assert 'id="rotation-panel"' in text
    assert 'id="rotation-values"' in text
    assert 'id="rotation-query"' in text
    assert 'id="rotation-up"' in text
    assert 'data-camera-up-mode' in text
    assert 'value="view"' in text
    assert 'value="world"' in text
    assert 'value="scene"' in text
    assert ".rotation-row select option" in text
    assert "background: #101820" in text
    assert "color: #f4f7fb" in text
    assert 'data-rotation-axis="rx"' in text
    assert 'data-rotation-axis="ry"' in text
    assert 'data-rotation-axis="rz"' in text
    assert 'js/gaussian_splat_viewer.js?v=20260630-download-progress' in text
    assert '"three": "/john_web/assets/vendor/three/0.155.0/build/three.module.js"' in text
    assert '"@mkkellogg/gaussian-splats-3d": "/john_web/assets/vendor/gaussian-splats-3d/0.4.7/build/gaussian-splats-3d.module.js"' in text
    assert "right: 12px" in text
    assert "bottom: 12px" in text
    assert "max-width: calc(100vw - 24px)" in text
    assert "overflow-wrap: anywhere" in text
    assert 'id="download-progress"' in text
    assert 'id="download-progress-fill"' in text
    assert 'id="download-progress-text"' in text
    assert 'role="progressbar"' in text


def test_viewer_php_bootstraps_splat_api_uuid_source():
    text = (ROOT / "viewer_splat.php").read_text()

    assert 'require __DIR__ . "/../inc/config.php";' in text
    assert 'require_once __DIR__ . "/job_view.php";' in text
    assert "$srcParam = trim((string)($_GET['src'] ?? ''));" in text
    assert "if($id <= 0 && ctype_digit($srcParam)) $id = (int)$srcParam;" in text
    assert "gs_splat_artifact_for_job($id)" in text
    assert "api.php?mode=getSplat&uuid=" in text
    assert "window.GS_SPLAT_VIEWER_BOOTSTRAP" in text
    assert '"format"' in text
    assert "'artifact_size_bytes'=>$artifact['size_bytes'] ?? 0" in text
    assert "uploads/" not in text
    assert "viewer_splat.html?src=" not in text


def test_htaccess_sets_splat_delivery_headers():
    text = (ROOT / ".htaccess").read_text()

    assert "AddType application/octet-stream .ply .splat .ksplat .spz" in text
    assert "AddType application/json .json" in text
    assert '<FilesMatch "\\.(ply|splat|ksplat|spz|json)$">' in text
    assert 'Header set Cache-Control "public, max-age=31536000, immutable"' in text
    assert 'Header set Content-Disposition "inline"' in text
    assert 'SetEnvIfNoCase Request_URI "\\.(ply|splat|ksplat|spz)$" no-gzip' in text
    assert 'SetEnvIfNoCase Request_URI "\\.(ply|splat|ksplat|spz)$" no-brotli' in text


def test_viewer_js_uses_add_splat_scene_and_query_src():
    text = (ROOT / "js" / "gaussian_splat_viewer.js").read_text()
    assert "new GaussianSplats3D.Viewer" in text
    assert "addSplatScene" in text
    assert "URLSearchParams" in text
    assert "GS_SPLAT_VIEWER_BOOTSTRAP" in text
    assert 'const requestedSrc = bootstrap.src || params.get("src") || "";' in text
    assert "bootstrap.format" in text
    assert "sharedMemoryForWorkers: false" in text
    assert "integerBasedSort: false" in text
    assert "splatSortDistanceMapPrecision: 32" in text
    assert "halfPrecisionCovariancesOnGPU: false" in text
    assert "splatAlphaRemovalThreshold" in text
    assert "rotationFromEulerDegrees" in text
    assert 'numberParam("rx", finiteNumber(viewerMeta?.viewer?.rx, 0))' in text
    assert 'numberParam("ry", finiteNumber(viewerMeta?.viewer?.ry, 0))' in text
    assert 'numberParam("rz", finiteNumber(viewerMeta?.viewer?.rz, 0))' in text
    assert 'positiveNumberParam("scale", positiveFiniteNumber(viewerMeta?.viewer?.scale, 1))' in text
    assert 'positiveNumberParam("splatScale", positiveFiniteNumber(viewerMeta?.viewer?.splatScale, 0.45))' in text
    assert 'positiveNumberParam("alpha", positiveFiniteNumber(viewerMeta?.viewer?.alpha, 20))' in text
    assert "viewer.setSplatScale" in text
    assert "pointCloudModeEnabled" in text
    assert "async function loadViewerMeta" in text
    assert "defaultMetaUrlFor" in text
    assert "fetch(metaUrl" in text
    assert "sceneFormatForSrc" in text
    assert "format: sceneOptions.format" in text
    assert "GaussianSplats3D.SceneFormat.Ply" in text
    assert "buildSceneOptions" in text
    assert "rotateVectorByQuaternion" in text
    assert "function finiteNumber" in text
    assert "function finiteVector3" in text
    assert "function positiveFiniteNumber" in text
    assert "finiteVector3(viewerMeta?.core?.center, [0, 0, 0])" in text
    assert "positiveFiniteNumber(viewerMeta?.core?.radius, 2)" in text
    assert "viewerMeta?.firstFrame" in text
    assert "cameraPosition" in text
    assert "cameraLookAt" in text
    assert "positiveNumberParam(\"distance\"" in text
    assert "initialCameraLookAt: sceneOptions.lookAt" in text
    assert "initialCameraPosition: sceneOptions.cameraPosition" in text
    assert "cameraUp: sceneOptions.cameraUp" in text
    assert "bindRotationControls" in text
    assert "applySceneRotation" in text
    assert "rotationValuesText" in text
    assert "cameraUpForMode" in text
    assert "upMode" in text
    assert "initialCameraPosition" in text
    assert "initialCameraLookAt" in text
    assert "cleanCandidateUrlFor" in text
    assert "resolveSceneSource" in text
    assert "splat.clean.ply" in text
    assert 'boolParam("raw", false)' in text
    assert "viewerMeta?.viewer?.cameraDistance" in text
    assert "downloadSceneWithProgress" in text
    assert "updateDownloadProgress" in text
    assert "hideDownloadProgress" in text
    assert "URL.revokeObjectURL" in text
    assert 'if (!requestedSource)' in text
    assert 'const requestedManifest = params.get("manifest")' in text
    assert 'const requestedStudioJobId = params.get("studio_job_id")' in text
    assert "manifestPathFromEntrypoint" in text
    assert "../studio/api.php?mode=job_detail&id=" in text
    assert "Delivery manifest not found" in text
    assert "delivery_tracks missing" in text
    assert "splat track missing" in text
    assert "primary_artifact missing" in text
    assert "Artifact not found" in text
    assert "legacy fallback" in text
    assert "artifactPathFromManifest" in text
    assert "return" in text
    assert "uploads/local-smoke/exports/splat.ply" not in text


def test_viewer_keyboard_moves_camera_forward_and_back():
    text = (ROOT / "js" / "gaussian_splat_viewer.js").read_text()

    assert 'typeof window !== "undefined" && typeof window.addEventListener === "function"' in text
    assert 'window.addEventListener("keydown", handleViewerKeyDown)' in text
    for code in ["KeyW", "KeyA", "KeyS", "KeyD", "KeyF", "KeyB"]:
        assert code in text
    assert "moveCameraAlongView(" in text
    assert "moveCameraSideways(" in text
    assert "resetViewerCamera(" in text
    assert "saveViewerOutputThumb(" in text
    assert "function postViewerOutputThumb" in text
    assert "navigator.sendBeacon" in text
    assert "navigator.sendBeacon(url, data)" in text
    assert 'fetch(url, { method: "POST", body: data, cache: "no-store" })' in text
    assert "const saved = await postViewerOutputThumb(data);" in text
    assert "api.php?mode=save_thumb" in text


def test_viewer_shows_one_line_keyboard_help():
    text = (ROOT / "viewer_splat.php").read_text()

    assert 'id="viewer-help"' in text
    assert "W/F 前進" in text
    assert "S/B 後退" in text
    assert "A/D 左右" in text
    assert "white-space: nowrap" in text


def test_viewer_js_resolves_splat_from_delivery_manifest(tmp_path):
    result = run_viewer_module_assertions(
        tmp_path,
        """
        import assert from "node:assert/strict";

        const manifest = {
          artifacts: [
            { type: "mesh", path: "exports/model.glb", role: "primary" },
            { type: "splat", path: "exports/splat.clean.ply", role: "diagnostic" },
          ],
        };

        assert.equal(
          artifactPathFromManifest(manifest, "splat", "uploads/9/delivery_manifest.json"),
          "uploads/9/exports/splat.clean.ply",
        );
        assert.equal(
          artifactPathFromManifest(manifest, "mesh", "uploads/9/delivery_manifest.json?ts=1"),
          "uploads/9/exports/model.glb",
        );
        """,
    )

    assert_node_ok(result)


def test_viewer_js_resolves_delivery_tracks_manifest(tmp_path):
    result = run_viewer_module_assertions(
        tmp_path,
        """
        import assert from "node:assert/strict";

        const manifest = {
          delivery_tracks: [
            {
              track: "mesh",
              primary_artifact: { type: "glb", path: "exports/model.glb" },
            },
            {
              track: "splat",
              role: "diagnostic",
              primary_artifact: { type: "splat", path: "exports/splat.clean.ply" },
            },
          ],
        };

        assert.equal(
          artifactPathFromManifest(manifest, "splat", "uploads/9/delivery_manifest.json"),
          "uploads/9/exports/splat.clean.ply",
        );
        assert.equal(
          artifactPathFromManifest(manifest, "mesh", "uploads/9/delivery_manifest.json"),
          "uploads/9/exports/model.glb",
        );
        """,
    )

    assert_node_ok(result)


def test_viewer_js_reports_manifest_errors_and_legacy_fallback(tmp_path):
    result = run_viewer_module_assertions(
        tmp_path,
        """
        import assert from "node:assert/strict";

        assert.equal(
          manifestArtifactResult({}, "splat", "uploads/9/delivery_manifest.json").error,
          "delivery_tracks missing",
        );
        assert.equal(
          manifestArtifactResult({ delivery_tracks: [] }, "splat", "uploads/9/delivery_manifest.json").error,
          "delivery_tracks missing",
        );
        assert.equal(
          manifestArtifactResult({ delivery_tracks: [{ track: "mesh", primary_artifact: { path: "exports/model.glb" } }] }, "splat", "uploads/9/delivery_manifest.json").error,
          "splat track missing",
        );
        assert.equal(
          manifestArtifactResult({ delivery_tracks: [{ track: "splat" }] }, "splat", "uploads/9/delivery_manifest.json").error,
          "primary_artifact missing for splat track",
        );

        const legacy = manifestArtifactResult({
          artifacts: [{ type: "splat", path: "exports/splat.clean.ply", role: "diagnostic" }],
        }, "splat", "uploads/9/delivery_manifest.json");
        assert.equal(legacy.path, "uploads/9/exports/splat.clean.ply");
        assert.equal(legacy.warning, "legacy fallback: delivery_tracks missing");
        """,
    )

    assert_node_ok(result)


def test_viewer_js_keeps_direct_src_as_php_fallback_entrypoint():
    text = (ROOT / "js" / "gaussian_splat_viewer.js").read_text()

    assert 'const requestedSrc = bootstrap.src || params.get("src") || "";' in text
    assert "const manifestResult = requestedSrc ? null : await srcResultFromEntrypoint(\"splat\")" in text


def test_viewer_js_downloads_splat_with_progress_chunks(tmp_path):
    result = run_viewer_module_assertions(
        tmp_path,
        """
        import assert from "node:assert/strict";

        let createdBlob = null;
        globalThis.URL = {
          createObjectURL: (blob) => {
            createdBlob = blob;
            return "blob:test-splat";
          },
          revokeObjectURL: () => {},
        };
        globalThis.fetch = async () => ({
          ok: true,
          status: 200,
          headers: new Map(),
          body: new ReadableStream({
            start(controller) {
              controller.enqueue(new Uint8Array([1, 2]));
              controller.enqueue(new Uint8Array([3, 4]));
              controller.close();
            },
          }),
        });

        const seen = [];
        const result = await downloadSceneWithProgress("scene.ply", (loaded, total) => {
          seen.push([loaded, total]);
        }, 4);

        assert.equal(result.url, "blob:test-splat");
        assert.equal(result.sizeBytes, 4);
        assert.equal(result.totalBytes, 4);
        assert.deepEqual(seen, [[2, 4], [4, 4]]);
        assert.equal(createdBlob.size, 4);
        """,
    )

    assert_node_ok(result)


def test_clean_candidate_url_only_rewrites_default_export_splat(tmp_path):
    result = run_viewer_module_assertions(
        tmp_path,
        """
        import assert from "node:assert/strict";

        assert.equal(
          cleanCandidateUrlFor("uploads/7/exports/splat.ply"),
          "uploads/7/exports/splat.clean.ply",
        );
        assert.equal(cleanCandidateUrlFor("uploads/7/exports/splat.clean.ply"), "");
        assert.equal(cleanCandidateUrlFor("uploads/7/exports/other.ply"), "");
        assert.equal(cleanCandidateUrlFor("scene.splat"), "");
        """,
    )

    assert_node_ok(result)


def test_build_scene_options_rotates_and_scales_first_frame_camera_vectors(tmp_path):
    result = run_viewer_module_assertions(
        tmp_path,
        """
        import assert from "node:assert/strict";

        function assertVectorAlmostEqual(actual, expected) {
          assert.equal(actual.length, expected.length);
          for (let index = 0; index < expected.length; index += 1) {
            assert.ok(
              Math.abs(actual[index] - expected[index]) < 1e-9,
              `index ${index}: expected ${expected[index]}, got ${actual[index]}`,
            );
          }
        }

        const options = buildSceneOptions({
          viewer: { rx: 0, ry: 0, rz: 90, scale: 2 },
          firstFrame: {
            cameraPosition: [1, 0, 0],
            cameraLookAt: [0, 1, 0],
          },
        }, "scene.ply");

        assertVectorAlmostEqual(options.cameraPosition, [0, 2, 0]);
        assertVectorAlmostEqual(options.lookAt, [-2, 0, 0]);
        """,
    )

    assert_node_ok(result)


def test_build_scene_options_defaults_to_view_camera_up(tmp_path):
    result = run_viewer_module_assertions(
        tmp_path,
        """
        import assert from "node:assert/strict";

        function assertVectorAlmostEqual(actual, expected) {
          assert.equal(actual.length, expected.length);
          for (let index = 0; index < expected.length; index += 1) {
            assert.ok(
              Math.abs(actual[index] - expected[index]) < 1e-9,
              `index ${index}: expected ${expected[index]}, got ${actual[index]}`,
            );
          }
        }

        const options = buildSceneOptions({
          core: { center: [0, 0, 0], radius: 2 },
          viewer: { rx: -90, ry: 0, rz: 0, scale: 1, cameraDistance: 4 },
        }, "scene.ply");

        assert.equal(options.upMode, "view");
        assertVectorAlmostEqual(options.cameraUp, [0, 0.41036467732879783, 0.9119215051751064]);
        """,
    )

    assert_node_ok(result)


def test_build_scene_options_uses_confirmed_identity_default_rotation_without_metadata(tmp_path):
    result = run_viewer_module_assertions(
        tmp_path,
        """
        import assert from "node:assert/strict";

        const options = buildSceneOptions(null, "scene.ply");

        assert.equal(options.rx, 0);
        assert.equal(options.ry, 0);
        assert.equal(options.rz, 0);
        assert.equal(options.upMode, "view");
        """,
    )

    assert_node_ok(result)


def test_build_scene_options_preserves_photo_direction_fallback_camera(tmp_path):
    result = run_viewer_module_assertions(
        tmp_path,
        """
        import assert from "node:assert/strict";

        function assertVectorAlmostEqual(actual, expected) {
          assert.equal(actual.length, expected.length);
          for (let index = 0; index < expected.length; index += 1) {
            assert.ok(
              Math.abs(actual[index] - expected[index]) < 1e-9,
              `index ${index}: expected ${expected[index]}, got ${actual[index]}`,
            );
          }
        }

        const options = buildSceneOptions({
          core: { center: [0, 0, 0], radius: 2 },
          viewer: { rx: 0, ry: 0, rz: 0, scale: 1, cameraDistance: 4 },
        }, "scene.ply");

        assertVectorAlmostEqual(options.lookAt, [0, 0, 0]);
        assertVectorAlmostEqual(options.cameraPosition, [0, -4, 1.8]);
        """,
    )

    assert_node_ok(result)


def test_camera_up_for_mode_allows_scene_and_flipped_modes(tmp_path):
    result = run_viewer_module_assertions(
        tmp_path,
        """
        import assert from "node:assert/strict";

        function assertVectorAlmostEqual(actual, expected) {
          assert.equal(actual.length, expected.length);
          for (let index = 0; index < expected.length; index += 1) {
            assert.ok(
              Math.abs(actual[index] - expected[index]) < 1e-9,
              `index ${index}: expected ${expected[index]}, got ${actual[index]}`,
            );
          }
        }

        const rotation = rotationFromEulerDegrees(-90, 0, 0);

        assertVectorAlmostEqual(cameraUpForMode("view", rotation, [0, -4, 2]), [0, 0.44721359549995804, 0.8944271909999157]);
        assertVectorAlmostEqual(cameraUpForMode("world", rotation), [0, 1, 0]);
        assertVectorAlmostEqual(cameraUpForMode("world-flip", rotation), [0, -1, 0]);
        assertVectorAlmostEqual(cameraUpForMode("scene", rotation), [0, 0, 1]);
        assertVectorAlmostEqual(cameraUpForMode("scene-flip", rotation), [0, 0, -1]);
        assertVectorAlmostEqual(cameraUpForMode("unknown", rotation, [0, -4, 2]), [0, 0.44721359549995804, 0.8944271909999157]);
        """,
    )

    assert_node_ok(result)


def test_rotation_readout_formats_values_for_copying(tmp_path):
    result = run_viewer_module_assertions(
        tmp_path,
        """
        import assert from "node:assert/strict";

        assert.equal(
          rotationValuesText({ rx: -90, ry: 0, rz: 180, upMode: "world" }),
          "rx=-90 ry=0 rz=180 up=world",
        );
        assert.equal(
          rotationQueryText({ rx: -90.25, ry: 10.5, rz: 0, upMode: "view" }),
          "rx=-90.25&ry=10.5&rz=0&up=view",
        );
        """,
    )

    assert_node_ok(result)


def test_apply_scene_rotation_updates_loaded_splat_scene(tmp_path):
    result = run_viewer_module_assertions(
        tmp_path,
        """
        import assert from "node:assert/strict";

        function assertVectorAlmostEqual(actual, expected) {
          assert.equal(actual.length, expected.length);
          for (let index = 0; index < expected.length; index += 1) {
            assert.ok(
              Math.abs(actual[index] - expected[index]) < 1e-9,
              `index ${index}: expected ${expected[index]}, got ${actual[index]}`,
            );
          }
        }

        const quaternionSets = [];
        const calls = [];
        const viewer = {
          camera: {
            up: {
              set: (...values) => calls.push(["cameraUp", ...values]),
            },
          },
          controls: {
            object: {
              up: {
                set: (...values) => calls.push(["controlUp", ...values]),
              },
            },
            update: () => calls.push("controls"),
          },
          getSplatScene: () => ({
            quaternion: {
              set: (...values) => quaternionSets.push(values),
            },
            updateMatrixWorld: () => calls.push("matrix"),
          }),
          getSplatMesh: () => ({
            updateTransforms: () => calls.push("transforms"),
          }),
          forceRenderNextFrame: () => calls.push("render"),
          runSplatSort: (...values) => calls.push(["sort", ...values]),
        };
        const options = buildSceneOptions({
          viewer: { rx: 0, ry: 0, rz: 90, scale: 1, upMode: "world" },
        }, "scene.ply");

        assert.equal(applySceneRotation(viewer, options), true);
        assertVectorAlmostEqual(
          quaternionSets[0],
          [0, 0, Math.SQRT1_2, Math.SQRT1_2],
        );
        assert.deepEqual(calls, [
          "matrix",
          ["cameraUp", 0, 1, 0],
          ["controlUp", 0, 1, 0],
          "controls",
          "transforms",
          "render",
          ["sort", true, true],
        ]);
        """,
    )

    assert_node_ok(result)


def test_build_scene_options_uses_partial_first_frame_fallbacks(tmp_path):
    result = run_viewer_module_assertions(
        tmp_path,
        """
        import assert from "node:assert/strict";

        function assertVectorAlmostEqual(actual, expected) {
          assert.equal(actual.length, expected.length);
          for (let index = 0; index < expected.length; index += 1) {
            assert.ok(
              Math.abs(actual[index] - expected[index]) < 1e-9,
              `index ${index}: expected ${expected[index]}, got ${actual[index]}`,
            );
          }
        }

        const options = buildSceneOptions({
          core: { center: [1, 1, 0], radius: 2 },
          viewer: { rx: 0, ry: 0, rz: 90, scale: 2, cameraDistance: 4 },
          firstFrame: {
            cameraPosition: [1, 0, 0],
            cameraLookAt: [0, Number.POSITIVE_INFINITY, 0],
          },
        }, "scene.ply");

        assertVectorAlmostEqual(options.cameraPosition, [0, 2, 0]);
        assertVectorAlmostEqual(options.lookAt, [-2, 2, 0]);
        """,
    )

    assert_node_ok(result)
