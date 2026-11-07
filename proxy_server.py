import asyncio
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List

# Pillar 8: UTF-8 Console Safety Guard
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import PROXY_HOST, PROXY_PORT, MS_BLOCKED_DOMAINS, RESOURCE_DIR, BASE_DIR
from rules import RuleEngine
from harness_core import supervisor, HarnessState
from portable_engine import portable_manager
from browser_detector import scan_all_browsers, set_browser_selection, resolve_selected_browser, is_cdp_enabled, set_cdp_enabled
import cert_manager
import default_browser

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

def open_url_in_running_browser(target_url: str) -> bool:
    """Invokes browser single-instance mechanism to open URL in existing window."""
    try:
        from launcher import setup_isolated_profile
        browser_bin, _ = resolve_selected_browser()
        profile_path = setup_isolated_profile("default")
        subprocess.Popen(
            [browser_bin, f"--user-data-dir={profile_path}", target_url],
            creationflags=CREATE_NO_WINDOW
        )
        return True
    except Exception as e:
        print(f"[Proxy] Error opening URL {target_url} in running browser: {e}")
        return False

DASHBOARD_HTML_PATH = RESOURCE_DIR / "dashboard.html"
if not DASHBOARD_HTML_PATH.exists():
    DASHBOARD_HTML_PATH = BASE_DIR / "dashboard.html"

class TrafficLogger:
    def __init__(self, max_items: int = 200):
        self.max_items = max_items
        self.items: List[Dict[str, Any]] = []
        self.blocked_ms_count = 0
        self.modified_count = 0
        self.total_count = 0

    def log(self, method: str, url: str, status: int = 200, blocked_ms: bool = False, modified: bool = False):
        self.total_count += 1
        if blocked_ms:
            self.blocked_ms_count += 1
        if modified:
            self.modified_count += 1

        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        entry = {
            "time": now_str,
            "method": method,
            "url": url,
            "status": status,
            "blocked_ms": blocked_ms,
            "modified": modified,
        }
        self.items.insert(0, entry)
        if len(self.items) > self.max_items:
            self.items.pop()

    def get_stats(self, active_rules: int) -> Dict[str, Any]:
        engine_info = portable_manager.get_engine_info()
        try:
            _, browser_name = resolve_selected_browser()
        except Exception:
            browser_name = "미지정"

        return {
            "total": self.total_count,
            "blocked_ms": self.blocked_ms_count,
            "modified": self.modified_count,
            "active_rules": active_rules,
            "state": supervisor.state.name,
            "ca_installed": cert_manager.get_cached_ca_status(),
            "engine": engine_info,
            "active_browser": browser_name,
            "enable_cdp": is_cdp_enabled()
        }

logger = TrafficLogger()
rule_engine = RuleEngine()

def is_ms_blocked(host: str) -> bool:
    host_clean = host.split(":")[0].lower()
    for domain in MS_BLOCKED_DOMAINS:
        if domain.startswith("*."):
            suffix = domain[2:].lower()
            if host_clean.endswith(suffix):
                return True
        elif host_clean == domain.lower() or host_clean.endswith("." + domain.lower()):
            return True
    return False

