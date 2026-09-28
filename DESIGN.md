# Sound Assistant

> A software-defined, extensible audio control system for heterogeneous devices.

## 1. Overview

**Sound Assistant** is a self-hosted, centralized audio orchestration system inspired by the philosophy of Home Assistant, but focused specifically on audio.

The goal is to make a collection of heterogeneous devices behave like a single programmable audio system.

Instead of configuring audio independently on every computer, phone, speaker, or Bluetooth device, Sound Assistant provides a central control plane where users can reason about:

* audio sources
* audio sinks
* devices
* zones
* routes
* permissions
* latency
* transport capabilities

The system should make it possible to express an intent such as:

> "Play the audio from my PC in the living room, kitchen, and balcony."

without requiring the user to know whether the underlying connection uses Snapcast, CoreAudio, Bluetooth, PipeWire, RTP, or another transport.

---

# 2. Motivation

Modern homes increasingly contain many devices capable of producing or consuming audio:

* Windows PCs
* macOS computers
* Android phones
* iPhones
* TVs
* Bluetooth speakers
* Bluetooth headphones
* USB audio devices
* Raspberry Pis
* network speakers

However, these devices generally operate as isolated audio systems.

Moving audio between them usually requires manually configuring:

* operating-system audio outputs
* Bluetooth pairings
* streaming applications
* multi-room audio systems
* different proprietary ecosystems

Existing projects solve parts of this problem, particularly multi-room synchronized playback, but they generally start from the perspective of:

> "I want to distribute music to several speakers."

Sound Assistant starts from a broader abstraction:

> **Any capable device can potentially become an audio source, sink, gateway, or both.**

The project therefore focuses on **orchestration rather than reinventing audio transport infrastructure**.

---

# 3. Goals

## Primary goals

### 3.1 Centralized audio routing

Allow users to dynamically route audio between devices and zones.

Examples:

```text
PC → Living Room
PC → Kitchen
PC → Balcony
```

or:

```text
PC → Living Room + Kitchen + Balcony
```

### 3.2 Heterogeneous devices

Support devices with very different capabilities and operating systems.

The system should not assume that every endpoint is a Raspberry Pi or a network speaker.

### 3.3 Device capability discovery

Devices should advertise what they can do.

For example:

```text
MacBook
├── system audio capture
├── application audio capture
├── local playback
├── Bluetooth
└── network audio
```

while a simple Raspberry Pi speaker might expose:

```text
Raspberry Pi
├── network audio
└── local playback
```

### 3.4 Centralized control

The user should interact primarily with the Sound Assistant UI rather than individual transport implementations.

The UI should operate on concepts such as:

* "Living Room"
* "Kitchen"
* "My MacBook"
* "Earbuds"
* "PC Game"
* "Guest Phone"

rather than:

* Snapcast stream IDs
* ALSA devices
* RTP endpoints
* CoreAudio devices

### 3.5 Graceful degradation

A device should not become unusable when Sound Assistant is unavailable.

Agents should support a distinction between:

**Central mode**

```text
Sound Assistant controls audio
```

and:

**Local mode**

```text
The operating system controls audio normally
```

If the central server goes offline, agents should fail gracefully and restore normal local behavior where possible.

### 3.6 Extensibility

The architecture should allow additional transports and operating systems to be added without changing the core routing model.

---

# 4. Non-goals

Sound Assistant should **not** initially attempt to:

* implement a new audio codec
* implement synchronized multi-room audio from scratch
* replace CoreAudio, WASAPI, PipeWire, or Android's audio stack
* implement Bluetooth itself
* support every music service
* automatically capture arbitrary applications where the OS does not permit it
* become a general-purpose DAW
* replace existing audio engines unnecessarily

The project should reuse mature audio infrastructure whenever possible.

---

# 5. Core concepts

## 5.1 Device

A physical or virtual machine participating in the audio network.

Examples:

```text
Windows PC
MacBook
Android Phone
iPhone
Raspberry Pi
TV
```

A device may expose multiple sources and sinks.

---

## 5.2 Source

Anything capable of producing an audio stream.

Examples:

