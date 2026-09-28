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
* **Custom Rust Snapcast client** (`agents/windows/sync-client/`) - a
  small CLI embedding a fork of the `snapcast-client` crate
  (`github.com/andylarquy/snapcast-rs`), built for the Windows
  sync-toggle work (see DESIGN.md section 15). Connects to the real
  `snapserver`, decodes the real `pc` stream, and plays it via `cpal` -
  confirmed by ear, in sync with the Ubuntu box's native `snapclient`,
  residual offset under ~100ms (down from the ~1s gap and total silence
  seen before fixing the two issues below). Two real bugs found and
  addressed along the way:
  * The crate's non-Unix clock source used wall-clock `SystemTime`
    instead of a genuinely monotonic clock, violating its own documented
    "both ends must share a clock domain" requirement - produced
    nonsensical multi-year-scale sync offsets. Fixed upstream in the fork
    (commit `860206c`): switched to a process-start-relative
    `std::time::Instant`.
  * Separately, the crate's public `audio_rx` API forwards decoded audio
    immediately, bypassing its own internal scheduler (`Stream`/
    `get_player_chunk`, which exists but is only reachable via a private
    field) entirely - so nothing using that public path was ever
    actually synchronized, clock bug or not. Worked around in our own
    CLI rather than patched further in the crate: `client.time_provider`
    and the clock offset it exposes are already public, so `main.rs`
    computes each frame's intended play time itself
    (`frame.timestamp_usec + buffer_ms`, translated into our clock
    domain) and sleeps until then before handing it to `cpal`.
  * Not yet wired to VB-CABLE - currently plays to whatever this PC's
    *current* default output device is, not specifically the virtual
    cable. That integration, and the actual enable/disable toggle around
    it, are still the remaining pieces (see below).

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

## Designed but not implemented

* **Windows sync toggle** (per-device enable/disable for genuinely
  synced local + networked playback, DESIGN.md section 15's "Closing the
  gap" material) - the hard technical risk (can a from-scratch Rust
  Snapcast client actually achieve real cross-machine sync at all) is
  now validated, see `sync-client` above. Still not built:
  * Wiring the sync-client to VB-CABLE specifically: capturing from
    "CABLE Input"'s loopback (via the existing, unchanged
    `agents/windows/capture.py`) as the source, while `sync-client`
    plays to the *real* output device - rather than today's spike, which
    plays to whatever the current default happens to be.
  * Backend/agent/UI wiring (a `Device.sync_enabled` field, an API to
    set it, the Windows agent polling for and acting on it via its
    existing heartbeat, default-output switching via `IPolicyConfig`,
    subprocess management for the Rust binary, a UI toggle) - not
    started; deferred to a dedicated planning round.

## Known gaps / deliberate simplifications

* No resampling or format negotiation between the agent's capture format
  and whatever a real transport expects - they're assumed to match.
* `SnapcastTransport.stop_route` mutes the group rather than
  un-assigning its stream (Snapcast has no generic "silence" stream to
  fall back to) - the group stays subscribed and decoding, just muted.
  Functionally equivalent from the listener's perspective. Found and
  fixed after testing showed audio kept playing even after every route
  was removed in the UI - the earlier no-op version genuinely didn't
  stop anything at the Snapcast level.
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
