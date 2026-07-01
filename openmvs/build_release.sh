#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RELEASE_DIR="$ROOT_DIR/release"
OUT="$RELEASE_DIR/openvms_2026_06_30.tar.gz"

required=(
  api.php
  index.php
  job_view.php
  migrate.php
  README.md
  crontab/1min.sh
  crontab/1_run.php
  crontab/inc/function.php
  scripts/install_openmvs_env.sh
  scripts/install_colmap_cuda.sh
  scripts/run_openmvs_pipeline.sh
  requirements/conda-openmvs.yml
  docs/history.md
  docs/superpowers
)

for path in "${required[@]}"; do
  if [ ! -e "$ROOT_DIR/$path" ]; then
    echo "missing required release path: $path" >&2
    exit 1
  fi
done

mkdir -p "$RELEASE_DIR"
rm -f "$OUT"

tar -C "$ROOT_DIR" \
  --exclude='./.git' \
  --exclude='./uploads' \
  --exclude='./release' \
  --exclude='./wiki_runs' \
  --exclude='./test-results' \
  --exclude='./.pytest_cache' \
  --exclude='*/__pycache__' \
  --exclude='*.pyc' \
  --exclude='*.log' \
  --exclude='*.lock' \
  --transform='s,^\.,openmvs,' \
  -czf "$OUT" .

tar -tzf "$OUT" >/dev/null
chmod 0644 "$OUT"
printf 'built %s\n' "$OUT"
