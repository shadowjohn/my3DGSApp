import * as GaussianSplats3D from "@mkkellogg/gaussian-splats-3d";

const params = new URLSearchParams(window.location.search);
const bootstrap = window.GS_SPLAT_VIEWER_BOOTSTRAP || {};
const requestedSrc = bootstrap.src || params.get("src") || "";
const requestedManifest = params.get("manifest") || bootstrap.manifest || "";
const requestedStudioJobId = params.get("studio_job_id") || bootstrap.studio_job_id || "";
const bootstrapJobId = Number.parseInt(bootstrap.job_id || "0", 10);
const bootstrapArtifactSizeBytes = Number.parseInt(bootstrap.artifact_size_bytes || "0", 10);
const statusEl = document.getElementById("status");
const statusTextEl = document.getElementById("status-text") || statusEl;
const downloadProgressEl = document.getElementById("download-progress");
const downloadProgressFillEl = document.getElementById("download-progress-fill");
const downloadProgressTextEl = document.getElementById("download-progress-text");
const rotationAxes = ["rx", "ry", "rz"];
const cameraUpModes = ["view", "world", "world-flip", "scene", "scene-flip"];

function setStatus(message) {
  statusTextEl.textContent = message;
}

function formatDownloadBytes(bytes) {
  const value = Number(bytes);
  if (!Number.isFinite(value) || value <= 0) return "0 B";
  if (value < 1024) return `${Math.round(value)} B`;
  const units = ["KB", "MB", "GB"];
  let amount = value / 1024;
  let unit = units[0];
  for (let index = 1; index < units.length && amount >= 1024; index += 1) {
    amount /= 1024;
    unit = units[index];
  }
  return `${amount >= 10 ? amount.toFixed(1) : amount.toFixed(2)} ${unit}`;
}

function updateDownloadProgress(loaded, total) {
  if (!downloadProgressEl || !downloadProgressFillEl || !downloadProgressTextEl) return;
  const loadedBytes = Math.max(0, Number(loaded) || 0);
  const totalBytes = Math.max(0, Number(total) || 0);
  const percent = totalBytes > 0 ? Math.min(100, Math.round((loadedBytes / totalBytes) * 100)) : 0;
  downloadProgressEl.hidden = false;
  downloadProgressTextEl.hidden = false;
  downloadProgressEl.setAttribute("aria-valuenow", String(percent));
  downloadProgressFillEl.style.width = `${percent}%`;
  downloadProgressTextEl.textContent = totalBytes > 0
    ? `${percent}% · ${formatDownloadBytes(loadedBytes)} / ${formatDownloadBytes(totalBytes)}`
    : `${formatDownloadBytes(loadedBytes)} / 未知大小`;
}

function hideDownloadProgress() {
  if (!downloadProgressEl || !downloadProgressFillEl || !downloadProgressTextEl) return;
  downloadProgressEl.hidden = true;
  downloadProgressTextEl.hidden = true;
  downloadProgressFillEl.style.width = "0";
  downloadProgressEl.setAttribute("aria-valuenow", "0");
}

function responseContentLength(response) {
  const raw = response?.headers?.get ? response.headers.get("content-length") : "";
  const total = Number.parseInt(raw || "", 10);
  return Number.isFinite(total) && total > 0 ? total : 0;
}

async function downloadSceneWithProgress(src, onProgress, expectedTotalBytes = 0) {
  const response = await fetch(src, { cache: "no-store" });
  if (!response.ok) throw new Error(`Splat download failed (${response.status}): ${src}`);

  const totalBytes = responseContentLength(response) || (Number.isFinite(expectedTotalBytes) && expectedTotalBytes > 0 ? expectedTotalBytes : 0);
  if (!response.body?.getReader) {
    const blob = await response.blob();
    const sizeBytes = blob.size || totalBytes;
    onProgress(sizeBytes, totalBytes || sizeBytes);
    return { url: URL.createObjectURL(blob), sizeBytes, totalBytes: totalBytes || sizeBytes };
  }

  const reader = response.body.getReader();
  const chunks = [];
  let loadedBytes = 0;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    if (!value) continue;
    chunks.push(value);
    loadedBytes += value.byteLength || value.length || 0;
    onProgress(loadedBytes, totalBytes);
  }

  const blob = new Blob(chunks, { type: "application/octet-stream" });
  const sizeBytes = loadedBytes || blob.size;
  if (sizeBytes === 0) onProgress(0, totalBytes);
  return { url: URL.createObjectURL(blob), sizeBytes, totalBytes: totalBytes || sizeBytes };
}

