"""Build a standalone Windows executable with PyInstaller.

    uv run python tools/build_exe.py

Produces dist/ql-console/ (one-dir, windowed) with ql-console.exe inside.
Bundles the assets folder (icons) and, if present, the generated cvar/command
catalog. Re-run after changing code or regenerating assets/_generated.py.
"""

from __future__ import annotations

import os
from pathlib import Path

import PyInstaller.__main__

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
ENTRY = ROOT / "main.py"
PKG = SRC / "ql_console"
ASSETS = PKG / "assets"
ICON = ASSETS / "icon.ico"
SEP = os.pathsep  # ';' on Windows, ':' elsewhere


def main() -> None:
    args = [
        str(ENTRY),
        "--name", "ql-console",
        "--onedir",
        "--windowed",
        "--noconfirm",
        "--clean",
        "--paths", str(SRC),
        # Ship the icons next to the package so appicon.py can find them.
        "--add-data", f"{ASSETS}{SEP}ql_console/assets",
        "--distpath", str(ROOT / "dist"),
        "--workpath", str(ROOT / "build"),
        "--specpath", str(ROOT / "build"),
    ]
    if ICON.exists():
        args += ["--icon", str(ICON)]
    # The generated catalog is optional and imported lazily; include it if built.
    if (PKG / "_generated.py").exists():
        args += ["--hidden-import", "ql_console._generated"]

    PyInstaller.__main__.run(args)
    print(f"\nDone. Executable: {ROOT / 'dist' / 'ql-console' / 'ql-console.exe'}")


if __name__ == "__main__":
    main()
