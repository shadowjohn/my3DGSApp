from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text()


def test_users_migration_defines_admin_login_schema():
    text = read("migrate.php")

    assert "CREATE TABLE IF NOT EXISTS `users`" in text
    for column in ["id", "loginid", "loginpd", "name", "is_admin", "createAt", "del"]:
        assert f"`{column}`" in text
    assert "SHA2(:admin_password, 256)" in text
    assert "FOCUSIT_ADMIN_PASSWORD" in text
    assert "*gis5200" not in text
    assert "ALTER TABLE `users` ADD COLUMN" in text
    assert "['is_admin'" in text


def test_login_and_checkpassword_use_users_table():
    login = read("login.php")
    guard = read("inc/checkpassword.php")

    assert 'name="loginid"' in login
    assert 'name="loginpd"' in login
    assert 'name="gdcode"' in login
    assert "ADMIN ACCESS" in login
    assert "後台管理者登入" in login
    assert "訓練家的會員登入" not in login
    assert 'id="loginClock"' in login
    assert "setInterval(updateLoginClock, 1000)" in login
    assert 'maxlength="4"' in login
    assert ">取消<" not in login
    assert "SELECT `id`,`loginid`,`name`,`is_admin`" in login
    assert "hash('sha256', $loginpd)" in login
    assert '$_SESSION["login_user"]' in login
    assert "auth_require_login" in guard
    assert 'header("Location: {$loginUrl}")' in guard
    assert '$_SESSION["login_user"]' in guard


def test_home_index_exposes_focusit_studio_entry_points():
    text = read("index.php")
    css = read("css/john_web.css")

    assert "Focusit Studio" in text
    assert "3D 重建與空間影像處理工作台" in text
    assert "GIS" in text
    assert "MIS" in text
    assert "AI" in text
    assert "IoT" in text
    assert "/john_web/openmvs/index.php" in text
    assert "/john_web/gaussian_splat/index.php" in text
    assert "後台管理" in text
    assert "智慧環境監控" in text
    assert ".jw-home-grid" in css


def test_home_index_overrides_legacy_main_layout_width():
    css = read("css/john_web.css")
    home_block = css.split(".jw-home {", 1)[1].split("}", 1)[0]

    assert "width: 100%;" in home_block
    assert "box-sizing: border-box;" in home_block
    assert "float: none;" in home_block


def test_gd_code_uses_four_clear_rotated_characters():
    gd = read("gd.php")

    assert '$chars = "3456789ABCDEFGHJKMNPQRSTUVWXY";' in gd
    assert "for($i = 0; $i < 4; $i++)" in gd
    assert "random_int(-25, 25)" in gd
    for ambiguous in ["0", "1", "2", "I", "L", "O", "Z"]:
        assert ambiguous not in gd.split('$chars = "', 1)[1].split('";', 1)[0]


def test_template_shims_and_include_mode_assets_are_wired():
    root_head = read("head.php")
    template_head = read("template/head.php")
    template_html = read("template/html.php")
    template_body = read("template/body.php")

    assert 'require __DIR__ . "/template/head.php";' in root_head
    assert "$include_mode" in template_head
    assert "preg_split('/[|,]+/'" in template_head
    assert 'has_include_mode("jquery-ui")' in template_head
    assert "jquery-ui/jquery-ui.min.js" in template_head
    assert 'has_include_mode("threejs")' in template_head
    assert 'has_include_mode("threejs155")' in template_head
    assert "/john_web/assets/vendor/three/0.155.0/build/three.module.js" in template_head
    assert "/john_web/assets/vendor/three/0.165.0/build/three.module.js" in template_head
    assert "<!DOCTYPE html>" in template_html
    assert "<body>" in template_body


def test_top_navigation_and_admin_pages_share_login_guard():
    top = read("top.php")
    login = read("login.php")
    ovm_index = read("openmvs/index.php")
    gs_admin = read("gaussian_splat/admin.php")
    ovm_admin = read("openmvs/admin.php")
    ovm_job_view = read("openmvs/job_view.php")

    assert "Focusit Studio" in top
    assert "Focusit Studio" in login
    assert "3WA Photogrammetry" not in top
    assert "3WA STUDIO" not in login
    assert "OpenMVS" in top
    assert "GaussianSplat" in top
    assert "login.php" in top
    assert "logout.php" in top
    assert "login_user" in top
    assert 'require "{$base_dir}/inc/checkpassword.php";' in gs_admin
    assert 'require "{$base_dir}/inc/checkpassword.php";' in ovm_admin
    assert "OpenMVS 轉檔後台" in ovm_admin
    assert '$_SESSION["login_user"]' in ovm_job_view
    assert "$isLoggedIn = !empty($_SESSION[\"login_user\"])" in ovm_index
    assert "<?php if($isLoggedIn): ?>" in ovm_index
