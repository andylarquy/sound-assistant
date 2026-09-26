"""Talks to the Sound Assistant control plane's REST API to announce this
device and its source, and to keep a heartbeat going (DESIGN.md section
5.6: "an agent should expose capabilities rather than forcing the server
to understand implementation details")."""
from __future__ import annotations

import logging

import httpx

logger = logging.getLogger("sound_assistant.agent.windows.control")


class ControlPlaneClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(base_url=self.base_url, timeout=5.0)

    def register_device(self, name: str, agent_endpoint: str | None = None) -> dict:
        resp = self._client.post(
            "/api/devices",
            json={"name": name, "platform": "windows", "agent_endpoint": agent_endpoint},
        )
        resp.raise_for_status()
        return resp.json()

    def register_source(self, device_id: str, name: str, kind: str = "system_audio") -> dict:
        resp = self._client.post(
            f"/api/devices/{device_id}/sources", json={"name": name, "kind": kind}
        )
        resp.raise_for_status()
        return resp.json()

    def heartbeat(self, device_id: str) -> None:
        resp = self._client.post(f"/api/devices/{device_id}/heartbeat")
        resp.raise_for_status()

    def close(self) -> None:
        self._client.close()
