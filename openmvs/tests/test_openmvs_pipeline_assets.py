import json
import subprocess
import sys
import zipfile
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]


def test_worker_invoked_scripts_are_world_readable_and_executable():
    for relative in [
        "scripts/prepare_images.py",
        "scripts/prepare_masks.py",
        "scripts/build_qa_report.py",
        "scripts/build_engine_contract.py",
        "scripts/build_validation_report.py",
        "scripts/build_delivery_manifest.py",
        "scripts/build_failure_summary.py",
        "scripts/backfill_standard_artifacts.py",
        "scripts/repair_texture_atlas.py",
        "scripts/write_default_transform.py",
        "scripts/run_openmvs_pipeline.sh",
    ]:
        mode = (ROOT / relative).stat().st_mode
        assert mode & 0o005 == 0o005, f"{relative} must be readable/executable by www-data"


def test_pipeline_shell_contains_colmap_openmvs_chain_and_env_defaults():
    text = (ROOT / "scripts" / "run_openmvs_pipeline.sh").read_text()

    assert "OPENMVS_CONDA_ENV=\"${OPENMVS_CONDA_ENV:-/DATA/conda_vm/openmvs}\"" in text
    assert "OPENMVS_BIN_DIR=\"${OPENMVS_BIN_DIR:-$OPENMVS_CONDA_ENV/bin}\"" in text
    assert "COLMAP_BIN_DIR=\"${COLMAP_BIN_DIR:-$OPENMVS_CONDA_ENV/bin}\"" in text
    assert "function log_colmap_binary_status" in text
    assert "COLMAP binary selected:" in text
    assert 'INPUT_FILE="$(realpath -m "$INPUT_FILE")"' in text
    assert 'JOB_DIR="$(realpath -m "$JOB_DIR")"' in text
    assert "QT_QPA_PLATFORM=\"${QT_QPA_PLATFORM:-offscreen}\"" in text
    assert "export QT_QPA_PLATFORM" in text
    assert "OVM_PREFERRED_CUDA_VERSION=\"${OVM_PREFERRED_CUDA_VERSION:-12.8}\"" in text
    assert "COLMAP_GPU_MODE=\"${COLMAP_GPU_MODE:-${COLMAP_USE_GPU:-auto}}\"" in text
    assert "COLMAP_GPU_PROBE=\"${COLMAP_GPU_PROBE:-1}\"" in text
    assert "OPENMVS_CUDA_DEVICE=\"${OPENMVS_CUDA_DEVICE:--1}\"" in text
    assert "OVM_TEXTURE_EMPTY_COLOR=\"${OVM_TEXTURE_EMPTY_COLOR:-16777215}\"" in text
    assert "OVM_TEXTURE_COST_SMOOTHNESS_RATIO=\"${OVM_TEXTURE_COST_SMOOTHNESS_RATIO:-1}\"" in text
    assert "OVM_TEXTURE_SHARPNESS_WEIGHT=\"${OVM_TEXTURE_SHARPNESS_WEIGHT:-0.35}\"" in text
    assert "OVM_TEXTURE_REPAIR_MODE=\"${OVM_TEXTURE_REPAIR_MODE:-auto}\"" in text
    assert "OVM_TEXTURE_REPAIR_TRIGGER_BLACK_RATIO" in text
    assert "OVM_TEXTURE_REPAIR_MAX_WHITE_RATIO" in text
    assert "OVM_QUALITY_PRESET=\"${OVM_QUALITY_PRESET:-normal}\"" in text
    assert "function apply_quality_preset" in text
    assert "fast)" in text
    assert "normal)" in text
    assert "high)" in text
    assert "quality preset:" in text
    assert "COLMAP_UNDISTORT_ROI_MIN_X=\"${COLMAP_UNDISTORT_ROI_MIN_X:-0}\"" in text
    assert "COLMAP_UNDISTORT_ROI_MIN_Y=\"${COLMAP_UNDISTORT_ROI_MIN_Y:-0}\"" in text
    assert "COLMAP_UNDISTORT_ROI_MAX_X=\"${COLMAP_UNDISTORT_ROI_MAX_X:-1}\"" in text
    assert "COLMAP_UNDISTORT_ROI_MAX_Y=\"${COLMAP_UNDISTORT_ROI_MAX_Y:-1}\"" in text
    assert "OVM_MASK_MODE=\"${OVM_MASK_MODE:-none}\"" in text
    assert "OVM_MASK_IGNORE_LABEL=\"${OVM_MASK_IGNORE_LABEL:-0}\"" in text
    assert "OVM_MASK_AUTO_RECT=\"${OVM_MASK_AUTO_RECT:-0.12,0.08,0.88,0.96}\"" in text
    assert "function configure_cuda_runtime" in text
    assert "/usr/local/cuda-${OVM_PREFERRED_CUDA_VERSION}" in text
    assert "/DATA/conda_vm/gs_scene" in text
    assert "targets/x86_64-linux/lib" in text
    assert "function detect_colmap_gpu_mode" in text
    assert "function run_colmap_gpu_probe" in text
    assert "/usr/bin/time -v" in text
    assert "resource usage will not be logged" in text
    assert "function run_colmap_feature_with_fallback" in text
    assert "function run_colmap_matcher_with_fallback" in text
    assert "function select_colmap_sparse_model" in text
    assert "colmap model_analyzer" in text
    assert "SELECTED_SPARSE_DIR" in text
    assert 'select_colmap_sparse_model' in text
    assert "COLMAP_USE_GPU=\"$(detect_colmap_gpu_mode)\"" in text
    assert "log_colmap_binary_status" in text
    assert "function detect_openmvs_cuda_device" in text
    assert "function openmvs_cuda_args_for" in text
    assert '"$tool" --help 2>&1 || true' in text
    assert "function run_openmvs_stage" in text
    assert "OPENMVS_EFFECTIVE_CUDA_DEVICE=\"$(detect_openmvs_cuda_device)\"" in text
    assert "falling back to CPU" in text
    assert "require_tool colmap" in text
    assert "require_tool InterfaceCOLMAP" in text
    assert "require_tool DensifyPointCloud" in text
    assert "require_tool ReconstructMesh" in text
    assert "require_tool TextureMesh" in text
    assert "require_tool TransformScene" not in text
    assert "colmap feature_extractor" in text
    assert "colmap exhaustive_matcher" in text
    assert "colmap mapper" in text
    assert "colmap image_undistorter" in text
    assert '--input_path "$SELECTED_SPARSE_DIR"' in text
    assert '--roi_min_x "$COLMAP_UNDISTORT_ROI_MIN_X"' in text
    assert '--roi_min_y "$COLMAP_UNDISTORT_ROI_MIN_Y"' in text
    assert '--roi_max_x "$COLMAP_UNDISTORT_ROI_MAX_X"' in text
    assert '--roi_max_y "$COLMAP_UNDISTORT_ROI_MAX_Y"' in text
    assert '--input_path "$SPARSE_DIR/0"' not in text
    assert "InterfaceCOLMAP -i" in text
    assert "function normalize_mask_mode" in text
    assert "function openmvs_mask_args" in text
    assert "prepare_masks.py" in text
    assert 'run_stage prepare_masks "prepare OpenMVS masks"' in text
    assert "--mode \"$OVM_MASK_MODE\"" in text
    assert "--auto-rect \"$OVM_MASK_AUTO_RECT\"" in text
    assert "--mask-path \"$DENSE_DIR/images/\"" in text
    assert "--ignore-mask-label \"$OVM_MASK_IGNORE_LABEL\"" in text
    assert "DensifyPointCloud" in text
    assert "ReconstructMesh" in text
    assert "RefineMesh" in text
    assert 'run_openmvs_stage openmvs_create_structure "OpenMVS native SfM" CreateStructure' in text
    assert "function openmvs_refine_args" in text
    assert "function openmvs_texture_args" in text
    assert "--cuda-device" in text
    assert "TextureMesh" in text
    assert "OPENMVS_TEXTURE_ARGS" in text
    assert "--empty-color" in text
    assert "--cost-smoothness-ratio" in text
    assert "--sharpness-weight" in text
    assert '"${OPENMVS_DENSIFY_MASK_ARGS[@]}"' in text
    assert '"${OPENMVS_TEXTURE_MASK_ARGS[@]}"' in text
    assert 'TextureMesh scene_dense.mvs -m scene_dense_mesh_refine.ply -o scene_dense_mesh_refine_texture.mvs "${OPENMVS_TEXTURE_ARGS[@]}"' in text
    assert 'TextureMesh scene_dense.mvs -m scene_dense_mesh_refine.ply -o scene_dense_mesh_refine_texture.glb --export-type glb "${OPENMVS_TEXTURE_ARGS[@]}"' in text
    assert "function copy_texture_sidecars" in text
    assert "scene_dense_mesh_refine_texture" in text
    assert 'copy_texture_sidecars "$MVS_DIR" "$EXPORTS_DIR" "scene_dense_mesh_refine_texture"' in text
    assert "TextureMesh scene_dense_mesh_refine.mvs" not in text
    assert "TransformScene" not in text
    assert "--convert" not in text
    assert "--export-type glb" in text
    assert "exports/model.glb" in text
    assert "function repair_export_textures" in text
    assert "repair_texture_atlas.py" in text
    assert "texture_repair_report.json" in text
    assert "repair_export_textures" in text
    assert "job_dir must be under" in text
    assert "[timing] START prepare_images" in text
    assert "[timing] START colmap_mapper" in text
    assert "[timing] START openmvs_texture" in text


