# sound-assistant

A software-defined, extensible audio control system for heterogeneous
devices. See [DESIGN.md](DESIGN.md) for the full architecture and
[docs/status.md](docs/status.md) for what's actually working right now
vs. planned.

## Quick start (control plane + UI, no real audio backend needed)

```powershell
python -m venv .venv
.venv\Scripts\pip install -r server\requirements.txt
.venv\Scripts\python -m uvicorn server.main:app --reload --port 8000
```

Build the UI (React + TypeScript + Vite, SCSS modules) once so the
control plane can serve it at http://localhost:8000/:

```powershell
cd ui\web
npm install
npm run build
```

For UI development, run `npm run dev` in `ui\web` instead and open
http://localhost:3000/ (hot reload; proxies `/api` and `/ws` to the
control plane on port 8000).

With nothing registered yet, seed some demo devices/zones in another
terminal:

```powershell
.venv\Scripts\python scripts\seed_demo.py
```

Refresh the page: you can now route "PC system audio" to Living Room
and/or Kitchen. This uses `MockTransport` (`server/transports/mock.py`),
so no real audio moves yet - it exercises the control plane and UI.

## Windows agent (real audio capture)

```powershell
.venv\Scripts\pip install -r agents\windows\requirements.txt
.venv\Scripts\python agents\windows\main.py --sink-host <snapserver-host> --sink-port <tcp-stream-port>
```

Captures real system audio via WASAPI loopback and streams it to a TCP
endpoint (intended to be a `snapserver` `tcp` stream source). Registers
itself with the control plane so it shows up as a source in the UI.
Requires an actual `snapserver`/`snapclient` setup to hear anything -
see [docs/status.md](docs/status.md) for exactly what has and hasn't
been tested.

## Repository layout

See DESIGN.md section 20 for the intended structure; `docs/status.md`
and the `README.md` in each still-empty directory note where things
actually stand today.
