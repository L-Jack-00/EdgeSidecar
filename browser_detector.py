import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Pillar 8: UTF-8 Console Safety Guard
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import BASE_DIR, EDGE_PATHS, CHROME_PATHS, BRAVE_PATHS, BIN_DIR

SETTINGS_FILE = BASE_DIR / "settings.json"

WHALE_PATHS = [
    os.path.expandvars(r"%LOCALAPPDATA%\Naver\Naver Whale\Application\whale.exe"),
    r"C:\Program Files\Naver\Naver Whale\Application\whale.exe",
    r"C:\Program Files (x86)\Naver\Naver Whale\Application\whale.exe",
]

PORTABLE_PATHS = [
    BIN_DIR / "chrome.exe",
    BIN_DIR / "ungoogled-chromium.exe",
    BIN_DIR / "msedge.exe",
    BIN_DIR / "Chromium" / "chrome.exe",
]

DEFAULT_SETTINGS = {
    "selected_browser": "auto",       # "auto", "edge", "chrome", "brave", "whale", "portable"
    "has_configured_browser": False,
    "last_used_path": "",
    "enable_cdp": True
}

def load_settings() -> Dict[str, Any]:
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return dict(DEFAULT_SETTINGS)

def save_settings(data: Dict[str, Any]):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Settings] Error saving settings: {e}")

def is_cdp_enabled() -> bool:
    return bool(load_settings().get("enable_cdp", True))

def set_cdp_enabled(enabled: bool):
    s = load_settings()
    s["enable_cdp"] = bool(enabled)
    save_settings(s)
    print(f"[Settings] CDP debugging port (9222) enabled set to: {s['enable_cdp']}")

def detect_portable_path() -> Optional[str]:
    from portable_engine import portable_manager
    p = portable_manager.get_portable_binary()
    if p:
        return str(p)
    for cand in PORTABLE_PATHS:
        if cand.exists() and cand.is_file():
            return str(cand)
    return None

def detect_first_existing(path_list: List[str]) -> Optional[str]:
    for p in path_list:
        if os.path.exists(p) and os.path.isfile(p):
            return p
    return None

def scan_all_browsers() -> List[Dict[str, Any]]:
    """Scans system and bin/ for all supported Chromium engines."""
    settings = load_settings()
    current_sel = settings.get("selected_browser", "auto")

    browsers = [
        {
            "id": "portable",
            "name": "포터블 크로뮴 (Portable Chromium)",
            "desc": "프로그램 내장 100% 완전 독립형 엔진 (bin/ 폴더)",
            "path": detect_portable_path(),
            "installed": False,
            "recommended": False
        },
        {
            "id": "edge",
            "name": "Microsoft Edge",
            "desc": "Windows 최적화 및 램 점유율 최저 엔진",
            "path": detect_first_existing(EDGE_PATHS),
            "installed": False,
            "recommended": True
        },
        {
            "id": "chrome",
            "name": "Google Chrome",
            "desc": "가장 표준적인 웹 호환성 엔진",
            "path": detect_first_existing(CHROME_PATHS),
            "installed": False,
            "recommended": False
        },
        {
            "id": "brave",
            "name": "Brave Browser",
            "desc": "강력한 개인정보 보호 엔진",
            "path": detect_first_existing(BRAVE_PATHS),
            "installed": False,
            "recommended": False
        },
        {
            "id": "whale",
            "name": "Naver Whale",
            "desc": "네이버 웨일 크로뮴 엔진",
            "path": detect_first_existing(WHALE_PATHS),
            "installed": False,
            "recommended": False
        }
    ]

    for b in browsers:
        b["installed"] = b["path"] is not None
        b["selected"] = (b["id"] == current_sel)

    return browsers

def resolve_selected_browser() -> Tuple[str, str]:
    """Resolves the user-configured browser or automatically chooses the best available."""
    settings = load_settings()
    selected_id = settings.get("selected_browser", "auto")
    browsers = scan_all_browsers()
    installed_browsers = [b for b in browsers if b["installed"]]

    if not installed_browsers:
        raise FileNotFoundError(
            "사용 가능한 웹 브라우저(Edge, Chrome, Brave, Whale 또는 포터블 크로뮴)를 찾을 수 없습니다."
        )

    # If user selected a specific browser and it's installed
    if selected_id != "auto":
        for b in installed_browsers:
            if b["id"] == selected_id:
                return b["path"], b["name"]

    # Fallback / Auto: Portable -> Edge -> Chrome -> Brave -> Whale -> first available
    priority = ["portable", "edge", "chrome", "brave", "whale"]
    for pid in priority:
        for b in installed_browsers:
            if b["id"] == pid:
                return b["path"], b["name"]

    # First available fallback
    first = installed_browsers[0]
    return first["path"], first["name"]

def set_browser_selection(browser_id: str):
    settings = load_settings()
    settings["selected_browser"] = browser_id
    settings["has_configured_browser"] = True
    save_settings(settings)
    print(f"[Settings] Selected browser set to: {browser_id}")

if __name__ == "__main__":
    print("Detected browsers:")
    for b in scan_all_browsers():
        status = f"INSTALLED at {b['path']}" if b['installed'] else "NOT INSTALLED"
        print(f" - {b['name']} ({b['id']}): {status}")
    path, name = resolve_selected_browser()
    print(f"\nResolved active browser: {name} ({path})")
