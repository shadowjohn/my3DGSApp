# Gaussian Splat vs Mesh Extraction 實作驗證計畫

## 目標

用同一組資料建立兩種成果：

```text
同一個花園桌子資料
 ↓
A. Gaussian Splat Viewer
B. Mesh Extraction → GLB Viewer
 ↓
並排比較
```

目的不是證明誰比較好，而是確認：

```text
Gaussian Splat 適合什麼
Mesh / GLB 適合什麼
未來工程平台該怎麼定位
```

---

## 結論假設

預期結果：

```text
Gaussian Splat：
視覺真實感較好，適合現況照片層、快速 Reality Layer。

Mesh / GLB：
幾何結構較明確，適合量測、碰撞、Cesium / BIM / 3D Tiles 管線。
```

---

## Phase 0：輸入資料

使用同一筆已跑過的花園桌子資料：

```text
gardenvase_720.mp4
```

或使用已完成的 job：

```text
uploads/7/
```

預期已存在：

```text
uploads/7/
 ├─ images/
 ├─ processed/
 ├─ outputs/
 └─ exports/
     ├─ splat.ply
     └─ splat.clean.ply
```

如果已經有 Nerfstudio 訓練 config，記下：

```text
uploads/7/outputs/processed/splatfacto/<run_id>/config.yml
```

---

## Phase 1：建立比較資料夾

新增：

```text
uploads/7/compare/
 ├─ splat/
 │   ├─ splat.ply
 │   ├─ splat.clean.ply
 │   └─ viewer.json
 ├─ mesh/
 │   ├─ raw_mesh.ply
 │   ├─ cleaned_mesh.obj
 │   ├─ cleaned_mesh.glb
 │   └─ mesh_report.json
 ├─ screenshots/
 │   ├─ splat_fixed_pose.png
 │   ├─ mesh_fixed_pose.png
 │   └─ side_by_side.png
 └─ verdict.md
```

---

## Phase 2：Gaussian Splat 基準組

### 使用既有輸出

```text
uploads/7/exports/splat.clean.ply
```

建立 viewer link：

```text
viewer_splat.html?src=uploads/7/exports/splat.clean.ply
```

固定 viewer 參數：

```text
rx=0
ry=0
rz=0
up=view
distance=12
alpha=40
splatScale=0.25
```

若花園桌子需要不同大小，可測：

```text
splatScale=0.25
splatScale=0.35
splatScale=0.45
```

記錄最佳參數到：

```json
{
  "type": "gaussian_splat",
  "src": "uploads/7/exports/splat.clean.ply",
  "rx": 0,
  "ry": 0,
  "rz": 0,
  "up": "view",
  "distance": 12,
  "alpha": 40,
  "splatScale": 0.35
}
```

---

## Phase 3：Mesh Extraction 路線 A：Nerfstudio 匯出 Poisson Mesh

如果目前已有 Nerfstudio config：

```bash
ns-export poisson \
  --load-config uploads/7/outputs/processed/splatfacto/<run_id>/config.yml \
  --output-dir uploads/7/compare/mesh/poisson
```

預期產出可能包含：

```text
mesh.ply
```

如果 `splatfacto` config 無法直接匯出 poisson，改用 Phase 4 的點雲轉 mesh 路線。

---

## Phase 4：Mesh Extraction 路線 B：Point Cloud / PLY 轉 Mesh

若已有 splat PLY，可以先嘗試萃取點雲：

```text
splat.clean.ply
 ↓
取 x,y,z,r,g,b
 ↓
point_cloud.ply
 ↓
Open3D / MeshLab / Blender
 ↓
mesh
```

### Python / Open3D 初版腳本

新增：

```text
scripts/splat_to_pointcloud.py
```

功能：

```text
1. 讀取 splat.clean.ply
2. 只保留 x,y,z,r,g,b
3. 移除 opacity 過低點
4. 移除 scale 過大點
5. 輸出 point_cloud.ply
```

執行：

```bash
python scripts/splat_to_pointcloud.py \
  --input uploads/7/exports/splat.clean.ply \
  --output uploads/7/compare/mesh/point_cloud.ply
```

---

## Phase 5：Open3D Poisson Reconstruction

新增：

```text
scripts/pointcloud_to_mesh.py
```

流程：

```text
point_cloud.ply
 ↓
estimate_normals
 ↓
poisson reconstruction
 ↓
crop bbox
 ↓
remove low density vertices
 ↓
mesh.ply
```

執行：

```bash
python scripts/pointcloud_to_mesh.py \
  --input uploads/7/compare/mesh/point_cloud.ply \
  --output uploads/7/compare/mesh/raw_mesh.ply \
  --depth 9
```

建議參數：

```text
preview:
depth=7

normal:
depth=8~9

high:
depth=10
```

---

## Phase 6：Blender 自動清理與 GLB 匯出

新增：

```text
scripts/blender_mesh_cleanup.py
```

功能：

```text
1. 匯入 raw_mesh.ply
2. 移除孤立小碎片
3. Decimate 降面數
4. Smooth shading
5. Optional: 補材質
6. 匯出 cleaned_mesh.glb
```

