# History

## 2026-07-01

- 建立本機版控 baseline 後，完成 OpenMVS / Gaussian Splat 轉檔流程修補與救援。
- OpenMVS / Gaussian 目前狀態已確認：
  - OpenMVS: `failed=0`, `pending=0`, `active=0`, `total=8`
  - Gaussian Splat: `failed=0`, `pending=0`, `active=0`, `total=7`
- OpenMVS #7 救援：
  - 原因：dense fusion 產出 0 points / mesh 0 faces。
  - 處理：用 `scene.mvs` 匯出 sparse point-cloud GLB。
  - 結果：`10,348 points`, `exports/model.glb`, status=2 `已完成（稀疏點雲備援）`。
- OpenMVS #8 救援：
  - 原因：`ReconstructMesh` 建出約 1.10M faces 後 RAM 打滿，`std::bad_alloc`。
  - 處理：用 `scene_dense.mvs + scene_dense.ply` 匯出 dense point-cloud GLB。
  - 結果：`795,431 points`, GLB `20.48 MB`, status=2 `已完成（密集點雲備援）`。
- Gaussian Splat #7 已由 checkpoint 備援恢復完成，viewer 實測展示效果可用。
- 驗證：
  - `git diff --check`
  - `/DATA/conda_vm/openmvs/bin/python3 -m pytest ...`
  - 結果：`69 passed, 1 warning`
- 已建立本機 commit：
  - `c6778de Deploy photogrammetry recovery flows`
- `git push` 嘗試失敗，原因是尚未設定 remote：
  - `fatal: No configured push destination.`
