# history

## 2026-06-29

- 工作區 `D:\mytools\my3DGSApp` 目前只有 `.git`，尚未有專案檔案或初始 commit。
- `origin/main` 顯示已不存在或未連上有效遠端分支。
- APP-A1 方向確認：`my3DGSAPP v0.1` 做手機 Capture Companion，不做手機端重建或原生 Viewer。
- v0.1 只支援 QA Scan；手機負責拍攝、上傳、建立 QA job、查狀態、開現有 Delivery / Compare Viewer。
- Auth 決策：採 A-light，Studio Admin 發 mobile API token；App 設定 `server_url` + token，所有 mobile API 帶 `Authorization: Bearer <token>`、`X-Device-Id`、`X-App-Version`。
- v0.1 token 權限只含 `mobile.upload`、`mobile.create_qa_job`、`mobile.read_own_jobs`、`mobile.read_job_detail`；不允許 delete、premium、worker retry、hard gate override、public share、admin list all jobs。
- Job ownership 決策：採 token-scoped ownership；`mobile.read_own_jobs` 回傳該 token 建立的 jobs，`X-Device-Id` 第一版只做稽核與 debug，不作權限條件。
- Upload format 決策：採 B-light，v0.1 上傳 package 是單一 `source.mp4` + `capture_metadata.json`；reconstruction input 仍只吃 MP4，metadata 作為 sidecar 保存、preflight 輔助與後續分析，不影響 worker 決策或 hard gate。
- v0.1 不支援 photo set、多影片、ZIP、raw frames、ARKit pose stream、LiDAR scan、Premium upload mode。
- `finalize_upload` 後 server 產生 `upload_manifest.json`，建議落在 `studio/uploads/mobile/{upload_id}/`，包含 `source.mp4`、`capture_metadata.json`、`upload_manifest.json`。
- API boundary 決策：採 two-step flow，`finalize_upload` 只驗證與封存 upload，不建立 job、不啟動 worker；App 之後呼叫 `create_qa_job_from_upload` 才建立 pending QA job。
- `upload_session.status` 建議：`created` -> `uploading` -> `finalized` -> `job_created`，錯誤狀態先保留 `failed`、`expired`。
- Idempotency 決策：重複 `finalize_upload` 回既有 finalized 狀態；若 metadata 不同則拒絕。重複 `create_qa_job_from_upload(upload_id)` 回既有 `studio_job_id`，同一 upload 只能建立一個 QA job。
- UI shell 調整：使用者希望手機 App 起始畫面就是 Easymap + Cesium 底圖，上面放錄影按鈕與 MP4 建模拍攝指引；錄影後走 offset-based upload，顯示進度並追蹤轉檔/job 狀態。
- Viewer/overlay 方向：最終可在 Easymap + Cesium 3D 看到影像/成果套疊，也可用 Three.js 看 3DGS 套疊；v0.1 應先以 WebView/既有 Web viewer 重用為主，不重做原生 renderer。
- Easymap 最新來源確認存在：`D:\GD\5project\108easymap\code\easymap_official\offical\Easymap`，包含 `easymap.js`、`map_ini.js`、`7/`、`MapLibre/`。
- Map overlay 決策：v0.1 先做 capture/job marker + 開 Viewer；若 server 後續提供 placement，展示時需讀取 server 端放置座標、scale、旋轉角度與高度，不由手機端自動精準定位。
- Placement contract 預留欄位：`lon`、`lat`、`height_m`、`scale`、`rotation_deg` 或 `heading/pitch/roll`、`source`、`updated_at`，由 `job_detail` 或 delivery manifest 回傳。
- Tech shell 決策：採 Capacitor + Vite + TypeScript，不用 Cordova 開新專案；Cordova plugin 只作最後 fallback。
- App 架構決策：WebView-first，Easymap / Cesium / Three.js / Studio UI / Delivery / Compare Viewer 都走 Web；native bridge 只負責 secure token storage、video capture/import、file access、chunk upload、app lifecycle。
- Token 儲存決策：`server_url` 等 UI preference 可放 Capacitor Preferences；API token 不放 localStorage/普通 Preferences，使用 iOS Keychain、Android Keystore 或 EncryptedSharedPreferences，先以 tiny `SecureToken` native plugin/interface 規劃。
- Capture 決策：v0.1a 先支援選 MP4 或系統相機錄完匯入；v0.1b 再補 App 內 native video capture plugin。v0.1 不把完整錄影 UI 當 blocker。
- Upload 決策：採 offset-based chunk upload A-light，避免整支 MP4 經 JS bridge/base64；支援前景上傳、進度條、App 回前景後 resume，不承諾 app 被 kill 或長時間背景仍持續上傳。
- APP-A1 spec 已建立：`docs/superpowers/specs/2026-06-29-my3dgsapp-capture-companion-design.md`。下一步等待 review，核准後進 APP-A2/API 或 APP-A3/Capacitor skeleton。
