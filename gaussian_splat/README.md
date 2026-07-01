# Gaussian Splat MVP

This prototype converts MP4 captures into a Nerfstudio Gaussian Splat export and displays the exported `splat.ply` in a browser viewer.

## Local Paths

- Project: `/var/www/html/demo/php/map/3D/gaussian_splat`
- CUDA/Python environment: `/DATA/conda_vm/gs_scene`
- Sample MP4: `/var/www/html/demo/php/map/3D/jpgtoglb/uploads/2/2.mp4`
- Alternate sample MP4: `/var/www/html/demo/php/map/3D/jpgtoglb/uploads/7/7.mp4`

## First Smoke Test

The following commands become runnable after the environment, pipeline scripts, and viewer are created in later tasks.

```bash
bash scripts/install_gs_env.sh
bash scripts/run_mvp_pipeline.sh /var/www/html/demo/php/map/3D/jpgtoglb/uploads/2/2.mp4 uploads/local-smoke
```

Open:

```text
http://localhost/demo/php/map/3D/gaussian_splat/viewer_splat.php?src=uploads/local-smoke/exports/splat.ply
```

## Final Smoke Test

```bash
rm -rf uploads/final-smoke
bash scripts/run_mvp_pipeline.sh /var/www/html/demo/php/map/3D/jpgtoglb/uploads/2/2.mp4 uploads/final-smoke
test -f uploads/final-smoke/exports/splat.ply
python3 -m json.tool uploads/final-smoke/qa_report.json >/dev/null
```

Open:

```text
http://localhost/demo/php/map/3D/gaussian_splat/viewer_splat.php?src=uploads/final-smoke/exports/splat.ply
```

## Cron

Run one queued job:

```bash
php crontab/1_run.php
```

Install one-minute cron:

```bash
*/1 * * * * cd /var/www/html/demo/php/map/3D/gaussian_splat/crontab && ./1min.sh
```
