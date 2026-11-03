import os
import shutil
import subprocess
import sys
from pathlib import Path

# Pillar 8: UTF-8 Console Safety Guard
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_DIR = Path(__file__).parent.resolve()
DIST_DIR = PROJECT_DIR / "dist"
BUILD_DIR = PROJECT_DIR / "build"

def build():
    print("=" * 65)
    print(" [Edge Sidecar Browser] Packaging Distribution (.exe)")
    print("=" * 65)

    # PyInstaller CLI arguments
    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--name=EdgeSidecar",
        "--noconsole",          # Hide black console window
        "--onedir",             # _internal directory isolation
        "--clean",
        "--noconfirm",
        f"--add-data={PROJECT_DIR / 'dashboard.html'};.",
        f"--add-data={PROJECT_DIR / 'rules.json'};.",
        f"--distpath={DIST_DIR}",
        f"--workpath={BUILD_DIR}",
        str(PROJECT_DIR / "tray_app.py")
    ]

    print("[*] Running PyInstaller build command...")
    res = subprocess.run(cmd, cwd=str(PROJECT_DIR))
    if res.returncode != 0:
        print(f"[!] Build failed with exit code {res.returncode}")
        return False

    output_exe = DIST_DIR / "EdgeSidecar" / "EdgeSidecar.exe"
    if not output_exe.exists():
        print(f"[!] Target binary not found: {output_exe}")
        return False

    # Bundle Portable Chromium into dist/EdgeSidecar/bin
    src_bin = PROJECT_DIR / "bin"
    target_bin = DIST_DIR / "EdgeSidecar" / "bin"
    if src_bin.exists() and (src_bin / "chrome.exe").exists():
        print("[*] Bundling Portable Chromium engine into distribution...")
        if target_bin.exists():
            shutil.rmtree(target_bin, ignore_errors=True)
        shutil.copytree(src_bin, target_bin)
        print(f"[*] Portable Chromium bundled at: {target_bin}")

    print("\n" + "=" * 65)
    print(" [SUCCESS] Standalone Executable Build Complete!")
    print(f" [*] Output Location: {output_exe}")
    print(" [*] Everything is bundled: Python interpreter, PyQt6, Cryptography, CDP engine")
    print(" [*] Distributable folder: " + str(DIST_DIR / "EdgeSidecar"))
    print("=" * 65)
    return True

if __name__ == "__main__":
    success = build()
    sys.exit(0 if success else 1)
