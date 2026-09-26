# Linux / Raspberry Pi agent

Not started. This is the other half of MVP0 (DESIGN.md section 21): a
thin endpoint running `snapclient` against PipeWire/ALSA. For the
initial prototype this may not need custom agent code at all beyond a
plain `snapclient` install plus registering the device/sink with the
control plane's REST API (see `agents/windows/control.py` for the
pattern) - see docs/status.md for what's actually running today.
