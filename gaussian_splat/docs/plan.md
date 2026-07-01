# 工程現場 Gaussian Splat 數位分身實作路線

## 目標

建立一條從手機拍攝到 WebGIS/3D 場景展示的流程：

```text
手機錄影 / 拍照
 ↓
抽幀
 ↓
COLMAP 相機定位
 ↓
Nerfstudio / gsplat 訓練 Gaussian Splat
 ↓
匯出 .ply / .splat / .ksplat / spz
 ↓
Three.js Viewer
 ↓
整合 Easymap / Cesium / MapLibre 場景
```

第一階段目標不是取代 BIM 或 CAD，而是建立「工程現場快速視覺紀錄」。

---

## 適用情境

適合：

* 工地現況掃描
* 橋梁、道路、邊坡、建物外觀紀錄
* 施工前 / 施工中 / 施工後對照
* 搭配 BIM / IFC / 3D Tiles 做現況疊合
* 工程版 Google Street View
* 巡檢紀錄平台

不適合第一版就做：

* 精準量測
* CAD 級拓樸
* 可編輯 Mesh
* 管線級碰撞檢查
* 法規級竣工模型

---

## Phase 0：技術驗證

### 目標

先在本機跑通完整流程。

### 輸入

使用手機拍攝一段 20～60 秒影片。

拍攝原則：

* 慢慢移動
* 不要只原地旋轉
* 要有左右位移
* 避免大面積純白牆、玻璃、反光、水面
* 光線穩定
* 盡量不要有人車大量穿越

### 建議測試場景

```text
小場景：
辦公室桌面、機車、樓梯口

中場景：
工地入口、橋墩旁、道路施工區

大場景：
橋面、河岸、建築外牆
```

---

## Phase 1：環境建立

### Linux / Ubuntu 建議

```bash
conda create -p /park/conda_vm/gs_scene python=3.10 -y
conda activate /park/conda_vm/gs_scene
```

安裝核心工具：

```bash
pip install nerfstudio
pip install gsplat
```

安裝 COLMAP：

```bash
sudo apt update
sudo apt install colmap ffmpeg -y
```

確認 GPU：

```bash
nvidia-smi
python -c "import torch; print(torch.cuda.is_available())"
```

---

## Phase 2：影片抽幀

### 目標

把手機影片轉成照片序列。

```bash
mkdir -p data/site001/images
ffmpeg -i input.mp4 -vf fps=2 data/site001/images/frame_%05d.jpg
```

建議：

```text
20 秒影片：fps=2，大約 40 張
60 秒影片：fps=2，大約 120 張
大場景：fps=1～2
小物件：fps=3～5
```

照片太少會失敗，照片太多會變慢。

---

## Phase 3：Nerfstudio 資料處理

### 使用 COLMAP 建立相機位置

```bash
ns-process-data images \
  --data data/site001/images \
  --output-dir data/site001_processed
```

輸出重點：

```text
data/site001_processed/
 ├─ images/
 ├─ transforms.json
 └─ colmap/
```

成功條件：

* COLMAP 有算出相機位置
* transforms.json 存在
* viewer 可看到相機路徑

失敗常見原因：

```text
1. 原地旋轉，沒有視差
2. 照片太模糊
3. 反光太多
4. 場景太空
5. 夜間雜訊太多
6. 人車移動太多
```

---

## Phase 4：訓練 Gaussian Splat

### 使用 splatfacto

```bash
ns-train splatfacto \
  --data data/site001_processed
```

訓練完成後會產生：

```text
outputs/
 └─ site001_processed/
     └─ splatfacto/
         └─ 日期時間/
             └─ config.yml
```

---

## Phase 5：匯出 Splat

```bash
ns-export gaussian-splat \
  --load-config outputs/site001_processed/splatfacto/日期時間/config.yml \
  --output-dir exports/site001_splat
```

預期輸出：

```text
exports/site001_splat/
 └─ splat.ply
```

第一版先保留 `.ply`。

後續再研究轉成：

```text
.splat
.ksplat
.spz
3D Tiles Gaussian Splat
```

---

## Phase 6：Three.js Viewer MVP

### 目標

先不要急著進 Cesium。

先做一個獨立頁面：

```text
viewer_splat.html
```