def test_openmvs_native_create_structure_uses_cpu_sift_detector():
    text = (ROOT / "scripts" / "run_openmvs_pipeline.sh").read_text()

    assert 'OVM_CREATE_STRUCTURE_DETECTOR_TYPE="${OVM_CREATE_STRUCTURE_DETECTOR_TYPE:-SIFT}"' in text
    assert '--detector-type "$OVM_CREATE_STRUCTURE_DETECTOR_TYPE"' in text


def test_openmvs_native_create_structure_disables_hierarchical_clustering():
    text = (ROOT / "scripts" / "run_openmvs_pipeline.sh").read_text()

    assert 'OVM_CREATE_STRUCTURE_MAX_VIEWS_PER_CLUSTER="${OVM_CREATE_STRUCTURE_MAX_VIEWS_PER_CLUSTER:-0}"' in text
    assert '--max-views-per-cluster "$OVM_CREATE_STRUCTURE_MAX_VIEWS_PER_CLUSTER"' in text


def test_high_preset_caps_create_structure_frame_count():
    text = (ROOT / "scripts" / "run_openmvs_pipeline.sh").read_text()
    high_block = text.split("    high)", 1)[1].split("      ;;", 1)[0]

    assert "OVM_MAX_FRAMES=240" in high_block


def test_openmvs_native_create_structure_exports_jpeg_undistorted_images():
    text = (ROOT / "scripts" / "run_openmvs_pipeline.sh").read_text()

    assert 'OVM_CREATE_STRUCTURE_UNDISTORT_EXTENSION="${OVM_CREATE_STRUCTURE_UNDISTORT_EXTENSION:-.jpg}"' in text
    assert '--undistort-extension "$OVM_CREATE_STRUCTURE_UNDISTORT_EXTENSION"' in text


