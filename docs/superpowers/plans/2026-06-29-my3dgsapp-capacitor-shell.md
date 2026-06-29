# my3DGSAPP Capacitor Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first runnable `my3dgsapp` Capacitor + Vite + TypeScript shell for the WebView-first Capture Companion.

**Architecture:** Keep the app as a small vanilla TypeScript web app wrapped by Capacitor. Easymap/Cesium/Three.js stay in the web layer; native capability is represented by narrow service interfaces and dev stubs until APP-A4.

**Tech Stack:** Capacitor, Vite, TypeScript, vanilla DOM, Easymap runtime assets, Node/Vite build checks.

---

## File Map

- Create `my3dgsapp/package.json`: npm scripts and dependencies.
- Create `my3dgsapp/index.html`: Vite entry HTML.
- Create `my3dgsapp/tsconfig.json`: TypeScript strict config.
- Create `my3dgsapp/vite.config.ts`: Vite build config.
- Create `my3dgsapp/capacitor.config.ts`: Capacitor app config.
- Create `my3dgsapp/src/main.ts`: bootstraps the app.
- Create `my3dgsapp/src/app.ts`: hash router and layout shell.
- Create `my3dgsapp/src/styles/app.css`: compact mobile UI.
- Create `my3dgsapp/src/models/*.ts`: Upload, metadata, job, placement, delivery models.
- Create `my3dgsapp/src/services/*.ts`: API, upload, token, job, placement, viewer helpers.
- Create `my3dgsapp/src/map/*.ts`: Easymap/Cesium shell, job markers, placement layer.
- Create `my3dgsapp/src/pages/*.ts`: Home, Settings, Capture, Upload, Job Status, Map, Result pages.
- Copy Easymap runtime from `D:\GD\5project\108easymap\code\easymap_official\offical\Easymap` to `my3dgsapp/public/vendor/easymap`.

## Task 1: Bootstrap Vite + Capacitor Project Files

**Files:**
- Create: `my3dgsapp/package.json`
- Create: `my3dgsapp/index.html`
- Create: `my3dgsapp/tsconfig.json`
- Create: `my3dgsapp/vite.config.ts`
- Create: `my3dgsapp/capacitor.config.ts`

- [ ] **Step 1: Create package and config files**

`my3dgsapp/package.json`:

```json
{
  "name": "my3dgsapp",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite --host 0.0.0.0",
    "build": "tsc --noEmit && vite build",
    "preview": "vite preview --host 0.0.0.0",
    "cap:sync": "cap sync"
  },
  "dependencies": {
    "@capacitor/core": "^7.0.0"
  },
  "devDependencies": {
    "@capacitor/android": "^7.0.0",
    "@capacitor/cli": "^7.0.0",
    "@capacitor/ios": "^7.0.0",
    "typescript": "^5.0.0",
    "vite": "^7.0.0"
  }
}
```

`my3dgsapp/index.html`:

```html
<!doctype html>
<html lang="zh-Hant">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
    <title>my3DGSAPP</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

`my3dgsapp/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "module": "ESNext",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "allowJs": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "moduleResolution": "Bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true
  },
  "include": ["src", "vite.config.ts", "capacitor.config.ts"]
}
```

`my3dgsapp/vite.config.ts`:

```ts
import { defineConfig } from "vite";

export default defineConfig({
  server: {
    host: "0.0.0.0",
    port: 5173
  },
  build: {
    outDir: "dist",
    emptyOutDir: true
  }
});
```

`my3dgsapp/capacitor.config.ts`:

```ts
import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "tw.threewa.my3dgsapp",
  appName: "my3DGSAPP",
  webDir: "dist"
};

