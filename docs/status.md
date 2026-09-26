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
  `main.py`) - registers device + source over REST, heartbeats
  periodically, retries with backoff if the control plane is
  unreachable instead of crashing. Verified against the running server.

## Implemented but not yet exercised against real infrastructure

* **`SnapcastTransport`** (`server/transports/snapcast.py`) - talks to a
  real `snapserver`'s JSON-RPC control port to assign client groups to
  streams. Written against Snapcast's documented protocol, but no
  `snapserver`/`snapclient` binaries are installed in this environment,
  so it has not been run against a live server yet.
* **End-to-end synchronized playback** (MVP0's actual goal: PC -> two
  Pi endpoints, synchronized) - requires `snapserver` running somewhere,
  `snapclient` on at least two real or virtual endpoints, and the
  Windows agent's stream format matching what `snapserver.conf` declares
  for its `tcp` stream source. None of that hardware/software exists in
  this dev environment yet.
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

## Next concrete step

Install `snapserver`/`snapclient` (or run them in containers/VMs) and
point `SnapcastTransport` + the Windows agent at a real instance to
validate the actual MVP0 goal: two synchronized endpoints.
