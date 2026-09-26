"""WASAPI loopback capture: the real, testable-today piece of the Windows
agent (DESIGN.md section 3.3 / 12 - "system audio capture").

Uses PyAudioWPatch (a PyAudio fork with WASAPI loopback support) rather
than writing a native WASAPI client from scratch, per DESIGN.md's "reuse
existing audio infrastructure" principle. A future native agent (Rust/C++)
can replace this without changing the control plane or transport
contracts - this module only needs to keep producing raw PCM chunks.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

import pyaudiowpatch as pyaudio


@dataclass
class AudioFormat:
    sample_rate: int
    channels: int
    sample_width: int  # bytes per sample (2 for 16-bit)


class WasapiLoopbackCapture:
    """Captures whatever is playing through the default Windows output
    device, as raw PCM, via its WASAPI loopback device."""

    def __init__(self, frames_per_buffer: int = 1024) -> None:
        self._frames_per_buffer = frames_per_buffer
        self._pa = pyaudio.PyAudio()
        self._stream = None
        self.format: AudioFormat | None = None

    def _find_default_loopback_device(self) -> dict:
        wasapi_info = self._pa.get_host_api_info_by_type(pyaudio.paWASAPI)
        default_speakers = self._pa.get_device_info_by_index(wasapi_info["defaultOutputDevice"])

        if default_speakers.get("isLoopbackDevice"):
            return default_speakers

        for loopback in self._pa.get_loopback_device_info_generator():
            if default_speakers["name"] in loopback["name"]:
                return loopback

        raise RuntimeError(
            f"no loopback device found for default output {default_speakers['name']!r}"
        )

    def __enter__(self) -> "WasapiLoopbackCapture":
        device = self._find_default_loopback_device()
        sample_rate = int(device["defaultSampleRate"])
        channels = device["maxInputChannels"]

        self._stream = self._pa.open(
            format=pyaudio.paInt16,
            channels=channels,
            rate=sample_rate,
            input=True,
            input_device_index=device["index"],
            frames_per_buffer=self._frames_per_buffer,
        )
        self.format = AudioFormat(sample_rate=sample_rate, channels=channels, sample_width=2)
        return self

    def __exit__(self, *exc) -> None:
        if self._stream is not None:
            self._stream.stop_stream()
            self._stream.close()
        self._pa.terminate()

    def chunks(self) -> Iterator[bytes]:
        """Yields raw PCM chunks until the stream is closed or interrupted."""
        assert self._stream is not None, "use within a `with` block"
        while self._stream.is_active():
            yield self._stream.read(self._frames_per_buffer, exception_on_overflow=False)