def test_product_mode_exports_only_requested_glb_texture_size():
    text = (ROOT / "scripts" / "run_openmvs_pipeline.sh").read_text()

    assert 'OVM_PRODUCT_TEXTURE_SIZE="${OVM_PRODUCT_TEXTURE_SIZE:-}"' in text
    assert 'OVM_PRODUCT_OUTPUT_DIR="${OVM_PRODUCT_OUTPUT_DIR:-}"' in text
    assert "invalid OVM_PRODUCT_TEXTURE_SIZE" in text
    assert 'function product_mode_requested' in text
    assert '[ -n "$OVM_PRODUCT_TEXTURE_SIZE" ] || [ -n "$OVM_PRODUCT_OUTPUT_DIR" ]' in text
    assert "incomplete OVM product env" in text
    assert "exit 2" in text
    assert 'expected_output_dir="$JOB_DIR/products/glb_${OVM_PRODUCT_TEXTURE_SIZE}"' in text
    assert "invalid OVM_PRODUCT_OUTPUT_DIR" in text
    assert 'function run_product_glb_export' in text
    assert 'scene_dense.mvs' in text
    assert 'scene_dense_mesh_refine.ply' in text
    assert '-o "product_glb_${OVM_PRODUCT_TEXTURE_SIZE}.glb"' in text
    assert '--max-texture-size "$OVM_PRODUCT_TEXTURE_SIZE"' in text
    assert 'embedded_product_glb_${OVM_PRODUCT_TEXTURE_SIZE}.glb' in text
    assert 'copy_texture_sidecars "$MVS_DIR" "$OVM_PRODUCT_OUTPUT_DIR" "product_glb_${OVM_PRODUCT_TEXTURE_SIZE}"' in text
    product_block = text.split("function run_product_glb_export", 1)[1].split("\n}", 1)[0]
    assert "prepare_images.py" not in product_block
    assert "COLMAP" not in product_block
    assert "DensifyPointCloud" not in product_block
    assert "ReconstructMesh" not in product_block


