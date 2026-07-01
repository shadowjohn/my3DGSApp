import json
from scripts.write_default_transform import build_transform


def test_build_transform_matches_alignment_schema():
    data = build_transform("site001", 121.456, 25.123, 12.5)
    assert data["job_id"] == "site001"
    assert data["source_type"] == "gaussian_splat"
    assert data["origin"] == {"lng": 121.456, "lat": 25.123, "height": 12.5}
    assert data["transform"] == {"heading": 0.0, "pitch": 0.0, "roll": 0.0, "scale": 1.0}
    assert data["camera"] == {
        "lng": None,
        "lat": None,
        "height": None,
        "heading": None,
        "pitch": None,
        "roll": None,
    }


def test_transform_is_json_serializable():
    encoded = json.dumps(build_transform("abc", 120.0, 24.0, 0.0), ensure_ascii=False)
    assert '"source_type": "gaussian_splat"' in encoded
