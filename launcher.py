import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Tuple

# Pillar 8: UTF-8 Console Safety Guard
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import PROFILE_DIR, PROXY_PORT, CDP_PORT
from browser_detector import resolve_selected_browser, is_cdp_enabled

# Backward-compatible alias
resolve_browser_binary = resolve_selected_browser

# Multi-Profile Presets
PROFILE_PRESETS = {
    "default": "Default",        # Clean Daily Browsing (Zero MS Bloat)
    "developer": "Developer",    # Deep Packet Analysis & Development Profile
    "isolated": "Isolated"       # Disposable Ephemeral Profile
}

def setup_isolated_profile(profile_key: str = "default") -> Path:
    """Pre-configures isolated profile sandbox to enable Chrome extensions and kill MS bloat."""
    sub_name = PROFILE_PRESETS.get(profile_key.lower(), "Default")
    target_profile_dir = PROFILE_DIR / sub_name
    default_dir = target_profile_dir / "Default"
    default_dir.mkdir(parents=True, exist_ok=True)
    pref_file = default_dir / "Preferences"

    prefs = {
        "browser": {
            "has_seen_welcome_page": True,
            "check_default_browser": False
        },
        "extensions": {
            "ui": {
                "developer_mode": True
            }
        },
        "edge": {
            "shopping": {
                "shopping_assistant_enabled": False
            },
            "fre": {
                "has_user_seen_fre": True
            },
            "webstore": {
                "allowed": True
            }
        },
        "sync": {
            "has_setup_completed": False
        },
        "ntp": {
            "num_personal_suggestions": 0
        }
    }

    if pref_file.exists():
        try:
            with open(pref_file, "r", encoding="utf-8") as f:
                existing = json.load(f)
            existing.setdefault("edge", {}).setdefault("webstore", {})["allowed"] = True
            existing.setdefault("ntp", {})["num_personal_suggestions"] = 0
            with open(pref_file, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2)
        except Exception:
            pass
    else:
        with open(pref_file, "w", encoding="utf-8") as f:
            json.dump(prefs, f, indent=2)

    return target_profile_dir

def launch_edge(profile_name: str = "default", headless: bool = False, extra_urls: list = None) -> subprocess.Popen:
    browser_bin, flavor = resolve_selected_browser()
    profile_path = setup_isolated_profile(profile_name)

    args = [
        browser_bin,
        f"--user-data-dir={profile_path}",
    ]

    if is_cdp_enabled():
        args.append(f"--remote-debugging-port={CDP_PORT}")

    args.extend([
        f"--proxy-server=http://127.0.0.1:{PROXY_PORT}",
        # Zero Bloatware & Telemetry flags
        "--disable-features=msEdgeSidebarV2,msHub,msHubApps,msEdgeShoppingAssistant,msEdgeCollections,EdgeAssetDelivery,msVisualSearch,msEdgeInlineCompose,msEdgeFre,msDefaultSearchEngineGroupPolicy,msEdgeDiscoverButton",
        "--disable-sync",
        "--disable-background-networking",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-search-engine-choice-screen",
        "--disable-background-mode",
        "--no-service-autorun",
        "--disable-ntp-popular-sites",
        "--extension-mime-request-handling=always-prompt-for-install",
    ])

    if headless:
        args.append("--headless=new")

    # URL determination: If extra_urls are provided (e.g. from external link clicks), open them.
    # Otherwise open dashboard by default.
    if extra_urls and len(extra_urls) > 0:
        urls = list(extra_urls)
    else:
        urls = [f"http://127.0.0.1:{PROXY_PORT}/dashboard"]

    args.extend(urls)

    print(f"[Launcher] Launching [{flavor}] (Profile: '{profile_name}') with {len(args)} flags...")
    proc = subprocess.Popen(args)
    return proc

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Edge Sidecar Launcher")
    parser.add_argument("--profile", default="default", choices=["default", "developer", "isolated"], help="Profile preset")
    parser.add_argument("--headless", action="store_true", help="Launch in headless mode")
    args = parser.parse_args()

    p = launch_edge(profile_name=args.profile, headless=args.headless)
    print(f"Browser started, PID={p.pid}")
