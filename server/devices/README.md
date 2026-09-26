DESIGN.md's proposed structure (section 20) has a dedicated `devices/`
package. For MVP0 that model is small enough to live directly in
`server/models.py` (the `Device`/`Source`/`Sink` classes) with CRUD in
`server/api/devices.py` and `server/api/sources_sinks.py`. This directory
is reserved for when device-specific logic (capability negotiation,
discovery) outgrows that.
