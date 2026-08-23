"""Bluetooth SIG Fitness Machine Service codecs, plus KingSmith extras."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from ..models import SpeedRange


class FtmsControl(IntEnum):
    REQUEST_CONTROL = 0x00
    RESET = 0x01
    SET_TARGET_SPEED = 0x02
    SET_TARGET_INCLINATION = 0x03
    START_RESUME = 0x07
    STOP_PAUSE = 0x08


class FtmsResult(IntEnum):
    SUCCESS = 0x01
    NOT_SUPPORTED = 0x02
    INVALID_PARAMETER = 0x03
    FAILED = 0x04
    CONTROL_NOT_PERMITTED = 0x05


class MachineStatus(IntEnum):
    RESET = 0x01
    STOPPED = 0x02
    STOPPED_SAFETY = 0x03
    STARTED = 0x04
    SPEED_CHANGED = 0x05
    CONTROL_LOST = 0xFF


def request_control() -> bytes:
    return bytes([FtmsControl.REQUEST_CONTROL])


def reset() -> bytes:
    return bytes([FtmsControl.RESET])


def start_resume() -> bytes:
    return bytes([FtmsControl.START_RESUME])


def stop() -> bytes:
    return bytes([FtmsControl.STOP_PAUSE, 0x01])


def pause() -> bytes:
    return bytes([FtmsControl.STOP_PAUSE, 0x02])


def set_target_speed(kmh: float) -> bytes:
    hundredths = max(0, min(65535, round(kmh * 100)))
    return bytes([FtmsControl.SET_TARGET_SPEED]) + hundredths.to_bytes(2, "little")


def set_target_incline(percent: float) -> bytes:
    tenths = max(-32768, min(32767, round(percent * 10)))
    return bytes([FtmsControl.SET_TARGET_INCLINATION]) + tenths.to_bytes(2, "little", signed=True)


@dataclass(frozen=True, slots=True)
class TreadmillData:
    speed_kmh: float | None = None
    distance_m: int | None = None
    elapsed_s: int | None = None
    steps: int | None = None
    calories: int | None = None
    incline_percent: float | None = None
    raw: bytes = b""


def parse_treadmill_data(raw: bytes) -> TreadmillData:
    """Parse FTMS Treadmill Data (0x2ACD), including KingSmith step bit 13."""
    if len(raw) < 2:
        return TreadmillData(raw=bytes(raw))
    flags = int.from_bytes(raw[0:2], "little")
    offset = 2

    def take(n: int) -> bytes:
        nonlocal offset
        chunk = raw[offset : offset + n]
        offset += n
        return chunk

    speed = None
    distance = None
    elapsed = None
    steps = None
    calories = None
    incline = None

    # Flag bit 0 clear means instantaneous speed is present (FTMS "more data" bit).
    if not flags & 0x01 and offset + 2 <= len(raw):
        speed = int.from_bytes(take(2), "little") / 100.0
    if flags & 0x02 and offset + 2 <= len(raw):
        take(2)  # average speed
    if flags & 0x04 and offset + 3 <= len(raw):
        distance = int.from_bytes(take(3) + b"\x00", "little")
    if flags & 0x08 and offset + 4 <= len(raw):
        incline = int.from_bytes(take(2), "little", signed=True) / 10.0
        take(2)  # ramp angle
    if flags & 0x10 and offset + 2 <= len(raw):
        take(2)  # elevation gain
    if flags & 0x20 and offset + 1 <= len(raw):
        take(1)  # instantaneous pace
    if flags & 0x40 and offset + 1 <= len(raw):
        take(1)  # average pace
    if flags & 0x80 and offset + 5 <= len(raw):
        calories = int.from_bytes(take(2), "little")
        take(3)
    if flags & 0x100 and offset + 1 <= len(raw):
        take(1)  # heart rate
    if flags & 0x200 and offset + 1 <= len(raw):
        take(1)  # MET
    if flags & 0x400 and offset + 2 <= len(raw):
        elapsed = int.from_bytes(take(2), "little")
    if flags & 0x800 and offset + 2 <= len(raw):
        take(2)  # remaining time
    if flags & 0x1000 and offset + 4 <= len(raw):
        take(4)  # force on belt + power
    if flags & 0x2000 and offset + 2 <= len(raw):
        steps = int.from_bytes(take(2), "little")

    return TreadmillData(
        speed_kmh=speed,
        distance_m=distance,
        elapsed_s=elapsed,
        steps=steps,
        calories=calories,
        incline_percent=incline,
        raw=bytes(raw),
    )


def parse_speed_range(raw: bytes) -> SpeedRange:
    if len(raw) < 6:
        return SpeedRange()
    return SpeedRange(
        min_kmh=int.from_bytes(raw[0:2], "little") / 100.0,
        max_kmh=int.from_bytes(raw[2:4], "little") / 100.0,
        step_kmh=int.from_bytes(raw[4:6], "little") / 100.0 or 0.1,
    )


def parse_control_response(raw: bytes) -> tuple[int, int] | None:
    """Return (request_opcode, result_code) from a 0x80 indication."""
    if len(raw) < 3 or raw[0] != 0x80:
        return None
    return raw[1], raw[2]
