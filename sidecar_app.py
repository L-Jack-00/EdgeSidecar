import argparse
import asyncio
import os
import signal
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
from config import PROXY_HOST, PROXY_PORT

async def main(profile_name: str = "default"):
    print("=" * 60)
    print("🛡️  EDGE SIDECAR BROWSER (v1.3.0)")
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

    # 3. Start CDP Interceptor
    interceptor = CDPInterceptor()
    cdp_task = asyncio.create_task(interceptor.start())
    supervisor.transition_to(HarnessState.RUNNING)

    print("\n[Supervisor] Engine is fully operational!")
    print(f"👉 대시보드 콘솔: http://127.0.0.1:{PROXY_PORT}/dashboard")
    print("👉 브라우저를 닫거나 Ctrl+C를 누르면 안전하게 종료됩니다.\n")

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

            await asyncio.sleep(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n[Supervisor] Emergency stop triggered.")
        supervisor.emergency_stop()
    finally:
        supervisor.transition_to(HarnessState.TERMINATING)
        interceptor.running = False
        cdp_task.cancel()
        server.close()
        await server.wait_closed()

        if edge_proc.poll() is None:
            try:
                edge_proc.terminate()
                edge_proc.wait(timeout=3)
            except Exception:
                edge_proc.kill()

        supervisor.transition_to(HarnessState.STOPPED)
        print("[Supervisor] All services safely terminated.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Edge Sidecar Browser Master")
    parser.add_argument("--profile", default="default", choices=["default", "developer", "isolated"], help="Profile preset")
    args = parser.parse_args()

    try:
        asyncio.run(main(profile_name=args.profile))
    except KeyboardInterrupt:
        pass