功能：

* 載入 splat.ply
* OrbitControls
* 顯示 FPS
* 顯示檔案大小
* 顯示相機位置
* 支援透明背景
* 支援和 GLB 同場景顯示

### Viewer 技術選擇

第一版可選：

```text
GaussianSplats3D
```

或：

```text
Spark.js
```

建議先試 GaussianSplats3D，因為案例多。

---

## Phase 7：接 Easymap / MapLibre / Three.js

### 目標

建立一個新的 Layer 類型：

```javascript
new dgGaussianSplat({
    url: "exports/site001_splat/splat.ply",
    position: [lng, lat, height],
    rotation: [0, 0, 0],
    scale: 1.0
});
```

### 第一版參數

```javascript
{
    url: "",
    lng: 121.0,
    lat: 25.0,
    height: 0,
    heading: 0,
    pitch: 0,
    roll: 0,
    scale: 1,
    visible: true,
    opacity: 1
}
```

### Easymap 整合方向

```text
MapLibre 底圖
 ↓
Three.js custom layer
 ↓
Gaussian Splat renderer
 ↓
GLB / BIM / IFC 模型同場景
```

---

## Phase 8：地理定位與貼合

Gaussian Splat 本身不會知道真實座標。

所以需要做一份定位設定檔：

```json
{
  "job_id": "site001",
  "source_type": "gaussian_splat",
  "origin": {
    "lng": 121.456,
    "lat": 25.123,
    "height": 12.5
  },
  "transform": {
    "heading": 35.0,
    "pitch": 0.0,
    "roll": 0.0,
    "scale": 1.0
  },
  "quality": {
    "frames": 120,
    "registered_frames": 95,
    "train_steps": 30000
  }
}
```

第一版人工貼合即可：

* 拖曳位置
* 旋轉 heading
* 調整 scale
* 調整 height
* 儲存 transform.json

---

## Phase 9：Cesium 整合策略

Cesium 有兩條路：

### 路線 A：Cesium + Three.js 混合

短期推薦。

```text
Cesium Viewer
 ↓
同步 Camera Matrix
 ↓
Three.js Overlay
 ↓
Gaussian Splat
```

優點：

* 可控
* 不等 Cesium 官方格式成熟
* 可以沿用現有 Three.js Splat viewer

缺點：

* camera sync 較麻煩
* depth occlusion 要另外處理

### 路線 B：3D Tiles Gaussian Splat

中長期推薦。

```text
Gaussian Splat
 ↓
3D Tiles Gaussian Splat
 ↓
CesiumJS 原生載入
```

優點：

* Cesium 原生串流
* 適合大場景
* 可做 LOD

缺點：

* 格式仍在快速變動
* 工具鏈還需要觀察

第一版先走路線 A。

---

## Phase 10：後端 Job 流程

### 資料表草案

```sql
CREATE TABLE PhotoSceneJob (
    SN INT IDENTITY(1,1) PRIMARY KEY,
    JobId NVARCHAR(50) NOT NULL,
    Title NVARCHAR(200),
    SourceType NVARCHAR(50),
    Status NVARCHAR(50),
    InputVideoPath NVARCHAR(500),
    ImageFolder NVARCHAR(500),
    ProcessedFolder NVARCHAR(500),
    OutputFolder NVARCHAR(500),
    SplatPath NVARCHAR(500),
    TransformJsonPath NVARCHAR(500),
    FrameCount INT,
    RegisteredFrameCount INT,
    ErrorMessage NVARCHAR(MAX),
    CreateTime DATETIME2 DEFAULT SYSDATETIME(),
    UpdateTime DATETIME2
);
```

### Job 狀態

```text
uploaded
extracting_frames
processing_colmap
training
exporting
ready
failed
```

---

## Phase 11：Web UI

### 頁面一：上傳任務

```text
photo_scene_upload.php
```

功能：

* 上傳影片
* 輸入場景名稱
* 選擇場景類型
* 選擇大約座標
* 建立 job

### 頁面二：任務詳情

```text
photo_scene_job_detail.php
```

顯示：

* 狀態
* 影片
* 抽幀數
* COLMAP 成功率
* 訓練時間
* 輸出檔案
* Viewer 連結

### 頁面三：貼合工具

