import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def write_qa(job: Path) -> None:
    exports = job / "exports"
    exports.mkdir(parents=True)
    (exports / "model.glb").write_bytes(b"glb")
    (exports / "mesh.ply").write_text("ply")
    (exports / "texture.png").write_bytes(b"png")
    (job / "qa_report.json").write_text(json.dumps({
        "job_id": job.name,
        "input_frame_count": 10,
        "registered_frame_count": 9,
        "glb_file_size_mb": 2.5,
        "mesh_file_size_mb": 1.5,
        "glb_path": str(exports / "model.glb"),
        "mesh_path": str(exports / "mesh.ply"),
        "texture_image_count": 1,
        "texture_width": 4096,
        "texture_height": 4096,
        "texture_black_pixel_ratio": 0.01,
        "texture_white_empty_pixel_ratio": 0.02,
        "texture_patch_count": 12,
        "texture_images": [{"path": str(exports / "texture.png")}],
    }))


def run(script: str, job: Path, *args: str) -> None:
    subprocess.run([sys.executable, str(ROOT / "scripts" / script), str(job), *args], check=True, text=True)


def test_openmvs_contract_validation_and_delivery_manifest_chain(tmp_path):
    job = tmp_path / "8"
    job.mkdir()
    write_qa(job)

    run("build_engine_contract.py", job, "--pipeline-mode", "openmvs_native")
    run("build_validation_report.py", job)
    run("build_delivery_manifest.py", job)

    contract = json.loads((job / "engine_contract.json").read_text())
    validation = json.loads((job / "validation" / "validation_report.json").read_text())
    delivery = json.loads((job / "delivery_manifest.json").read_text())

    assert contract["engine"] == "openmvs"
    assert contract["mode"] == "fast"
    assert contract["metrics"]["registrationRatio"] == 0.9
    assert contract["artifacts"][0]["path"] == "exports/model.glb"
    assert validation["decision"]["status"] == "deliverable"
    assert validation["scores"]["capture"] == 90
    assert delivery["schema_version"] == "1.0"
    assert delivery["status"] == "ready"
    assert delivery["delivery_tracks"][0]["track"] == "mesh"
    assert delivery["delivery_tracks"][0]["engine"] == "openmvs"
    assert delivery["delivery_tracks"][0]["role"] == "delivery_candidate"
    assert delivery["delivery_tracks"][0]["delivery_capable"] is True
    assert delivery["delivery_tracks"][0]["primary_artifact"]["path"] == "exports/model.glb"
    assert delivery["delivery_tracks"][0]["contract_path"] == "engine_contract.json"
    assert delivery["delivery_tracks"][0]["validation_report_path"] == "validation/validation_report.json"
    assert delivery["primaryArtifact"]["path"] == "exports/model.glb"
    assert delivery["debug"]["validationReport"] == "validation/validation_report.json"
    assert oct((job / "engine_contract.json").stat().st_mode & 0o777) == "0o644"
    assert oct((job / "validation").stat().st_mode & 0o777) == "0o755"
    assert oct((job / "delivery_manifest.json").stat().st_mode & 0o777) == "0o644"


def test_validation_marks_low_registration_as_recapture(tmp_path):
    job = tmp_path / "low"
    job.mkdir()
    write_qa(job)
    qa = json.loads((job / "qa_report.json").read_text())
    qa["registered_frame_count"] = 2
    (job / "qa_report.json").write_text(json.dumps(qa))

    run("build_engine_contract.py", job)
    run("build_validation_report.py", job)

    validation = json.loads((job / "validation" / "validation_report.json").read_text())
    assert validation["decision"]["status"] == "recapture_recommended"
    assert validation["decision"]["root_cause"] == "capture"
