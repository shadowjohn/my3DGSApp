import json

import pytest

from scripts.build_georef_metadata import build_georef_metadata, write_georef_metadata


def test_build_georef_metadata_defaults_to_none():
    data = build_georef_metadata()

    assert data["mode"] == "none"
    assert data["crs"] is None
    assert data["origin"] == {"lat": None, "lng": None, "height": None}
    assert data["headingDegrees"] is None
    assert data["scaleMetersPerUnit"] is None
    assert data["controlPoints"] == []
    assert data["confidence"] == "none"
    assert data["notes"] == []


def test_build_georef_metadata_manual_origin():
    data = build_georef_metadata(
        mode="manual",
        lat=24.15,
        lng=120.66,
        height=12.5,
        heading=30.0,
        scale=0.01,
        crs="EPSG:4326",
        note="field estimate",
    )

    assert data["mode"] == "manual"
    assert data["origin"] == {"lat": 24.15, "lng": 120.66, "height": 12.5}
    assert data["headingDegrees"] == 30.0
    assert data["scaleMetersPerUnit"] == 0.01
    assert data["crs"] == "EPSG:4326"
    assert data["confidence"] == "low"
    assert data["notes"] == ["field estimate"]


def test_write_georef_metadata(tmp_path):
    output = tmp_path / "georef.json"

    write_georef_metadata(output, mode="manual", lat=1.0, lng=2.0)

    data = json.loads(output.read_text())
    assert data["mode"] == "manual"
    assert data["origin"]["lat"] == 1.0
    assert data["origin"]["lng"] == 2.0


@pytest.mark.parametrize(
    ("mode", "confidence"),
    [
        ("none", "none"),
        ("exif", "low"),
        ("manual", "low"),
        ("gcp", "medium"),
        ("rtk", "high"),
    ],
)
def test_build_georef_metadata_confidence_for_supported_modes(mode, confidence):
    data = build_georef_metadata(mode=mode)

    assert data["confidence"] == confidence


def test_build_georef_metadata_rejects_unsupported_mode():
    with pytest.raises(ValueError, match="unsupported georef mode: drone"):
        build_georef_metadata(mode="drone")
