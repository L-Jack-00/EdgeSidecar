import os
import sys
from pathlib import Path

# Pillar 8: UTF-8 Console Safety Guard
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Determine runtime directory vs frozen resource directory
if getattr(sys, "frozen", False):
    RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    BASE_DIR = Path(sys.executable).parent.resolve()
else:
    RESOURCE_DIR = Path(__file__).parent.resolve()
    BASE_DIR = RESOURCE_DIR

PROFILE_DIR = BASE_DIR / "profile"
RULES_FILE = BASE_DIR / "rules.json"
BIN_DIR = BASE_DIR / "bin"

PROXY_HOST = "127.0.0.1"
PROXY_PORT = 8899
CDP_PORT = 9222

# Microsoft Telemetry, Tracking, MSN, Shopping, and Bing endpoints to drop
MS_BLOCKED_DOMAINS = [
    "browser.pipe.aria.microsoft.com",
    "pipe.aria.microsoft.com",
    "activity.windows.com",
    "edge.activity.windows.com",
    "edge-enterprise.activity.windows.com",
    "data.microsoft.com",
    "v10.events.data.microsoft.com",
    "v20.events.data.microsoft.com",
    "self.events.data.microsoft.com",
    "config.edge.skype.com",
    "msedge.net",
    "telemetry.microsoft.com",
    "nexusrules.officeapps.live.com",
    "msn.com",
    "assets.msn.com",
    "ntp.msn.com",
    "api.msn.com",
    "shopping.microsoft.com",
    "edge.microsoft.com",
    "edge-shopping.microsoft.com",
    "edgeservices.bing.com",
    "rewards.bing.com",
    "copilot.microsoft.com",
    "cortana.ai",
]

# Browser executable candidates in prioritized search order
EDGE_PATHS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
]

CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
]

BRAVE_PATHS = [
    r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
]