```text
photo_scene_align_viewer.php
```

功能：

* 地圖上顯示 Splat
* 拖曳位置
* 旋轉
* 縮放
* 調高度
* 儲存 transform

---

## Phase 12：品質檢查

### 建議輸出 QA Report

```json
{
  "job_id": "site001",
  "frame_count": 120,
  "registered_frame_count": 95,
  "registered_ratio": 0.79,
  "splat_file_size_mb": 350,
  "has_transform": true,
  "viewer_ready": true,
  "warnings": [
    "registered_ratio lower than 0.8",
    "splat file larger than 300MB"
  ]
}
```

### 判斷規則

```text
registered_ratio >= 0.8：良好
registered_ratio 0.5~0.8：可用但可能破
registered_ratio < 0.5：建議重拍
```

---

## Phase 13：第一版目錄結構

```text
photo_scene/
 ├─ jobs/
 │   └─ site001/
 │       ├─ input/
 │       │   └─ input.mp4
 │       ├─ images/
 │       ├─ processed/
 │       ├─ outputs/
 │       ├─ exports/
 │       │   └─ splat.ply
 │       ├─ transform.json
 │       └─ qa_report.json
 ├─ scripts/
 │   ├─ extract_frames.py
 │   ├─ process_colmap.sh
 │   ├─ train_splat.sh
 │   ├─ export_splat.sh
 │   └─ build_qa_report.py
 ├─ web/
 │   ├─ photo_scene_upload.php
 │   ├─ photo_scene_job_detail.php
 │   ├─ photo_scene_viewer.php
 │   └─ photo_scene_align_viewer.php
 └─ viewers/
     └─ gaussian_splat_layer.js
```

---

## Phase 14：MVP 驗收標準

### MVP 完成條件

```text
1. 手機影片可上傳
2. 系統可自動抽幀
3. COLMAP 可產 transforms.json
4. Nerfstudio 可訓練 splatfacto
5. 可匯出 splat.ply
6. Three.js 可載入顯示
7. 可手動貼到地圖座標
8. 可儲存 transform.json
9. 可再次開啟並還原位置
```

---

## Phase 15：後續升級

### v1.1 壓縮與網頁效能

* `.ply` 轉 `.splat`
* `.splat` 轉 `.ksplat`
* 嘗試 `.spz`
* 加 progressive loading
* 加 LOD
* 加 crop tool

### v1.2 時間軸

```text
同一地點：
2026-06-01
2026-06-15
2026-07-01
```

可做：

* 施工前後比較
* slider 切換
* 半透明疊合
* 分期紀錄

### v1.3 BIM 對齊

```text
IFC / GLB / 3D Tiles
+
Gaussian Splat 現況
```

用途：

* 設計 vs 現況
* 施工偏差觀察
* 工地巡檢
* 現況留存

### v1.4 App 化

手機 App 功能：

* 拍攝導引
* 自動提示移動方向
* 上傳影片
* 記錄 GPS
* 記錄 IMU
* 顯示任務狀態
* 回看成果

---

## 建議優先順序

第一週：

```text
1. 本機跑通 Nerfstudio splatfacto
2. 影片抽幀
3. 匯出 splat.ply
4. Three.js Viewer 顯示
```

第二週：

```text
1. 做 PHP Job 流程
2. 做任務資料夾
3. 做狀態頁
4. 做 QA Report
```

第三週：

```text
1. 接 Easymap / MapLibre / Three.js
2. 做人工貼合工具
3. 儲存 transform.json
```

第四週：

```text
1. 與 GLB / BIM 同場景
2. 測試橋梁 / 工地 / 道路場景
3. 評估 Cesium 3D Tiles Gaussian Splat
```

---

## 結論

這條路線不應該定位成「照片轉 CAD」。

它應該定位成：

```text
工程現場快速數位分身
```

核心價值是：

```text
拍一圈
 ↓
自動重建
 ↓
WebGIS 上看現況
 ↓
跟 BIM / 3D Tiles / 地圖疊合
```

短期先走：

```text
Nerfstudio + splatfacto + Three.js
```

中期接：

```text
Easymap / MapLibre / Cesium overlay
```

長期再走：

```text
3D Tiles Gaussian Splat + LOD + 時間軸
```
