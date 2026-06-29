# APP-A1: my3DGSAPP Capture Companion Product Spec

日期：2026-06-29

## 目標

`my3DGSAPP v0.1` 是 3DGS / Photogrammetry Studio 的手機 Capture Companion。

第一版補的是使用者入口，不重做重建核心：

- 手機負責 Easymap + Cesium 工作台、MP4 拍攝/匯入、上傳、建立 QA job、查狀態、開現有 Viewer。
- Server 負責 preflight、QA orchestration、OpenMVS、Gaussian diagnostic、delivery manifest、evidence、viewer。
- v0.1 只支援 QA Scan，不建立 Premium job。

現有參考主線是 `https://3wa.tw/demo/php/map/3D/gaussian_splat/` 的 Photogrammetry Studio：建立專案、上傳 MP4、選模式、job 列表、狀態與檢視入口。

## 技術殼

採用 Capacitor + Vite + TypeScript，WebView-first。

Web layer：

- Easymap + Cesium 作為手機 App 起始工作台。
- Studio job list/status、Delivery Page、Compare Viewer、Three.js / 3DGS Viewer 都走 Web。
- Easymap 依既有 CDN/global SDK 模型載入，不改成 ESM import。

Native bridge：

- Secure token storage。
- MP4 錄影或匯入。
- File URI access。
- Offset-based chunk upload。
- App lifecycle / resume。

不使用 Cordova 開新專案。Cordova plugin 只作最後 fallback。

Easymap runtime 來源：

- `D:\GD\5project\108easymap\code\easymap_official\offical\Easymap`
- 已確認包含 `easymap.js`、`map_ini.js`、`7/`、`MapLibre/`。
- APP-A3 實作時可複製到專案 web assets，例如 `public/vendor/easymap/`，並保持 loader / asset path contract。

## App 畫面

1. Settings
   - 設定 `server_url`。
   - 輸入 Studio Admin 發的 mobile API token。
   - 顯示 token 驗證狀態。

2. Map Home
   - 起始就是 Easymap + Cesium 底圖。
   - 顯示最近 jobs / capture markers。
   - 放錄影 / 匯入 MP4 的主要按鈕。
   - 點 marker 可看狀態與開 Viewer。

3. Capture / Import
   - v0.1a 支援選 MP4 或系統相機錄完後匯入。
   - v0.1b 再補 App 內 native video capture plugin。
   - 顯示拍攝指引：慢速移動、保持穩定、避免過暗/反光/模糊、建議 20-60 秒。

4. Capture Review
   - 播放剛選取或錄製的 MP4。
   - 顯示長度、解析度、fps、檔案大小。
   - 允許重選/重拍、確認上傳。

5. Upload Progress
   - 顯示百分比、已上傳大小、總大小、速度、目前 chunk。
   - 失敗可重試。
   - App 回前景後可查 `upload_status` 續傳。

6. Create QA Job
   - `finalize_upload` 成功後，使用者可確認 title / note。
   - 呼叫 `create_qa_job_from_upload` 建立 pending QA job。

7. Job Status / Result
   - 顯示 pipeline stage、品質/信心、補拍建議。
   - 提供 Delivery Page 與 Compare Viewer 入口。

8. Web Viewer
   - 直接用 WebView 或外部瀏覽器開既有頁面。
   - 入口包含 `delivery.php?job_id=...` 與 `viewer_compare_splat_mesh.html?studio_job_id=...`。

## 使用者流程

```text
Settings 設定 server_url + token
  -> Map Home
  -> 錄影或匯入 MP4
  -> Capture Review
  -> create_upload_session
  -> upload_chunk source.mp4
  -> finalize_upload(metadata)
  -> 使用者確認 title
  -> create_qa_job_from_upload
  -> poll job_detail / my_jobs
  -> marker 顯示狀態
  -> 開 Delivery / Compare Viewer
```

## Auth

v0.1 採 A-light：Studio Admin 產生 mobile API token。

App 設定：

- `server_url`
- `token`

所有 mobile API 都帶：

```http
Authorization: Bearer m3d_xxxxxxxxxxxxxxxxx
X-Device-Id: ios-xxxxx
X-App-Version: 0.1.0
```

