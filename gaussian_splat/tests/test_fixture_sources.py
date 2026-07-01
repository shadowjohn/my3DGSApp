from conftest import SAMPLE_MP4, SAMPLE_MP4_ALT, SAMPLE_ZIP


def test_jpgtoglb_sample_inputs_exist():
    assert SAMPLE_MP4.is_file()
    assert SAMPLE_MP4_ALT.is_file()
    assert SAMPLE_ZIP.is_file()
    assert SAMPLE_MP4.stat().st_size > 0
    assert SAMPLE_MP4_ALT.stat().st_size > 0
    assert SAMPLE_ZIP.stat().st_size > 0