執行：

```bash
blender -b --python scripts/blender_mesh_cleanup.py -- \
  --input uploads/7/compare/mesh/raw_mesh.ply \
  --output uploads/7/compare/mesh/cleaned_mesh.glb \
  --target_faces 100000
```

第一版目標：

```text
100k faces 以下
檔案 30MB 以下
Three.js 可順暢載入
```

---

## Phase 7：建立 Mesh Viewer

新增：

```text
viewer_mesh.html
```

功能：

```text
1. 載入 cleaned_mesh.glb
2. OrbitControls
3. 固定 camera pose
4. 顯示 triangle count
5. 顯示檔案大小
6. 支援 wireframe 開關
7. 支援 opacity
```

Viewer link：

```text
viewer_mesh.html?src=uploads/7/compare/mesh/cleaned_mesh.glb
```

---

## Phase 8：並排比較 Viewer

新增：

```text
viewer_compare_splat_mesh.html
```

版面：

```text
左：Gaussian Splat
右：GLB Mesh
```

或三欄：

```text
左：raw splat
中：clean splat
右：mesh glb
```

固定同樣視角：

```text
distance
heading
pitch
target
```

UI 顯示：

```text
Gaussian Splat:
- splat count
- file size
- visual notes

Mesh:
- vertex count
- face count
- file size
- visual notes
```

---

## Phase 9：評估標準

建立：

```text
uploads/7/compare/verdict.md
```

內容：

```markdown
# Gaussian Splat vs Mesh Verdict

## Input

- Source: gardenvase_720.mp4
- Job: uploads/7
- Date:

## Numeric Summary

| Variant | File | Size | Count | Load Time | Notes |
| --- | --- | ---: | ---: | ---: | --- |
| Clean Splat | splat.clean.ply | | splats | | |
| Mesh GLB | cleaned_mesh.glb | | triangles | | |

## Visual Verdict

| Criterion | Gaussian Splat | Mesh GLB |
| --- | --- | --- |
| Photo realism | | |
| Geometry clarity | | |
| Close-view stability | | |
| Artifact amount | | |
| File size | | |
| Load speed | | |
| WebGIS suitability | | |
| Engineering usefulness | | |

## Conclusion

Gaussian Splat is better for:

-

Mesh / GLB is better for:

-

Recommended product usage:

-
```

---

## Phase 10：預期結果判讀

### 如果 Gaussian 勝出

代表：

```text
Reality Layer 方向正確
Mesh extraction 暫緩
```

後續優先：

```text
PLY → KSPLAT / SPZ
Artifact Cleaner v2
Viewer loading optimization
```

### 如果 Mesh 勝出

代表：

```text
GLB/3D Tiles 管線可接現場照片重建
```

後續優先：

```text
Mesh cleanup
Texture baking
3D Tiles export
Cesium integration
```

### 如果兩者都不理想

代表：

```text
輸入資料品質不足
或
花園植被不適合
```

下一步換資料：

```text
靜態建築
橋墩
牆面
機房
設備間
```

---

## Phase 11：工程平台定位建議

不要把兩者視為互斥。

建議平台長期架構：

```text
BIM / IFC / GLB / 3D Tiles
= Design Layer / Engineering Layer

Gaussian Splat
= Reality Layer / Site Photo Layer

Mesh Extraction
= Optional Bridge Layer
```

Cesium / Easymap 上可做：

```text
Layer 1: 地圖
Layer 2: BIM / GLB / 3D Tiles
Layer 3: Gaussian Reality Layer
Layer 4: Extracted Mesh
```

---

## Phase 12：MVP 驗收標準

完成條件：

```text
1. 同一筆資料可產出 clean splat
2. 同一筆資料可產出 mesh glb
3. 兩者可在 viewer 中載入
4. 可固定同一視角截圖
5. 可產生 side-by-side comparison
6. verdict.md 有人工結論
```

---

## 建議 Commit 拆分

### Commit 1：Mesh extraction pipeline

```text
feat(gaussian): add mesh extraction comparison pipeline
```

包含：

```text
scripts/splat_to_pointcloud.py
scripts/pointcloud_to_mesh.py
scripts/blender_mesh_cleanup.py
```

### Commit 2：Comparison viewer

```text
feat(viewer): add splat mesh comparison viewer
```

包含：

```text
viewer_mesh.html
viewer_compare_splat_mesh.html
```

### Commit 3：Docs

```text
docs(gaussian): add splat versus mesh extraction plan
```

包含：

```text
docs/gaussian-splat-vs-mesh-extraction-plan.md
```

---

## 注意事項

第一版不要期待 mesh 很漂亮。

從 Gaussian Splat 轉 Mesh 常見問題：

```text
1. 表面糊
2. 草葉變成牆
3. 漂浮點變成破片
4. 色彩貼圖不完整
5. 孔洞很多
```

所以這次驗證重點不是「做出完美 Mesh」，而是判斷：

```text
這條路線是否值得變成產品功能
```