Token 儲存：

- `server_url` 與普通 UI preference 可放 Capacitor Preferences。
- API token 不放 localStorage，不放普通 Preferences。
- iOS 使用 Keychain。
- Android 使用 Keystore 或 EncryptedSharedPreferences。
- v0.1 規劃 `SecureToken` interface；native 實作可在 APP-A3/A4 細切。

Token 權限：

- `mobile.upload`
- `mobile.create_qa_job`
- `mobile.read_own_jobs`
- `mobile.read_job_detail`

不允許：

- artifact delete
- retry worker
- recover stuck job
- create premium job
- hard gate override
- public share
- admin list all jobs

Ownership：

- 採 token-scoped ownership。
- `mobile.read_own_jobs` 回傳該 token 建立的 jobs。
- `X-Device-Id` v0.1 只做稽核與 debug，不作權限條件。

## Upload Package

v0.1 採 B-light：單一 MP4 + metadata sidecar。

支援：

- Exactly one `source.mp4`
- Exactly one `capture_metadata.json`
- H.264 preferred
- AAC audio optional
- max size 先由 APP-A2 實作時設定內測值，例如 2GB

不支援：

- photo set
- multiple videos
- ZIP upload
- raw frames
- ARKit pose stream
- LiDAR scan
- Premium upload mode

Server 落檔：

```text
studio/uploads/mobile/{upload_id}/
  source.mp4
  capture_metadata.json
  upload_manifest.json
```

`upload_manifest.json` 由 server 產生：

```json
{
  "schema_version": "1.0",
  "upload_id": "up_abc123",
  "media_type": "video",
  "source_video_path": "source.mp4",
  "capture_metadata_path": "capture_metadata.json",
  "created_at": "2026-06-29T10:00:00+08:00"
}
```

Metadata 不影響 v0.1 worker 決策，也不驅動 hard gate。QA worker input 仍只有 `source.mp4`。

## Capture Metadata Schema

```json
{
  "schema_version": "1.0",
  "app": {
    "name": "my3DGSAPP",
    "version": "0.1.0"
  },
  "device": {
    "platform": "ios",
    "model": "iPhone",
    "os_version": "18.x"
  },
  "capture": {
    "mode": "qa",
    "media_type": "video",
    "duration_sec": 42.5,
    "width": 1920,
    "height": 1080,
    "fps": 30,
    "orientation": "landscape",
    "recorded_at": "2026-06-29T10:00:00+08:00"
  },
  "quality_hints": {
    "blur_warning": false,
    "low_light_warning": false,
    "motion_too_fast_warning": false,
    "too_short_warning": false,
    "coverage_hint": "unknown"
  },
  "notes": {
    "user_title": "test scan",
    "user_note": ""
  }
}
```

Server rules：

- `schema_version` 必須存在。
- `capture.mode` v0.1 必須是 `qa`。
- `capture.media_type` 必須是 `video`。
- 非必要欄位可缺少。
- finalized 後 metadata 不允許任意覆寫。

## Upload API Contract

Endpoint base：

```text
/studio/mobile_api.php
```

### create_upload_session

```http
POST /studio/mobile_api.php?mode=create_upload_session
```

Request：

```json
{
  "file_name": "source.mp4",
  "file_size": 123456789,
  "mime_type": "video/mp4",
  "sha256": "optional"
}
```

Response：

```json
{
  "ok": true,
  "upload_id": "up_abc123",
  "status": "created",
  "chunk_size": 8388608,
  "next_offset": 0
}
```

### upload_chunk

採 offset-based A-light。不要把整支 MP4 轉 base64 或一次丟進 JS bridge。

```http
POST /studio/mobile_api.php?mode=upload_chunk&upload_id=up_abc123&offset=0
Content-Type: application/octet-stream
```

Body 是 binary chunk。

Response：

```json
{
  "ok": true,
  "upload_id": "up_abc123",
  "status": "uploading",
  "received_bytes": 8388608,
  "next_offset": 8388608
}
```

Rules：

