"""Populate a freshly-started control plane with demo devices/sources/
sinks/zones so the UI has something to route between, without needing a
real Windows agent or Raspberry Pi endpoints yet.

Usage (with the server already running, default http://localhost:8000):
    python scripts/seed_demo.py
"""
from __future__ import annotations

import json
import urllib.request

BASE = "http://localhost:8000"


def post(path: str, body: dict) -> dict:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}{path}", data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def put(path: str) -> dict:
    req = urllib.request.Request(f"{BASE}{path}", method="PUT")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def main() -> None:
    pc = post("/api/devices", {"name": "Andres' PC", "platform": "windows"})
    post(f"/api/devices/{pc['id']}/sources", {"name": "PC system audio", "kind": "system_audio"})

    living_room_pi = post("/api/devices", {"name": "Living Room Pi", "platform": "linux"})
    living_room_sink = post(
        f"/api/devices/{living_room_pi['id']}/sinks",
        {"name": "Living Room speaker", "kind": "speaker"},
    )

    kitchen_pi = post("/api/devices", {"name": "Kitchen Pi", "platform": "linux"})
    kitchen_sink = post(
        f"/api/devices/{kitchen_pi['id']}/sinks", {"name": "Kitchen speaker", "kind": "speaker"}
    )

    living_room_zone = post("/api/zones", {"name": "Living Room"})
    kitchen_zone = post("/api/zones", {"name": "Kitchen"})
    put(f"/api/zones/{living_room_zone['id']}/sinks/{living_room_sink['id']}")
    put(f"/api/zones/{kitchen_zone['id']}/sinks/{kitchen_sink['id']}")

    print("Seeded demo devices, one source (PC), two zones (Living Room, Kitchen).")
    print("Open http://localhost:8000/ to try routing PC audio to them (mock transport).")


if __name__ == "__main__":
    main()
