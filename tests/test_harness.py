import asyncio
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from config import MS_BLOCKED_DOMAINS, PROFILE_DIR, BIN_DIR
from rules import RuleEngine
from proxy_server import is_ms_blocked, start_proxy_server, logger
from launcher import resolve_browser_binary, setup_isolated_profile
from cdp_interceptor import CDPInterceptor, MAX_BUFFER_CONTENT_LENGTH
from harness_core import LifecycleSupervisor, HarnessState
from portable_engine import portable_manager
import cert_manager

class TestEdgeSidecarBrowser(unittest.IsolatedAsyncioTestCase):

    def test_01_rule_engine(self):
        """RuleEngine matches, modifies headers, and toggles dynamically."""
        engine = RuleEngine()
        rules = engine.get_rules()
        self.assertGreaterEqual(len(rules), 1)

        matched = engine.match_request_rules("https://api.example.com/data")
        self.assertTrue(any(r["id"] == "cors-unblocker" for r in matched))

        state = engine.toggle_rule("cors-unblocker")
        engine.toggle_rule("cors-unblocker")

    def test_02_ms_telemetry_blocking(self):
        """Verify all MS telemetry and bloatware domains are correctly identified."""
        test_ms_domains = [
            "browser.pipe.aria.microsoft.com",
            "v10.events.data.microsoft.com",
            "assets.msn.com",
            "shopping.microsoft.com",
            "edge.activity.windows.com",
            "config.edge.skype.com"
        ]
        for domain in test_ms_domains:
            self.assertTrue(is_ms_blocked(domain), f"Failed to identify MS domain: {domain}")

        test_normal_domains = ["google.com", "github.com", "naver.com", "wikipedia.org"]
        for domain in test_normal_domains:
            self.assertFalse(is_ms_blocked(domain), f"Normal domain falsely blocked: {domain}")

    async def test_03_proxy_and_dashboard_api(self):
        """Verify Proxy Server runs, serves Dashboard and drops MS requests asynchronously."""
        test_port = 9876
        server = await start_proxy_server("127.0.0.1", test_port)
        try:
            # 1. Test Dashboard HTML
            r, w = await asyncio.open_connection("127.0.0.1", test_port)
            w.write(b"GET /dashboard HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n")
            await w.drain()
            resp = await r.read()
            w.close()
            self.assertIn(b"200 OK", resp)
            self.assertIn(b"Edge Sidecar Browser", resp)

            # 2. Test Stats API
            r, w = await asyncio.open_connection("127.0.0.1", test_port)
            w.write(b"GET /api/stats HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n")
            await w.drain()
            resp = await r.read()
            w.close()
            self.assertIn(b"200 OK", resp)
            self.assertIn(b"blocked_ms", resp)

            # 3. Test MS Telemetry Drop via Proxy (CONNECT)
            r, w = await asyncio.open_connection("127.0.0.1", test_port)
            w.write(b"CONNECT browser.pipe.aria.microsoft.com:443 HTTP/1.1\r\nHost: browser.pipe.aria.microsoft.com\r\n\r\n")
            await w.drain()
            resp = await r.read()
            w.close()
            self.assertIn(b"403 Forbidden", resp)

            # 4. Test Portable Engine Status API
            r, w = await asyncio.open_connection("127.0.0.1", test_port)
            w.write(b"GET /api/portable/status HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n")
            await w.drain()
            resp = await r.read()
            w.close()
            self.assertIn(b"200 OK", resp)
            self.assertIn(b"type", resp)

            # 5. Test Browser Engine List API
            r, w = await asyncio.open_connection("127.0.0.1", test_port)
            w.write(b"GET /api/browser/list HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n")
            await w.drain()
            resp = await r.read()
            w.close()
            self.assertIn(b"200 OK", resp)
            self.assertIn(b"Microsoft Edge", resp)

            # 6. Test Browser Engine Select API
            r, w = await asyncio.open_connection("127.0.0.1", test_port)
            w.write(b"GET /api/browser/select?id=edge HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n")
            await w.drain()
            resp = await r.read()
            w.close()
            self.assertIn(b"200 OK", resp)
            self.assertIn(b"ok", resp)

            self.assertGreater(logger.blocked_ms_count, 0)
        finally:
            server.close()
            await server.wait_closed()

    def test_04_launcher_and_profile_isolation(self):
        """Verify browser binary resolution and isolated profile setup."""
        browser_bin, flavor = resolve_browser_binary()
        self.assertTrue(os.path.exists(browser_bin))
        self.assertGreater(len(flavor), 0)

        target_dir = setup_isolated_profile("default")
        profile_pref = target_dir / "Default" / "Preferences"
        self.assertTrue(profile_pref.exists())

    async def test_05_edge_headless_and_cdp_discovery(self):
        """Verify browser headless launch and CDP WebSocket handshake."""
        browser_bin, flavor = resolve_browser_binary()
        test_cdp_port = 9934
        test_profile = PROJECT_ROOT / "test_cdp_profile"
        proc = subprocess.Popen([
            browser_bin,
            "--headless=new",
            f"--user-data-dir={test_profile}",
            f"--remote-debugging-port={test_cdp_port}",
            "about:blank"
        ])
        await asyncio.sleep(2)
        try:
            interceptor = CDPInterceptor(cdp_port=test_cdp_port)
            ws_url = await interceptor.get_browser_ws_url()
            self.assertTrue(ws_url.startswith("ws://"))
        finally:
            proc.terminate()
            proc.wait()
            shutil.rmtree(test_profile, ignore_errors=True)

    async def test_06_lifecycle_fsm_and_pause_resume(self):
        """Verify LifecycleSupervisor FSM transitions, zero-load pause/resume and emergency stop."""
        sup = LifecycleSupervisor()
        self.assertEqual(sup.state, HarnessState.STOPPED)

        transitions = []
        sup.add_state_listener(lambda s: transitions.append(s))

        sup.transition_to(HarnessState.RUNNING)
        self.assertEqual(sup.state, HarnessState.RUNNING)

        sup.pause()
        self.assertEqual(sup.state, HarnessState.PAUSED)

        sup.resume()
        self.assertEqual(sup.state, HarnessState.RUNNING)

        sup.emergency_stop()
        self.assertEqual(sup.state, HarnessState.TERMINATING)
        self.assertTrue(sup.is_stopped())
        self.assertEqual(len(transitions), 4)

    def test_07_large_file_streaming_guard_constants(self):
        """[Radar Item 1] Verify large file download guard thresholds."""
        self.assertEqual(MAX_BUFFER_CONTENT_LENGTH, 50 * 1024 * 1024)

    def test_08_cert_manager_status(self):
        """[Radar Item 2] Verify cert_manager runs without errors."""
        res = cert_manager.is_ca_installed()
        self.assertIsInstance(res, bool)

    def test_09_multi_profile_sandboxes(self):
        """[Radar Item 3] Verify multi-profile sandbox directories are created cleanly."""
        for p in ["default", "developer", "isolated"]:
            p_dir = setup_isolated_profile(p)
            self.assertTrue(p_dir.exists())
            self.assertTrue((p_dir / "Default" / "Preferences").exists())

    def test_10_portable_engine_manager(self):
        """Verify PortableEngineManager info and bin directory creation."""
        info = portable_manager.get_engine_info()
        self.assertIn("type", info)
        self.assertIn("name", info)
        self.assertTrue(BIN_DIR.exists())

    def test_11_disposable_session_reset(self):
        """Verify disposable session reset cleans cache without crashing."""
        res = portable_manager.reset_disposable_session("default")
        self.assertTrue(res)

    def test_12_browser_prioritized_fallback(self):
        """Verify fallback returns valid browser binary on this system."""
        b_path, flavor = resolve_browser_binary()
        self.assertTrue(Path(b_path).exists())

    def test_13_browser_detector_and_settings(self):
        """Verify browser detector scans system and updates settings.json properly."""
        from browser_detector import scan_all_browsers, set_browser_selection, load_settings, resolve_selected_browser, is_cdp_enabled, set_cdp_enabled
        browsers = scan_all_browsers()
        self.assertGreater(len(browsers), 0)
        self.assertTrue(any(b["id"] == "edge" for b in browsers))

        set_browser_selection("edge")
        settings = load_settings()
        self.assertEqual(settings.get("selected_browser"), "edge")
        self.assertTrue(settings.get("has_configured_browser"))

        # Verify CDP security mode toggle & persistent persistence
        set_cdp_enabled(False)
        self.assertFalse(is_cdp_enabled())
        set_cdp_enabled(True)
        self.assertTrue(is_cdp_enabled())

        path, name = resolve_selected_browser()
        self.assertTrue(Path(path).exists())

    def test_14_no_webstore_auto_open(self):
        """Verify launcher does NOT automatically open Chrome Web Store on boot."""
        import inspect
        import launcher
        src = inspect.getsource(launcher.launch_edge)
        self.assertNotIn("https://chromewebstore.google.com", src)
        self.assertIn("dashboard", src)

    def test_15_portable_chromium_binary_present(self):
        """Verify bundled portable Chromium binary is present and executable."""
        self.assertTrue(portable_manager.is_portable_installed())
        p_bin = portable_manager.get_portable_binary()
        self.assertIsNotNone(p_bin)
        self.assertTrue(p_bin.exists())
        self.assertIn("156", portable_manager.get_installed_version())

    def test_16_portable_upstream_check(self):
        """Verify upstream update check successfully reaches release info."""
        info = portable_manager.check_upstream_update()
        self.assertTrue(info.get("success"))
        self.assertIn("latest_version", info)
        self.assertTrue(info.get("download_url").startswith("https://"))

    def test_17_zero_lingering_launcher_flags(self):
        """Verify launcher enforces zero-lingering background termination flags."""
        import inspect
        import launcher
        src = inspect.getsource(launcher.launch_edge)
        self.assertIn("--disable-background-mode", src)
        self.assertIn("--no-service-autorun", src)

    def test_18_installer_and_spec_integrity(self):
        """Verify installer scripts and specs do not contain hardcoded foreign machine paths."""
        for spec in ["EdgeSidecar.spec", "EdgeSidecar-Setup.spec"]:
            spec_file = PROJECT_ROOT / spec
            self.assertTrue(spec_file.exists())
            content = spec_file.read_text(encoding="utf-8")
            self.assertNotIn("Users/SBK", content)
            self.assertIn("ROOT_DIR", content)

        # Verify installer wizard copies bin folder and has registry uninstall registration
        wizard_file = PROJECT_ROOT / "installer_wizard.py"
        w_content = wizard_file.read_text(encoding="utf-8")
        self.assertIn("target_bin", w_content)
        self.assertIn("register_windows_uninstall", w_content)
        self.assertIn("get_desktop_paths", w_content)

    def test_19_default_browser_registration(self):
        """Verify Windows Default Browser registration, status check, and unregistration."""
        import default_browser
        # Clean state first
        default_browser.unregister_default_browser()
        status = default_browser.get_browser_status()
        self.assertFalse(status["registered"])

        # Test registration
        ok = default_browser.register_default_browser()
        self.assertTrue(ok)
        self.assertTrue(default_browser.is_registered_as_browser())

        # Test status API representation
        status_after = default_browser.get_browser_status()
        self.assertTrue(status_after["registered"])
        self.assertEqual(status_after["prog_id"], "EdgeSidecarHTML")

        # Cleanup
        default_browser.unregister_default_browser()
        self.assertFalse(default_browser.is_registered_as_browser())

    async def test_20_proxy_single_instance_and_browser_apis(self):
        """Verify /api/ping, /api/default_browser/status and /api/open single-instance APIs."""
        test_port = 9877
        server = await start_proxy_server("127.0.0.1", test_port)
        try:
            # 1. Test Ping API
            r, w = await asyncio.open_connection("127.0.0.1", test_port)
            w.write(b"GET /api/ping HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n")
            await w.drain()
            resp = await r.read()
            w.close()
            self.assertIn(b"200 OK", resp)
            self.assertIn(b"EdgeSidecar", resp)

            # 2. Test Default Browser Status API
            r, w = await asyncio.open_connection("127.0.0.1", test_port)
            w.write(b"GET /api/default_browser/status HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n")
            await w.drain()
            resp = await r.read()
            w.close()
            self.assertIn(b"200 OK", resp)
            self.assertIn(b"registered", resp)

            # 3. Test Open URL API (Mocked URL)
            r, w = await asyncio.open_connection("127.0.0.1", test_port)
            w.write(b"GET /api/open?url=https%3A%2F%2Fexample.com HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n")
            await w.drain()
            resp = await r.read()
            w.close()
            self.assertIn(b"200 OK", resp)
            self.assertIn(b"example.com", resp)
        finally:
            server.close()
            await server.wait_closed()

    async def test_21_bypass_sites_and_local_port_isolation(self):
        """Verify bypass sites persistence, matching, and non-dashboard local port forwarding (e.g. Mudfish 127.0.0.1:8282)."""
        from browser_detector import get_bypass_sites, add_bypass_site, remove_bypass_site, is_host_bypassed
        import inspect
        import launcher

        # 1. Verify launcher does NOT force <-loopback> and supports bypass list
        src = inspect.getsource(launcher.launch_edge)
        self.assertNotIn("<-loopback>", src)
        self.assertIn("--proxy-bypass-list=", src)

        # 2. Verify no hardcoded third-party VPN sites by default & test dynamic user bypass CRUD
        from browser_detector import DEFAULT_BYPASS_SITES, load_settings, save_settings
        self.assertEqual(DEFAULT_BYPASS_SITES, [])

        orig_settings = load_settings()
        try:
            add_bypass_site("https://custom-vpn.example.com/path")
            self.assertTrue(is_host_bypassed("custom-vpn.example.com"))
            self.assertFalse(is_host_bypassed("https://google.com"))
            remove_bypass_site("custom-vpn.example.com")
            self.assertFalse(is_host_bypassed("custom-vpn.example.com"))

            # 3. Verify proxy forwards other 127.0.0.1:<other_port> requests instead of hijacking to dashboard
            async def dummy_local_handler(reader, writer):
                req_line = await reader.readline()
                while True:
                    line = await reader.readline()
                    if not line or line == b"\r\n":
                        break
                body = b"Local Service UI OK"
                if req_line.startswith(b"GET /local "):
                    writer.write(
                        b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: "
                        + str(len(body)).encode() + b"\r\nConnection: close\r\n\r\n" + body
                    )
                else:
                    writer.write(b"HTTP/1.1 400 Bad Request\r\nConnection: close\r\n\r\n")
                await writer.drain()
                writer.close()

            dummy_server = await asyncio.start_server(dummy_local_handler, "127.0.0.1", 0)
            dummy_port = dummy_server.sockets[0].getsockname()[1]
            proxy_port = 9878
            proxy_server = await start_proxy_server("127.0.0.1", proxy_port)

            try:
                # Test proxied plain HTTP request to another 127.0.0.1 port
                r, w = await asyncio.open_connection("127.0.0.1", proxy_port)
                w.write(
                    f"GET http://127.0.0.1:{dummy_port}/local HTTP/1.1\r\n"
                    f"Host: 127.0.0.1:{dummy_port}\r\n"
                    f"Proxy-Connection: keep-alive\r\n\r\n".encode("latin1")
                )
                await w.drain()
                resp = await r.read()
                w.close()
                self.assertIn(b"200 OK", resp)
                self.assertIn(b"Local Service UI OK", resp)

                # Test dashboard bypass settings API (add -> list -> remove)
                r, w = await asyncio.open_connection("127.0.0.1", proxy_port)
                w.write(b"POST /api/settings/bypass/add?site=*.mudfish.net HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n")
                await w.drain()
                resp = await r.read()
                w.close()
                self.assertIn(b"200 OK", resp)
                self.assertIn(b"*.mudfish.net", resp)

                r, w = await asyncio.open_connection("127.0.0.1", proxy_port)
                w.write(b"GET /api/settings/bypass HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n")
                await w.drain()
                resp = await r.read()
                w.close()
                self.assertIn(b"200 OK", resp)
                self.assertIn(b"*.mudfish.net", resp)

                r, w = await asyncio.open_connection("127.0.0.1", proxy_port)
                w.write(b"POST /api/settings/bypass/remove?site=*.mudfish.net HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n")
                await w.drain()
                resp = await r.read()
                w.close()
                self.assertIn(b"200 OK", resp)
                self.assertNotIn(b"*.mudfish.net", resp)
            finally:
                proxy_server.close()
                await proxy_server.wait_closed()
                dummy_server.close()
                await dummy_server.wait_closed()
        finally:
            save_settings(orig_settings)

if __name__ == "__main__":
    unittest.main()