async def handle_dashboard_request(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, path: str):
    if path == "/" or path == "/dashboard":
        if DASHBOARD_HTML_PATH.exists():
            with open(DASHBOARD_HTML_PATH, "r", encoding="utf-8") as f:
                content = f.read().encode("utf-8")
            resp = (
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: text/html; charset=utf-8\r\n"
                b"Content-Length: " + str(len(content)).encode() + b"\r\n"
                b"Connection: close\r\n\r\n" + content
            )
        else:
            resp = b"HTTP/1.1 404 Not Found\r\n\r\nDashboard missing"
        writer.write(resp)
        await writer.drain()
        return

    if path == "/api/stats":
        active_cnt = sum(1 for r in rule_engine.get_rules() if r.get("enabled", True))
        data = json.dumps(logger.get_stats(active_cnt)).encode("utf-8")
        resp = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: application/json\r\n"
            b"Access-Control-Allow-Origin: *\r\n"
            b"Content-Length: " + str(len(data)).encode() + b"\r\n"
            b"Connection: close\r\n\r\n" + data
        )
        writer.write(resp)
        await writer.drain()
        return

    if path == "/api/traffic":
        data = json.dumps(logger.items).encode("utf-8")
        resp = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: application/json\r\n"
            b"Access-Control-Allow-Origin: *\r\n"
            b"Content-Length: " + str(len(data)).encode() + b"\r\n"
            b"Connection: close\r\n\r\n" + data
        )
        writer.write(resp)
        await writer.drain()
        return

    if path == "/api/rules":
        data = json.dumps(rule_engine.get_rules()).encode("utf-8")
        resp = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: application/json\r\n"
            b"Access-Control-Allow-Origin: *\r\n"
            b"Content-Length: " + str(len(data)).encode() + b"\r\n"
            b"Connection: close\r\n\r\n" + data
        )
        writer.write(resp)
        await writer.drain()
        return

    if path.startswith("/api/rules/toggle"):
        m = re.search(r"id=([^&]+)", path)
        if m:
            import urllib.parse
            rule_id = urllib.parse.unquote(m.group(1))
            rule_engine.toggle_rule(rule_id)
        resp = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: application/json\r\n"
            b"Access-Control-Allow-Origin: *\r\n"
            b"Content-Length: 15\r\n"
            b"Connection: close\r\n\r\n"
            b'{"status":"ok"}'
        )
        writer.write(resp)
        await writer.drain()
        return

    # Browser Engine Detection & Selection API
    if path == "/api/browser/list":
        browsers = scan_all_browsers()
        data = json.dumps(browsers).encode("utf-8")
        resp = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: application/json\r\n"
            b"Access-Control-Allow-Origin: *\r\n"
            b"Content-Length: " + str(len(data)).encode() + b"\r\n"
            b"Connection: close\r\n\r\n" + data
        )
        writer.write(resp)
        await writer.drain()
        return

    if path.startswith("/api/browser/select"):
        m = re.search(r"id=([^&]+)", path)
        if m:
            import urllib.parse
            b_id = urllib.parse.unquote(m.group(1))
            set_browser_selection(b_id)
        resp = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: application/json\r\n"
            b"Access-Control-Allow-Origin: *\r\n"
            b"Content-Length: 15\r\n"
            b"Connection: close\r\n\r\n"
            b'{"status":"ok"}'
        )
        writer.write(resp)
        await writer.drain()
        return

    if path == "/api/ping":
        data = json.dumps({"status": "ok", "app": "EdgeSidecar", "version": "1.3.3"}).encode("utf-8")
        resp = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: application/json\r\n"
            b"Access-Control-Allow-Origin: *\r\n"
            b"Content-Length: " + str(len(data)).encode() + b"\r\n"
            b"Connection: close\r\n\r\n" + data
        )
        writer.write(resp)
        await writer.drain()
        return

    if path.startswith("/api/open"):
        import urllib.parse
        m = re.search(r"[?&]url=([^&]+)", path)
        target_url = None
        if m:
            target_url = urllib.parse.unquote(m.group(1))
        
        opened = False
        if target_url:
            opened = open_url_in_running_browser(target_url)
        
        data = json.dumps({"status": "ok" if opened else "error", "opened": target_url}).encode("utf-8")
        resp = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: application/json\r\n"
            b"Access-Control-Allow-Origin: *\r\n"
            b"Content-Length: " + str(len(data)).encode() + b"\r\n"
            b"Connection: close\r\n\r\n" + data
        )
        writer.write(resp)
        await writer.drain()
        return

    if path == "/api/default_browser/status":
        data = json.dumps(default_browser.get_browser_status()).encode("utf-8")
        resp = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: application/json\r\n"
            b"Access-Control-Allow-Origin: *\r\n"
            b"Content-Length: " + str(len(data)).encode() + b"\r\n"
            b"Connection: close\r\n\r\n" + data
        )
        writer.write(resp)
        await writer.drain()
        return

    if path == "/api/default_browser/register":
        ok = default_browser.register_default_browser()
        if ok:
            default_browser.open_default_apps_settings()
        data = json.dumps({"status": "ok" if ok else "error", "registered": ok}).encode("utf-8")
        resp = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: application/json\r\n"
            b"Access-Control-Allow-Origin: *\r\n"
            b"Content-Length: " + str(len(data)).encode() + b"\r\n"
            b"Connection: close\r\n\r\n" + data
        )
        writer.write(resp)
        await writer.drain()
        return

    if path == "/api/default_browser/open_settings":
        ok = default_browser.open_default_apps_settings()
        data = json.dumps({"status": "ok" if ok else "error"}).encode("utf-8")
        resp = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: application/json\r\n"
            b"Access-Control-Allow-Origin: *\r\n"
            b"Content-Length: " + str(len(data)).encode() + b"\r\n"
            b"Connection: close\r\n\r\n" + data
        )
        writer.write(resp)
        await writer.drain()
        return

    if path == "/api/settings/cdp":
        data = json.dumps({"enable_cdp": is_cdp_enabled()}).encode("utf-8")
        resp = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: application/json\r\n"
            b"Access-Control-Allow-Origin: *\r\n"
            b"Content-Length: " + str(len(data)).encode() + b"\r\n"
            b"Connection: close\r\n\r\n" + data
        )
        writer.write(resp)
        await writer.drain()
        return

    if path.startswith("/api/settings/toggle_cdp"):
        cur = is_cdp_enabled()
        set_cdp_enabled(not cur)
        data = json.dumps({"enable_cdp": not cur}).encode("utf-8")
        resp = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: application/json\r\n"
            b"Access-Control-Allow-Origin: *\r\n"
            b"Content-Length: " + str(len(data)).encode() + b"\r\n"
            b"Connection: close\r\n\r\n" + data
        )
        writer.write(resp)
        await writer.drain()
        return

    if path == "/api/portable/status":
        data = json.dumps(portable_manager.get_engine_info()).encode("utf-8")
        resp = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: application/json\r\n"
            b"Access-Control-Allow-Origin: *\r\n"
            b"Content-Length: " + str(len(data)).encode() + b"\r\n"
            b"Connection: close\r\n\r\n" + data
        )
        writer.write(resp)
        await writer.drain()
        return

    if path == "/api/portable/check_update":
        loop = asyncio.get_running_loop()
        update_info = await loop.run_in_executor(None, portable_manager.check_upstream_update)
        data = json.dumps(update_info).encode("utf-8")
        resp = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: application/json\r\n"
            b"Access-Control-Allow-Origin: *\r\n"
            b"Content-Length: " + str(len(data)).encode() + b"\r\n"
            b"Connection: close\r\n\r\n" + data
        )
        writer.write(resp)
        await writer.drain()
        return

    if path == "/api/portable/swap":
        if portable_manager.swap_state.get("status") not in ("downloading", "extracting"):
            threading.Thread(target=portable_manager.download_and_swap_engine, daemon=True).start()
        data = json.dumps({"status": "started"}).encode("utf-8")
        resp = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: application/json\r\n"
            b"Access-Control-Allow-Origin: *\r\n"
            b"Content-Length: " + str(len(data)).encode() + b"\r\n"
            b"Connection: close\r\n\r\n" + data
        )
        writer.write(resp)
        await writer.drain()
        return

    if path == "/api/portable/progress":
        data = json.dumps(portable_manager.swap_state).encode("utf-8")
        resp = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: application/json\r\n"
            b"Access-Control-Allow-Origin: *\r\n"
            b"Content-Length: " + str(len(data)).encode() + b"\r\n"
            b"Connection: close\r\n\r\n" + data
        )
        writer.write(resp)
        await writer.drain()
        return

    if path.startswith("/api/session/reset"):
        portable_manager.reset_disposable_session()
        resp = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: application/json\r\n"
            b"Access-Control-Allow-Origin: *\r\n"
            b"Content-Length: 21\r\n"
            b"Connection: close\r\n\r\n"
            b'{"status":"cleared"}'
        )
        writer.write(resp)
        await writer.drain()
        return

    if path == "/api/ca/status":
        data = json.dumps({"installed": cert_manager.get_cached_ca_status()}).encode("utf-8")
        resp = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: application/json\r\n"
            b"Access-Control-Allow-Origin: *\r\n"
            b"Content-Length: " + str(len(data)).encode() + b"\r\n"
            b"Connection: close\r\n\r\n" + data
        )
        writer.write(resp)
        await writer.drain()
        return

    if path == "/api/ca/install":
        ok = cert_manager.install_ca()
        data = json.dumps({"success": ok, "installed": cert_manager.get_cached_ca_status()}).encode("utf-8")
        resp = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: application/json\r\n"
            b"Access-Control-Allow-Origin: *\r\n"
            b"Content-Length: " + str(len(data)).encode() + b"\r\n"
            b"Connection: close\r\n\r\n" + data
        )
        writer.write(resp)
        await writer.drain()
        return

    if path == "/api/ca/uninstall":
        ok = cert_manager.uninstall_ca()
        data = json.dumps({"success": ok, "installed": cert_manager.get_cached_ca_status()}).encode("utf-8")
        resp = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: application/json\r\n"
            b"Access-Control-Allow-Origin: *\r\n"
            b"Content-Length: " + str(len(data)).encode() + b"\r\n"
            b"Connection: close\r\n\r\n" + data
        )
        writer.write(resp)
        await writer.drain()
        return

    if path == "/api/pause":
        supervisor.pause()
        resp = b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n{\"state\":\"PAUSED\"}"
        writer.write(resp)
        await writer.drain()
        return

    if path == "/api/resume":
        supervisor.resume()
        resp = b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n{\"state\":\"RUNNING\"}"
        writer.write(resp)
        await writer.drain()
        return

    if path == "/api/shutdown":
        resp = b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n{\"state\":\"SHUTTING_DOWN\"}"
        writer.write(resp)
        await writer.drain()
        asyncio.get_event_loop().call_later(0.5, supervisor.emergency_stop)
        return

    writer.write(b"HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\n\r\n")
    await writer.drain()

async def tunnel_streams(reader_a: asyncio.StreamReader, writer_a: asyncio.StreamWriter,
                         reader_b: asyncio.StreamReader, writer_b: asyncio.StreamWriter):
    async def forward(src, dst):
        try:
            while not supervisor.is_stopped():
                await supervisor.wait_if_paused()
                data = await src.read(65536)
                if not data:
                    break
                dst.write(data)
                await dst.drain()
        except Exception:
            pass
        finally:
            try:
                dst.close()
            except Exception:
                pass

    t1 = asyncio.create_task(forward(reader_a, writer_b))
    t2 = asyncio.create_task(forward(reader_b, writer_a))
    done, pending = await asyncio.wait([t1, t2], return_when=asyncio.FIRST_COMPLETED)
    for t in pending:
        t.cancel()
    try:
        writer_a.close()
    except Exception:
        pass
    try:
        writer_b.close()
    except Exception:
        pass

async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    try:
        await supervisor.wait_if_paused()
        req_line = await reader.readline()
        if not req_line:
            writer.close()
            return

        line_str = req_line.decode("latin1").strip()
        parts = line_str.split()
        if len(parts) < 2:
            writer.close()
            return

        method, target = parts[0], parts[1]

        headers = {}
        while True:
            h_line = await reader.readline()
            if not h_line or h_line == b"\r\n":
                break
            try:
                k, v = h_line.decode("latin1").split(":", 1)
                headers[k.strip().lower()] = v.strip()
            except ValueError:
                continue

        host_header = headers.get("host", target)

        if host_header.startswith("127.0.0.1") or host_header.startswith("localhost") or host_header.startswith("sidecar.local"):
            path = target
            if path.startswith("http://") or path.startswith("https://"):
                path = "/" + "/".join(path.split("/")[3:])
            await handle_dashboard_request(reader, writer, path)
            writer.close()
            return

        if is_ms_blocked(host_header):
            if method == "CONNECT":
                logger.log("CONNECT", f"https://{host_header}", status=403, blocked_ms=True)
                writer.write(b"HTTP/1.1 403 Forbidden\r\nConnection: close\r\nContent-Length: 0\r\n\r\n")
            else:
                logger.log(method, target, status=204, blocked_ms=True)
                writer.write(b"HTTP/1.1 204 No Content\r\nConnection: close\r\n\r\n")
            await writer.drain()
            writer.close()
            return

        if method == "CONNECT":
            if ":" in target:
                dest_host, dest_port = target.split(":")
                dest_port = int(dest_port)
            else:
                dest_host, dest_port = target, 443

            logger.log("CONNECT", f"https://{dest_host}:{dest_port}", status=200)

            try:
                upstream_reader, upstream_writer = await asyncio.wait_for(
                    asyncio.open_connection(dest_host, dest_port),
                    timeout=10.0
                )
            except Exception:
                writer.write(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
                await writer.drain()
                writer.close()
                return

            writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            await writer.drain()

            await tunnel_streams(reader, writer, upstream_reader, upstream_writer)
            return

        else:
            logger.log(method, target, status=200)
            if ":" in host_header:
                dest_host, dest_port = host_header.split(":")
                dest_port = int(dest_port)
            else:
                dest_host, dest_port = host_header, 80

            try:
                upstream_reader, upstream_writer = await asyncio.wait_for(
                    asyncio.open_connection(dest_host, dest_port),
                    timeout=10.0
                )
            except Exception:
                writer.write(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
                await writer.drain()
                writer.close()
                return

            upstream_writer.write(req_line)
            for k, v in headers.items():
                upstream_writer.write(f"{k}: {v}\r\n".encode("latin1"))
            upstream_writer.write(b"\r\n")
            await upstream_writer.drain()

            await tunnel_streams(reader, writer, upstream_reader, upstream_writer)
            return

    except Exception:
        pass
    finally:
        try:
            writer.close()
        except Exception:
            pass

async def start_proxy_server(host=PROXY_HOST, port=PROXY_PORT):
    server = await asyncio.start_server(handle_client, host, port)
    print(f"[Sidecar Proxy] Running on http://{host}:{port}")
    print(f"[Sidecar Proxy] Dashboard available at http://{host}:{port}/dashboard")
    return server

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    server = loop.run_until_complete(start_proxy_server())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
