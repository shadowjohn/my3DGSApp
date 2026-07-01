#!/usr/bin/env python3
"""Maintain a small JSON timing report for Gaussian Splat pipeline stages."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
import time


def now_record():
    epoch = time.time()
    return epoch, datetime.fromtimestamp(epoch).isoformat(timespec="seconds")


def duration(start_epoch, end_epoch):
    return round(float(end_epoch) - float(start_epoch), 2)


def read_report(path: Path):
    if not path.exists():
        return {"stages": []}
    return json.loads(path.read_text(encoding="utf-8"))


def write_report(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def init_report(path: Path, key: str, label: str):
    epoch, iso = now_record()
    write_report(
        path,
        {
            "key": key,
            "label": label,
            "status": "running",
            "started_epoch": epoch,
            "started_at": iso,
            "finished_epoch": None,
            "finished_at": None,
            "duration_seconds": None,
            "message": "",
            "stages": [],
        },
    )


def start_stage(path: Path, key: str, label: str):
    data = read_report(path)
    epoch, iso = now_record()
    data.setdefault("stages", []).append(
        {
            "key": key,
            "label": label,
            "status": "running",
            "started_epoch": epoch,
            "started_at": iso,
            "finished_epoch": None,
            "finished_at": None,
            "duration_seconds": None,
            "message": "",
        }
    )
    write_report(path, data)


def finish_stage(data, key: str, status: str, message: str, epoch: float, iso: str):
    for stage in reversed(data.setdefault("stages", [])):
        if stage.get("key") == key and stage.get("status") == "running":
            stage["status"] = status
            stage["finished_epoch"] = epoch
            stage["finished_at"] = iso
            stage["duration_seconds"] = duration(stage["started_epoch"], epoch)
            stage["message"] = message
            return True
    return False


def finish_report(path: Path, key: str, status: str, message: str):
    data = read_report(path)
    epoch, iso = now_record()
    if key == data.get("key", "pipeline"):
        data["status"] = status
        data["finished_epoch"] = epoch
        data["finished_at"] = iso
        data["duration_seconds"] = duration(data["started_epoch"], epoch)
        data["message"] = message
    else:
        if not finish_stage(data, key, status, message, epoch, iso):
            data.setdefault("stages", []).append(
                {
                    "key": key,
                    "label": key,
                    "status": status,
                    "started_epoch": epoch,
                    "started_at": iso,
                    "finished_epoch": epoch,
                    "finished_at": iso,
                    "duration_seconds": 0.0,
                    "message": message,
                }
            )
    write_report(path, data)


def fail_report(path: Path, key: str, status: str, message: str):
    data = read_report(path)
    epoch, iso = now_record()
    data["status"] = status
    data["finished_epoch"] = epoch
    data["finished_at"] = iso
    if data.get("started_epoch") is not None:
        data["duration_seconds"] = duration(data["started_epoch"], epoch)
    data["message"] = message
    for stage in data.setdefault("stages", []):
        if stage.get("status") == "running":
            stage["status"] = "failed"
            stage["finished_epoch"] = epoch
            stage["finished_at"] = iso
            stage["duration_seconds"] = duration(stage["started_epoch"], epoch)
            stage["message"] = message
    write_report(path, data)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Update a Gaussian Splat timing report.")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init")
    init.add_argument("report")
    init.add_argument("key")
    init.add_argument("label")

    start = sub.add_parser("start")
    start.add_argument("report")
    start.add_argument("key")
    start.add_argument("label")

    finish = sub.add_parser("finish")
    finish.add_argument("report")
    finish.add_argument("key")
    finish.add_argument("status")
    finish.add_argument("message")

    fail = sub.add_parser("fail")
    fail.add_argument("report")
    fail.add_argument("key")
    fail.add_argument("status")
    fail.add_argument("message")

    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    report = Path(args.report)
    try:
        if args.command == "init":
            init_report(report, args.key, args.label)
        elif args.command == "start":
            start_stage(report, args.key, args.label)
        elif args.command == "finish":
            finish_report(report, args.key, args.status, args.message)
        elif args.command == "fail":
            fail_report(report, args.key, args.status, args.message)
    except Exception as exc:
        print(f"pipeline_timing.py: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