export default config;
```

- [ ] **Step 2: Install dependencies**

Run:

```powershell
cd D:\mytools\my3DGSApp\my3dgsapp
npm install
```

Expected: `node_modules` and `package-lock.json` are created.

## Task 2: Add Models and Service Interfaces

**Files:**
- Create: `my3dgsapp/src/models/Placement.ts`
- Create: `my3dgsapp/src/models/CaptureMetadata.ts`
- Create: `my3dgsapp/src/models/UploadSession.ts`
- Create: `my3dgsapp/src/models/StudioJob.ts`
- Create: `my3dgsapp/src/models/DeliveryManifest.ts`
- Create: `my3dgsapp/src/services/viewerLinks.ts`
- Create: `my3dgsapp/src/services/secureToken.ts`
- Create: `my3dgsapp/src/services/mobileApi.ts`
- Create: `my3dgsapp/src/services/uploadClient.ts`
- Create: `my3dgsapp/src/services/jobStatus.ts`
- Create: `my3dgsapp/src/services/placementClient.ts`

- [ ] **Step 1: Create model files**

`Placement.ts`:

```ts
export type PlacementSource = "server_adjusted" | "manual" | "estimated";

export interface Placement {
  lon: number;
  lat: number;
  height_m: number;
  scale: number;
  rotation_deg?: number;
  heading_deg?: number;
  pitch_deg?: number;
  roll_deg?: number;
  source: PlacementSource;
  updated_at: string;
}
```

`CaptureMetadata.ts`:

```ts
export interface CaptureMetadata {
  schema_version: "1.0";
  app: {
    name: "my3DGSAPP";
    version: string;
  };
  device: {
    platform: "ios" | "android" | "web";
    model: string;
    os_version: string;
  };
  capture: {
    mode: "qa";
    media_type: "video";
    duration_sec: number;
    width: number;
    height: number;
    fps: number;
    orientation: "portrait" | "landscape" | "unknown";
    recorded_at: string;
  };
  quality_hints: {
    blur_warning: boolean;
    low_light_warning: boolean;
    motion_too_fast_warning: boolean;
    too_short_warning: boolean;
    coverage_hint: "unknown" | "poor" | "ok" | "good";
  };
  notes: {
    user_title: string;
    user_note: string;
  };
}
```

`UploadSession.ts`:

```ts
export type UploadStatus = "created" | "uploading" | "finalized" | "job_created" | "failed" | "expired";

export interface UploadSession {
  upload_id: string;
  status: UploadStatus;
  file_size: number;
  received_bytes: number;
  next_offset: number;
  chunk_size: number;
}
```

`StudioJob.ts`:

```ts
import type { Placement } from "./Placement";

export type StudioJobStatus =
  | "pending"
  | "preflight"
  | "running_openmvs"
  | "running_gaussian"
  | "aggregating"
  | "completed"
  | "partial_failed"
  | "failed";

export interface StudioJob {
  studio_job_id: number;
  title: string;
  mode: "qa";
  status: StudioJobStatus;
  app_stage: string;
  created_at: string;
  confidence_level?: string;
  placement?: Placement;
  viewer_urls?: {
    delivery: string;
    compare: string;
  };
}
```

`DeliveryManifest.ts`:

```ts
import type { Placement } from "./Placement";

export interface DeliveryManifest {
  schema_version: "1.0";
  studio_job_id: number;
  delivery_url: string;
  compare_url: string;
  placement?: Placement;
}
```

- [ ] **Step 2: Create service files**

`viewerLinks.ts`:

```ts
export function openCompareViewer(baseUrl: string, studioJobId: number): string {
  return `${trimSlash(baseUrl)}/viewer_compare_splat_mesh.html?studio_job_id=${encodeURIComponent(studioJobId)}`;
}

export function openDeliveryPage(baseUrl: string, jobId: number): string {
  return `${trimSlash(baseUrl)}/delivery.php?job_id=${encodeURIComponent(jobId)}`;
}

function trimSlash(value: string): string {
  return value.replace(/\/+$/, "");
}
```

`secureToken.ts`:

```ts
const TOKEN_KEY = "my3dgsapp.mobile_api_token";
const SERVER_URL_KEY = "my3dgsapp.server_url";

export interface SecureTokenStore {
  getToken(): Promise<string | null>;
  setToken(token: string): Promise<void>;
  removeToken(): Promise<void>;
  getServerUrl(): Promise<string | null>;
  setServerUrl(serverUrl: string): Promise<void>;
}

