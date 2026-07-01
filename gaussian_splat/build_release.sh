#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NAME="${1:-gaussian_splat_2026_06_30.tar.gz}"
OUT_DIR="$ROOT/release"
OUT="$OUT_DIR/$NAME"
TMP="$OUT.tmp"

mkdir -p "$OUT_DIR"
rm -f "$OUT" "$TMP"

tar -C "$ROOT/.." -czf "$TMP" \
  --exclude='gaussian_splat/.git' \
  --exclude='gaussian_splat/upload' \
  --exclude='gaussian_splat/uploads' \
  --exclude='gaussian_splat/release' \
  --exclude='gaussian_splat/data' \
  --exclude='gaussian_splat/downloads' \
  --exclude='gaussian_splat/external' \
  --exclude='gaussian_splat/output' \
  --exclude='gaussian_splat/outputs' \
  --exclude='gaussian_splat/.pytest_cache' \
  --exclude='gaussian_splat/.playwright-cli' \
  --exclude='gaussian_splat/**/__pycache__' \
  --exclude='gaussian_splat/*.pyc' \
  --exclude='gaussian_splat/*.log' \
  --exclude='gaussian_splat/crontab/*.lock' \
  gaussian_splat

mv "$TMP" "$OUT"
tar -tzf "$OUT" >/dev/null

printf 'release: %s\n' "$OUT"
du -h "$OUT"
