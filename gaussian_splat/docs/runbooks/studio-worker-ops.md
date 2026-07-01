# Studio Worker Ops Runbook

這份手冊整理 Studio worker 的日常操作與故障排查。目標是讓操作者敢用，不靠直接改 DB 或手動刪檔。

## 架構總覽

Studio 只做 orchestration：

- `studio_jobs` 記錄 Studio pipeline job。
- `studio_engine_runs` 記錄 OpenMVS / Gaussian Splat engine run。
- `qa_worker.php` 建立 OpenMVS `delivery_candidate` 與 Gaussian `diagnostic` run。
- `premium_worker.php` 建立 OpenMVS `delivery_capable` 與 Gaussian `delivery_capable` run。
- OpenMVS / Gaussian 仍由各自既有 queue、DB、worker、lock 負責實際重建。

目前 cron wrapper 只跑 QA worker：

```bash
/var/www/html/demo/php/map/3D/studio/crontab/1min.sh
```

`crontab/1_run.php` 使用 `flock`，同一時間只允許一個 Studio QA worker 執行。Premium worker 目前用手動 CLI 執行。

## Deployment Notes

- Gaussian DB migration 需包含 `pipeline_mode`。若缺欄位，先跑 `php /var/www/html/demo/php/map/3D/gaussian_splat/migrate.php`。
- `studio/jobs` 需允許 `www-data` 寫入，否則 preflight、worker log、manifest 會寫不進去。
- Gaussian crontab runner 需允許 worker 執行：`crontab/` 與 `crontab/inc/` 可進入，`crontab/1_run.php` 與 `crontab/inc/function.php` 可讀。
- Gaussian scripts 需允許 worker 讀取與執行：`scripts/` 至少要讓 `www-data` 可進入，`scripts/*.py` / `scripts/*.sh` 可讀；否則 confidence gate 或 pipeline script 會 permission denied。
- Nerfstudio / gsplat runtime cache 需允許 `www-data` 寫入：`/var/www/.triton`、`/var/www/.cache`。第一次 cu128 / gsplat CUDA extension 可能會在 `/var/www/.cache/torch_extensions/py310_cu128/gsplat_cuda` 編譯，時間可能比短訓練本身更久。
- QA 模式的 Gaussian diagnostic 必須有 training cap。cron worker 預設用 `GS_QA_TRAIN_MAX_ITERATIONS=1000`，可用環境變數覆蓋；`run_mvp_pipeline.sh` 在 `GS_PIPELINE_MODE=qa` 但缺 `GS_TRAIN_MAX_ITERATIONS` 時會拒跑。

## Known-good Smoke Baseline

目前封版基準線：

- Baseline: `studio-qa-full-pass-2026-06-29`
- Studio job: `#10`
- OpenMVS job: `#23`
- Gaussian diagnostic job: `#15`
- Manifest: `studio/jobs/10/delivery_manifest.json`
- Viewer: `/demo/php/map/3D/gaussian_splat/viewer_compare_splat_mesh.html?studio_job_id=10`
- Delivery page: `/demo/php/map/3D/studio/delivery.php?job_id=10`，未登入應回 `302 login`
- QA Gaussian cap: `GS_QA_TRAIN_MAX_ITERATIONS=10`
- 測試基準：`pytest -q` 275 passed，`php -l` OK，`bash -n` OK

搬機或重編 cu128 後，先用這組基準線做 smoke，再開新功能。

## 常用指令

跑一批 QA jobs：

```bash
php /var/www/html/demo/php/map/3D/studio/qa_worker.php --limit=5
```

指定 QA job：

```bash
php /var/www/html/demo/php/map/3D/studio/qa_worker.php --job-id=123
```

跑一批 Premium jobs：

```bash
php /var/www/html/demo/php/map/3D/studio/premium_worker.php --limit=5
```

指定 Premium job：

```bash
php /var/www/html/demo/php/map/3D/studio/premium_worker.php --job-id=123
```

## Log 查看

Studio job detail 會顯示 `worker_log_path`，也會提供「查看 log」連結。

直接開：

```text
/demo/php/map/3D/studio/log.php?job_id=123
```

