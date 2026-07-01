import json

import pytest

from scripts.build_trench_delivery import build_trench_delivery


def test_build_trench_delivery_copies_clean_splat_and_writes_metadata(tmp_path):
    job = tmp_path / "job"
    exports = job / "exports"
    exports.mkdir(parents=True)
    clean = exports / "splat.clean.ply"
    clean.write_bytes(
        b"ply\nformat binary_little_endian 1.0\nelement vertex 0\nend_header\n"
    )
    (exports / "splat.clean.viewer.json").write_text(
        json.dumps(
            {
                "core": {"center": [1, 2, 3], "radius": 4},
                "quality": {"score": 0.91},
                "viewer": {"rx": 0, "exposure": 1.25},
            }
        )
    )

    result = build_trench_delivery(job)

    assert result["delivery_mode"] == "gaussian_splat"
    assert result["source_splat"] == str(clean)
    assert result["trench_splat"] == str(exports / "splat.trench.ply")
    assert (exports / "splat.trench.ply").read_bytes() == clean.read_bytes()
    metadata = json.loads((exports / "splat.trench.viewer.json").read_text())
    assert metadata["mode"] == "trench"
    assert metadata["core"] == {"center": [1, 2, 3], "radius": 4}
    assert metadata["quality"] == {"score": 0.91}
    assert metadata["delivery"]["sourceSplat"] == str(clean)
    assert metadata["delivery"]["policy"] == "v1_clean_splat_as_trench_focus"
    assert metadata["viewer"]["rx"] == 0
    assert metadata["viewer"]["exposure"] == 1.25
    assert metadata["viewer"]["focusMode"] == "trench"


def test_build_trench_delivery_uses_raw_splat_when_clean_splat_is_missing(tmp_path):
    job = tmp_path / "job"
    exports = job / "exports"
    exports.mkdir(parents=True)
    raw = exports / "splat.ply"
    raw.write_bytes(b"ply\nformat ascii 1.0\nelement vertex 0\nend_header\n")

    result = build_trench_delivery(job)

    assert result["source_splat"] == str(raw)
    assert (exports / "splat.trench.ply").read_bytes() == raw.read_bytes()


def test_build_trench_delivery_raises_when_no_source_splat_exists(tmp_path):
    job = tmp_path / "job"

    with pytest.raises(FileNotFoundError, match="No source splat found"):
        build_trench_delivery(job)
