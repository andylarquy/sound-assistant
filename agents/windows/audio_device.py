"""Default playback device get/set for the Windows sync toggle
(DESIGN.md section 15).

Enumerating devices and reading the current default is done via the
standard, documented Core Audio API. *Setting* the default device has no
public Win32 API at all - every tool that does it (nircmd,
SoundVolumeView, EarTrumpet) goes through the same undocumented
`IPolicyConfig` COM interface. Rather than hand-roll that interface
ourselves (a real risk if the vtable layout is wrong), this reuses
`pycaw`'s existing, widely-used implementation of it.
"""
from __future__ import annotations

from dataclasses import dataclass

from pycaw.constants import DEVICE_STATE, EDataFlow, ERole
from pycaw.utils import AudioUtilities

# Mirrors what Windows' own Settings UI does when you pick a device: set
# it as the default for every role, not just Console, so nothing (e.g. a
# VoIP app pinned to the Communications role) keeps using the old one.
_ALL_ROLES = [ERole.eConsole, ERole.eMultimedia, ERole.eCommunications]


@dataclass
class PlaybackDevice:
    id: str
    name: str


class AudioDeviceError(RuntimeError):
    pass


def list_playback_devices() -> list[PlaybackDevice]:
    devices = AudioUtilities.GetAllDevices(
        data_flow=EDataFlow.eRender.value, device_state=DEVICE_STATE.ACTIVE.value
    )
    return [PlaybackDevice(id=d.id, name=d.FriendlyName) for d in devices]


def get_default_playback_device() -> PlaybackDevice:
    speakers = AudioUtilities.GetSpeakers()  # already an AudioDevice wrapper, not a raw COM pointer
    if speakers is None:
        raise AudioDeviceError("no default playback device found")
    return PlaybackDevice(id=speakers.id, name=speakers.FriendlyName)


def find_playback_device(name_substring: str) -> PlaybackDevice:
    for device in list_playback_devices():
        if name_substring.lower() in device.name.lower():
            return device
    raise AudioDeviceError(f"no active playback device matching {name_substring!r}")


def set_default_playback_device(device_id: str) -> None:
    AudioUtilities.SetDefaultDevice(device_id, roles=_ALL_ROLES)