def test_openmvs_native_registered_manifest_counts_undistorted_outputs():
    text = (ROOT / "scripts" / "run_openmvs_pipeline.sh").read_text()

    create_idx = text.index('run_openmvs_stage openmvs_create_structure "OpenMVS native SfM"')
    manifest_idx = text.index('write_registered_frame_manifest "$MVS_DIR/undistorted" "$JOB_DIR/colmap_manifest.json"')
    densify_idx = text.index('run_openmvs_stage openmvs_densify "OpenMVS dense point cloud"')

    assert create_idx < manifest_idx < densify_idx


def test_openmvs_gpu_arg_detection_supports_current_and_legacy_option_names():
    text = (ROOT / "scripts" / "run_openmvs_pipeline.sh").read_text()

    assert '"--gpu-device"' in text
    assert '"--cuda-device"' in text
    assert 'OPENMVS_TOOL_GPU_OPTION' in text


def test_prepare_images_safely_extracts_zip_images(tmp_path):
    zip_path = tmp_path / "images.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("nested/a.jpg", b"fake jpg")
        zf.writestr("../escape.jpg", b"escape")
        zf.writestr("notes.txt", b"ignore")

    output_dir = tmp_path / "images"
    report_path = tmp_path / "manifest.json"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "prepare_images.py"),
            str(zip_path),
            str(output_dir),
            "--report",
            str(report_path),
            "--min-frames",
            "1",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    images = sorted(output_dir.glob("*"))
    assert [p.name for p in images] == ["frame_00001.jpg"]
    assert not (tmp_path / "escape.jpg").exists()
    report = json.loads(report_path.read_text())
    assert report["source_type"] == "zip"
    assert report["frame_count"] == 1
    assert report["images"][0]["original_name"] == "nested/a.jpg"


def test_prepare_images_extracts_matching_zip_masks_without_counting_them_as_images(tmp_path):
    zip_path = tmp_path / "masked_images.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("nested/a.jpg", b"fake jpg")
        zf.writestr("nested/a.mask.png", b"fake mask")
        zf.writestr("nested/only.mask.png", b"mask without image")

    output_dir = tmp_path / "images"
    report_path = tmp_path / "manifest.json"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "prepare_images.py"),
            str(zip_path),
            str(output_dir),
            "--report",
            str(report_path),
            "--min-frames",
            "1",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    assert sorted(p.name for p in output_dir.iterdir()) == ["frame_00001.jpg", "frame_00001.mask.png"]
    report = json.loads(report_path.read_text())
    assert report["frame_count"] == 1
    assert report["mask_count"] == 1
    assert report["images"][0]["mask_filename"] == "frame_00001.mask.png"
    assert report["images"][0]["mask_original_name"] == "nested/a.mask.png"


def test_prepare_images_downsizes_zip_images_and_masks(tmp_path):
    zip_path = tmp_path / "large_images.zip"
    image_path = tmp_path / "a.jpg"
    mask_path = tmp_path / "a.mask.png"
    Image.new("RGB", (10, 20), (120, 130, 140)).save(image_path)
    Image.new("L", (10, 20), 255).save(mask_path)
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(image_path, "nested/a.jpg")
        zf.write(mask_path, "nested/a.mask.png")

    output_dir = tmp_path / "images"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "prepare_images.py"),
            str(zip_path),
            str(output_dir),
            "--width",
            "5",
            "--min-frames",
            "1",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    assert Image.open(output_dir / "frame_00001.jpg").size == (5, 10)
    assert Image.open(output_dir / "frame_00001.mask.png").size == (5, 10)


