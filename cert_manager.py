import os
import subprocess
import sys
from pathlib import Path
from config import BASE_DIR

# Pillar 8: UTF-8 Console Safety Guard
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

CA_CERT_PATH = BASE_DIR / "certs" / "ca.crt"
CA_NAME = "EdgeSidecar Root CA"

# Flag to prevent console window from flashing on Windows
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

_ca_status_cache = None

def get_cached_ca_status() -> bool:
    """Returns cached CA status to avoid running subprocess on every 1-second poll."""
    global _ca_status_cache
    if _ca_status_cache is None:
        _ca_status_cache = is_ca_installed()
    return _ca_status_cache

def is_ca_installed() -> bool:
    """Checks if EdgeSidecar Root CA is installed in the Windows CurrentUser Root store."""
    global _ca_status_cache
    try:
        res = subprocess.run(
            ["certutil", "-user", "-verifystore", "Root", CA_NAME],
            capture_output=True,
            text=True,
            check=False,
            creationflags=CREATE_NO_WINDOW  # Completely suppresses black cmd window flashing
        )
        _ca_status_cache = (res.returncode == 0)
        return _ca_status_cache
    except Exception:
        _ca_status_cache = False
        return False

def install_ca() -> bool:
    """Installs EdgeSidecar Root CA into CurrentUser Root store (no admin required)."""
    global _ca_status_cache
    if not CA_CERT_PATH.exists():
        import ca
        ca.ensure_ca()

    try:
        res = subprocess.run(
            ["certutil", "-addstore", "-user", "Root", str(CA_CERT_PATH)],
            capture_output=True,
            text=True,
            check=False,
            creationflags=CREATE_NO_WINDOW  # Completely suppresses black cmd window flashing
        )
        _ca_status_cache = (res.returncode == 0)
        return _ca_status_cache
    except Exception as e:
        print(f"[CertManager] Install failed: {e}")
        _ca_status_cache = False
        return False

def uninstall_ca() -> bool:
    """Removes EdgeSidecar Root CA from CurrentUser Root store."""
    global _ca_status_cache
    try:
        res = subprocess.run(
            ["certutil", "-delstore", "-user", "Root", CA_NAME],
            capture_output=True,
            text=True,
            check=False,
            creationflags=CREATE_NO_WINDOW  # Completely suppresses black cmd window flashing
        )
        _ca_status_cache = False
        return res.returncode == 0
    except Exception as e:
        print(f"[CertManager] Uninstall failed: {e}")
        return False

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="EdgeSidecar Windows Root CA Manager")
    parser.add_argument("action", choices=["status", "install", "uninstall"], help="Action to perform")
    args = parser.parse_args()

    if args.action == "status":
        installed = is_ca_installed()
        print(f"EdgeSidecar Root CA Status: {'INSTALLED (Trusted)' if installed else 'NOT INSTALLED'}")
    elif args.action == "install":
        ok = install_ca()
        print("Installation successful!" if ok else "Installation failed.")
    elif args.action == "uninstall":
        ok = uninstall_ca()
        print("Uninstallation successful!" if ok else "Uninstallation failed.")
