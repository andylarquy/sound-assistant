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