def test_prepare_images_rejects_zip_without_images(tmp_path):
    zip_path = tmp_path / "empty.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("notes.txt", b"ignore")

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "prepare_images.py"),
            str(zip_path),
            str(tmp_path / "images"),
            "--min-frames",
            "1",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode != 0
    assert "no usable images" in result.stderr.lower()


def test_build_qa_report_summarizes_artifacts(tmp_path):
    job_dir = tmp_path / "job"
    exports = job_dir / "exports"
    mvs = job_dir / "mvs"
    exports.mkdir(parents=True)
    mvs.mkdir()
    (exports / "model.glb").write_bytes(b"1234567890")
    (exports / "scene_dense_mesh_refine_texture.ply").write_bytes(b"ply")
    Image.new("RGB", (2, 2)).putdata([(0, 0, 0), (255, 255, 255), (20, 30, 40), (100, 120, 140)])
    texture = Image.new("RGB", (2, 2))
    texture.putdata([(0, 0, 0), (255, 255, 255), (20, 30, 40), (100, 120, 140)])
    texture.save(exports / "scene_dense_mesh_refine_texture_0.png")
    (mvs / "TextureMesh-test.log").write_text(
        "Generating texture atlas and image completed: 7 patches, 2048 image size, 1 textures\n"
    )
    (job_dir / "texture_repair_report.json").write_text(json.dumps({
        "mode": "auto",
        "repaired_count": 1,
    }))
    (job_dir / "input_manifest.json").write_text(json.dumps({"frame_count": 12}))
    (job_dir / "colmap_manifest.json").write_text(json.dumps({"registered_frame_count": 10}))

    report_path = job_dir / "qa_report.json"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_qa_report.py"),
            "42",
            str(job_dir),
            "--output",
            str(report_path),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(report_path.read_text())
    assert report["job_id"] == "42"
    assert report["input_frame_count"] == 12
    assert report["registered_frame_count"] == 10
    assert report["glb_file_size_mb"] > 0
    assert report["mesh_file_size_mb"] > 0
    assert report["texture_image_count"] == 1
    assert report["texture_width"] == 2
    assert report["texture_height"] == 2
    assert report["texture_black_pixel_ratio"] == 0.25
    assert report["texture_white_empty_pixel_ratio"] == 0.25
    assert report["texture_patch_count"] == 7
    assert report["texture_repair"]["repaired_count"] == 1
    assert report["texture_images"][0]["path"].endswith("scene_dense_mesh_refine_texture_0.png")


def test_repair_texture_atlas_inpaints_black_regions(tmp_path):
    exports = tmp_path / "exports"
    exports.mkdir()
    texture = Image.new("RGB", (16, 16), (180, 150, 100))
    for y in range(4, 12):
        for x in range(4, 12):
            texture.putpixel((x, y), (0, 0, 0))
    texture.save(exports / "scene_dense_mesh_refine_texture_0.png")

    report_path = tmp_path / "texture_repair_report.json"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "repair_texture_atlas.py"),
            str(exports),
            "--mode",
            "deblack",
            "--report",
            str(report_path),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    repaired = Image.open(exports / "scene_dense_mesh_refine_texture_0.png").convert("RGB")
    black_pixels = sum(1 for red, green, blue in repaired.getdata() if max(red, green, blue) < 12)
    assert black_pixels == 0
    repair_report = json.loads(report_path.read_text())
    assert repair_report["repaired_count"] == 1
    assert repair_report["textures"][0]["before"]["black_pixel_ratio"] > repair_report["textures"][0]["after"]["black_pixel_ratio"]


