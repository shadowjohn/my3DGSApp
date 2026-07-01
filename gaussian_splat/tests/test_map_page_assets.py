from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_map_page_requires_auth_ready_job_and_splat_file():
    text = (ROOT / "map.php").read_text()

    assert 'require "../../../../../inc/config.php";' in text
    assert 'require "{$base_dir}/inc/checkpassword.php";' in text
    assert '$include_mode = "easymap7115";' in text
    assert '$include_mode = "easymap7115|three.js-r155";' not in text
    assert "SELECT * FROM `gaussian_splat_jobs` WHERE `id`=? AND `del`='0' LIMIT 1" in text
    assert "$isReady = (string)$info['status'] === '2';" in text
    assert 'exit("工作不存在")' in text
    assert 'exit("工作尚未完成")' in text
    assert 'splat.clean.ply' in text
    assert 'exit("找不到 splat 檔")' in text


def test_map_page_builds_easymap_form_preview_and_save_payload():
    text = (ROOT / "map.php").read_text()
    api_text = (ROOT / "api.php").read_text()

    assert "<title>Gaussian Splat 定位校正</title>" in text
    assert 'document.title = "Gaussian Splat 定位校正";' in text
    assert '<div id="map"></div>' in text
    assert 'new Easymap("map")' in text
    assert "map.panToXYZ(new dgXY(targetLon(), targetLat()), 19);" in text
    assert 'map.panToXYZ(new dgXY(parseFloat($("#lon").val()), parseFloat($("#lat").val())), 19);' not in text
    assert "map.panToXYZ(new dgXY" in text
    assert 'map.attachEvent("onclick"' in text
    assert "定位校正" in text
    assert "經度" in text
    assert "緯度" in text
    assert "高度" in text
    assert "比例" in text
    assert "模型方向" in text
    assert "俯仰" in text
    assert "翻滾" in text
    assert "相機經度" in text
    assert "相機緯度" in text
    assert "相機高度" in text
    assert "相機方向" in text
    assert "相機俯仰" in text
    assert "相機翻滾" in text
    assert "圖台旋轉" in text
    assert 'id="lon"' in text
    assert 'id="lat"' in text
    assert 'id="alt"' in text
    assert 'id="heading"' in text
    assert 'id="pitch"' in text
    assert 'id="roll"' in text
    assert 'id="scale"' in text
    assert 'id="map_rotate"' in text
    assert 'id="map_rotate_range"' in text
    assert 'id="locate2d"' in text
    assert 'id="locate3d"' in text
    assert 'id="applyMapRotate"' in text
    assert 'viewer_splat.php?id=' in text
    assert 'viewer_splat.html?src=' not in text
    assert '<iframe id="preview"' in text
    assert 'api.php?mode=save_transform' in text
    assert "base64_encode(JSON.stringify(payload()))" in text
    assert 'map_rotate: numberOrNull("#map_rotate")' in text
    assert "camera_lon" in text
    assert "camera_heading" in text
    assert "'lon','lat','alt','heading','pitch','roll','scale','camera_lon','camera_lat','camera_alt','camera_heading','camera_pitch','camera_roll'" in api_text
    assert "'lon','lat','alt','heading','pitch','roll','scale','camera_lon','camera_lat','camera_alt','camera_heading','camera_pitch','camera_roll','map_rotate'" not in api_text
    assert "map.enable3D(function" in text
    assert "map.panTo3D(new dgXYZ" in text
    assert "heading: numberOrDefault(\"#camera_heading\", numberOrDefault(\"#heading\", 0))" in text
    assert "pitch: numberOrDefault(\"#camera_pitch\", -35)" in text
    assert "roll: numberOrDefault(\"#camera_roll\", 0)" in text
    assert "map.rotate(numberOrDefault(\"#map_rotate\", 0))" in text
    assert "方向旋轉" in text
    assert "儲存定位" in text
    assert "開啟獨立檢視器" in text
    assert "正在儲存..." in text
    assert "已儲存。" in text
    assert "儲存失敗。" in text