`log.php` 只顯示最近 200 行 worker log，且需要後台登入。`delivery.php` 不顯示 raw worker log。

## Stuck Recovery

先 dry-run：

```bash
php /var/www/html/demo/php/map/3D/studio/recover_stuck_jobs.php --mode=all --older-than-minutes=180 --limit=20
```

確認候選後才 apply：

```bash
php /var/www/html/demo/php/map/3D/studio/recover_stuck_jobs.php --mode=all --older-than-minutes=180 --limit=20 --apply
```

判斷規則：

- 只處理 `studio_jobs.status = running`。
- 使用 `last_heartbeat_at`，缺值時退回 `work_st_datetime` / `c_datetime`。
- 超過 `--older-than-minutes` 才視為 stuck。
- apply 只把 Studio job 排回 `pending`，不刪 artifacts，不直接跑 engine worker。

檢查 failed / partial_failed：

```bash
php /var/www/html/demo/php/map/3D/studio/recover_stuck_jobs.php --include-failed
```

目前 failed / partial_failed 只輸出 `BLOCKED-RETRY`。原因是既有 worker 會重用第一筆 engine_run；安全重跑需要先定義 engine_run replacement / supersede policy。

## Retention Audit

只產生報表，不刪檔：

```bash
php /var/www/html/demo/php/map/3D/studio/retention_audit.php --older-than-days=30 --limit=50
```

輸出包含：

- `candidate_count`
- `studio_job_id`
- `mode`
- `status`
- `finished_at`
- `delivery_manifest_path`
- `engine_run_count`

目前 retention audit 是 dry-run only。artifact delete 需要先決定保留天數、交付物是否可刪、是否需要還原、誰有權限刪。

## 常見故障排查

### pending 太久

先確認 cron：

```bash
php /var/www/html/demo/php/map/3D/studio/crontab/1_run.php
```

再指定 job 跑 worker：

```bash
php /var/www/html/demo/php/map/3D/studio/qa_worker.php --job-id=123
```

Premium job 需手動：

```bash
php /var/www/html/demo/php/map/3D/studio/premium_worker.php --job-id=123
```

### running 太久

看 job detail 的 `last_heartbeat_at` 與 `worker_log_path`。

dry-run stuck recovery：

```bash
php /var/www/html/demo/php/map/3D/studio/recover_stuck_jobs.php --older-than-minutes=180
```

### engine_run failed

先看 engine run 的：

- `engine_name`
- `role`
- `status`
- `last_error`
- `error_summary_path`
- `external_table`
- `external_job_id`

不要直接改 `studio_engine_runs.status` 當 retry。先到 OpenMVS / Gaussian 原本後台確認底層 job 狀態。

### delivery_manifest_path 缺失

常見原因：

- engine_runs 還沒 terminal。
- QA / Premium worker 還沒重新跑到 aggregation 階段。
- 某個 engine run failed，job 進 `failed` / `partial_failed`。

處理方式：

```bash
php /var/www/html/demo/php/map/3D/studio/qa_worker.php --job-id=123
php /var/www/html/demo/php/map/3D/studio/premium_worker.php --job-id=123
```

### Viewer HTTP 404

先用 Studio delivery manifest 檢查 artifact path：

```bash
python3 /var/www/html/demo/php/map/3D/gaussian_splat/scripts/studio_e2e_smoke.py --job-id=123
```

若 manifest 存在但 artifact 404，回到對應 engine job 檢查 exports 是否存在。

### evidence not_available

這是允許狀態，不等於重建失敗。Evidence 需要 `evidence_manifest_path`、camera evidence、spatial index、LOD sparse points。缺 evidence 時 viewer 應顯示 not available，不應白畫面。

## 明確禁止

- 不手動刪 artifacts。
- 不直接改 DB status 當 retry。
- 不繞過 Studio worker 直接把 OpenMVS / Gaussian 結果塞成 completed。
- 不從 Studio worker 直接呼叫 OpenMVS / Gaussian 底層 pipeline script。
- 不把 `delivery.php` 改成公開分享入口；公開 token / 權限另開任務。
