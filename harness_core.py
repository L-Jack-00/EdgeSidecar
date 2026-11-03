import asyncio
from enum import Enum, auto
import os
import signal
import sys
from typing import Callable, List, Optional

# Pillar 8: UTF-8 Console Safety Guard for Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

class HarnessState(Enum):
    """Explicit FSM State Machine for Sidecar Browser Lifecycle."""
    STOPPED = auto()
    INITIALIZING = auto()
    PROXY_READY = auto()
    EDGE_RUNNING = auto()
    CDP_CONNECTED = auto()
    RUNNING = auto()
    PAUSED = auto()
    TERMINATING = auto()
    ERROR = auto()

class LifecycleSupervisor:
    """Supervisor loop managing FSM, zero-load pause, and emergency stop."""
    def __init__(self):
        self._state = HarnessState.STOPPED
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # set() means running (not paused)
        self._stop_event = asyncio.Event()
        self.stop_requested = False
        self._state_callbacks: List[Callable[[HarnessState], None]] = []

    @property
    def state(self) -> HarnessState:
        return self._state

    def add_state_listener(self, cb: Callable[[HarnessState], None]):
        self._state_callbacks.append(cb)

    def transition_to(self, new_state: HarnessState):
        prev = self._state
        self._state = new_state
        print(f"[Lifecycle] State transition: {prev.name} ➔ {new_state.name}")
        for cb in self._state_callbacks:
            try:
                cb(new_state)
            except Exception:
                pass

    def pause(self):
        """Zero-load pause: event-driven pause without CPU spinning."""
        if self._state == HarnessState.RUNNING:
            self._pause_event.clear()
            self.transition_to(HarnessState.PAUSED)
            print("[Lifecycle] Engine PAUSED (Zero CPU Load)")

    def resume(self):
        """Resume execution from pause."""
        if self._state == HarnessState.PAUSED:
            self._pause_event.set()
            self.transition_to(HarnessState.RUNNING)
            print("[Lifecycle] Engine RESUMED")

    async def wait_if_paused(self):
        """Workers call this to wait indefinitely with 0% CPU while paused."""
        await self._pause_event.wait()

    def emergency_stop(self):
        """Immediate abort and emergency stop interlock."""
        self.stop_requested = True
        self.transition_to(HarnessState.TERMINATING)
        self._stop_event.set()
        self._pause_event.set()  # unblock any paused workers so they can exit
        print("[Lifecycle] EMERGENCY STOP triggered. Clean abort in progress.")

    def is_stopped(self) -> bool:
        return self.stop_requested or self._stop_event.is_set()

# Global supervisor singleton
supervisor = LifecycleSupervisor()
