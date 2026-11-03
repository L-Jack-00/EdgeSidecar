import json
import os
import shutil
import ssl
import sys
import threading
import time
import urllib.request
import zipfile
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Callable

# Pillar 8: UTF-8 Console Safety Guard
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import BASE_DIR, PROFILE_DIR

BIN_DIR = BASE_DIR / "bin"
VERSION_FILE = BIN_DIR / "version.json"

PORTABLE_CANDIDATES = [
    BIN_DIR / "chrome.exe",
    BIN_DIR / "ungoogled-chromium.exe",
    BIN_DIR / "msedge.exe",
    BIN_DIR / "Chromium" / "chrome.exe",
]

UPSTREAM_RELEASE_API = "https://api.github.com/repos/ungoogled-software/ungoogled-chromium-windows/releases/latest"

def _get_ssl_context():
    try:
        return ssl.create_default_context()
    except Exception:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

class PortableEngineManager:
    def __init__(self, bin_dir: Path = BIN_DIR):
        self.bin_dir = bin_dir
        self.bin_dir.mkdir(parents=True, exist_ok=True)
        self.swap_state = {
            "status": "idle",       # "idle", "downloading", "extracting", "done", "error"
            "progress": 0,
            "message": "준비됨"
        }
        self._lock = threading.Lock()

    def get_portable_binary(self) -> Optional[Path]:
        """Returns path to portable chromium binary if present in bin/."""
        for candidate in PORTABLE_CANDIDATES:
            if candidate.exists() and candidate.is_file():
                return candidate
        # Recursive search in subdirectories of bin/
        for root, _, files in os.walk(self.bin_dir):
            if "chrome.exe" in files:
                return Path(root) / "chrome.exe"
            if "ungoogled-chromium.exe" in files:
                return Path(root) / "ungoogled-chromium.exe"
        return None

    def is_portable_installed(self) -> bool:
        return self.get_portable_binary() is not None

    def get_installed_version(self) -> str:
        if VERSION_FILE.exists():
            try:
                with open(VERSION_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("version", "알 수 없음")
            except Exception:
                pass
        if self.is_portable_installed():
            return "내장 포터블 (버전 미기록)"
        return "미설치"

    def get_engine_info(self) -> Dict[str, Any]:
        portable_bin = self.get_portable_binary()
        installed_ver = self.get_installed_version()
        if portable_bin:
            return {
                "type": "portable",
                "installed": True,
                "version": installed_ver,
                "path": str(portable_bin),
                "name": f"포터블 크로뮴 ({installed_ver})",
                "status": "내장 엔진 가동 중 (100% 독립형)"
            }
        return {
            "type": "system",
            "installed": False,
            "version": "N/A",
            "path": "System Installed",
            "name": "시스템 브라우저 (Edge / Chrome)",
            "status": "OS 시스템 브라우저 연동 중"
        }

    def check_upstream_update(self) -> Dict[str, Any]:
        """Checks for latest security releases from upstream repository."""
        cur_ver = self.get_installed_version()
        try:
            ctx = _get_ssl_context()
            req = urllib.request.Request(
                UPSTREAM_RELEASE_API,
                headers={"User-Agent": "EdgeSidecar-Updater/1.2.1"}
            )
            try:
                resp = urllib.request.urlopen(req, timeout=6, context=ctx)
            except Exception:
                # SSL unverified fallback
                ctx2 = ssl._create_unverified_context()
                resp = urllib.request.urlopen(req, timeout=6, context=ctx2)

            data = json.loads(resp.read().decode("utf-8"))
            tag_name = data.get("tag_name", "Unknown")
            html_url = data.get("html_url", "")
            published_at = data.get("published_at", "")[:10]

            # Find x64 zip asset
            assets = data.get("assets", [])
            x64_asset = None
            for a in assets:
                name = a.get("name", "")
                if "windows_x64.zip" in name or ("x64" in name and name.endswith(".zip")):
                    x64_asset = a
                    break

            if not x64_asset and assets:
                x64_asset = assets[0]

            download_url = x64_asset.get("browser_download_url", "") if x64_asset else ""
            download_size = x64_asset.get("size", 0) if x64_asset else 0
            size_mb = round(download_size / (1024 * 1024), 1)

            has_update = (cur_ver != tag_name) or (not self.is_portable_installed())

            return {
                "success": True,
                "has_update": has_update,
                "current_version": cur_ver,
                "latest_version": tag_name,
                "download_url": download_url,
                "download_size_mb": size_mb,
                "release_date": published_at,
                "url": html_url,
                "status": f"최신 릴리즈 확인 완료 (v{tag_name}, {size_mb}MB)"
            }
        except Exception as e:
            return {
                "success": False,
                "has_update": False,
                "current_version": cur_ver,
                "latest_version": "확인 불가",
                "download_url": "",
                "download_size_mb": 0,
                "release_date": "",
                "status": f"최신 정보 조회 실패: {str(e)[:45]}"
            }

    def download_and_swap_engine(self, progress_callback: Optional[Callable[[int, str], None]] = None) -> Tuple[bool, str]:
        """Downloads the latest upstream portable Chromium zip, extracts, and swaps into bin/."""
        with self._lock:
            def update_progress(pct: int, msg: str):
                self.swap_state["progress"] = pct
                self.swap_state["message"] = msg
                if progress_callback:
                    try:
                        progress_callback(pct, msg)
                    except Exception:
                        pass

            try:
                self.swap_state["status"] = "downloading"
                update_progress(5, "최신 포터블 릴리즈 정보 조회 중...")

                info = self.check_upstream_update()
                if not info.get("success") or not info.get("download_url"):
                    err = f"업스트림 다운로드 URL을 찾을 수 없습니다: {info.get('status')}"
                    self.swap_state["status"] = "error"
                    update_progress(0, err)
                    return False, err

                dl_url = info["download_url"]
                tag_name = info["latest_version"]
                size_mb = info.get("download_size_mb", 0)
                zip_path = self.bin_dir / "portable_update_temp.zip"

                update_progress(10, f"다운로드 시작 (v{tag_name}, {size_mb} MB)...")

                ctx = ssl._create_unverified_context()
                req = urllib.request.Request(dl_url, headers={"User-Agent": "Mozilla/5.0 EdgeSidecar-Updater/1.2.1"})

                with urllib.request.urlopen(req, timeout=30, context=ctx) as resp, open(zip_path, "wb") as out_f:
                    total_len = int(resp.headers.get("Content-Length", 0)) or (int(size_mb * 1024 * 1024))
                    downloaded = 0
                    last_time = time.time()
                    last_downloaded = 0
                    speed_str = ""

                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        out_f.write(chunk)
                        downloaded += len(chunk)

                        now = time.time()
                        if now - last_time >= 0.5:
                            speed = (downloaded - last_downloaded) / (now - last_time) / (1024 * 1024)
                            speed_str = f" ({speed:.1f} MB/s)"
                            last_time = now
                            last_downloaded = downloaded

                            if total_len > 0:
                                pct = 10 + int((downloaded / total_len) * 70)
                                cur_mb = round(downloaded / (1024 * 1024), 1)
                                update_progress(pct, f"포터블 크로뮴 다운로드 중: {cur_mb}/{size_mb} MB{speed_str}")

                # Extraction phase
                self.swap_state["status"] = "extracting"
                update_progress(82, "다운로드 완료. 압축 해제 및 엔진 갈아끼우기 진행 중...")

                extract_dir = self.bin_dir / "extract_temp"
                if extract_dir.exists():
                    shutil.rmtree(extract_dir, ignore_errors=True)
                extract_dir.mkdir(parents=True, exist_ok=True)

                with zipfile.ZipFile(zip_path, "r") as zf:
                    zf.extractall(extract_dir)

                update_progress(92, "엔진 파일 동기화 및 바이너리 재배치 중...")

                # Find nested chrome.exe if inside a subfolder
                source_root = extract_dir
                subdirs = [d for d in extract_dir.iterdir() if d.is_dir()]
                if len(subdirs) == 1 and ((subdirs[0] / "chrome.exe").exists() or (subdirs[0] / "ungoogled-chromium.exe").exists()):
                    source_root = subdirs[0]

                # Move files into bin_dir
                for item in source_root.iterdir():
                    target = self.bin_dir / item.name
                    if target.exists():
                        if target.is_dir():
                            shutil.rmtree(target, ignore_errors=True)
                        else:
                            try:
                                target.unlink(missing_ok=True)
                            except Exception:
                                pass
                    try:
                        shutil.move(str(item), str(target))
                    except Exception:
                        pass

                # Clean up temp files
                shutil.rmtree(extract_dir, ignore_errors=True)
                if zip_path.exists():
                    zip_path.unlink(missing_ok=True)

                # Record version metadata
                version_meta = {
                    "version": tag_name,
                    "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "source_url": dl_url
                }
                with open(VERSION_FILE, "w", encoding="utf-8") as f:
                    json.dump(version_meta, f, indent=2, ensure_ascii=False)

                # Switch browser selection to portable in settings.json
                from browser_detector import set_browser_selection
                set_browser_selection("portable")

                msg = f"최신 포터블 크로뮴(v{tag_name}) 교체 및 기본 엔진 설정 완료!"
                self.swap_state["status"] = "done"
                update_progress(100, msg)
                return True, msg

            except Exception as e:
                err_msg = f"포터블 크로뮴 교체 실패: {str(e)}"
                self.swap_state["status"] = "error"
                update_progress(0, err_msg)
                return False, err_msg

    def reset_disposable_session(self, profile_name: str = "default") -> bool:
        """Safely wipes cache, cookies, and local session storage for disposable privacy."""
        target_sub = "Default" if profile_name.lower() == "default" else profile_name.capitalize()
        profile_path = PROFILE_DIR / target_sub / "Default"
        if not profile_path.exists():
            return True

        targets_to_clear = [
            profile_path / "Cache",
            profile_path / "Code Cache",
            profile_path / "GPUCache",
            profile_path / "Service Worker",
            profile_path / "IndexedDB",
            profile_path / "Network" / "Cookies",
            profile_path / "Network" / "Cookies-journal",
            profile_path / "Sessions",
            profile_path / "Session Storage"
        ]

        cleared_count = 0
        for t in targets_to_clear:
            try:
                if t.is_dir():
                    shutil.rmtree(t, ignore_errors=True)
                    cleared_count += 1
                elif t.is_file():
                    t.unlink(missing_ok=True)
                    cleared_count += 1
            except Exception:
                pass

        print(f"[PortableEngine] Disposable session reset complete ({cleared_count} targets cleared).")
        return True

portable_manager = PortableEngineManager()

if __name__ == "__main__":
    info = portable_manager.get_engine_info()
    print("Engine info:", info)
    print("Update check:", portable_manager.check_upstream_update())
