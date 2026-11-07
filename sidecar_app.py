import argparse
import asyncio
import os
import signal
import subprocess
import sys
import time

# Pillar 8: UTF-8 Encoding Guard
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from harness_core import supervisor, HarnessState
from proxy_server import start_proxy_server
from cdp_interceptor import CDPInterceptor
from launcher import launch_edge
from browser_detector import is_cdp_enabled
from config import PROXY_HOST, PROXY_PORT

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

def kill_process_tree(pid: int):
    """Forcefully terminates the target process and all descendant processes on Windows without console flashing."""
    try:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                capture_output=True,
                check=False,
                creationflags=CREATE_NO_WINDOW
            )
        else:
            os.kill(pid, signal.SIGKILL)
    except Exception:
        pass

async def main(profile_name: str = "default"):
    print("=" * 60)
    print("🛡️  EDGE SIDECAR BROWSER (v1.3.1)")
    print(f" - 프로필 모드: [{profile_name.upper()}]")
    print(" - 패킷 통제 엔진: 실시간 헤더/본문 변조 & Manifest V3 탈피")
    print(" - 마이크로소프트 텔레메트리/블로트웨어 원천 차단 (Zero Telemetry)")
    print(" - 모든 크롬 확장 프로그램 100% 네이티브 호환")
    print(" - 대용량 파일 스트리밍 메모리 안전 가드 가동")
    print("=" * 60)

    supervisor.transition_to(HarnessState.INITIALIZING)

    # 1. Start Proxy Server
    server = await start_proxy_server(PROXY_HOST, PROXY_PORT)
    supervisor.transition_to(HarnessState.PROXY_READY)

    # 2. Launch Microsoft Edge with chosen isolated profile
    edge_proc = launch_edge(profile_name=profile_name, headless=False)
    supervisor.transition_to(HarnessState.EDGE_RUNNING)
    print(f"[Supervisor] Microsoft Edge launched (PID={edge_proc.pid})")

    # 3. Start CDP Interceptor (Only if CDP is enabled)
    interceptor = None
    cdp_task = None
    if is_cdp_enabled():
        interceptor = CDPInterceptor()
        cdp_task = asyncio.create_task(interceptor.start())
        print("[Supervisor] CDP Interceptor started on port 9222.")
    else:
        print("[Supervisor] Secure Mode: Remote debugging port (CDP) disabled.")
    supervisor.transition_to(HarnessState.RUNNING)

    print("\n[Supervisor] Engine is fully operational!")
    print(f"👉 대시보드 콘솔: http://127.0.0.1:{PROXY_PORT}/dashboard")
    print("👉 브라우저 창을 닫으면 사이드카 및 백그라운드 서비스가 완전히 종료됩니다.\n")

    def sig_handler():
        print("\n[Supervisor] Shutdown signal received.")
        supervisor.emergency_stop()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, sig_handler)
        except NotImplementedError:
            pass

    try:
        while not supervisor.is_stopped():
            await supervisor.wait_if_paused()

            poll = edge_proc.poll()
            if poll is not None:
                print(f"[Supervisor] Edge closed (exit code {poll}). Initiating clean shutdown...")
                supervisor.emergency_stop()
                break

            await asyncio.sleep(0.5)
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n[Supervisor] Emergency stop triggered.")
        supervisor.emergency_stop()
    finally:
        supervisor.transition_to(HarnessState.TERMINATING)
        if interceptor:
            interceptor.running = False
        if cdp_task:
            cdp_task.cancel()
        server.close()
        await server.wait_closed()

        if edge_proc.poll() is None:
            try:
                edge_proc.terminate()
                edge_proc.wait(timeout=2)
            except Exception:
                pass
        kill_process_tree(edge_proc.pid)

        supervisor.transition_to(HarnessState.STOPPED)
        print("[Supervisor] All services safely terminated.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Edge Sidecar Browser Master")
    parser.add_argument("--profile", default="default", choices=["default", "developer", "isolated"], help="Profile preset")
    args = parser.parse_args()

    # First launch: prompt for browser engine selection if not configured yet
    try:
        from browser_dialog import prompt_first_run_browser_selection
        prompt_first_run_browser_selection()
    except Exception as e:
        print(f"[Supervisor] First-run prompt skipped: {e}")

    try:
        asyncio.run(main(profile_name=args.profile))
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        os._exit(0)