- `upload_id` 必須屬於目前 token。
- `offset` 必須等於 server 期待的 `next_offset`，避免錯位寫入。
- chunk size 建議 8MB 或 16MB。
- server 只 append 或寫入已驗證 offset。

### upload_status

```http
GET /studio/mobile_api.php?mode=upload_status&upload_id=up_abc123
```

Response：

```json
{
  "ok": true,
  "upload_id": "up_abc123",
  "status": "uploading",
  "received_bytes": 8388608,
  "next_offset": 8388608,
  "file_size": 123456789
}
```

### finalize_upload

`finalize_upload` 只驗證與封存 upload，不建立 job，不啟動 worker。

```http
POST /studio/mobile_api.php?mode=finalize_upload
```

Request：

```json
{
  "upload_id": "up_abc123",
  "metadata": {
    "schema_version": "1.0",
    "app": {
      "name": "my3DGSAPP",
      "version": "0.1.0"
    },
    "capture": {
      "mode": "qa",
      "media_type": "video",
      "duration_sec": 42.5,
      "width": 1920,
      "height": 1080,
      "fps": 30
    },
    "quality_hints": {
      "blur_warning": false,
      "low_light_warning": false,
      "motion_too_fast_warning": false
    }
  }
}
```

Response：

```json
{
  "ok": true,
  "upload_id": "up_abc123",
  "status": "finalized",
  "upload_manifest_path": "studio/uploads/mobile/up_abc123/upload_manifest.json",
  "next_action": "create_qa_job_from_upload"
}
```

Idempotency：

- 已 finalized 且 metadata 相同時，回 existing finalized 狀態。
- 已 finalized 但 metadata 不同時，回 `upload_already_finalized`。

### create_qa_job_from_upload

```http
POST /studio/mobile_api.php?mode=create_qa_job_from_upload
```

Request：

```json
{
  "upload_id": "up_abc123",
  "title": "My first scan",
  "note": ""
}
```

Response：

```json
{
  "ok": true,
  "upload_id": "up_abc123",
  "studio_job_id": 123,
  "mode": "qa",
  "status": "pending",
  "next_worker": "qa_worker.php"
}
```

Rules：

- upload 必須是 `finalized`。
- v0.1 只能建立 QA job。
- 不啟動 worker。
- 不允許從別人的 token 建 job。
- 同一 `upload_id` 只能建立一個 QA job。

Idempotency：

- 重複呼叫同一 `upload_id` 回既有 `studio_job_id`。
- 不建立第二個 job。

### my_jobs

```http
GET /studio/mobile_api.php?mode=my_jobs
```

Response：

```json
{
  "ok": true,
  "jobs": [
    {
      "studio_job_id": 123,
      "title": "My first scan",
      "mode": "qa",
      "status": "running_openmvs",
      "app_stage": "reconstruction",
      "created_at": "2026-06-29T10:00:00+08:00",
      "marker": {
        "lon": 120.123456,
        "lat": 23.123456
      }
    }
  ]
}
```

### job_detail

```http
GET /studio/mobile_api.php?mode=job_detail&id=123
```

Response：

```json
{
  "ok": true,
  "studio_job_id": 123,
  "mode": "qa",
  "status": "completed",
  "app_stage": "completed",
  "confidence_level": "good",
  "advisory": {
    "needs_recapture": false,
    "messages": []
  },
  "viewer_urls": {
    "delivery": "delivery.php?job_id=123",
    "compare": "viewer_compare_splat_mesh.html?studio_job_id=123"
  },
  "placement": {
    "lon": 120.123456,
    "lat": 23.123456,
    "height_m": 12.5,
    "scale": 1.0,
    "rotation_deg": 0,
    "heading_deg": 0,
    "pitch_deg": 0,
    "roll_deg": 0,
    "source": "server_adjusted",
    "updated_at": "2026-06-29T16:30:00+08:00"
  }
}
```

## Status Mapping

App 不直接暴露過多後台術語。Server raw status 可對應成手機語意：

