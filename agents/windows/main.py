"""Windows agent entrypoint (DESIGN.md section 12: Windows agent).

Captures system audio via WASAPI loopback and streams it, raw, to a TCP
endpoint (a snapserver `tcp` stream source). Registers the device +
source with the control plane so it shows up as something routable in
the UI, and polls (via its existing heartbeat) for the sync toggle
(DESIGN.md section 15): when enabled, the pipeline is torn down and
restarted against VB-CABLE instead of the real output device, with
`sync_controller.SyncController` managing the actual switch and the
`sync-client` Rust binary.

Usage:
    python main.py --server http://localhost:8000 --sink-host <snapserver-ip> --sink-port 4953

If the control plane can't be reached, the agent retries with backoff
instead of crashing (DESIGN.md section 3.5: graceful degradation) - this
capture method is a passive tap on the loopback device, so normal local
playback is never affected either way.
"""
from __future__ import annotations

import argparse
import logging
import socket
import sys
import threading
import time

from capture import WasapiLoopbackCapture
from control import ControlPlaneClient
from streamer import TcpPcmStreamer
from sync_controller import SyncController

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("sound_assistant.agent.windows")


def register_with_retry(client: ControlPlaneClient, device_name: str, stream_name: str) -> dict:
    delay = 2.0
    while True:
        try:
            device = client.register_device(device_name)
            source = client.register_source(
                device["id"], "PC system audio", transport_ref=stream_name
            )
            logger.info("registered as device %s, source %s", device["id"], source["id"])
            return device
        except Exception as exc:  # control plane unreachable, bad response, etc.
            logger.warning("could not reach control plane (%s); retrying in %.0fs", exc, delay)
            time.sleep(delay)
            delay = min(delay * 1.5, 30.0)


def heartbeat_loop(
    client: ControlPlaneClient,
    device_id: str,
    interval: float,
    stop: threading.Event,
    desired_sync: threading.Event,
    pipeline_restart: threading.Event,
) -> None:
    """Piggybacks on the existing heartbeat to learn the desired sync
    state - the heartbeat response already includes the full Device, no
    separate polling endpoint needed. Flips `desired_sync` and signals
    `pipeline_restart` whenever it actually changes."""
    while not stop.wait(interval):
        try:
            device = client.heartbeat(device_id)
            new_state = bool(device.get("sync_enabled", False))
            if new_state != desired_sync.is_set():
                if new_state:
                    desired_sync.set()
                else:
                    desired_sync.clear()
                pipeline_restart.set()
        except Exception as exc:
            logger.warning("heartbeat failed: %s", exc)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sound Assistant Windows agent")
    parser.add_argument("--server", default="http://localhost:8000", help="control plane base URL")
    parser.add_argument("--sink-host", required=True, help="snapserver host")
    parser.add_argument("--sink-port", type=int, required=True, help="snapserver tcp stream *source* port")
    parser.add_argument(
        "--sync-port",
        type=int,
        default=1704,
        help="snapserver's client stream port, used by sync-client when the sync toggle is on",
    )
    parser.add_argument("--name", default=socket.gethostname(), help="device name to register as")
    parser.add_argument(
        "--stream-name",
        default="pc",
        help="snapserver stream id this source maps to (must match the `name=` in snapserver.conf's tcp source)",
    )
    parser.add_argument("--heartbeat-interval", type=float, default=15.0)
    args = parser.parse_args()

    client = ControlPlaneClient(args.server)
    device = register_with_retry(client, args.name, args.stream_name)

    stop_heartbeat = threading.Event()
    desired_sync = threading.Event()
    pipeline_restart = threading.Event()
    hb_thread = threading.Thread(
        target=heartbeat_loop,
        args=(client, device["id"], args.heartbeat_interval, stop_heartbeat, desired_sync, pipeline_restart),
        daemon=True,
    )
    hb_thread.start()

    sync_controller = SyncController(args.sink_host, args.sync_port)
    streamer = TcpPcmStreamer(args.sink_host, args.sink_port)

    try:
        while True:
            pipeline_restart.clear()

            if desired_sync.is_set():
                try:
                    sync_controller.enable()
                except Exception as exc:
                    logger.error("failed to enable sync: %s", exc)
            else:
                sync_controller.disable()

            try:
                with WasapiLoopbackCapture() as capture:
                    streamer.connect(capture.format)
                    logger.info(
                        "streaming system audio to %s:%s (Ctrl+C to stop)",
                        args.sink_host,
                        args.sink_port,
                    )
                    streamer.send(capture.chunks(stop_when=pipeline_restart))
            except OSError as exc:
                logger.warning("sink connection dropped (%s); restarting pipeline", exc)

            if not pipeline_restart.is_set():
                # chunks() only returns early for a real stop_when signal
                # or a genuine capture/stream failure (handled above) - if
                # neither, something else stopped iteration; don't spin.
                break
    except KeyboardInterrupt:
        logger.info("stopping")
    finally:
        stop_heartbeat.set()
        sync_controller.disable()
        streamer.close()
        client.close()


if __name__ == "__main__":
    sys.exit(main() or 0)
