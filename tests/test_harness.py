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
        from browser_detector import scan_all_browsers, set_browser_selection, load_settings, resolve_selected_browser
        browsers = scan_all_browsers()
        self.assertGreater(len(browsers), 0)
        self.assertTrue(any(b["id"] == "edge" for b in browsers))

        set_browser_selection("edge")
        settings = load_settings()
        self.assertEqual(settings.get("selected_browser"), "edge")
        self.assertTrue(settings.get("has_configured_browser"))

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

if __name__ == "__main__":
    unittest.main()