| Server status | App stage | App label |
| --- | --- | --- |
| `pending` | `pending` | 等待處理 |
| `preflight` | `quality_check` | 品質檢查 |
| `running_openmvs` | `reconstruction` | 3D 重建中 |
| `running_gaussian` | `gaussian_diagnostic` | Gaussian 診斷中 |
| `aggregating` | `delivery_building` | 產生交付結果 |
| `completed` | `completed` | 完成 |
| `partial_failed` | `partial_failed` | 部分完成 |
| `failed` | `failed` | 失敗 |

## Map / Overlay Contract

v0.1 地圖先做 capture/job marker + 開 Viewer。

Required：

- marker 代表 capture/job。
- marker 顯示狀態 badge。
- 點 marker 顯示 title、status、created_at、viewer links。

Optional server placement：

- 若 server 回傳 `placement`，App 展示時可讀取 server placement 放置成果。
- 手機端不負責自動精準地理貼合。
- 後台或 server 修正位置後，App 以 server 回傳為準。

Placement fields：

- `lon`
- `lat`
- `height_m`
- `scale`
- `rotation_deg`
- `heading_deg`
- `pitch_deg`
- `roll_deg`
- `source`
- `updated_at`

Easymap usage：

- 使用 `new Easymap("map")` 建立 map。
- 使用 `dgMarker` 顯示 job marker。
- 使用 `map.addItem(...)` 加入 Easymap object。
- 需要 3D 模式時使用既有 Easymap / Cesium API，不繞過 SDK lifecycle。

## Upload State Machine

```text
created
  -> uploading
  -> finalized
  -> job_created
```

Error states：

- `failed`
- `expired`

v0.1 不做 cancel API。

## Error Handling

Auth：

- token 錯誤回 401。
- token revoked 或權限不足回 403。

Upload：

- offset 不符回 `offset_mismatch` 並附 `next_offset`。
- upload 不屬於 token 回 403。
- upload expired 回 `upload_expired`。
- finalized 後 metadata 不同回 `upload_already_finalized`。

Job：

- upload 未 finalized 回 `upload_not_finalized`。
- 非 QA mode 回 `mode_not_allowed`。
- 重複 create 回既有 job，不視為錯誤。

App：

- 上傳期間提示使用者保持 App 開啟。
- 若中斷，回前景後查 `upload_status` 續傳。
- v0.1 不承諾 app 被 kill 或 iOS 長時間背景仍繼續大檔上傳。

## 分期

APP-A1：本文件，產品與 API spec。

APP-A2：Studio Mobile Upload API。

- mobile token 驗證
- upload session / chunk / status / finalize
- create QA job from upload
- my_jobs / job_detail

APP-A3：Capacitor Shell / Skeleton。

- Capacitor + Vite + TypeScript
- Easymap + Cesium web shell
- SecureToken interface
- mobileApi / uploadClient / jobStatus / placementClient
- v0.1a MP4 import flow

APP-A4：Capture Guidance MVP。

- 過暗、模糊、移動太快、太短等提示
- v0.1b native video capture plugin

APP-A5：Job Status + Viewer Polish。

- marker status
- placement display
- Delivery / Compare Viewer entry

## Skipped

v0.1 明確不做：

- Cordova project
- Ionic UI
- native Cesium
- native 3DGS renderer
- 手機端 OpenMVS
- 手機端 Gaussian 訓練
- Premium job 建立
- public share token
- 正式登入帳號
- 匿名上傳
- 付款 / 訂閱
- 團隊權限
- artifact delete
- worker retry / recover stuck job
- hard gate override
- photo set / ZIP / 多影片
- ARKit full pose stream
- LiDAR scan
- 自動精準地理貼合
- position/rotation/scale 編輯器
- app 被 kill 後仍持續背景上傳

## Acceptance

APP-A1 完成條件：

- v0.1 App 定位清楚：Capture Companion，不是手機重建器。
- 技術殼定案：Capacitor + Vite + TypeScript，WebView-first。
- Auth 定案：Studio mobile API token。
- Upload 定案：offset-based chunk，單一 MP4 + metadata sidecar。
- Job 建立定案：`finalize_upload` 與 `create_qa_job_from_upload` 分兩步。
- Map 定案：Easymap + Cesium marker first，server placement optional。
- Skipped 清單明確，避免 APP-A2/A3 蔓延。
