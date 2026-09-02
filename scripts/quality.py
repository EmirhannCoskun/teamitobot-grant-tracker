"""Run the canonical fast local and CI quality checks."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
LEGACY_PRODUCTION_MODULES = ("bot.py", "config.py", "database.py", "scraper.py")
QUALITY_COMMANDS = (
    ("Install dependencies", ("-m", "pip", "install", "-r", "requirements-dev.txt")),
    ("Compile", ("-m", "compileall", "-q", ".", "-x", r"[\\/]\.?(?:venv|env)[\\/]")),
    ("Ruff format", ("-m", "ruff", "format", "--check", ".")),
    ("Ruff lint", ("-m", "ruff", "check", ".")),
    (
        "Production critical lint",
        (
            "-m",
            "ruff",
            "check",
            "--no-force-exclude",
            "--select",
            "E9,F63,F7,F82",
            *LEGACY_PRODUCTION_MODULES,
        ),
    ),
    ("Fast pytest", ("-m", "pytest", "-q")),
)


def main() -> int:
    """Run each quality gate in fail-fast order."""
    for label, arguments in QUALITY_COMMANDS:
        print(f"==> {label}", flush=True)
        completed = subprocess.run(
            (sys.executable, *arguments),
            cwd=REPOSITORY_ROOT,
            check=False,
        )
        if completed.returncode:
            return completed.returncode

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
