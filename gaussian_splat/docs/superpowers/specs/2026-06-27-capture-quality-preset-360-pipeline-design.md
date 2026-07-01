# Task -1D+ Capture Quality Preset / 360 Pipeline Preset Design

## Goal

Add the first durable data model for capture conditions before rebuilding the whole platform.

This slice lands in OpenMVS first, but uses shared `capture_*` and `diagnostic_*` names so future Gaussian Splat, VGGT, SuGaR, or other engines can reuse the same concepts.

## Decision

Use option C: OpenMVS first, shared naming.

Reasons:

- It keeps the blast radius small.
- OpenMVS gets useful capture statistics immediately.
- Gaussian Splat keeps its existing `confidence_*` gate fields.
- Future engine contracts can map these fields without renaming OpenMVS-specific columns.

## Scope

Add compact capture summary fields to `openmvs_jobs`.

Recommended fields:

```text
capture_source_type
capture_preset
capture_quality_score
capture_quality_grade
capture_quality_decision
capture_mask_status
capture_frame_count
capture_selected_frame_count
capture_aligned_camera_count
capture_registered_ratio
capture_warning_count
capture_updated_at
```

Normalize OpenMVS diagnostics toward engine-agnostic wording.

Recommended diagnostic fields:

```text
diagnostic_category
diagnostic_code
diagnostic_severity
diagnostic_count
diagnostic_value
diagnostic_message
diagnostic_source
```

## Non-Goals

- Do not migrate Gaussian Splat in this slice.
- Do not merge `confidence_*` into `capture_*`.
- Do not create a shared `reconstruction_jobs` table yet.
- Do not build a dashboard yet.
- Do not support full 360 reconstruction behavior yet.

## Data Meaning

`capture_source_type` describes uploaded source shape:

```text
images
video
360_video
```

`capture_preset` describes intended shooting pattern:

```text
normal_orbit
close_object
indoor_room
360_walkaround
```

`capture_mask_status` describes whether the job has masking support:

```text
none
provided
auto
missing
```

`capture_quality_decision` should stay close to existing confidence gate language:

```text
run
warn
hold
reject
```

The first implementation can derive these values from existing upload metadata, `qa_report.json`, and OpenMVS worker results. If a value is unknown, leave it `NULL` instead of inventing a score.

## Data Flow

1. Upload creates or reuses an OpenMVS job.
2. Job stores source-level defaults:
   - `capture_source_type` from `kind`
   - `capture_preset` from UI/default
   - `capture_mask_status` from `mask_mode`
3. Worker runs the existing OpenMVS pipeline.
4. Worker reads `qa_report.json`.
5. Worker persists compact capture summary fields.
6. Existing diagnostics parser writes normalized diagnostic rows.
7. Admin/index pages show Chinese capture quality labels.

## UI Copy

Use Chinese labels in operator-facing pages.

Suggested labels:

```text
拍攝來源
拍攝模式
遮罩狀態
品質分數
品質等級
品質決策
影像數
選用影像
對齊相機
註冊比例
警示數
更新時間
```

Decision labels:

```text
run    建議執行
warn   可執行但有風險
hold   等待覆核
reject 不建議重建
```

## Error Handling

- Missing `qa_report.json`: keep capture summary nullable and add one warning diagnostic.
- Malformed `qa_report.json`: do not fail a completed job only for summary persistence; record a diagnostic row.
- Unknown preset/source type: store `NULL` or a safe default, not arbitrary free text.
- Division by zero: `capture_registered_ratio` remains `NULL` when frame count is empty.

## Tests

Add the smallest checks that catch schema drift:

- migration text contains all new `capture_*` columns
- migration text contains normalized `diagnostic_*` fields or aliases
- worker asset test verifies `qa_report.json` values are mapped into capture summary fields
- admin/index asset test verifies Chinese labels render
- parser test verifies one OpenMVS log warning becomes a normalized diagnostic row

Suggested focused commands:

```bash
pytest -q tests/test_openmvs_php_assets.py
php tests/openmvs_diagnostics_parser_test.php
php -l migrate.php
php -l crontab/1_run.php
```

Run the OpenMVS commands from `/var/www/html/demo/php/map/3D/openmvs`.

## Done

- OpenMVS job rows can be sorted or filtered by capture quality summary.
- Operator UI shows capture condition fields in Chinese.
- Existing OpenMVS jobs do not break when fields are empty.
- Gaussian Splat behavior is unchanged.
- The naming remains reusable by future engines.

## Spec Self-Review

- No incomplete fields or future-only tables are required.
- The scope is OpenMVS-only for implementation, but names are shared.
- `confidence_*` and `capture_*` are intentionally separate.
- Unknown or missing data is nullable instead of guessed.
