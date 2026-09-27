# Status

Tracks what's real vs. mocked, so this doesn't get oversold. See DESIGN.md
for the full architecture and milestone list (section 21-22); this is the
state of MVP0.

## Working and verified in this environment

* **Control plane** (`server/`) - FastAPI + SQLite. Device/Source/Sink/Zone/Route
  models, REST API, websocket state sync, a `RoutingEngine` that resolves
  zones to sinks and delegates to a transport. Verified end to end: seed
  demo devices, create a route (`PC -> Living Room + Kitchen`), see it
  active, stop it.
* **Web UI** (`ui/web/`) - React + TypeScript + Vite, SCSS modules for
  styling, plain `fetch` service layer and a context-based snapshot store
  fed by the websocket (no TanStack Query yet - add when the app becomes
  request-driven). The control plane serves the built `ui/web/dist` at
  `/`. Renders the
  MVP0 mockup from DESIGN.md section 21: pick a source, check
  destinations, ROUTE, see/stop active routes. Live-updates over `/ws`.
* **`MockTransport`** (`server/transports/mock.py`) - default transport.
  No real audio backend needed; lets the control plane + UI loop be
  exercised on their own.
* **Windows agent capture** (`agents/windows/capture.py`) - WASAPI
  loopback capture via PyAudioWPatch. Verified on this machine: captures
  real system audio as 48kHz/stereo/16-bit PCM.
* **Windows agent streaming** (`agents/windows/streamer.py`) - forwards
  captured PCM over a raw TCP socket. Verified against a throwaway TCP
  listener (not a real snapserver): ~192KB/s sustained, matching the
  expected PCM bitrate exactly.
* **Windows agent <-> control plane** (`agents/windows/control.py`,
  `main.py`) - registers device + source over REST (including the
  `transport_ref` matching a real snapserver stream id via
  `--stream-name`), heartbeats periodically, retries with backoff if the
  control plane is unreachable instead of crashing. Verified against the
  running server.
* **Control plane, containerized** (`server/Dockerfile`,
  `docker-compose.yml`) - multi-stage build (Node build of `ui/web`, then
  Python runtime), SQLite persisted via a bind-mounted volume. Deployed
  on a real Ubuntu box (Docker already present there) using
  `network_mode: host` specifically so the existing `ufw` LAN-only
  firewall rules stay effective - Docker's default port publishing
  bypasses `ufw` entirely, which was a hard requirement here. Verified:
  built and running there, reachable from another machine on the LAN at
  `http://<host>:8000/`.
* **Real Snapcast infrastructure** - `snapserver` + `snapclient` 0.27.0
  installed natively (via `apt`) on that same Ubuntu box, not
  containerized (no meaningful dependency isolation to gain there, and
  `snapclient` needs real audio hardware/PipeWire access that's much
  simpler native). `snapclient` runs as a **user-level** systemd unit
  (`systemctl --user`), not the packaged system-wide one - Ubuntu
  24.04's audio stack (PipeWire) lives in the user session, and the
  distro's system-wide `snapclient.service` can't reach it.
* **`SnapcastTransport`, end to end, with real audible playback** -
  validated for real: WASAPI loopback capture on this Windows machine ->
  real TCP stream -> real `snapserver` (`pc` stream) -> real `snapclient`
  -> actual audible sound out of the Ubuntu box's speakers, with the
  route created through the real control plane API (not `MockTransport`).
  Confirmed by ear, twice, including with an independently-generated
  clean test tone (isolating the agent's capture path from the
  Snapcast/config path). This is the actual thing MVP0 exists to prove.

## Implemented but not yet exercised against real infrastructure

* **Two synchronized endpoints** - MVP0's full goal is one source to
  *two or more* speakers, synchronized. Only one real sink
  (`snapclient` on the same Ubuntu box) has been validated so far. A
  second endpoint (another box, or a second `snapclient` instance) is
  the remaining piece.
* **`snapcast-rs`** - not evaluated at all yet. DESIGN.md section 9 flags
  its maturity as something to check before depending on it; for now the
  project talks to a plain `snapserver` process instead (see
  `SnapcastTransport`'s docstring for the reasoning).

## Known gaps / deliberate simplifications

* No resampling or format negotiation between the agent's capture format
  and whatever a real transport expects - they're assumed to match.
* `SnapcastTransport.stop_route` is a no-op (Snapcast has no generic
  "silence" stream to fall back to yet).
* No persistence for `RouteSink` cascade deletes, no auth/permissions,
  no latency model - all explicitly out of scope until their milestone
  (MVP4/MVP5 in DESIGN.md section 22).
* macOS/Linux/Android/iOS agents don't exist yet (MVP2/MVP3/MVP6).
* `snapserver`'s `tcp` source in `mode=server` does not gracefully handle
  a second producer connecting while one is already active - the second
  connection's bytes just queue up unread rather than being rejected or
  swapped in. Only ever run one producer (one Windows agent instance) per
  stream; this bit us during testing when a stale agent process and a
  manual test script were briefly connected at the same time.

## Next concrete step

Bring up a second real sink (another box, or a second `snapclient`
instance) and validate genuinely synchronized playback across two
endpoints - the last piece of MVP0's actual goal.
