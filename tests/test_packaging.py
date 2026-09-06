"""
Paket metadata, build ve import davranışını doğrulayan testler
"""

import os
import site
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path
from zipfile import ZipFile

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

EXPECTED_MODULES = (
    "bot.py",
    "config.py",
    "database.py",
    "scraper.py",
    "smtp_notifier.py",
    "domain/__init__.py",
    "adapters/__init__.py",
)


def test_dependency_groups_are_separated():
    """pyproject.toml'da runtime bağımlılıkları test/lint araçlarını içermemeli,
    dev extra'sı içermeli."""

    with open(REPO_ROOT / "pyproject.toml", "rb") as handle:
        data = tomllib.load(handle)

    runtime_deps = {
        dep.split("==")[0].lower() for dep in data["project"]["dependencies"]
    }
    dev_deps = {
        dep.split("==")[0].lower()
        for dep in data["project"]["optional-dependencies"]["dev"]
    }

    assert "pytest" not in runtime_deps
    assert "ruff" not in runtime_deps
    assert "pytest" in dev_deps
    assert "ruff" in dev_deps


def test_wheel_build_contains_expected_modules_only(tmp_path):
    """Paket build edilince beklenen modülleri içermeli; test/lint araçlarını
    dosya olarak hiç barındırmamalı."""

    subprocess.run(
        [sys.executable, "-m", "pip", "wheel", "--no-deps", "-w", str(tmp_path), "."],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )

    wheels = list(tmp_path.glob("*.whl"))
    assert len(wheels) == 1

    with ZipFile(wheels[0]) as archive:
        names = archive.namelist()

    for expected in EXPECTED_MODULES:
        assert expected in names

    assert not any("pytest" in name or "ruff" in name for name in names)


@pytest.mark.timeout(120)
def test_runtime_import_smoke():
    """Build edilip kurulan paket, gerçek bağımlılıklarla birlikte import edilebilmeli.

    Kurulum --no-deps ile yapılır (hızlı, ağ gerektirmez); import sırasında
    gereken üçüncü parti kütüphaneler bu test ortamında zaten kurulu olanlardan
    (dev venv) çözülür. Global 30s limitten daha yüksek bir timeout kullanılır
    çünkü disk/antivirus yüküne bağlı olarak kurulum adımı yavaşlayabiliyor.
    """

    with tempfile.TemporaryDirectory() as tmp_dir:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--no-deps",
                "--target",
                tmp_dir,
                ".",
            ],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )

        env = {
            **os.environ,
            "PYTHONPATH": os.pathsep.join([tmp_dir, *site.getsitepackages()]),
            "TELEGRAM_BOT_TOKEN": "dummy-token",
            "DATABASE_URL": "postgresql://user:pass@127.0.0.1:1/itobot_test",
        }

        result = subprocess.run(
            [sys.executable, "-c", "import bot; print('IMPORT_OK')"],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )

    assert result.returncode == 0
    assert "IMPORT_OK" in result.stdout