```text
PC system audio
MacBook system audio
MacBook application audio
Android application audio
Microphone
TV audio
```

A source is a logical entity and should not necessarily be tied directly to a particular transport.

---

## 5.3 Sink

Anything capable of consuming an audio stream.

Examples:

```text
Living Room speakers
Kitchen speaker
TV
MacBook speakers
Bluetooth earbuds
Bluetooth JBL speaker
```

---

## 5.4 Zone

A logical grouping of one or more sinks.

For example:

```text
Living Room
├── TV
└── Stereo speakers
```

or:

```text
Outdoor
├── Balcony
└── Patio
```

Zones allow the user to control multiple physical endpoints as one logical destination.

---

## 5.5 Route

A connection between a source and one or more sinks.

Example:

```text
PC Game
   │
   ├── Living Room
   ├── Kitchen
   └── Balcony
```

A route may have properties such as:

* volume
* latency
* synchronization
* transport
* reliability
* codec
* status

---

## 5.6 Agent

An OS-specific component responsible for integrating a device with Sound Assistant.

Agents abstract away platform-specific audio APIs.

Potential agents:

```text
agent-windows
agent-macos
agent-linux
agent-android
agent-ios
```

An agent should expose capabilities rather than forcing the server to understand the implementation details of its platform.

---

# 6. Architecture

Sound Assistant is divided into three conceptual layers.

```text
┌──────────────────────────────────────────────┐
│                 CONTROL PLANE                │
│                                              │
│ Devices / Sources / Sinks / Zones            │
│ Routing / Permissions / Sessions / Latency   │
│ API / UI                                     │
└──────────────────────┬───────────────────────┘
                       │
                 Transport API
                       │
┌──────────────────────▼───────────────────────┐
│                 AUDIO LAYER                  │
│                                              │
│ Snapcast / future transports / agents        │
│ Synchronization / buffering / streaming      │
└──────────────────────┬───────────────────────┘
                       │
                  OS audio APIs
                       │
             ┌─────────┼─────────┐
             ▼         ▼         ▼
          CoreAudio  WASAPI   PipeWire
```

---

# 7. Control Plane

The control plane is the heart of Sound Assistant.

It maintains the global model of the audio network.

Responsibilities include:

* device registry
* device discovery
* capability discovery
* source/sink management
* zones
* routes
* users
* permissions
* sessions
* transport selection
* latency information
* state synchronization
* API
* web UI

The control plane should express **intent**, not low-level audio operations.

For example:

```text
route(
    source = "pc-game",
    destination = "living-room"
)
```

rather than:

```text
create_snapcast_stream(...)
assign_client_to_group(...)
```

The latter is an implementation detail of a transport backend.

---

# 8. Audio Layer

The audio layer is responsible for actually moving audio.

The first major technology chosen for this layer is **Snapcast**, accessed through **snapcast-rs** where practical.

Snapcast provides the difficult infrastructure required for synchronized network audio, including:

* audio streaming
* buffering
* synchronization
* client/server communication
* codec support
* multi-room playback

Sound Assistant should treat Snapcast as a transport implementation rather than as the application's domain model.

---

# 9. snapcast-rs

The project will investigate and use **snapcast-rs** as the primary embedded synchronized-audio transport.

The motivation for using snapcast-rs instead of treating `snapserver` and `snapclient` as completely separate external applications is tighter integration with Sound Assistant.

Conceptually:

```text
┌──────────────────────────────────────────────┐
│              Sound Assistant                 │
│                                              │
│  Control Plane                               │
│       │                                      │
│       ▼                                      │
│  Transport Abstraction                       │
│       │                                      │
│       ▼                                      │
│  snapcast-rs                                 │
│       │                                      │
│       ▼                                      │
│  Network / synchronized audio                │
└──────────────────────────────────────────────┘
```

This allows the project to control the audio engine programmatically without making Snapcast's concepts the foundation of the entire application.

### Important consideration

`snapcast-rs` should be treated as an external dependency with a potentially evolving API.

Its maturity, API stability, licensing, and supported functionality should be evaluated during the initial prototype.