export class DevSecureTokenStore implements SecureTokenStore {
  async getToken(): Promise<string | null> {
    return localStorage.getItem(TOKEN_KEY);
  }

  async setToken(token: string): Promise<void> {
    localStorage.setItem(TOKEN_KEY, token);
  }

  async removeToken(): Promise<void> {
    localStorage.removeItem(TOKEN_KEY);
  }

  async getServerUrl(): Promise<string | null> {
    return localStorage.getItem(SERVER_URL_KEY);
  }

  async setServerUrl(serverUrl: string): Promise<void> {
    localStorage.setItem(SERVER_URL_KEY, serverUrl);
  }
}
```

`mobileApi.ts`:

```ts
import type { CaptureMetadata } from "../models/CaptureMetadata";
import type { StudioJob } from "../models/StudioJob";
import type { UploadSession } from "../models/UploadSession";
import type { SecureTokenStore } from "./secureToken";

export class MobileApiClient {
  constructor(private readonly tokenStore: SecureTokenStore) {}

  async createUploadSession(input: { file_name: string; file_size: number; mime_type: string; sha256?: string }): Promise<UploadSession> {
    return this.post("create_upload_session", input);
  }

  async uploadChunk(uploadId: string, offset: number, chunk: Blob): Promise<UploadSession> {
    const baseUrl = await this.requireServerUrl();
    const token = await this.requireToken();
    const url = `${baseUrl}/studio/mobile_api.php?mode=upload_chunk&upload_id=${encodeURIComponent(uploadId)}&offset=${encodeURIComponent(offset)}`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "X-Device-Id": getDeviceId(),
        "X-App-Version": "0.1.0",
        "Content-Type": "application/octet-stream"
      },
      body: chunk
    });
    return readJson<UploadSession>(response);
  }

  async finalizeUpload(uploadId: string, metadata: CaptureMetadata): Promise<{ upload_id: string; status: "finalized"; upload_manifest_path: string; next_action: string }> {
    return this.post("finalize_upload", { upload_id: uploadId, metadata });
  }

  async createQaJobFromUpload(uploadId: string, title: string, note = ""): Promise<{ upload_id: string; studio_job_id: number; mode: "qa"; status: "pending"; next_worker: string }> {
    return this.post("create_qa_job_from_upload", { upload_id: uploadId, title, note });
  }

  async jobDetail(studioJobId: number): Promise<StudioJob> {
    return this.get(`job_detail&id=${encodeURIComponent(studioJobId)}`);
  }

  async myJobs(): Promise<{ jobs: StudioJob[] }> {
    return this.get("my_jobs");
  }

  private async post<T>(mode: string, body: unknown): Promise<T> {
    const baseUrl = await this.requireServerUrl();
    const token = await this.requireToken();
    const response = await fetch(`${baseUrl}/studio/mobile_api.php?mode=${mode}`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "X-Device-Id": getDeviceId(),
        "X-App-Version": "0.1.0",
        "Content-Type": "application/json"
      },
      body: JSON.stringify(body)
    });
    return readJson<T>(response);
  }

  private async get<T>(mode: string): Promise<T> {
    const baseUrl = await this.requireServerUrl();
    const token = await this.requireToken();
    const response = await fetch(`${baseUrl}/studio/mobile_api.php?mode=${mode}`, {
      headers: {
        Authorization: `Bearer ${token}`,
        "X-Device-Id": getDeviceId(),
        "X-App-Version": "0.1.0"
      }
    });
    return readJson<T>(response);
  }

  private async requireServerUrl(): Promise<string> {
    const serverUrl = await this.tokenStore.getServerUrl();
    if (!serverUrl) throw new Error("server_url is not configured");
    return serverUrl.replace(/\/+$/, "");
  }

  private async requireToken(): Promise<string> {
    const token = await this.tokenStore.getToken();
    if (!token) throw new Error("mobile API token is not configured");
    return token;
  }
}

async function readJson<T>(response: Response): Promise<T> {
  const payload = await response.json();
  if (!response.ok || payload.ok === false) {
    throw new Error(payload.error || `HTTP ${response.status}`);
  }
  return payload as T;
}

