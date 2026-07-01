import json
import subprocess
from pathlib import Path

import pytest

from scripts.build_delivery_manifest import build_delivery_manifest


ROOT = Path(__file__).resolve().parents[1]


def test_build_delivery_manifest_defaults_to_gaussian_splat(tmp_path):
    job = tmp_path / "job"
    exports = job / "exports"
    exports.mkdir(parents=True)
    (exports / "splat.trench.ply").write_bytes(b"ply")
    (exports / "splat.trench.viewer.json").write_text("{}")

    manifest = build_delivery_manifest(job)

    assert manifest["delivery_mode"] == "gaussian_splat"
    assert manifest["layers"]["gaussian_splat"]["splat"] == str(exports / "splat.trench.ply")
    assert manifest["layers"]["oblique_projection"] is None
    assert manifest["layers"]["glb_hybrid"] is None


def test_build_delivery_manifest_accepts_mixed_placeholders(tmp_path):
    job = tmp_path / "job"

    manifest = build_delivery_manifest(
        job,
        delivery_mode="mixed",
        oblique_projection="overlays/orthophoto.png",
        glb_hybrid="models/manhole.glb",
    )

    assert manifest["delivery_mode"] == "mixed"
    assert manifest["layers"]["oblique_projection"] == "overlays/orthophoto.png"
    assert manifest["layers"]["glb_hybrid"] == "models/manhole.glb"


def test_build_delivery_manifest_rejects_unsupported_mode(tmp_path):
    with pytest.raises(ValueError, match="unsupported delivery mode"):
        build_delivery_manifest(tmp_path, delivery_mode="drone")