The architecture must remain capable of replacing it with another transport if necessary.

---

# 10. Transport abstraction

The system should define a transport abstraction above any particular implementation.

Conceptually:

```text
AudioTransport
├── SnapcastTransport
├── RTPTransport
├── WebRTCTransport
├── LocalTransport
├── BluetoothGatewayTransport
└── Future transports
```

Only Snapcast needs to be implemented initially.

Other transports should be added when an actual use case demonstrates that Snapcast is insufficient.

This avoids prematurely solving hypothetical problems.

---

# 11. Why not make ScreamRouter the foundation?

ScreamRouter is an interesting existing project and may eventually be useful as an audio backend.

However, Sound Assistant should not depend on ScreamRouter's routing model.

Instead, ScreamRouter should remain a possible future transport/routing backend:

```text
                 Sound Assistant
                       │
                Transport layer
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
       Snapcast    ScreamRouter   Agents
```

This keeps the Sound Assistant domain model independent of any individual audio engine.

---

# 12. Agents

Agents are responsible for the platform-specific parts of the system.

## Windows agent

Potential responsibilities:

* system audio capture
* application/process audio capture where possible
* local audio playback
* output device management
* Bluetooth integration
* communication with the Sound Assistant server

Potential technologies include WASAPI and existing Windows audio APIs.

---

## macOS agent

The macOS agent is particularly important because macOS devices can act as both sources and sinks.

Potential capabilities:

* CoreAudio playback
* system audio capture
* per-application audio capture
* output device selection
* Bluetooth gateway
* network audio playback
* built-in speakers

Example:

```text
MacBook
├── System Audio Source
├── Application Audio Source
├── Built-in Speakers
├── Bluetooth Earbuds
└── Bluetooth Speaker
```

This enables routes such as:

```text
PC
 ↓
Sound Assistant
 ↓
MacBook
 ↓
Bluetooth
 ↓
Earbuds
```

---

## Linux / Raspberry Pi agent

The Linux agent will provide inexpensive physical endpoints.

A typical endpoint may consist of:

```text
Raspberry Pi
    │
    ├── Sound Assistant agent
    │
    ├── Snapcast transport
    │
    └── PipeWire / ALSA
            │
            ▼
          DAC
            │
            ▼
         Speaker
```

These endpoints should require minimal configuration.

---

## Android agent

Android can potentially provide:

* network playback
* local speaker/headphone playback
* Bluetooth gateway
* application/system playback capture where permitted

Android playback capture is subject to OS and application capture policies and user authorization.

Therefore, arbitrary application capture should be treated as a capability rather than a guaranteed feature.

---

## iOS agent

iOS should initially focus on:

* network playback
* local playback
* Bluetooth/AirPlay-related output capabilities
* gateway functionality

Generic arbitrary system/application audio capture is significantly more constrained than on macOS or Android and should not be a foundational assumption.

---

# 13. Example: Bluetooth gateway

One of the system's important use cases is using a computer or phone as an audio gateway.

Example:

```text
PC
 │
 │ network
 ▼
Sound Assistant
 │
 ▼
MacBook agent
 │
 │ CoreAudio
 ▼
Bluetooth
 │
 ▼
Earbuds
```

The earbuds don't need to be paired with the PC.

The MacBook acts as their persistent Bluetooth host.

The user simply selects:

```text
PC → Earbuds
```

from Sound Assistant.

The system resolves the route automatically.

---

# 14. Latency model

Audio routes have different latency characteristics.

Sound Assistant should therefore maintain an estimated latency model.

A route may contain:

```text
estimated_latency
latency_range
jitter
synchronization_support
reliability
confidence
```

Example:

```text
PC → Living Room
~20 ms
high confidence
```

versus:

```text
PC → MacBook → Bluetooth Earbuds
~120–180 ms
medium confidence
```

The system can use this information to describe route suitability.

For example:

```text
Interactive audio
Music
Video
Gaming
Instrument monitoring
```

Different use cases may have different acceptable latency.

Initially, latency values can be manually configured or estimated from known transport characteristics, but is not strictly necessary to send a packet to specifically test latency.

