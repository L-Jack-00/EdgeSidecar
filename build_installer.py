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
DIST_DIR = PROJECT_DIR / "dist" / "EdgeSidecar"
INSTALLER_DIST = PROJECT_DIR / "dist_installer"
WORK_DIR = PROJECT_DIR / "build_installer_temp"

def build_installer():
    print("=" * 65)
    print(" [Edge Sidecar Browser] Packaging Standalone Setup (.exe)")
    print("=" * 65)

    if not DIST_DIR.exists() or not (DIST_DIR / "EdgeSidecar.exe").exists():
        print("[*] Main binary package missing. Building dist/EdgeSidecar first...")
        from build_package import build
        if not build():
            print("[!] Failed to build base binary package.")
            return False

    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--name=EdgeSidecar-Setup",
        "--noconsole",
        "--onefile",
        "--clean",
        "--noconfirm",
        f"--add-data={DIST_DIR};payload",
        f"--distpath={INSTALLER_DIST}",
        f"--workpath={WORK_DIR}",
        str(PROJECT_DIR / "installer_wizard.py")
    ]

    print("[*] Compiling installer executable with PyInstaller...")
    res = subprocess.run(cmd, cwd=str(PROJECT_DIR))
    if res.returncode != 0:
        print(f"[!] Installer compilation failed with exit code {res.returncode}")
        return False

    output_setup = INSTALLER_DIST / "EdgeSidecar-Setup.exe"
    if not output_setup.exists():
        print(f"[!] Target setup binary not found: {output_setup}")
        return False

    print("\n" + "=" * 65)
    print(" [SUCCESS] Standalone Windows Setup (.exe) Created!")
    print(f" [*] Installer Location: {output_setup}")
    print(" [*] File Size: ~" + str(round(output_setup.stat().st_size / (1024 * 1024), 1)) + " MB")
    print(" [*] Ready to distribute to any regular Windows user!")
    print("=" * 65)
    return True

if __name__ == "__main__":
    success = build_installer()
    sys.exit(0 if success else 1)