function getDeviceId(): string {
  const key = "my3dgsapp.device_id";
  const existing = localStorage.getItem(key);
  if (existing) return existing;
  const value = `web-${crypto.randomUUID()}`;
  localStorage.setItem(key, value);
  return value;
}
```

`uploadClient.ts`:

```ts
import type { CaptureMetadata } from "../models/CaptureMetadata";
import type { UploadSession } from "../models/UploadSession";
import type { MobileApiClient } from "./mobileApi";

export interface UploadProgress {
  uploadId: string;
  sentBytes: number;
  totalBytes: number;
  percent: number;
}

export class UploadClient {
  constructor(private readonly api: MobileApiClient) {}

  async uploadMp4(file: File, metadata: CaptureMetadata, onProgress: (progress: UploadProgress) => void): Promise<UploadSession> {
    let session = await this.api.createUploadSession({
      file_name: file.name || "source.mp4",
      file_size: file.size,
      mime_type: file.type || "video/mp4"
    });

    while (session.next_offset < file.size) {
      const nextOffset = session.next_offset;
      const chunk = file.slice(nextOffset, Math.min(nextOffset + session.chunk_size, file.size));
      session = await this.api.uploadChunk(session.upload_id, nextOffset, chunk);
      onProgress({
        uploadId: session.upload_id,
        sentBytes: session.received_bytes,
        totalBytes: file.size,
        percent: Math.round((session.received_bytes / file.size) * 100)
      });
    }

    await this.api.finalizeUpload(session.upload_id, metadata);
    return { ...session, status: "finalized", received_bytes: file.size, next_offset: file.size };
  }
}
```

`jobStatus.ts`:

```ts
import type { StudioJob, StudioJobStatus } from "../models/StudioJob";

export function getJobLabel(job: StudioJob): string {
  return statusLabels[job.status] || "處理中";
}

const statusLabels: Record<StudioJobStatus, string> = {
  pending: "等待處理",
  preflight: "品質檢查",
  running_openmvs: "3D 重建中",
  running_gaussian: "Gaussian 診斷中",
  aggregating: "產生交付結果",
  completed: "完成",
  partial_failed: "部分完成",
  failed: "失敗"
};
```

`placementClient.ts`:

```ts
import type { Placement } from "../models/Placement";
import type { StudioJob } from "../models/StudioJob";

export function getServerPlacement(job: StudioJob): Placement | null {
  return job.placement || null;
}
```

## Task 3: Add App Shell, Pages, and Styles

**Files:**
- Create: `my3dgsapp/src/main.ts`
- Create: `my3dgsapp/src/app.ts`
- Create: `my3dgsapp/src/styles/app.css`
- Create: `my3dgsapp/src/pages/HomePage.ts`
- Create: `my3dgsapp/src/pages/SettingsPage.ts`
- Create: `my3dgsapp/src/pages/CapturePage.ts`
- Create: `my3dgsapp/src/pages/UploadPage.ts`
- Create: `my3dgsapp/src/pages/JobStatusPage.ts`
- Create: `my3dgsapp/src/pages/MapPage.ts`
- Create: `my3dgsapp/src/pages/ResultPage.ts`

- [ ] **Step 1: Create the app shell**

`main.ts`:

```ts
import "./styles/app.css";
import { createApp } from "./app";

const root = document.querySelector<HTMLDivElement>("#app");
if (!root) throw new Error("#app not found");

createApp(root);
```

`app.ts`:

```ts
import { renderCapturePage } from "./pages/CapturePage";
import { renderHomePage } from "./pages/HomePage";
import { renderJobStatusPage } from "./pages/JobStatusPage";
import { renderMapPage } from "./pages/MapPage";
import { renderResultPage } from "./pages/ResultPage";
import { renderSettingsPage } from "./pages/SettingsPage";
import { renderUploadPage } from "./pages/UploadPage";

type Route = "home" | "settings" | "capture" | "upload" | "jobs" | "map" | "result";