Automatic measurement and learning can be added later.

---

# 15. Local / Central mode

Agents should support two conceptual modes.

## Central mode

Sound Assistant controls the device's audio routing.

```text
Sound Assistant
       │
       ▼
     Agent
       │
       ▼
  OS audio system
```

## Local mode

The device behaves normally.

```text
User / OS
   │
   ▼
OS audio system
```

Switching to local mode should effectively remove the device from centralized control.

If the Sound Assistant server disappears, agents should fail gracefully and restore normal local operation whenever possible.

This prevents the system from becoming a single point of failure for basic audio functionality.

## Mirror mode

A third, distinct mode: the device's normal local playback is left completely untouched, while a copy of the same audio is also captured and made available to Sound Assistant for routing elsewhere.

```text
        User / OS
           │
           ├───────────────────────────────┐
           ▼                               ▼
      OS audio system              Agent (capture)
      (local speakers,                    │
       unaffected)                        ▼
                                   Sound Assistant → other zones
```

This is not a hybrid of Central and Local mode - it is a source acting in both roles at once: locally exactly as if Sound Assistant did not exist, and simultaneously as a source for other zones. This is what the Windows agent's WASAPI loopback capture implements today: a passive tap, never redirecting or interrupting local output.

### Latency mismatch is expected, not a defect

Sound Assistant's synchronized transports (e.g. Snapcast) deliberately buffer audio - typically several hundred milliseconds to around a second - so that multiple destination endpoints can stay in sync with each other despite network jitter. That buffer only applies to the routed copy; the device's own local playback has no such delay.

Consequence: a user positioned near both the source device and a mirrored destination will hear the destination noticeably lag the source. This is inherent to any system that guarantees multi-room synchronization over a network, not something Mirror mode is expected to eliminate. The gap can be *reduced* (a smaller stream buffer, traded against tolerance for network jitter) but not removed to the point of feeling instantaneous - that would require abandoning cross-room synchronization guarantees entirely.

Muting or redirecting the source device's own local output, so only the remote copy is heard, is a possible per-route option for a future milestone, but must never be the default: Mirror mode's entire purpose is that local playback keeps working untouched.

### Closing the gap requires intercepting the local path - and not every platform allows that

The latency gap above assumes a *passive* capture (a tap that observes the signal without touching it), which is all every platform's basic loopback/capture API provides. Genuinely closing the gap - so the source's own speakers play the *same delayed, synchronized copy* as every other destination, rather than the immediate original - requires something to sit in the local render path and prevent the immediate original from reaching hardware directly. Whether a platform can do that at all, and how invasively, varies enormously:

