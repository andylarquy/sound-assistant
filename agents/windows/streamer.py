"""Forwards captured PCM to a TCP listener - typically a snapserver `tcp`
stream source (DESIGN.md section 21, MVP0 requirement 2: "audio reaches
the server"). Kept transport-agnostic at the byte level: this just opens
a socket and writes chunks, so pointing it at snapserver vs. a plain test
listener requires no code change.

Known gap (see docs/status.md): this does not resample or convert
sample format. The stream's format (from capture.AudioFormat) must match
what the receiving end expects - for snapserver, the tcp stream's
`sampleformat` must be set to the same rate/channels/bit depth.
"""
from __future__ import annotations

import logging
import socket
from typing import Iterable

from capture import AudioFormat

logger = logging.getLogger("sound_assistant.agent.windows.streamer")


class TcpPcmStreamer:
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self._sock: socket.socket | None = None

    def connect(self, audio_format: AudioFormat) -> None:
        logger.info(
            "connecting to %s:%s (expects %sHz %sch %s-bit PCM)",
            self.host,
            self.port,
            audio_format.sample_rate,
            audio_format.channels,
            audio_format.sample_width * 8,
        )
        self._sock = socket.create_connection((self.host, self.port))

    def send(self, chunks: Iterable[bytes]) -> None:
        assert self._sock is not None, "call connect() first"
        for chunk in chunks:
            self._sock.sendall(chunk)

    def close(self) -> None:
        if self._sock is not None:
            self._sock.close()
            self._sock = None
