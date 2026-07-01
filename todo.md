# TODO

## 2026-07-01

- [ ] 設定 git remote，然後推送目前本機 commit。
  - current commit: `c6778de Deploy photogrammetry recovery flows`
  - command: `git remote add origin <url>` then `git push -u origin main`
- [ ] OpenMVS worker 加入自動 fallback：`ReconstructMesh` OOM 或 mesh 0 faces 時，直接輸出 point-cloud GLB 並標示為備援完成。
- [ ] OpenMVS #8 若要正式 mesh，改用較低密度或拆 batch；目前 high preset 在 `ReconstructMesh` 會吃滿約 61GB RAM。
- [ ] Gaussian/OpenMVS viewer 加預設展示視角，讓成果一打開就落在好看的角度。
- [ ] 研發 OpenMVS 上傳前處理：AI 人臉模糊、車牌遮蔽、人物移除、主體隔離，可用勾選設定；先確認模型、速度與失敗回復策略後再開 UI。