function numberParam(name, defaultValue) {
  const value = Number.parseFloat(params.get(name));
  return Number.isFinite(value) ? value : defaultValue;
}

function positiveNumberParam(name, defaultValue) {
  const value = Number.parseFloat(params.get(name));
  return Number.isFinite(value) && value > 0 ? value : defaultValue;
}

function finiteNumber(value, defaultValue) {
  return Number.isFinite(value) ? value : defaultValue;
}

function positiveFiniteNumber(value, defaultValue) {
  return Number.isFinite(value) && value > 0 ? value : defaultValue;
}

function finiteVector3(value, defaultValue) {
  if (!Array.isArray(value) || value.length !== 3) return defaultValue;
  return value.every((component) => Number.isFinite(component)) ? value : defaultValue;
}

function boolParam(name, defaultValue) {
  const value = params.get(name);
  if (value === null) return defaultValue;
  return value === "1" || value.toLowerCase() === "true";
}

function cameraUpMode(value) {
  return cameraUpModes.includes(value) ? value : "view";
}

function cameraUpModeParam(defaultValue) {
  const value = params.get("up");
  return cameraUpMode(value || defaultValue);
}

function rotationFromEulerDegrees(rx, ry, rz) {
  const cx = Math.cos((rx * Math.PI / 180) / 2);
  const sx = Math.sin((rx * Math.PI / 180) / 2);
  const cy = Math.cos((ry * Math.PI / 180) / 2);
  const sy = Math.sin((ry * Math.PI / 180) / 2);
  const cz = Math.cos((rz * Math.PI / 180) / 2);
  const sz = Math.sin((rz * Math.PI / 180) / 2);

  return [
    sx * cy * cz - cx * sy * sz,
    cx * sy * cz + sx * cy * sz,
    cx * cy * sz - sx * sy * cz,
    cx * cy * cz + sx * sy * sz,
  ];
}