def test_prepare_masks_supports_provided_and_auto_modes(tmp_path):
    raw = tmp_path / "raw"
    dense = tmp_path / "dense"
    raw.mkdir()
    dense.mkdir()
    Image.new("RGB", (4, 4), (120, 120, 120)).save(raw / "frame_00001.jpg")
    mask = Image.new("L", (4, 4), 0)
    mask.putpixel((1, 1), 255)
    mask.save(raw / "frame_00001.mask.png")
    Image.new("RGB", (2, 2), (120, 120, 120)).save(dense / "frame_00001.jpg")
    manifest = tmp_path / "input_manifest.json"
    manifest.write_text(json.dumps({
        "images": [{
            "filename": "frame_00001.jpg",
            "mask_filename": "frame_00001.mask.png",
        }]
    }))
    provided_report = tmp_path / "provided_masks.json"

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "prepare_masks.py"),
            "--mode",
            "provided",
            "--manifest",
            str(manifest),
            "--raw-images",
            str(raw),
            "--dense-images",
            str(dense),
            "--report",
            str(provided_report),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    dense_mask = dense / "frame_00001.mask.png"
    assert dense_mask.is_file()
    assert Image.open(dense_mask).size == (2, 2)
    provided = json.loads(provided_report.read_text())
    assert provided["mode"] == "provided"
    assert provided["generated_count"] == 1

    dense_mask.unlink()
    auto_report = tmp_path / "auto_masks.json"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "prepare_masks.py"),
            "--mode",
            "auto",
            "--manifest",
            str(manifest),
            "--raw-images",
            str(raw),
            "--dense-images",
            str(dense),
            "--report",
            str(auto_report),
            "--auto-rect",
            "0.2,0.2,0.8,0.8",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0, result.stderr
    assert dense_mask.is_file()
    auto = json.loads(auto_report.read_text())
    assert auto["mode"] == "auto"
    assert auto["generated_count"] == 1
    assert auto["auto_method"] in {"grabcut", "ellipse"}


def test_install_script_targets_openmvs_conda_path_without_password():
    text = (ROOT / "scripts" / "install_openmvs_env.sh").read_text()

    assert "/DATA/conda_vm/openmvs" in text
    assert "OVM_PREFERRED_CUDA_VERSION=\"${OVM_PREFERRED_CUDA_VERSION:-12.8}\"" in text
    assert "/usr/local/cuda-${OVM_PREFERRED_CUDA_VERSION}" in text
    assert "/DATA/conda_vm/gs_scene" in text
    assert "targets/x86_64-linux/lib" in text
    assert "OpenMVS_USE_CUDA=\"${OpenMVS_USE_CUDA:-ON}\"" in text
    assert "OVM_CUDA_ARCHITECTURES" in text
    assert "CMAKE_CUDA_ARCHITECTURES" in text
    assert "CMAKE_CUDA_COMPILER" in text
    assert "requirements/conda-openmvs.yml" in text
    assert "env create -y -p" in text
    assert "openMVS" in text
    assert "CMAKE_INSTALL_PREFIX" in text
    assert "*gis5200" not in text


def test_release_builder_requires_deployable_inputs():
    text = (ROOT / "build_release.sh").read_text()

    assert "requirements/conda-openmvs.yml" in text
    assert "migrate.php" in text
    assert "docs/superpowers" in text
    assert "--exclude='./.git'" in text
    assert "--exclude='./uploads'" in text


def test_colmap_cuda_install_script_targets_openmvs_env_and_cu128():
    text = (ROOT / "scripts" / "install_colmap_cuda.sh").read_text()

    assert "ENV_PATH=\"${OPENMVS_CONDA_ENV:-/DATA/conda_vm/openmvs}\"" in text
    assert "COLMAP_SRC=\"$WORK_ROOT/colmap\"" in text
    assert "COLMAP_VERSION=\"${COLMAP_VERSION:-3.9.1}\"" in text
    assert "OVM_PREFERRED_CUDA_VERSION=\"${OVM_PREFERRED_CUDA_VERSION:-12.8}\"" in text
    assert "/DATA/conda_vm/gs_scene" in text
    assert "CMAKE_CUDA_ARCHITECTURES" in text
    assert "CMAKE_CUDA_COMPILER" in text
    assert "CUDA_ENABLED=ON" in text
    assert "GUI_ENABLED=OFF" in text
    assert "CMAKE_INSTALL_PREFIX=\"$ENV_PATH\"" in text
    assert '"$ENV_PATH/bin/colmap" -h' in text
    assert "without CUDA" in text
    assert "*gis5200" not in text