* **Windows** - capture works today (WASAPI loopback, implemented in `agents/windows/capture.py`). Closing the gap needs either a third-party virtual audio driver (e.g. VB-CABLE - free, mature, but kernel-mode) as the system's default output, or a more surgical native alternative: per-process loopback capture combined with per-app volume muting (`ISimpleAudioVolume`, e.g. via `pycaw`) - no driver install, but scoped to one application rather than whole-system audio, and meaningfully more integration work than device-level capture.
* **macOS** - capture works the same way (Core Audio loopback / process tap). Closing the gap is comparatively the nicest case: macOS's built-in Multi-Output Device can combine local speakers with an **AirPlay** target and keeps them in sync natively - a first-party feature, not a driver. This implies routing such sources over a distinct `AirPlayTransport` (see section 10) to AirPlay-capable receivers (e.g. `shairport-sync`), rather than through Snapcast.
* **Linux** - capture works (PipeWire/PulseAudio monitor sources). Closing the gap is native and requires no third-party tooling at all: virtual/null sinks are a first-class feature of the audio server already in use.
* **Android** - capture is best-effort (`AudioPlaybackCapture`, introduced Android 10; individual apps can opt out, and most DRM'd/streaming apps do). There is no way to close the gap: no per-app mute granularity exists for muting a specific *other* app, and there is no native simultaneous local+network output comparable to macOS's Multi-Output Device. Android should therefore only ever run in **Central mode** for a given source - capture the (opt-in) media stream while muting the local media volume stream outright - never Mirror mode.
* **iOS** - no general audio capture API exists for third-party apps at all. iOS cannot be a Mirror-mode *or* Central-mode source; it remains sink-only (DESIGN.md section 12).

This is a capability distinction, in the same spirit as section 3.3's device capability discovery - not every device needs to expose the same set of behaviors, and the control plane and UI should reflect what a given device can actually do rather than assuming uniform support.

### Windows: the chosen approach, and why the official snapclient was rejected

Two concrete decisions for Windows, reached after evaluating the alternatives above:

**The virtual audio interface is VB-CABLE**, not the open-source Synchronous Audio Router. SAR's license (GPL-3.0, fully auditable) is objectively cleaner than VB-CABLE's closed-source freeware terms, but SAR is built for DAW/pro-audio routing and would need real work to shape into "one simple cable," and its maintenance is fragmented across community forks of a less-active original project. VB-CABLE is purpose-built for exactly this, with over a decade of proven stability - more important than usual here since this is kernel-mode territory, where a bug means instability, not just a caught exception. VB-CABLE is installed and verified in this project's Windows dev environment: its render endpoint ("CABLE Input") exposes a proper WASAPI loopback view, so the existing `agents/windows/capture.py` works with it unchanged, once it becomes the default output device.

**The synced playback client will not be the official C++ `snapclient.exe`.** This project's dependencies should be things installed through a programming language's own package manager (pip/cargo/npm), not separately-versioned third-party applications carrying their own licensing/availability risk (a project can be discontinued or paywalled with no recourse). VB-CABLE is accepted as the one necessary exception - a driver is unavoidable for real interception - but a second bundled application should not be stacked on top of it. Instead, the plan is a **small custom Rust CLI binary**, built by this project, embedding the `snapcast-client` crate (from the `metaneutrons/snapcast-rs` project, protocol-compatible with the existing C++ Snapcast ecosystem) rather than shelling out to somebody else's executable. The Windows agent manages it as a subprocess - deliberately not embedded in-process via PyO3, so a crash or audio glitch on the Rust side can't take down the agent's capture/registration/heartbeat logic.

This is also the first concrete use of section 19's "Rust for the audio/native layer," scoped for now to just the Windows sync-client rather than the whole audio engine. It does not touch the existing Ubuntu `snapserver`/`snapclient` (native, `apt`-installed, already proven), which stay exactly as they are.

Accepted, not dismissed, risk: the `snapcast-client` crate has 0 GitHub stars - essentially unvetted by the community - a real gap in the "reuse mature infrastructure" principle that section 9 already flagged for `snapcast-rs` in general. It's accepted here in service of the dependency-purity principle above, to be validated hands-on before being depended on further.

**Update: validated and fully wired, with three real bugs found along the way.** `agents/windows/sync-client/` embeds a fork of the crate (`github.com/andylarquy/snapcast-rs`) and achieves genuine cross-machine synchronized playback against the real Ubuntu `snapserver`/`snapclient` - confirmed by ear, residual offset under ~100ms. The 0-star risk was real: the crate's non-Unix clock source used wall-clock time instead of a monotonic one, its public API bypassed its own internal synchronization scheduler entirely (worked around by scheduling playback ourselves, using the clock offset and buffer setting the crate already exposes publicly), and `receive_loop` raced a non-cancellation-safe socket read inside `tokio::select!`, silently desyncing the stream's framing under sustained load (surfaced as intermittent "payload too large" disconnects, fixed by moving the read onto its own task). See `docs/status.md` for the full detail. The toggle is now fully wired end to end - VB-CABLE default-device switching, the `sync-client` subprocess, the backend API, and the UI checkbox - and validated including a real WiFi stress test (carrying the Ubuntu box around the room, briefly behind a wall) that stayed in sync with no packet loss.

### `buffer_ms`: fixed for now, revisit once WiFi jitter is actually a problem

`buffer_ms` is currently a hardcoded constant in the Ubuntu box's `/etc/snapserver.conf`, tuned by hand. Two things worth recording about that choice.

First, what the manual tuning actually established: pushing it down to 100ms produced continuous "not enough frames"/XRUN errors - but on *both* the custom Rust `sync-client` and the stock, unmodified, upstream `snapclient` running on the Ubuntu box, at the same time, for the full duration of sustained playback (not just at start/stop). That rules out a bug in our own scheduling code - even the mature C++ client can't keep up at that value on this network - so the floor here is a genuine property of the network/OS-scheduling jitter, not something to keep hunting for in application code.

Second, why this isn't automated yet, and what "automated" would even mean here: `buffer_ms` is a single value shared by every client in a stream (Snapcast only lets you offset per-client via `latency`, not resize the buffer per-client) - so growing the number of connected agents doesn't mean tuning N independent values, just keeping the one shared value large enough for whichever currently-connected client has the worst jitter. Today only the Windows PC is wired; the Ubuntu box is on WiFi, and more WiFi agents are planned. WiFi jitter is a materially different problem from wired jitter - bursty rather than smoothly variable, dominated by things like retransmits and power-save mode's periodic 100-300ms latency spikes - so a value hand-tuned today isn't guaranteed to still be the right floor once the device mix or RF environment changes. (Worth checking independently of any of this: WiFi power-save mode on the Ubuntu box's adapter is a well-known cause of exactly this symptom, and disabling it might raise the real floor by itself, cheaper than any buffer tuning.)

Given that, for now: keep it a fixed, manually-set constant, and defer building anything automatic until a real WiFi agent actually makes the fixed value uncomfortable. When that happens, options on the table (none decided, none started):

* Calculate it once, e.g. at startup - measure round-trip jitter to connected clients for a few seconds, pick a value with margin.
* Recalculate periodically over long windows, so the system adapts as the device mix or RF conditions drift, without the complexity/oscillation risk of continuous per-frame adaptation.
* Expose it as a UI-adjustable setting, so the user can re-find the sweet spot by hand after changing their physical setup, without needing a code change.

Any of these could reuse the round-trip latency data already flowing through the existing clock-sync mechanism (the Time message exchange used for offset calculation) rather than needing new probing infrastructure.

**Update: manually tuned to 132ms, then 140ms.** Stepped down from 200ms (too much lip-sync lag) through 150/130/125ms; 125ms produced audible glitches, 130ms was clean except for an occasional small dropout roughly every 10s, and 132ms held up with no further dropouts - including a stress test physically walking the Ubuntu box around the living room and briefly behind a wall, no packet loss. Sputtering later came back at 132ms with no code or config change on either side; raised to 140ms, which resolved it again. Read as the WiFi-jitter-isn't-stable risk flagged above actually showing up, not a mystery regression - reinforces that a single hand-tuned constant found once is not guaranteed to keep holding, which is exactly the case for the periodic-recalibration option above. Currently set in `/etc/snapserver.conf`; still a manually-found fixed value, not calculated - the options above remain unstarted and undecided.

### Rejected: building our own virtual audio driver instead of depending on VB-CABLE

Considered explicitly, for the same reason the project forked `snapcast-client` rather than depend on someone else's unmodifiable binary: avoiding a dependency that could be discontinued or paywalled with no recourse. Rejected anyway, because a Windows virtual audio driver is not comparable in risk or effort to a user-mode crate fork:

* **Blast radius.** Every fix made to `snapcast-client` lived in user-mode code - worst case, our own process crashes. A bug in kernel-mode audio driver code can blue-screen the whole machine or corrupt system state, not just our own process. Same category of mistake (a bad index, a race condition), a completely different category of consequence.
* **Tooling immaturity, specifically for audio.** `windows-drivers-rs` (Microsoft's own effort to bring Rust into kernel driver development) covers general KMDF drivers, but there is no mature Rust reference for the audio-miniport driver class specifically. This would mean porting the logic of Microsoft's C++ "SysVAD" sample driver into unsafe Rust FFI largely from scratch - materially more open-ended than reading and patching an existing crate.
* **Test-signing isn't free, even for personal use.** Beyond a persistent desktop watermark, machines with Core Isolation/HVCI enabled (increasingly the Windows 11 default) can block test-signed kernel drivers outright unless that protection is also weakened - a real adoption cost for anyone other than the original developer.
* **Debugging requires a skill set nothing else in this project needs** - kernel debugging (WinDbg, ideally a second machine or VM), rather than anything used so far.
* **The problem it would solve is low-probability and already has a fallback.** VB-CABLE has been stable and free for over a decade. If it ever were discontinued or paywalled, Synchronous Audio Router (open-source, GPL-3.0, evaluated above) is a known, already-vetted alternative.

Decision: not worth the effort/risk against a low-probability problem that already has a fallback. If ever revisited, it should be the very last thing this project tackles - after everything else is otherwise complete - not folded into the sync-toggle work.

---

# 16. Guest access

Sound Assistant should support temporary or restricted users.

A guest may be granted permissions such as:

```text
Guest
├── transmit audio
├── receive audio
├── Living Room
├── Kitchen
└── Balcony
```

while being denied:

```text
Bedroom
Administrative controls
Device configuration
Other users' devices
```

Guest access should support temporary sessions and explicit permissions.

A guest should ideally be able to access the system through the web UI without installing specialized software.

---

# 17. Routing graph

The internal representation should eventually be a graph rather than a collection of static device-to-device connections.

Example:

```text
                  ┌── Living Room
                  │
PC Game ──────────┼── Kitchen
                  │
                  └── Balcony


MacBook ─────────────── Earbuds
                            │
                         Bluetooth
```

Graph edges may contain properties such as:

```text
latency
jitter
bandwidth
transport
reliability
synchronization
```

This creates the possibility of future route planning.

For example, Sound Assistant could eventually determine that one path is preferable for a given use case because it has lower latency or better synchronization.

Automatic route optimization is not an initial requirement.

---

# 18. Scenes

A future feature is the ability to save common routing configurations as scenes.

Examples:

```text
Movie Night
Gaming
Party
Whole House
Work
Quiet
```

A scene might configure:

```text
Movie Night
├── PC / TV audio → Living Room
├── TV → Living Room speakers
└── notifications → local device only
```

Scenes should be implemented at the control-plane level rather than being tied to Snapcast concepts.

---

# 19. Technology stack

The initial stack is intentionally split according to responsibilities.

## Control plane

Potential stack:

* Python
* FastAPI
* WebSockets
* SQLite initially
* PostgreSQL later if needed

Python is chosen for rapid development of:

* business logic
* APIs
* orchestration
* state management
* permissions
* routing logic

---

## Audio/native layer

Primary candidate:

* Rust
* snapcast-rs

Responsibilities:

* network audio
* synchronization
* buffering
* transport implementation
* native audio integration where necessary

Rust is not being selected merely because it is a "low-level language."

It is useful because this subsystem involves:

* concurrency
* networking
* realtime-ish processing
* precise timing
* resource management
* native APIs
* potentially long-running audio pipelines

Memory safety is also valuable for a process that will eventually sit directly in the audio path.

---

## Frontend

Initial UI:

* web application, React based
* responsive design
* usable from desktop and mobile

The UI should be transport-agnostic.

Users should not need to understand Snapcast, RTP, PipeWire, or CoreAudio.

---

# 20. Proposed repository structure

A possible initial structure:

```text
sound-assistant/
│
├── server/
│   ├── api/
│   ├── devices/
│   ├── routing/
│   ├── zones/
│   ├── permissions/
│   ├── sessions/
│   ├── latency/
│   ├── transports/
│   └── persistence/
│
├── audio-engine/
│   ├── src/
│   ├── transports/
│   │   └── snapcast/
│   └── agents/
│
├── agents/
│   ├── windows/
│   ├── macos/
│   ├── linux/
│   ├── android/
│   └── ios/
│
├── ui/
│   └── web/
│
├── protocol/
│   └── agent/
│
├── docs/
│
└── README.md
```

The exact structure can evolve.

The important architectural boundary is:

```text
Control Plane
        │
        │ stable protocol
        ▼
Audio / Agent Layer
```

---

# 21. Initial milestone

The first milestone should be deliberately small.

### MVP 0 — synchronized network playback

Build:

```text
Windows PC
     │
     ▼
Sound Assistant server
     │
     ▼
snapcast-rs
     │
 ┌───┴────┐
 ▼        ▼
Pi       Pi
│         │
speaker  speaker
```

Requirements:

1. PC audio can be captured.
2. Audio reaches the server.
3. Two or more endpoints can receive it.
4. Endpoints remain synchronized.
5. Sound Assistant can start/stop the route.
6. Sound Assistant can select which endpoints participate.

The first UI can be extremely simple.

For example:

```text
Source:
[ PC ]

Destinations:
[x] Living Room
[x] Kitchen
[ ] Bedroom

[ ROUTE ]
```

If this works reliably, the fundamental architecture has been validated.

---

# 22. Subsequent milestones

### MVP 1 — Device model

Implement:

* device registry
* capabilities
* sources
* sinks
* zones
* route state

### MVP 2 — macOS agent

Support:

* local playback
* system audio capture
* Bluetooth outputs

### MVP 3 — Bluetooth gateway

Enable:

```text
PC → MacBook → Bluetooth earbuds
```

### MVP 4 — latency model

Introduce:

* estimated latency
* route suitability
* synchronization metadata

### MVP 5 — guest access

Implement:

* guest sessions
* permissions
* allowed zones
* temporary access

### MVP 6 — Android

Add Android playback and supported capture capabilities.

### MVP 7 — additional transports

Only add alternatives such as RTP, WebRTC, or ScreamRouter when concrete requirements justify them.

---

# 23. Design principles

The project should follow these principles throughout development.

### 1. Intent over implementation

The control plane should express:

```text
PC → Kitchen
```

not:

```text
Snapcast stream 3 → group 7
```

### 2. Transport independence

Snapcast is the first transport, not the definition of the system.

### 3. Agents own platform-specific complexity

The server should not contain macOS CoreAudio or Windows WASAPI logic.

### 4. Graceful degradation

Centralized control should be optional, not required for basic device operation.

### 5. Reuse existing audio infrastructure

Do not reinvent:

* synchronization
* codecs
* Bluetooth
* OS audio systems
* network audio protocols

unless there is a compelling reason.

### 6. Optimize for the weird use cases

The project should eventually be capable of things conventional multi-room systems aren't designed around:

```text
PC → MacBook → Bluetooth earbuds
```

```text
Guest phone → server → multiple zones
```

```text
MacBook application → kitchen
```

```text
PC game → multiple synchronized rooms
```

These use cases should guide the architecture.

### 7. Start simple

Do not build every agent, transport, permission system, and UI feature before proving that the fundamental audio path works.

---

# 24. Long-term vision

The eventual goal is for Sound Assistant to make the entire home behave like a programmable audio network.

A user should be able to look at the system and see something like:

```text
                         SOUND ASSISTANT

Sources
────────────────────────────────────────────

🖥 PC
💻 MacBook
📱 Andres' Phone
📱 Guest Phone
📺 TV


Zones
────────────────────────────────────────────

🏠 Living Room
   ├── TV
   └── Speakers

🍳 Kitchen
   └── Speaker

🌿 Balcony
   └── Speaker

🛏 Bedroom
   └── Speaker


Current Routes
────────────────────────────────────────────

🖥 PC Game
   ├── 🔊 Living Room
   ├── 🔊 Kitchen
   └── 🔊 Balcony

💻 MacBook
   └── 🎧 Bluetooth Earbuds

📱 Guest
   └── 🔊 Living Room
```

The physical technologies underneath may be completely different.

That should be invisible to the user.

---

# 25. The core idea

Sound Assistant is **not a replacement for Snapcast, PipeWire, CoreAudio, WASAPI, Bluetooth, or other audio technologies**.

It is an orchestration layer that makes them part of one coherent system.

The fundamental architectural principle is:

> **Sound Assistant owns the intent.
> Agents own the devices.
> Transports own the audio.**

This separation should allow the project to evolve from a small synchronized multi-room experiment into a general-purpose, programmable audio network without requiring the entire system to be redesigned.
