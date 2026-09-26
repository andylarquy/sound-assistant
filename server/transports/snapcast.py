"""Snapcast transport (DESIGN.md sections 8-9).

Talks to a running `snapserver`'s JSON-RPC control API over a plain TCP
socket (newline-delimited JSON-RPC 2.0, default port 1705). This is the
"reuse mature audio infrastructure" path from DESIGN.md's design
principles: rather than depending on the still-evolving `snapcast-rs`
crate (no Rust toolchain available yet either, see docs/status.md),
MVP0 controls a real `snapserver` process directly.

Important constraint inherited from Snapcast itself: snapserver's control
API assigns *existing* groups to *existing* streams - it does not create
new audio input streams at runtime in older versions. Streams (e.g. a
"pc" pipe/tcp stream fed by the Windows agent) are expected to already be
declared in snapserver.conf. So:

  * Source.transport_ref  -> a snapcast stream id (from snapserver.conf)
  * Sink.transport_ref    -> a snapcast client id (assigned by snapclient)

start_route() therefore means "point the group containing each of these
clients at this stream", which is exactly the semantics Snapcast supports
today. Newer snapserver versions additionally expose Stream.AddStream /
Stream.RemoveStream for fully dynamic streams; that can replace the
static-pipe assumption later without changing this class's public
interface.

This has not yet been exercised against a real snapserver in this
environment (none is installed here) - see docs/status.md.
"""
from __future__ import annotations

import itertools
import json
import logging
import socket

from server.models import Route, Sink, Source
from server.transports.base import AudioTransport, TransportError

logger = logging.getLogger("sound_assistant.transports.snapcast")


class SnapcastTransport(AudioTransport):
    name = "snapcast"

    def __init__(self, host: str = "127.0.0.1", port: int = 1705, timeout: float = 5.0) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self._id_counter = itertools.count(1)

    def _rpc(self, method: str, params: dict | None = None) -> dict:
        request_id = next(self._id_counter)
        payload = {"id": request_id, "jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        data = (json.dumps(payload) + "\r\n").encode("utf-8")

        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
                sock.sendall(data)
                buf = b""
                sock.settimeout(self.timeout)
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        raise TransportError(f"snapserver closed connection during {method}")
                    buf += chunk
                    while b"\n" in buf:
                        line, buf = buf.split(b"\n", 1)
                        line = line.strip()
                        if not line:
                            continue
                        message = json.loads(line)
                        if message.get("id") == request_id:
                            if "error" in message:
                                raise TransportError(f"{method} failed: {message['error']}")
                            return message.get("result", {})
                        # else: a notification (e.g. Client.OnConnect) - ignore, keep reading
        except OSError as exc:
            raise TransportError(f"could not reach snapserver at {self.host}:{self.port}: {exc}") from exc

    def _group_id_for_client(self, client_transport_ref: str, status: dict | None = None) -> str:
        status = status or self._rpc("Server.GetStatus")
        for group in status["server"]["groups"]:
            for client in group["clients"]:
                if client["id"] == client_transport_ref:
                    return group["id"]
        raise TransportError(f"no snapcast group contains client {client_transport_ref!r}")

    def start_route(self, route: Route, source: Source, sinks: list[Sink]) -> None:
        if not source.transport_ref:
            raise TransportError(f"source {source.name!r} has no snapcast stream id configured")

        status = self._rpc("Server.GetStatus")
        for sink in sinks:
            if not sink.transport_ref:
                raise TransportError(f"sink {sink.name!r} has no snapcast client id configured")
            group_id = self._group_id_for_client(sink.transport_ref, status)
            self._rpc("Group.SetStream", {"id": group_id, "stream_id": source.transport_ref})
        logger.info(
            "route %s: snapcast stream %s -> groups for clients %s",
            route.id,
            source.transport_ref,
            [s.transport_ref for s in sinks],
        )

    def stop_route(self, route: Route) -> None:
        # There's no "silence" stream id in general; MVP0 relies on the
        # caller re-routing groups elsewhere (or the group having an idle
        # default stream). Revisit once Stream.AddStream-based virtual
        # silence streams are in place.
        logger.info("route %s stop requested (no-op at transport level for now)", route.id)

    def set_volume(self, sink: Sink, volume: float) -> None:
        if not sink.transport_ref:
            raise TransportError(f"sink {sink.name!r} has no snapcast client id configured")
        percent = max(0, min(100, round(volume * 100)))
        self._rpc(
            "Client.SetVolume",
            {"id": sink.transport_ref, "volume": {"muted": False, "percent": percent}},
        )

    def status(self) -> dict:
        try:
            return {"transport": self.name, "server": self._rpc("Server.GetStatus")}
        except TransportError as exc:
            return {"transport": self.name, "error": str(exc)}