const routes: Record<Route, () => string> = {
  home: renderHomePage,
  settings: renderSettingsPage,
  capture: renderCapturePage,
  upload: renderUploadPage,
  jobs: renderJobStatusPage,
  map: renderMapPage,
  result: renderResultPage
};

export function createApp(root: HTMLElement): void {
  const render = () => {
    const route = getRoute();
    root.innerHTML = `
      <main class="app-shell">
        <section class="app-content">${routes[route]()}</section>
        <nav class="tabbar">
          ${navItem("home", "首頁", route)}
          ${navItem("map", "地圖", route)}
          ${navItem("capture", "拍攝", route)}
          ${navItem("jobs", "任務", route)}
          ${navItem("settings", "設定", route)}
        </nav>
      </main>
    `;
  };

  window.addEventListener("hashchange", render);
  render();
}

function getRoute(): Route {
  const raw = location.hash.replace(/^#\/?/, "");
  if (raw in routes) return raw as Route;
  return "home";
}

function navItem(route: Route, label: string, activeRoute: Route): string {
  const active = route === activeRoute ? " active" : "";
  return `<a class="tabbar-item${active}" href="#${route}">${label}</a>`;
}
```

- [ ] **Step 2: Create pages**

Each page returns static markup first. API wiring comes after APP-A2.

`HomePage.ts`:

```ts
export function renderHomePage(): string {
  return `
    <header class="page-header">
      <h1>my3DGSAPP</h1>
      <p>Capture Companion for 3DGS Studio</p>
    </header>
    <section class="panel">
      <h2>最近掃描</h2>
      <p class="muted">尚未載入 jobs。APP-A2 接上 mobile API 後會顯示 token 底下的任務。</p>
      <a class="primary-action" href="#capture">開始拍攝 / 匯入 MP4</a>
    </section>
  `;
}
```

`SettingsPage.ts`:

```ts
export function renderSettingsPage(): string {
  return `
    <header class="page-header">
      <h1>設定</h1>
      <p>Studio mobile API token</p>
    </header>
    <section class="panel form-panel">
      <label>Server URL <input value="https://3wa.tw/demo/php/map/3D/gaussian_splat" /></label>
      <label>API Token <input type="password" placeholder="m3d_xxxxxxxxxxxxxxxxx" /></label>
      <button class="primary-action" type="button">儲存設定</button>
      <p class="muted">v0.1 native SecureToken 先以 interface + dev stub 表示，後續接 Keychain / Keystore。</p>
    </section>
  `;
}
```

`CapturePage.ts`:

```ts
export function renderCapturePage(): string {
  return `
    <header class="page-header">
      <h1>拍攝 / 匯入</h1>
      <p>QA Scan only</p>
    </header>
    <section class="panel">
      <h2>拍攝指引</h2>
      <ul class="checklist">
        <li>繞物體或場景慢慢移動</li>
        <li>保持畫面穩定，避免快速晃動</li>
        <li>避免過暗、反光、透明與大面積純色</li>
        <li>建議影片長度 20-60 秒</li>
      </ul>
      <label class="file-picker">
        選擇 MP4
        <input type="file" accept="video/mp4,video/*" />
      </label>
    </section>
  `;
}
```

`UploadPage.ts`:

```ts
export function renderUploadPage(): string {
  return `
    <header class="page-header">
      <h1>上傳</h1>
      <p>Offset chunk upload</p>
    </header>
    <section class="panel">
      <div class="progress"><span style="width: 0%"></span></div>
      <p class="muted">上傳期間請保持 App 開啟；中斷後可重新開啟續傳。</p>
    </section>
  `;
}
```

`JobStatusPage.ts`:

```ts
export function renderJobStatusPage(): string {
  return `
    <header class="page-header">
      <h1>任務狀態</h1>
      <p>QA pipeline stages</p>
    </header>
    <section class="panel status-list">
      <div>等待處理</div>
      <div>品質檢查</div>
      <div>3D 重建中</div>
      <div>Gaussian 診斷中</div>
      <div>產生交付結果</div>
    </section>
  `;
}
```

`MapPage.ts`:

```ts
export function renderMapPage(): string {
  return `
    <section class="map-page">
      <div id="map" class="map-container">
        <div class="map-placeholder">
          Easymap + Cesium container
          <span>APP-A3 建立容器；APP-A5 接 job marker 與 placement display。</span>
        </div>
      </div>
      <a class="record-fab" href="#capture">錄影</a>
    </section>
  `;
}
```

`ResultPage.ts`:

```ts
export function renderResultPage(): string {
  return `
    <header class="page-header">
      <h1>成果</h1>
      <p>Delivery / Compare Viewer</p>
    </header>
    <section class="panel">
      <a class="primary-action" href="#map">回到地圖</a>
      <p class="muted">viewerLinks 會產生 delivery.php 與 viewer_compare_splat_mesh.html 入口。</p>
    </section>
  `;
}
```

- [ ] **Step 3: Create styles**

`app.css`:

```css
* {
  box-sizing: border-box;
}

html,
body,
#app {
  width: 100%;
  height: 100%;
  margin: 0;
}

