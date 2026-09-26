"""Windows agent entrypoint (DESIGN.md section 12: Windows agent).

MVP0 scope: capture system audio via WASAPI loopback and stream it, raw,
to a TCP endpoint (a snapserver `tcp` stream source). Registers the
device + source with the control plane so it shows up as something
routable in the UI.

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

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("sound_assistant.agent.windows")


def register_with_retry(client: ControlPlaneClient, device_name: str) -> dict:
    delay = 2.0
    while True:
        try:
            device = client.register_device(device_name)
            source = client.register_source(device["id"], "PC system audio")
            logger.info("registered as device %s, source %s", device["id"], source["id"])
            return device
        except Exception as exc:  # control plane unreachable, bad response, etc.
            logger.warning("could not reach control plane (%s); retrying in %.0fs", exc, delay)
            time.sleep(delay)
            delay = min(delay * 1.5, 30.0)


def heartbeat_loop(client: ControlPlaneClient, device_id: str, interval: float, stop: threading.Event) -> None:
    while not stop.wait(interval):
        try:
            client.heartbeat(device_id)
        except Exception as exc:
            logger.warning("heartbeat failed: %s", exc)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sound Assistant Windows agent")
    parser.add_argument("--server", default="http://localhost:8000", help="control plane base URL")
    parser.add_argument("--sink-host", required=True, help="snapserver tcp stream host")
    parser.add_argument("--sink-port", type=int, required=True, help="snapserver tcp stream port")
    parser.add_argument("--name", default=socket.gethostname(), help="device name to register as")
    parser.add_argument("--heartbeat-interval", type=float, default=15.0)
    args = parser.parse_args()

    client = ControlPlaneClient(args.server)
    device = register_with_retry(client, args.name)

    stop_heartbeat = threading.Event()
    hb_thread = threading.Thread(
        target=heartbeat_loop,
        args=(client, device["id"], args.heartbeat_interval, stop_heartbeat),
        daemon=True,
    )
    hb_thread.start()

    streamer = TcpPcmStreamer(args.sink_host, args.sink_port)
    try:
        with WasapiLoopbackCapture() as capture:
            streamer.connect(capture.format)
            logger.info("streaming system audio to %s:%s (Ctrl+C to stop)", args.sink_host, args.sink_port)
            streamer.send(capture.chunks())
    except KeyboardInterrupt:
        logger.info("stopping")
    except OSError as exc:
        logger.warning("sink connection dropped (%s); stopping", exc)
    finally:
        stop_heartbeat.set()
        streamer.close()
        client.close()


if __name__ == "__main__":
    sys.exit(main() or 0)