function pathWithoutQuery(path) {
  return path ? path.split(/[?#]/, 1)[0] : "";
}

function resolveManifestArtifactPath(manifestPath, artifactPath) {
  if (!artifactPath || /^(?:[a-z][a-z0-9+.-]*:|\/)/i.test(artifactPath)) return artifactPath || "";
  const basePath = pathWithoutQuery(manifestPath).replace(/[^/]*$/, "");
  return `${basePath}${artifactPath}`;
}

function resolveStudioPath(path) {
  if (!path || /^(?:[a-z][a-z0-9+.-]*:|\/)/i.test(path)) return path || "";
  return `../${path.replace(/^\/+/, "")}`;
}

async function manifestPathFromStudioJob(studioJobId) {
  const response = await fetch(`../studio/api.php?mode=job_detail&id=${encodeURIComponent(studioJobId)}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`Studio job API unavailable: ${studioJobId}`);
  const data = await response.json();
  if (data.status !== "OK") throw new Error(data.reason || `Studio job not found: ${studioJobId}`);
  const manifestPath = data.job?.delivery_manifest_path || data.delivery_manifest_path || "";
  if (!manifestPath) throw new Error(`Studio job has no delivery_manifest_path: ${studioJobId}`);
  return resolveStudioPath(manifestPath);
}

async function manifestPathFromEntrypoint() {
  if (requestedManifest) return requestedManifest;
  if (requestedStudioJobId) return manifestPathFromStudioJob(requestedStudioJobId);
  return "";
}

function legacyArtifactResult(manifest, type, manifestPath, warning) {
  const artifacts = Array.isArray(manifest?.artifacts) ? manifest.artifacts : [];
  const artifact = artifacts.find((item) => item?.type === type && item?.role === "primary")
    || artifacts.find((item) => item?.type === type);
  const path = resolveManifestArtifactPath(manifestPath, typeof artifact?.path === "string" ? artifact.path : "");
  return path ? { path, warning: `legacy fallback: ${warning}` } : null;
}

function manifestArtifactResult(manifest, type, manifestPath = "") {
  const tracks = Array.isArray(manifest?.delivery_tracks) ? manifest.delivery_tracks : [];
  if (!tracks.length) {
    return legacyArtifactResult(manifest, type, manifestPath, "delivery_tracks missing") || { path: "", error: "delivery_tracks missing" };
  }
  const track = tracks.find((item) => item?.track === type)
    || tracks.find((item) => item?.primary_artifact?.type === type)
    || (type === "mesh" ? tracks.find((item) => item?.primary_artifact?.type === "glb") : null);
  if (!track) {
    const error = type === "splat" ? "splat track missing" : "mesh track missing";
    return legacyArtifactResult(manifest, type, manifestPath, error) || { path: "", error };
  }
  if (!track.primary_artifact?.path) {
    const error = type === "splat" ? "primary_artifact missing for splat track" : "primary_artifact missing for mesh track";
    return legacyArtifactResult(manifest, type, manifestPath, error) || { path: "", error };
  }
  return { path: resolveManifestArtifactPath(manifestPath, track.primary_artifact.path), warning: "" };
}

function artifactPathFromManifest(manifest, type, manifestPath = "") {
  return manifestArtifactResult(manifest, type, manifestPath).path || "";
}

async function srcResultFromManifest(manifestPath, type) {
  if (!manifestPath) return { path: "", error: "" };
  try {
    const response = await fetch(manifestPath, { cache: "no-store" });
    if (!response.ok) return { path: "", error: `Delivery manifest not found: ${manifestPath}` };
    return manifestArtifactResult(await response.json(), type, manifestPath);
  } catch (error) {
    console.warn("Delivery manifest unavailable", error);
    return { path: "", error: `Delivery manifest not found: ${manifestPath}` };
  }
}

async function srcResultFromEntrypoint(type) {
  try {
    return srcResultFromManifest(await manifestPathFromEntrypoint(), type);
  } catch (error) {
    return { path: "", error: error.message || "Delivery manifest not found" };
  }
}

async function resourceExists(url) {
  try {
    const response = await fetch(url, { method: "HEAD", cache: "no-store" });
    return response.ok;
  } catch (error) {
    return false;
  }
}

function defaultMetaUrlFor(path) {
  const cleanPath = pathWithoutQuery(path);
  if (!cleanPath.toLowerCase().endsWith(".ply")) return "";
  return cleanPath.replace(/\.ply$/i, ".viewer.json");
}

function cleanCandidateUrlFor(path) {
  const cleanPath = pathWithoutQuery(path);
  if (!cleanPath.toLowerCase().endsWith("exports/splat.ply")) return "";
  return cleanPath.replace(/splat\.ply$/i, "splat.clean.ply");
}

async function resolveSceneSource(path) {
  if (boolParam("raw", false)) return path;

  const cleanCandidate = cleanCandidateUrlFor(path);
  if (!cleanCandidate) return path;

  try {
    const response = await fetch(cleanCandidate, { method: "HEAD", cache: "no-store" });
    if (response.ok) return cleanCandidate;
  } catch (error) {
    console.warn("Clean splat candidate unavailable", error);
  }

  return path;
}

function sceneFormatForSrc(path) {
  const hintedFormat = String(bootstrap.format || "").toLowerCase();
  if (hintedFormat === "ply") return GaussianSplats3D.SceneFormat.Ply;
  if (hintedFormat === "splat") return GaussianSplats3D.SceneFormat.Splat;
  if (hintedFormat === "ksplat") return GaussianSplats3D.SceneFormat.KSplat;
  if (hintedFormat === "spz") return GaussianSplats3D.SceneFormat.Spz;
  const cleanPath = pathWithoutQuery(path).toLowerCase();
  if (cleanPath.endsWith(".ply")) return GaussianSplats3D.SceneFormat.Ply;
  if (cleanPath.endsWith(".splat")) return GaussianSplats3D.SceneFormat.Splat;
  if (cleanPath.endsWith(".ksplat")) return GaussianSplats3D.SceneFormat.KSplat;
  if (cleanPath.endsWith(".spz")) return GaussianSplats3D.SceneFormat.Spz;
  return undefined;
}

async function loadViewerMeta(path) {
  const metaParam = params.get("meta");
  if (metaParam === "0" || metaParam === "false") return null;

  const metaUrl = metaParam || defaultMetaUrlFor(path);
  if (!metaUrl) return null;

  try {
    const response = await fetch(metaUrl, { cache: "no-store" });
    if (!response.ok) return null;
    return await response.json();
  } catch (error) {
    console.warn("Viewer metadata unavailable", error);
    return null;
  }
}

function rotateVectorByQuaternion(vector, quaternion) {
  const [x, y, z] = vector;
  const [qx, qy, qz, qw] = quaternion;
  const ix = qw * x + qy * z - qz * y;
  const iy = qw * y + qz * x - qx * z;
  const iz = qw * z + qx * y - qy * x;
  const iw = -qx * x - qy * y - qz * z;

  return [
    ix * qw + iw * -qx + iy * -qz - iz * -qy,
    iy * qw + iw * -qy + iz * -qx - ix * -qz,
    iz * qw + iw * -qz + ix * -qy - iy * -qx,
  ];
}

function transformSceneVector(vector, rotation, sceneScale) {
  return rotateVectorByQuaternion(vector, rotation).map((value) => value * sceneScale);
}

function dotVector(left, right) {
  return left.reduce((sum, value, index) => sum + value * right[index], 0);
}

function normalizeVector(vector, fallback) {
  const length = Math.sqrt(dotVector(vector, vector));
  if (!Number.isFinite(length) || length <= 1e-9) return fallback;
  return vector.map((value) => value / length);
}

function cameraUpFromViewOffset(viewOffset) {
  const worldUp = [0, 1, 0];
  const direction = normalizeVector(viewOffset, [0, 0, 1]);
  const upDot = dotVector(worldUp, direction);
  const projectedUp = worldUp.map((value, index) => value - upDot * direction[index]);
  return normalizeVector(projectedUp, [0, 0, 1]);
}

function formatAngle(value) {
  const rounded = Math.round(Number(value) * 100) / 100;
  const cleanValue = Object.is(rounded, -0) ? 0 : rounded;
  return cleanValue.toFixed(2).replace(/\.?0+$/, "");
}

function rotationValuesText(sceneOptions) {
  const rotationText = rotationAxes
    .map((axis) => `${axis}=${formatAngle(sceneOptions[axis])}`)
    .join(" ");
  return `${rotationText} up=${cameraUpMode(sceneOptions.upMode)}`;
}

function rotationQueryText(sceneOptions) {
  const rotationText = rotationAxes
    .map((axis) => `${axis}=${formatAngle(sceneOptions[axis])}`)
    .join("&");
  return `${rotationText}&up=${cameraUpMode(sceneOptions.upMode)}`;
}

function cameraUpForMode(upMode, rotation, viewOffset = [0, 0, 1]) {
  switch (cameraUpMode(upMode)) {
    case "view":
      return cameraUpFromViewOffset(viewOffset);
    case "world-flip":
      return [0, -1, 0];
    case "scene":
      return transformSceneVector([0, -1, 0], rotation, 1);
    case "scene-flip":
      return transformSceneVector([0, 1, 0], rotation, 1);
    case "world":
    default:
      return [0, 1, 0];
  }
}

function updateRotationState(sceneOptions, values) {
  rotationAxes.forEach((axis) => {
    const value = values[axis];
    if (Number.isFinite(value)) sceneOptions[axis] = value;
  });
  if (values.upMode) sceneOptions.upMode = cameraUpMode(values.upMode);
  sceneOptions.rotation = rotationFromEulerDegrees(sceneOptions.rx, sceneOptions.ry, sceneOptions.rz);
  sceneOptions.cameraUp = cameraUpForMode(sceneOptions.upMode, sceneOptions.rotation, sceneOptions.viewOffset);
}

function applySceneRotation(viewer, sceneOptions) {
  if (!viewer || !sceneOptions?.rotation) return false;
  const scene = typeof viewer.getSplatScene === "function" ? viewer.getSplatScene(0) : null;
  if (!scene?.quaternion?.set) return false;

  scene.quaternion.set(...sceneOptions.rotation);
  if (typeof scene.updateMatrixWorld === "function") scene.updateMatrixWorld(true);

  if (viewer.camera?.up?.set) viewer.camera.up.set(...sceneOptions.cameraUp);
  if (viewer.controls?.object?.up?.set) viewer.controls.object.up.set(...sceneOptions.cameraUp);
  if (typeof viewer.controls?.update === "function") viewer.controls.update();

  const splatMesh = typeof viewer.getSplatMesh === "function" ? viewer.getSplatMesh() : viewer.splatMesh;
  if (typeof splatMesh?.updateTransforms === "function") splatMesh.updateTransforms();
  if (typeof viewer.forceRenderNextFrame === "function") viewer.forceRenderNextFrame();
  if (typeof viewer.runSplatSort === "function") viewer.runSplatSort(true, true);

  return true;
}

function isTypingTarget(target) {
  const tagName = target?.tagName?.toLowerCase();
  return target?.isContentEditable || ["input", "textarea", "select", "button"].includes(tagName);
}

function moveCameraAlongView(viewer, direction, sceneOptions) {
  const camera = viewer?.camera || viewer?.controls?.object;
  if (!camera?.position?.clone || typeof camera.getWorldDirection !== "function") return false;
  const view = camera.position.clone();
  view.set(0, 0, 0);
  camera.getWorldDirection(view);
  const distance = Math.sqrt(dotVector(sceneOptions.viewOffset, sceneOptions.viewOffset));
  view.multiplyScalar(Math.max(distance * 0.05, 0.08) * direction);
  return moveCameraByVector(viewer, view);
}

function moveCameraSideways(viewer, direction, sceneOptions) {
  const camera = viewer?.camera || viewer?.controls?.object;
  if (!camera?.position?.clone || typeof camera.getWorldDirection !== "function") return false;
  const up = camera.up || viewer?.controls?.object?.up;
  if (!up) return false;
  const view = camera.position.clone();
  view.set(0, 0, 0);
  camera.getWorldDirection(view);
  const right = view.clone();
  if (typeof right.crossVectors === "function") right.crossVectors(view, up);
  else if (typeof right.cross === "function") right.cross(up);
  else return false;
  if (typeof right.normalize === "function") right.normalize();
  const distance = Math.sqrt(dotVector(sceneOptions.viewOffset, sceneOptions.viewOffset));
  right.multiplyScalar(Math.max(distance * 0.05, 0.08) * direction);
  return moveCameraByVector(viewer, right);
}

function moveCameraByVector(viewer, vector) {
  const camera = viewer?.camera || viewer?.controls?.object;
  if (!camera?.position?.add || !vector) return false;
  camera.position.add(vector);
  const target = viewer?.controls?.target;
  if (target?.add) target.add(vector);
  if (typeof viewer?.controls?.update === "function") viewer.controls.update();
  if (typeof viewer?.forceRenderNextFrame === "function") viewer.forceRenderNextFrame();
  return true;
}

function resetViewerCamera(viewer, sceneOptions) {
  const camera = viewer?.camera || viewer?.controls?.object;
  if (camera?.position?.set && Array.isArray(sceneOptions?.cameraPosition)) {
    camera.position.set(...sceneOptions.cameraPosition);
  }
  const target = viewer?.controls?.target;
  if (target?.set && Array.isArray(sceneOptions?.lookAt)) {
    target.set(...sceneOptions.lookAt);
  }
  if (typeof viewer?.controls?.update === "function") viewer.controls.update();
  if (typeof viewer?.forceRenderNextFrame === "function") viewer.forceRenderNextFrame();
}

function postViewerOutputThumb(data) {
  const url = "api.php?mode=save_thumb";
  if (typeof navigator !== "undefined" && typeof navigator.sendBeacon === "function" && navigator.sendBeacon(url, data)) {
    return Promise.resolve(true);
  }
  if (typeof fetch !== "function") return Promise.resolve(false);
  return fetch(url, { method: "POST", body: data, cache: "no-store" })
    .then((response) => response.ok)
    .catch(() => false);
}

function saveViewerOutputThumb(jobId) {
  if (!jobId) return;
  window.setTimeout(async () => {
    try {
      const source = document.querySelector("#viewer-root canvas");
      if (!source || source.width <= 0 || source.height <= 0) return;
      const canvas = document.createElement("canvas");
      canvas.width = 400;
      canvas.height = 360;
      const ctx = canvas.getContext("2d");
      ctx.fillStyle = "#07111f";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      const scale = Math.max(canvas.width / source.width, canvas.height / source.height);
      const drawWidth = source.width * scale;
      const drawHeight = source.height * scale;
      ctx.drawImage(source, (canvas.width - drawWidth) / 2, (canvas.height - drawHeight) / 2, drawWidth, drawHeight);
      const data = new FormData();
      data.append("id", String(jobId));
      data.append("image", canvas.toDataURL("image/png"));
      const saved = await postViewerOutputThumb(data);
      if (!saved) console.warn("Unable to save viewer thumbnail");
    } catch (error) {
      console.warn("Unable to save viewer thumbnail", error);
    }
  }, 900);
}

function handleViewerKeyDown(event) {
  if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey || isTypingTarget(event.target)) return;
  const viewer = window.GS_SPLAT_ACTIVE_VIEWER;
  const sceneOptions = window.GS_SPLAT_ACTIVE_SCENE_OPTIONS;
  if (!viewer || !sceneOptions) return;
  const keyActions = {
    KeyW: () => moveCameraAlongView(viewer, 1, sceneOptions),
    KeyF: () => moveCameraAlongView(viewer, 1, sceneOptions),
    KeyS: () => moveCameraAlongView(viewer, -1, sceneOptions),
    KeyB: () => moveCameraAlongView(viewer, -1, sceneOptions),
    KeyA: () => moveCameraSideways(viewer, -1, sceneOptions),
    KeyD: () => moveCameraSideways(viewer, 1, sceneOptions),
  };
  const action = keyActions[event.code];
  if (!action) return;
  event.preventDefault();
  action();
}

if (typeof window !== "undefined" && typeof window.addEventListener === "function") {
  window.addEventListener("keydown", handleViewerKeyDown);
}

function setRotationControlValues(sceneOptions) {
  rotationAxes.forEach((axis) => {
    document.querySelectorAll(`[data-rotation-axis="${axis}"]`).forEach((input) => {
      input.value = formatAngle(sceneOptions[axis]);
    });
  });
  document.querySelectorAll("[data-camera-up-mode]").forEach((input) => {
    input.value = cameraUpMode(sceneOptions.upMode);
  });
}

function updateRotationReadout(sceneOptions) {
  const valuesEl = document.getElementById("rotation-values");
  const queryEl = document.getElementById("rotation-query");
  if (valuesEl) valuesEl.textContent = rotationValuesText(sceneOptions);
  if (queryEl) queryEl.textContent = rotationQueryText(sceneOptions);
}

function updateRotationUrl(sceneOptions) {
  if (!window.history?.replaceState) return;
  rotationAxes.forEach((axis) => {
    params.set(axis, formatAngle(sceneOptions[axis]));
  });
  params.set("up", cameraUpMode(sceneOptions.upMode));
  window.history.replaceState(null, "", `${window.location.pathname}?${params.toString()}${window.location.hash}`);
}

function bindRotationControls(sceneOptions, onChange, onReset) {
  const controls = Array.from(document.querySelectorAll("[data-rotation-axis]"));
  const upControls = Array.from(document.querySelectorAll("[data-camera-up-mode]"));
  const resetButton = document.getElementById("rotation-reset");
  const copyButton = document.getElementById("rotation-copy");
  const initialValues = {
    rx: sceneOptions.rx,
    ry: sceneOptions.ry,
    rz: sceneOptions.rz,
    upMode: sceneOptions.upMode,
  };

  const sync = (values, updateUrl = true) => {
    updateRotationState(sceneOptions, values);
    setRotationControlValues(sceneOptions);
    updateRotationReadout(sceneOptions);
    if (updateUrl) updateRotationUrl(sceneOptions);
    if (onChange) onChange(sceneOptions);
  };

  controls.forEach((control) => {
    control.addEventListener("input", () => {
      const axis = control.dataset.rotationAxis;
      const value = Number.parseFloat(control.value);
      if (!rotationAxes.includes(axis) || !Number.isFinite(value)) return;
      sync({ [axis]: value });
    });
  });

  upControls.forEach((control) => {
    control.addEventListener("change", () => {
      sync({ upMode: control.value });
    });
  });

  resetButton?.addEventListener("click", () => {
    sync(initialValues);
    if (onReset) onReset(sceneOptions);
  });

  copyButton?.addEventListener("click", () => {
    const text = rotationQueryText(sceneOptions);
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(text).catch((error) => {
        console.warn("Unable to copy rotation values", error);
      });
    }
  });

  sync(sceneOptions, false);
}

function buildSceneOptions(viewerMeta, sourcePath) {
  const rx = numberParam("rx", finiteNumber(viewerMeta?.viewer?.rx, 0));
  const ry = numberParam("ry", finiteNumber(viewerMeta?.viewer?.ry, 0));
  const rz = numberParam("rz", finiteNumber(viewerMeta?.viewer?.rz, 0));
  const sceneScale = positiveNumberParam("scale", positiveFiniteNumber(viewerMeta?.viewer?.scale, 1));
  const splatScale = positiveNumberParam("splatScale", positiveFiniteNumber(viewerMeta?.viewer?.splatScale, 0.45));
  const alpha = positiveNumberParam("alpha", positiveFiniteNumber(viewerMeta?.viewer?.alpha, 20));
  const pointCloudModeEnabled = boolParam("point", false);
  const upMode = cameraUpModeParam(viewerMeta?.viewer?.upMode || viewerMeta?.viewer?.up || "view");
  const rotation = rotationFromEulerDegrees(rx, ry, rz);
  const center = finiteVector3(viewerMeta?.core?.center, [0, 0, 0]);
  const radius = positiveFiniteNumber(viewerMeta?.core?.radius, 2);
  const firstFrameCameraPosition = finiteVector3(viewerMeta?.firstFrame?.cameraPosition, null);
  const firstFrameCameraLookAt = finiteVector3(viewerMeta?.firstFrame?.cameraLookAt, null);
  const defaultDistance = positiveFiniteNumber(
    viewerMeta?.viewer?.cameraDistance,
    Math.max(1, radius * 2.2),
  );
  const distance = positiveNumberParam("distance", defaultDistance);
  const fallbackLookAt = transformSceneVector(center, rotation, sceneScale);
  const fallbackCameraPosition = [
    fallbackLookAt[0],
    fallbackLookAt[1] - distance,
    fallbackLookAt[2] + Math.max(1, distance * 0.45),
  ];
  const lookAt = firstFrameCameraLookAt
    ? transformSceneVector(firstFrameCameraLookAt, rotation, sceneScale)
    : fallbackLookAt;
  const cameraPosition = firstFrameCameraPosition
    ? transformSceneVector(firstFrameCameraPosition, rotation, sceneScale)
    : fallbackCameraPosition;
  const viewOffset = cameraPosition.map((value, index) => value - lookAt[index]);
  const cameraUp = cameraUpForMode(upMode, rotation, viewOffset);

  return {
    rx,
    ry,
    rz,
    sceneScale,
    splatScale,
    alpha,
    pointCloudModeEnabled,
    upMode,
    rotation,
    format: sceneFormatForSrc(sourcePath),
    lookAt,
    cameraPosition,
    viewOffset,
    cameraUp,
  };
}

async function main() {
  const manifestResult = requestedSrc ? null : await srcResultFromEntrypoint("splat");
  if (manifestResult?.error) {
    setStatus(manifestResult.error);
    return;
  }
  const requestedSource = requestedSrc || manifestResult?.path;
  if (!requestedSource) {
    setStatus("請提供 Splat 檔案 Provide a splat file with ?src=path/to/splat.ply or ?manifest=path/to/delivery_manifest.json");
    return;
  }
  if (manifestResult?.path && !(await resourceExists(requestedSource))) {
    setStatus(`找不到產物 Artifact not found: ${requestedSource}`);
    return;
  }

  setStatus(`${manifestResult?.warning ? `${manifestResult.warning}\n` : ""}載入中 Loading ${requestedSource}`);

  const src = await resolveSceneSource(requestedSource);
  if (src !== requestedSource) {
    params.set("src", src);
    setStatus(`載入清理後 Splat Loading cleaned splat ${src}`);
  }
  const viewerMeta = await loadViewerMeta(src);
  const sceneOptions = buildSceneOptions(viewerMeta, src);

  const viewer = new GaussianSplats3D.Viewer({
    rootElement: document.getElementById("viewer-root"),
    cameraUp: sceneOptions.cameraUp,
    initialCameraPosition: sceneOptions.cameraPosition,
    initialCameraLookAt: sceneOptions.lookAt,
    sharedMemoryForWorkers: false,
    integerBasedSort: false,
    splatSortDistanceMapPrecision: 32,
    gpuAcceleratedSort: false,
    halfPrecisionCovariancesOnGPU: false,
    ignoreDevicePixelRatio: false,
    sphericalHarmonicsDegree: 0,
    pointCloudModeEnabled: sceneOptions.pointCloudModeEnabled,
  });
  window.GS_SPLAT_ACTIVE_VIEWER = viewer;
  window.GS_SPLAT_ACTIVE_SCENE_OPTIONS = sceneOptions;
  let sceneReady = false;

  bindRotationControls(sceneOptions, () => {
    if (sceneReady) applySceneRotation(viewer, sceneOptions);
  }, () => {
    if (sceneReady) resetViewerCamera(viewer, sceneOptions);
  });

  let downloadedScene = null;
  try {
    downloadedScene = await downloadSceneWithProgress(src, updateDownloadProgress, bootstrapArtifactSizeBytes);
    setStatus(`解析中 Preparing splat ${formatDownloadBytes(downloadedScene.sizeBytes)}`);
    await viewer.addSplatScene(downloadedScene.url, {
      splatAlphaRemovalThreshold: sceneOptions.alpha,
      showLoadingUI: true,
      format: sceneOptions.format,
      position: [0, 0, 0],
      rotation: sceneOptions.rotation,
      scale: [sceneOptions.sceneScale, sceneOptions.sceneScale, sceneOptions.sceneScale],
    });
    if (typeof viewer.setSplatScale === "function") {
      viewer.setSplatScale(sceneOptions.splatScale);
    }
    sceneReady = true;
    applySceneRotation(viewer, sceneOptions);
    viewer.start();
    saveViewerOutputThumb(bootstrapJobId);
    hideDownloadProgress();
    setStatus(`就緒 Ready: ${src} | ${rotationValuesText(sceneOptions)} alpha=${sceneOptions.alpha} splatScale=${sceneOptions.splatScale}`);
  } catch (error) {
    console.error(error);
    hideDownloadProgress();
    setStatus(`載入失敗 Load failed: ${error.message}`);
  } finally {
    if (downloadedScene?.url) URL.revokeObjectURL(downloadedScene.url);
  }
}

main();