body {
  font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: #101418;
  color: #f5f7fa;
}

a {
  color: inherit;
  text-decoration: none;
}

.app-shell {
  min-height: 100%;
  display: grid;
  grid-template-rows: 1fr auto;
}

.app-content {
  min-height: 0;
  overflow: auto;
  padding: 18px 16px 88px;
}

.page-header h1 {
  margin: 0;
  font-size: 28px;
}

.page-header p,
.muted {
  color: #a9b4c0;
}

.panel {
  margin-top: 16px;
  padding: 16px;
  border: 1px solid #2b3540;
  border-radius: 8px;
  background: #182029;
}

.form-panel {
  display: grid;
  gap: 14px;
}

.form-panel label {
  display: grid;
  gap: 6px;
  color: #cfd8e3;
}

.form-panel input {
  width: 100%;
  padding: 12px;
  border: 1px solid #3a4754;
  border-radius: 6px;
  background: #0f151b;
  color: #f5f7fa;
}

.primary-action,
.file-picker,
button.primary-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
  padding: 0 16px;
  border: 0;
  border-radius: 8px;
  background: #39a0ff;
  color: #06111d;
  font-weight: 700;
}

.file-picker input {
  display: none;
}

.checklist {
  padding-left: 20px;
  line-height: 1.8;
}

.progress {
  height: 12px;
  overflow: hidden;
  border-radius: 999px;
  background: #2b3540;
}

.progress span {
  display: block;
  height: 100%;
  background: #39a0ff;
}

.status-list {
  display: grid;
  gap: 10px;
}

.status-list div {
  padding: 12px;
  border-radius: 6px;
  background: #101820;
}

.map-page {
  position: fixed;
  inset: 0 0 64px;
}

.map-container {
  width: 100%;
  height: 100%;
  background: #0b1117;
}

.map-placeholder {
  display: grid;
  place-items: center;
  height: 100%;
  padding: 20px;
  text-align: center;
  color: #cfd8e3;
}

.map-placeholder span {
  display: block;
  margin-top: 10px;
  color: #8795a3;
  font-size: 14px;
}

.record-fab {
  position: fixed;
  right: 18px;
  bottom: 84px;
  display: grid;
  place-items: center;
  width: 68px;
  height: 68px;
  border-radius: 50%;
  background: #ff4d4f;
  color: white;
  font-weight: 800;
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.35);
}

.tabbar {
  position: fixed;
  right: 0;
  bottom: 0;
  left: 0;
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  height: 64px;
  border-top: 1px solid #26313b;
  background: #111820;
}

.tabbar-item {
  display: grid;
  place-items: center;
  color: #95a3b1;
  font-size: 13px;
}

.tabbar-item.active {
  color: #39a0ff;
}
```

## Task 4: Add Map Shell and Viewer Data Helpers

**Files:**
- Create: `my3dgsapp/src/map/easymapCesiumShell.ts`
- Create: `my3dgsapp/src/map/jobMarkers.ts`
- Create: `my3dgsapp/src/map/placementLayer.ts`

- [ ] **Step 1: Create map shell helpers**

`easymapCesiumShell.ts`:

```ts
declare global {
  interface Window {
    Easymap?: new (target: string) => unknown;
  }
}

