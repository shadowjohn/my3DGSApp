#!/usr/bin/env python3
"""Backfill standard OpenMVS contract artifacts for existing uploads."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from build_delivery_manifest import build_delivery_manifest
from build_engine_contract import build_engine_contract
from build_failure_summary import build_failure_documents, write_json
from build_validation_report import build_validation_report


TIMING_RE = re.compile(r"^\[timing\] START ([A-Za-z0-9_-]+)")


def last_stage_and_reason(job_dir: Path) -> tuple[str, str]:
    log = job_dir / "logs" / "openmvs_pipeline.log"
    if not log.is_file():
        log = job_dir / "process.log"
    stage = "unknown"
    reason = "OpenMVS job failed before qa_report.json"
    if not log.is_file():
        return stage, reason
    for line in log.read_text(errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        match = TIMING_RE.match(line)
        if match:
            stage = match.group(1)
        else:
            reason = line
    return stage, reason


def write_success(job_dir: Path) -> None:
    write_json(job_dir / "engine_contract.json", build_engine_contract(job_dir))
    write_json(job_dir / "validation" / "validation_report.json", build_validation_report(job_dir))
    write_json(job_dir / "delivery_manifest.json", build_delivery_manifest(job_dir))


def write_failure(job_dir: Path) -> None:
    stage, reason = last_stage_and_reason(job_dir)
    docs = build_failure_documents(job_dir, stage, reason, [])
    write_json(job_dir / "failure_summary.json", docs["summary"])
    write_json(job_dir / "engine_contract.json", docs["contract"])
    write_json(job_dir / "validation" / "validation_report.json", docs["validation"])


def iter_jobs(uploads_dir: Path):
    try:
        items = sorted(uploads_dir.iterdir(), key=lambda item: item.name)
    except OSError as exc:
        raise SystemExit(f"Cannot read uploads dir {uploads_dir}: {exc}") from exc
    for path in items:
        if not path.is_dir() or path.name.startswith("_"):
            continue
        yield path


def is_file(path: Path) -> bool:
    try:
        return path.is_file()
    except OSError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("uploads_dir", type=Path, nargs="?", default=Path("uploads"))
    parser.add_argument("--include-failures", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    success = failures = skipped = 0
    for job_dir in iter_jobs(args.uploads_dir):
        if is_file(job_dir / "qa_report.json"):
            success += 1
            print(f"{job_dir.name} success")
            if not args.dry_run:
                write_success(job_dir)
        elif args.include_failures and (is_file(job_dir / "logs" / "openmvs_pipeline.log") or is_file(job_dir / "process.log")):
            failures += 1
            print(f"{job_dir.name} failure")
            if not args.dry_run:
                write_failure(job_dir)
        else:
            skipped += 1

    print(f"done success={success} failure={failures} skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
