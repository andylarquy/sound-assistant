"""Orchestrates the Windows sync toggle (DESIGN.md section 15): switches
the OS default output to VB-CABLE and starts our custom Rust Snapcast
client (`sync-client`) playing to the *real* hardware device, so this
PC's speakers hear the synced, buffered copy instead of the instant
original. Disabling reverses both steps.
"""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from audio_device import (
    find_playback_device,
    get_default_playback_device,
    set_default_playback_device,
)

logger = logging.getLogger("sound_assistant.agent.windows.sync_controller")

# Debug build is fine for now - this hasn't been packaged for distribution
# yet (see docs/status.md). Switch to target/release for lower latency.
SYNC_CLIENT_EXE = Path(__file__).parent / "sync-client" / "target" / "debug" / "sync-client.exe"
VIRTUAL_CABLE_NAME = "CABLE Input"


class SyncController:
    def __init__(self, snapserver_host: str, snapserver_port: int = 1704) -> None:
        self._snapserver_host = snapserver_host
        self._snapserver_port = snapserver_port
        self._process: subprocess.Popen | None = None
        self._original_device_id: str | None = None
        self._original_device_name: str | None = None
        self.enabled = False

    def enable(self) -> None:
        if self.enabled:
            return
        if not SYNC_CLIENT_EXE.exists():
            raise RuntimeError(f"sync-client binary not found at {SYNC_CLIENT_EXE}; build it first")

        original = get_default_playback_device()
        self._original_device_id = original.id
        self._original_device_name = original.name
        logger.info("enabling sync: current output is %r", original.name)

        cable = find_playback_device(VIRTUAL_CABLE_NAME)
        set_default_playback_device(cable.id)
        logger.info("default output switched to %r", cable.name)

        self._process = subprocess.Popen(
            [
                str(SYNC_CLIENT_EXE),
                "--host",
                self._snapserver_host,
                "--port",
                str(self._snapserver_port),
                "--device",
                original.name,
            ]
        )
        self.enabled = True

    def disable(self) -> None:
        if not self.enabled:
            return

        if self._process is not None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None

        if self._original_device_id is not None:
            try:
                set_default_playback_device(self._original_device_id)
                logger.info("default output restored to %r", self._original_device_name)
            except OSError as exc:
                # Device may have been unplugged/renamed since - log and
                # move on rather than crash the agent over a cosmetic
                # restore failure; the user can pick a device manually.
                logger.warning("could not restore original output device: %s", exc)
            self._original_device_id = None
            self._original_device_name = None

        self.enabled = False
