"""Classic KingSmith WiLink frames on service 0xFE00."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from ..models import BeltState, Mode


class WilinkCommand(IntEnum):
    STATUS = 0x00
    SET_SPEED = 0x01
    SET_MODE = 0x02
    SET_INCLINE = 0x03
    START = 0x04
    PAUSE = 0x05
    HEART_RATE = 0x06
    LOCK = 0x07


class WilinkPref(IntEnum):
    TARGET = 0x01
    MAX_SPEED = 0x03
    START_SPEED = 0x04
    AUTO_START = 0x05
    SENSITIVITY = 0x06
    DISPLAY = 0x07
    UNITS = 0x08
    CHILD_LOCK = 0x09


WILINK_START_OUT = 0xF7
WILINK_START_IN = 0xF8
WILINK_END = 0xFD
WILINK_TYPE_CMD = 0xA2
WILINK_TYPE_PREF = 0xA6
WILINK_TYPE_HIST = 0xA7


def wilink_checksum(body: bytes) -> int:
    """Checksum is (sum of TYPE through last payload byte) mod 256."""
    return sum(body) & 0xFF


def wilink_frame(frame_type: int, opcode: int, payload: bytes = b"") -> bytes:
    body = bytes([frame_type, opcode]) + payload
    return bytes([WILINK_START_OUT]) + body + bytes([wilink_checksum(body), WILINK_END])


def cmd(opcode: int, payload: bytes = b"") -> bytes:
    return wilink_frame(WILINK_TYPE_CMD, opcode, payload)


def pref(key: int, payload: bytes) -> bytes:
    return wilink_frame(WILINK_TYPE_PREF, key, payload)


def request_status() -> bytes:
    return cmd(WilinkCommand.STATUS, b"\x00")


def set_speed(kmh: float) -> bytes:
    return cmd(WilinkCommand.SET_SPEED, bytes([max(0, min(255, round(kmh * 10)))]))


def set_mode(mode: Mode) -> bytes:
    return cmd(WilinkCommand.SET_MODE, bytes([mode.to_wilink()]))


def start_belt() -> bytes:
    return cmd(WilinkCommand.START, b"\x01")


def stop_belt() -> bytes:
    return set_speed(0)


def pause_belt() -> bytes:
    return cmd(WilinkCommand.PAUSE, b"\x01")


def set_incline(percent: float) -> bytes:
    return cmd(WilinkCommand.SET_INCLINE, bytes([max(0, min(255, round(percent * 10)))]))


def set_heart_rate(bpm: int) -> bytes:
    return cmd(WilinkCommand.HEART_RATE, bytes([max(0, min(255, bpm))]))


def set_runtime_lock(enabled: bool) -> bytes:
    return cmd(WilinkCommand.LOCK, bytes([1 if enabled else 0]))


def set_pref_max_speed(kmh: float) -> bytes:
    return pref(WilinkPref.MAX_SPEED, bytes([round(kmh * 10)]))


def set_pref_start_speed(kmh: float) -> bytes:
    return pref(WilinkPref.START_SPEED, bytes([round(kmh * 10)]))


def set_pref_child_lock(enabled: bool) -> bytes:
    return pref(WilinkPref.CHILD_LOCK, bytes([1 if enabled else 0]))


def set_pref_units_miles(miles: bool) -> bytes:
    return pref(WilinkPref.UNITS, bytes([1 if miles else 0]))


def set_pref_auto_start(enabled: bool) -> bytes:
    return pref(WilinkPref.AUTO_START, bytes([1 if enabled else 0]))


def _u24be(data: bytes, offset: int) -> int:
    return (data[offset] << 16) | (data[offset + 1] << 8) | data[offset + 2]


@dataclass(frozen=True, slots=True)
class WilinkStatus:
    belt_state: BeltState
    speed_kmh: float
    mode: Mode
    elapsed_s: int
    distance_km: float
    steps: int
    app_speed_kmh: float | None
    button: int
    raw: bytes


@dataclass(frozen=True, slots=True)
class WilinkLastStatus:
    elapsed_s: int
    distance_km: float
    steps: int
    raw: bytes


def parse_wilink_status(frame: bytes) -> WilinkStatus | None:
    if len(frame) < 19 or frame[0] != WILINK_START_IN or frame[1] != WILINK_TYPE_CMD:
        return None
    if frame[-1] != WILINK_END:
        return None
    return WilinkStatus(
        belt_state=BeltState.from_wilink(frame[2]),
        speed_kmh=frame[3] / 10.0,
        mode=Mode.from_wilink(frame[4]),
        elapsed_s=_u24be(frame, 5),
        distance_km=_u24be(frame, 8) / 100.0,
        steps=_u24be(frame, 11),
        app_speed_kmh=(frame[14] / 30.0) if frame[14] else None,
        button=frame[16],
        raw=bytes(frame),
    )


def parse_wilink_last_status(frame: bytes) -> WilinkLastStatus | None:
    if len(frame) < 18 or frame[0] != WILINK_START_IN or frame[1] != WILINK_TYPE_HIST:
        return None
    return WilinkLastStatus(
        elapsed_s=_u24be(frame, 8),
        distance_km=_u24be(frame, 11) / 100.0,
        steps=_u24be(frame, 14),
        raw=bytes(frame),
    )


def extract_wilink_frames(buffer: bytearray) -> list[bytes]:
    """Split coalesced/split notify bytes on F8…FD boundaries."""
    frames: list[bytes] = []
    while True:
        try:
            start = buffer.index(WILINK_START_IN)
        except ValueError:
            buffer.clear()
            return frames
        if start > 0:
            del buffer[:start]
        try:
            end = buffer.index(WILINK_END, 1)
        except ValueError:
            return frames
        frames.append(bytes(buffer[: end + 1]))
        del buffer[: end + 1]
