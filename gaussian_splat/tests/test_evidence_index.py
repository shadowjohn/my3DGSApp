import json
import subprocess
import sys
from pathlib import Path

from scripts.build_evidence_index import build_evidence_index, query_spatial_tile


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_evidence_index.py"


def write_evidence_inputs(evidence_dir: Path) -> None:
    evidence_dir.mkdir(parents=True)
    (evidence_dir / "cameras.json").write_text(json.dumps({
        "cameras": [
            {"image_id": 1, "name": "frame_0001.jpg", "tvec": [0, 0, 0]},
            {"image_id": 2, "name": "frame_0002.jpg", "position": [4, 0, 4]},
        ]
    }))
    rows = [
        {"point3d_id": 10, "xyz": [0.1, 0, 0.1], "rgb": [255, 0, 0], "error": 0.2, "track": [{"image_id": 1}, {"image_id": 2}]},
        {"point3d_id": 11, "xyz": [0.4, 0, 0.2], "rgb": [0, 255, 0], "error": 0.3, "track": [{"image_id": 1}]},
        {"point3d_id": 12, "xyz": [9.0, 0, 9.0], "rgb": [0, 0, 255], "error": 0.4, "track": [{"image_id": 2}]},
    ]
    (evidence_dir / "points3d_tracks.jsonl").write_text("\n".join(json.dumps(row) for row in rows) + "\n")


def test_build_evidence_index_writes_query_ready_manifest_and_tiles(tmp_path):
    evidence_dir = tmp_path / "evidence"
    write_evidence_inputs(evidence_dir)

    manifest_path = build_evidence_index(evidence_dir, grid_size=2, sample_limit=2)

    manifest = json.loads(manifest_path.read_text())
    assert manifest["schema_version"] == "1.0"
    assert manifest["camera_count"] == 2
    assert manifest["sparse_point_count"] == 3
    assert manifest["cameras_path"] == "cameras.json"
    assert manifest["camera_path_path"] == "camera_path.json"
    assert manifest["spatial_index_type"] == "grid"
    assert manifest["spatial_index_path"] == "spatial_index.json"
    assert manifest["lod_sparse_points_path"] == "lod_sparse_points.json"
    assert manifest["coverage_query_ready"] is True
    assert "points3d_tracks" not in json.dumps(manifest)

    index = json.loads((evidence_dir / "spatial_index.json").read_text())
    tile = query_spatial_tile(index, [0.2, 0, 0.2])
    assert tile["point_count"] == 2
    assert tile["visible_camera_ids"] == [1, 2]
    assert tile["coverage_score"] == 1.0
    assert len(tile["sample_sparse_points"]) == 2

    lod = json.loads((evidence_dir / "lod_sparse_points.json").read_text())
    assert lod["points"][0]["point3d_id"] == 10
    assert "track" not in lod["points"][0]


def test_build_evidence_index_cli_prints_manifest_path(tmp_path):
    evidence_dir = tmp_path / "evidence"
    write_evidence_inputs(evidence_dir)

    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(evidence_dir), "--grid-size=2"],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(evidence_dir / "evidence_manifest.json")
