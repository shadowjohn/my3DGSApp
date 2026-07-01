from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "install_gs_env.sh"


def test_installer_uses_requested_cu128_stack():
    text = SCRIPT.read_text()
    assert 'ENV_PATH="${GS_CONDA_ENV:-/DATA/conda_vm/gs_scene}"' in text
    assert "python=3.10" in text
    assert "https://download.pytorch.org/whl/cu128" in text
    assert "torch==2.10.0" in text
    assert "torchvision==0.25.0" in text
    assert "torchaudio==2.10.0" in text
    assert "cuda-toolkit=12.8.0" in text
    assert "setuptools==80.10.2" in text
    assert "--no-build-isolation" in text
    assert "CUDA_HOME=\"$ENV_PATH\"" in text
    assert "CC=\"$ENV_PATH/bin/x86_64-conda-linux-gnu-gcc\"" in text
    assert "CXX=\"$ENV_PATH/bin/x86_64-conda-linux-gnu-g++\"" in text
    assert "install nerfstudio" in text
    assert "install gsplat" in text
    assert "torch.cuda.is_available()" in text


def test_installer_is_strict_bash():
    text = SCRIPT.read_text()
    assert text.startswith("#!/usr/bin/env bash")
    assert "set -euo pipefail" in text
