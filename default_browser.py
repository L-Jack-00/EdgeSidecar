"""
Windows Default Web Browser Registration and Handler for EdgeSidecar.
Enables EdgeSidecar to be recognized and selected as the system-wide Default Web Browser.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Tuple, Dict, Any

# Pillar 8: UTF-8 Console Safety Guard
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

PROG_ID = "EdgeSidecarHTML"
APP_NAME = "EdgeSidecar"
DISPLAY_NAME = "Edge Sidecar Browser"
APP_DESC = "Edge Sidecar Browser - Zero-Telemetry & Rule Engine Web Browser"

def get_installed_exe_path() -> Path:
    """Returns the most appropriate executable path for registration."""
    # 1. If running as a frozen executable
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve()
    
    # 2. Check if installed in standard LocalAppData location
    local_installed = Path(os.path.expandvars(r"%LOCALAPPDATA%\EdgeSidecar\EdgeSidecar.exe"))
    if local_installed.exists():
        return local_installed.resolve()

    # 3. Check dist directory in repo
    repo_dist = Path(__file__).parent / "dist" / "EdgeSidecar" / "EdgeSidecar.exe"
    if repo_dist.exists():
        return repo_dist.resolve()

    # 4. Fallback to current python interpreter or sys.executable
    return Path(sys.executable).resolve()

def is_registered_as_browser() -> bool:
    """Checks whether EdgeSidecar is registered in Windows StartMenuInternet and RegisteredApplications."""
    if sys.platform != "win32":
        return False
    try:
        import winreg
        # Check StartMenuInternet registration
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, rf"Software\Clients\StartMenuInternet\{APP_NAME}") as key:
            pass
        # Check RegisteredApplications registration
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\RegisteredApplications") as key:
            val, _ = winreg.QueryValueEx(key, APP_NAME)
            if not val:
                return False
        # Check ProgId registration
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{PROG_ID}\shell\open\command") as key:
            pass
        return True
    except Exception:
        return False

def is_current_default_browser() -> bool:
    """Checks if EdgeSidecar is currently selected as Windows Default Browser for HTTP/HTTPS."""
    if sys.platform != "win32":
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice") as key:
            prog_id, _ = winreg.QueryValueEx(key, "ProgId")
            return prog_id.lower() == PROG_ID.lower()
    except Exception:
        return False

def register_default_browser(exe_path: Path = None) -> bool:
    """
    Registers EdgeSidecar in HKCU so Windows recognizes it as a Web Browser in 'Default Apps'.
    No administrator privileges required (HKCU).
    """
    if sys.platform != "win32":
        return False

    if exe_path is None:
        exe_path = get_installed_exe_path()
    
    exe_str = str(exe_path)
    icon_str = f'"{exe_str}",0'
    cmd_str = f'"{exe_str}" "%1"'
    open_cmd_str = f'"{exe_str}"'

    try:
        import winreg

        # 1. Register ProgId in HKCU\Software\Classes\EdgeSidecarHTML
        prog_key_path = rf"Software\Classes\{PROG_ID}"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, prog_key_path) as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, "Edge Sidecar HTML Document")
            winreg.SetValueEx(k, "FriendlyTypeName", 0, winreg.REG_SZ, "Edge Sidecar HTML Document")
            winreg.SetValueEx(k, "AppUserModelId", 0, winreg.REG_SZ, APP_NAME)

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"{prog_key_path}\DefaultIcon") as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, icon_str)

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"{prog_key_path}\shell\open\command") as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, cmd_str)

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"{prog_key_path}\Application") as k:
            winreg.SetValueEx(k, "ApplicationName", 0, winreg.REG_SZ, DISPLAY_NAME)
            winreg.SetValueEx(k, "ApplicationIcon", 0, winreg.REG_SZ, icon_str)
            winreg.SetValueEx(k, "ApplicationDescription", 0, winreg.REG_SZ, APP_DESC)

        # 2. Register Applications\EdgeSidecar.exe
        app_exe_name = exe_path.name
        app_key_path = rf"Software\Classes\Applications\{app_exe_name}"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, app_key_path) as k:
            winreg.SetValueEx(k, "FriendlyAppName", 0, winreg.REG_SZ, DISPLAY_NAME)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"{app_key_path}\DefaultIcon") as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, icon_str)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"{app_key_path}\shell\open\command") as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, cmd_str)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"{app_key_path}\SupportedTypes") as k:
            for ext in [".htm", ".html", ".shtml", ".xhtml", ".xht"]:
                winreg.SetValueEx(k, ext, 0, winreg.REG_SZ, "")

        # 3. Register StartMenuInternet client
        smi_path = rf"Software\Clients\StartMenuInternet\{APP_NAME}"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, smi_path) as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, DISPLAY_NAME)
            winreg.SetValueEx(k, "LocalizedString", 0, winreg.REG_SZ, DISPLAY_NAME)

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"{smi_path}\DefaultIcon") as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, icon_str)

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"{smi_path}\shell\open\command") as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, open_cmd_str)

        # 4. Capabilities (File Associations & URL Associations)
        cap_path = rf"{smi_path}\Capabilities"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, cap_path) as k:
            winreg.SetValueEx(k, "ApplicationName", 0, winreg.REG_SZ, DISPLAY_NAME)
            winreg.SetValueEx(k, "ApplicationIcon", 0, winreg.REG_SZ, icon_str)
            winreg.SetValueEx(k, "ApplicationDescription", 0, winreg.REG_SZ, APP_DESC)
            winreg.SetValueEx(k, "StartMenuInternet", 0, winreg.REG_SZ, APP_NAME)

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"{cap_path}\FileAssociations") as k:
            for ext in [".htm", ".html", ".shtml", ".xhtml", ".xht"]:
                winreg.SetValueEx(k, ext, 0, winreg.REG_SZ, PROG_ID)

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"{cap_path}\URLAssociations") as k:
            winreg.SetValueEx(k, "http", 0, winreg.REG_SZ, PROG_ID)
            winreg.SetValueEx(k, "https", 0, winreg.REG_SZ, PROG_ID)
            winreg.SetValueEx(k, "ftp", 0, winreg.REG_SZ, PROG_ID)

        # 5. Register in RegisteredApplications
        reg_app_path = r"Software\RegisteredApplications"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_app_path) as k:
            winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, rf"Software\Clients\StartMenuInternet\{APP_NAME}\Capabilities")

        print(f"[DefaultBrowser] Successfully registered '{DISPLAY_NAME}' as browser handler for {exe_str}")
        return True
    except Exception as e:
        print(f"[DefaultBrowser] Error registering browser: {e}")
        return False

def unregister_default_browser() -> bool:
    """Removes all EdgeSidecar default browser registrations from HKCU."""
    if sys.platform != "win32":
        return False
    try:
        import winreg

        # Helper recursive key delete
        def delete_key_tree(root, path):
            try:
                with winreg.OpenKey(root, path, 0, winreg.KEY_ALL_ACCESS) as k:
                    while True:
                        try:
                            sub = winreg.EnumKey(k, 0)
                            delete_key_tree(root, f"{path}\\{sub}")
                        except OSError:
                            break
                winreg.DeleteKey(root, path)
            except OSError:
                pass

        delete_key_tree(winreg.HKEY_CURRENT_USER, rf"Software\Clients\StartMenuInternet\{APP_NAME}")
        delete_key_tree(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{PROG_ID}")
        delete_key_tree(winreg.HKEY_CURRENT_USER, rf"Software\Classes\Applications\EdgeSidecar.exe")

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\RegisteredApplications", 0, winreg.KEY_SET_VALUE) as k:
                winreg.DeleteValue(k, APP_NAME)
        except OSError:
            pass

        print("[DefaultBrowser] Successfully unregistered EdgeSidecar browser handlers.")
        return True
    except Exception as e:
        print(f"[DefaultBrowser] Error unregistering browser: {e}")
        return False

def open_default_apps_settings() -> bool:
    """
    Opens Windows Default Apps settings dialog so user can confirm EdgeSidecar as default.
    Windows 10/11 requires user action to change UserChoice hash.
    """
    if sys.platform != "win32":
        return False
    try:
        # Try direct app page first, fallback to general defaultapps
        commands = [
            ["explorer.exe", f"ms-settings:defaultapps?registeredAppMachine={APP_NAME}"],
            ["explorer.exe", "ms-settings:defaultapps"]
        ]
        for cmd in commands:
            try:
                subprocess.Popen(cmd, creationflags=CREATE_NO_WINDOW)
                return True
            except Exception:
                continue
        return False
    except Exception as e:
        print(f"[DefaultBrowser] Failed to open Windows Settings: {e}")
        return False

def get_browser_status() -> Dict[str, Any]:
    """Returns registration and system default status."""
    return {
        "registered": is_registered_as_browser(),
        "is_default": is_current_default_browser(),
        "prog_id": PROG_ID,
        "app_name": APP_NAME
    }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="EdgeSidecar Default Browser Manager")
    parser.add_argument("--register", action="store_true", help="Register as Windows browser")
    parser.add_argument("--unregister", action="store_true", help="Unregister from Windows")
    parser.add_argument("--settings", action="store_true", help="Open Windows Default Apps settings")
    parser.add_argument("--status", action="store_true", help="Show registration status")
    args = parser.parse_args()

    if args.register:
        success = register_default_browser()
        if success:
            open_default_apps_settings()
        sys.exit(0 if success else 1)
    elif args.unregister:
        success = unregister_default_browser()
        sys.exit(0 if success else 1)
    elif args.settings:
        open_default_apps_settings()
        sys.exit(0)
    else:
        status = get_browser_status()
        print(f"Status: {status}")
