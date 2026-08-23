#!/usr/bin/env python3
"""Copy the local library into the Home Assistant custom component."""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "kingsmith_walkingpad"
DST = ROOT / "custom_components" / "kingsmith_walkingpad" / "kingsmith_walkingpad"
SKIP_DIRS = {"server", "web", "__pycache__"}
SKIP_FILES = {"cli.py", "wifi.py", "demo.py"}


def main() -> None:
    if DST.exists():
        shutil.rmtree(DST)
    shutil.copytree(
        SRC,
        DST,
        ignore=lambda directory, names: [
            name
            for name in names
            if name in SKIP_DIRS
            or name in SKIP_FILES
            or name.endswith(".pyc")
        ],
    )
    print(f"Vendored {SRC} -> {DST}")


if __name__ == "__main__":
    main()
