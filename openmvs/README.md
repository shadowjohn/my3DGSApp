# OpenMVS Upload Queue

This app accepts MP4 videos or image ZIP packages, queues a background conversion job, and exports a browser-viewable GLB through COLMAP + OpenMVS.

## Migration

```bash
php migrate.php
```

## Cron

```bash
*/1 * * * * cd /var/www/html/demo/php/map/3D/openmvs/crontab && ./1min.sh
```

## Environment

The pipeline defaults to `/DATA/conda_vm/openmvs`:

```bash
bash scripts/install_openmvs_env.sh
```

If OpenMVS is installed elsewhere:

```bash
OPENMVS_BIN_DIR=/path/to/openmvs/bin php crontab/1_run.php
```

The install helper does not store sudo credentials.

## GPU selection

COLMAP defaults to `COLMAP_GPU_MODE=auto`. Before each conversion, the
pipeline prefers CUDA 12.8 (`OVM_PREFERRED_CUDA_VERSION=12.8`), checks
`/usr/local/cuda-12.8`, `/DATA/conda_vm/gs_scene`, then `/usr/local/cuda`,
and runs a small COLMAP GPU probe. If the probe or the real COLMAP GPU stage
fails, the job falls back to CPU and continues.

Useful overrides:

```bash
COLMAP_GPU_MODE=cpu php crontab/1_run.php
COLMAP_GPU_MODE=gpu OVM_CUDA_ROOT=/DATA/conda_vm/gs_scene php crontab/1_run.php
```

OpenMVS GPU support depends on how OpenMVS was compiled. The install helper now
defaults to `OpenMVS_USE_CUDA=ON` and prefers CUDA 12.8, but an existing
CPU-only OpenMVS build must be rebuilt before OpenMVS stages can use CUDA.