def test_build_delivery_manifest_cli_writes_custom_output_with_unicode(tmp_path):
    job = tmp_path / "job"
    output = job / "reports" / "delivery_manifest.json"
    script = ROOT / "scripts" / "build_delivery_manifest.py"

    result = subprocess.run(
        [
            "python3",
            str(script),
            str(job),
            "--output",
            str(output),
            "--delivery-mode",
            "mixed",
            "--oblique-projection",
            "overlays/施工.png",
            "--glb-hybrid",
            "models/人孔.glb",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout == str(output) + "\n"
    raw_text = output.read_text(encoding="utf-8")
    assert "施工" in raw_text
    assert "人孔" in raw_text
    manifest = json.loads(raw_text)
    assert manifest["delivery_mode"] == "mixed"
    assert manifest["layers"]["oblique_projection"] == "overlays/施工.png"
    assert manifest["layers"]["glb_hybrid"] == "models/人孔.glb"


def test_build_studio_delivery_manifest_for_fast_mesh_primary(tmp_path):
    from scripts.build_delivery_manifest import build_studio_delivery_manifest

    job = tmp_path / "42"
    (job / "exports").mkdir(parents=True)
    (job / "exports" / "model.glb").write_bytes(b"glb")

    manifest = build_studio_delivery_manifest(job, "fast")

    assert manifest["schema_version"] == "1.0"
    assert manifest["version"] == "1.0.3"
    assert manifest["studio_job_id"] is None
    assert manifest["job_id"] == "42"
    assert manifest["mode"] == "fast"
    assert manifest["primary_artifact"] == {
        "type": "mesh",
        "path": "exports/model.glb",
        "engine": "openmvs",
        "role": "primary",
    }
    assert manifest["delivery_tracks"][0]["track"] == "mesh"
    assert manifest["delivery_tracks"][0]["engine"] == "openmvs"
    assert manifest["delivery_tracks"][0]["role"] == "delivery_candidate"
    assert manifest["delivery_tracks"][0]["delivery_capable"] is True
    assert manifest["delivery_tracks"][0]["primary_artifact"]["path"] == "exports/model.glb"
    assert manifest["readiness"] == "review_needed"


def test_fast_manifest_uses_one_primary_artifact(tmp_path):
    from scripts.build_delivery_manifest import build_studio_delivery_manifest

    job = tmp_path / "fast"
    (job / "exports").mkdir(parents=True)
    (job / "exports" / "model.glb").write_bytes(b"glb")
    (job / "exports" / "splat.clean.ply").write_bytes(b"ply")

    manifest = build_studio_delivery_manifest(job, "fast")

    deliverables = [item for item in manifest["artifacts"] if item["role"] == "primary"]
    assert deliverables == [
        {"type": "mesh", "path": "exports/model.glb", "engine": "openmvs", "role": "primary"}
    ]


def test_qa_manifest_keeps_splat_diagnostic_not_primary(tmp_path):
    from scripts.build_delivery_manifest import build_studio_delivery_manifest

    job = tmp_path / "qa"
    (job / "exports").mkdir(parents=True)
    (job / "exports" / "model.glb").write_bytes(b"glb")
    (job / "exports" / "splat.clean.ply").write_bytes(b"ply")

    manifest = build_studio_delivery_manifest(job, "qa")

    assert manifest["primary_artifact"]["type"] == "mesh"
    splat = [item for item in manifest["artifacts"] if item["type"] == "splat"][0]
    assert splat["role"] == "diagnostic"
    splat_track = [item for item in manifest["delivery_tracks"] if item["track"] == "splat"][0]
    assert splat_track["engine"] == "gaussian_splat"
    assert splat_track["role"] == "diagnostic"
    assert splat_track["delivery_capable"] is False
    assert splat_track["primary_artifact"]["type"] == "splat"
    assert splat_track["primary_artifact"]["format"] == "ply"
    assert splat_track["primary_artifact"]["uuid"].startswith("gs_qa_")


def test_manifest_uses_gaussian_engine_contract_role_when_present(tmp_path):
    from scripts.build_delivery_manifest import build_studio_delivery_manifest

    job = tmp_path / "qa"
    (job / "exports").mkdir(parents=True)
    (job / "exports" / "model.glb").write_bytes(b"glb")
    (job / "exports" / "splat.clean.ply").write_bytes(b"ply")
    (job / "engine_contract.json").write_text(json.dumps({
        "engine_name": "gaussian_splat",
        "pipeline_mode": "qa",
        "role": "diagnostic",
        "delivery_capable": False,
        "artifacts": [
            {
                "type": "splat",
                "path": "exports/splat.clean.ply",
                "role": "diagnostic",
                "delivery_capable": False,
            }
        ],
    }))

    manifest = build_studio_delivery_manifest(job, "qa")

    splat_track = [item for item in manifest["delivery_tracks"] if item["track"] == "splat"][0]
    assert splat_track["role"] == "diagnostic"
    assert splat_track["delivery_capable"] is False
    assert splat_track["contract_path"] == "engine_contract.json"


def test_qa_manifest_without_mesh_has_no_primary_delivery(tmp_path):
    from scripts.build_delivery_manifest import build_studio_delivery_manifest

    job = tmp_path / "qa"
    (job / "exports").mkdir(parents=True)
    (job / "exports" / "splat.clean.ply").write_bytes(b"ply")

    manifest = build_studio_delivery_manifest(job, "qa")

    assert manifest["primary_artifact"] is None
    splat = [item for item in manifest["artifacts"] if item["type"] == "splat"][0]
    assert splat["role"] == "diagnostic"
    splat_track = [item for item in manifest["delivery_tracks"] if item["track"] == "splat"][0]
    assert splat_track["delivery_capable"] is False


def test_premium_manifest_marks_splat_as_fidelity(tmp_path):
    from scripts.build_delivery_manifest import build_studio_delivery_manifest

    job = tmp_path / "premium"
    (job / "exports").mkdir(parents=True)
    (job / "exports" / "model.glb").write_bytes(b"glb")
    (job / "exports" / "splat.clean.ply").write_bytes(b"ply")

    manifest = build_studio_delivery_manifest(job, "premium")

    roles = {item["type"]: item["role"] for item in manifest["artifacts"]}
    assert roles["mesh"] == "primary"
    assert roles["splat"] == "delivery_capable"
    tracks = {item["track"]: item for item in manifest["delivery_tracks"]}
    assert tracks["mesh"]["delivery_capable"] is True
    assert tracks["splat"]["role"] == "delivery_capable"
    assert tracks["splat"]["delivery_capable"] is True
    assert tracks["splat"]["primary_artifact"]["uuid"].startswith("gs_premium_")
    assert tracks["splat"]["primary_artifact"]["format"] == "ply"


def test_compare_mesh_manifest_uses_mesh_extraction_engine(tmp_path):
    from scripts.build_delivery_manifest import build_studio_delivery_manifest

    job = tmp_path / "premium"
    (job / "compare" / "mesh").mkdir(parents=True)
    (job / "exports").mkdir(parents=True)
    (job / "compare" / "mesh" / "cleaned_mesh.glb").write_bytes(b"glb")
    (job / "exports" / "splat.clean.ply").write_bytes(b"ply")

    manifest = build_studio_delivery_manifest(job, "premium")

    mesh = [item for item in manifest["artifacts"] if item["type"] == "mesh"][0]
    assert mesh == {
        "type": "mesh",
        "path": "compare/mesh/cleaned_mesh.glb",
        "engine": "mesh_extraction",
        "role": "primary",
    }


def test_build_studio_delivery_manifest_cli_writes_pipeline_mode(tmp_path):
    job = tmp_path / "qa"
    output = job / "delivery_manifest.json"
    (job / "exports").mkdir(parents=True)
    (job / "exports" / "model.glb").write_bytes(b"glb")
    script = ROOT / "scripts" / "build_delivery_manifest.py"

    result = subprocess.run(
        ["python3", str(script), str(job), "--output", str(output), "--pipeline-mode", "qa"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout == str(output) + "\n"
    manifest = json.loads(output.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "1.0"
    assert manifest["mode"] == "qa"
    assert manifest["primary_artifact"]["path"] == "exports/model.glb"
    assert manifest["delivery_tracks"][0]["primary_artifact"]["path"] == "exports/model.glb"