export interface EasymapShell {
  map: unknown | null;
  ready: boolean;
}

export function createEasymapShell(targetId: string): EasymapShell {
  if (!window.Easymap) {
    return { map: null, ready: false };
  }

  return {
    map: new window.Easymap(targetId),
    ready: true
  };
}
```

`jobMarkers.ts`:

```ts
import type { StudioJob } from "../models/StudioJob";

export interface JobMarker {
  id: number;
  title: string;
  lon: number;
  lat: number;
  status: string;
}

export function toJobMarkers(jobs: StudioJob[]): JobMarker[] {
  return jobs
    .filter((job) => Boolean(job.placement))
    .map((job) => ({
      id: job.studio_job_id,
      title: job.title,
      lon: job.placement!.lon,
      lat: job.placement!.lat,
      status: job.status
    }));
}
```

`placementLayer.ts`:

```ts
import type { Placement } from "../models/Placement";

export interface PlacementTransform {
  position: [number, number, number];
  scale: number;
  rotationDegrees: {
    heading: number;
    pitch: number;
    roll: number;
  };
}

export function toPlacementTransform(placement: Placement): PlacementTransform {
  return {
    position: [placement.lon, placement.lat, placement.height_m],
    scale: placement.scale,
    rotationDegrees: {
      heading: placement.heading_deg ?? placement.rotation_deg ?? 0,
      pitch: placement.pitch_deg ?? 0,
      roll: placement.roll_deg ?? 0
    }
  };
}
```

## Task 5: Copy Easymap Runtime Assets

**Files:**
- Create directory: `my3dgsapp/public/vendor/easymap`

- [ ] **Step 1: Copy runtime**

Run:

```powershell
Copy-Item -Recurse -Force -LiteralPath 'D:\GD\5project\108easymap\code\easymap_official\offical\Easymap' -Destination 'D:\mytools\my3DGSApp\my3dgsapp\public\vendor\easymap'
```

Expected:

```text
my3dgsapp/public/vendor/easymap/easymap.js
my3dgsapp/public/vendor/easymap/map_ini.js
my3dgsapp/public/vendor/easymap/7/
my3dgsapp/public/vendor/easymap/MapLibre/
```

## Task 6: Build, Sync, and Record Progress

**Files:**
- Modify: `history.md`

- [ ] **Step 1: Run build**

Run:

```powershell
cd D:\mytools\my3DGSApp\my3dgsapp
npm run build
```

Expected: TypeScript passes and Vite creates `dist/`.

- [ ] **Step 2: Add Capacitor platforms when local toolchain allows**

Run:

```powershell
cd D:\mytools\my3DGSApp\my3dgsapp
npx cap add android
npx cap add ios
npx cap sync
```

Expected:

- Android/iOS projects are created if platform prerequisites exist.
- If iOS fails on Windows, record it as expected environment limitation and still require `npm run build` to pass.

- [ ] **Step 3: Update history**

Append:

```markdown
- APP-A3 skeleton completed: Capacitor + Vite + TypeScript app created under `my3dgsapp/`; includes pages, service interfaces, Easymap/Cesium placeholder, placement model, viewer link helpers, and copied Easymap runtime assets.
```

- [ ] **Step 4: Commit**

Run:

```powershell
git add history.md my3dgsapp docs/superpowers/plans/2026-06-29-my3dgsapp-capacitor-shell.md
git commit -m "feat: add my3dgsapp capacitor shell"
```

Expected: commit succeeds without adding `.superpowers/`, `node_modules/`, or local IDE files.

## Self-Review

- Spec coverage: covers Capacitor shell, pages, API interfaces, upload interface, job status, Easymap/Cesium placeholder, placement model, viewer links, and skipped native-heavy work.
- Known deferral: native video capture plugin, secure native token implementation, true background upload, API smoke against real Studio server.
- Placeholder scan: no `TBD`, `TODO`, or unspecified implementation step remains.
