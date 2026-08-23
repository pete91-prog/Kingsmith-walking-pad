"""Shared status and capability models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ProtocolType(str, Enum):
    WILINK = "wilink"
    FTMS = "ftms"
    DEMO = "demo"


class Mode(str, Enum):
    AUTO = "auto"
    MANUAL = "manual"
    STANDBY = "standby"
    UNKNOWN = "unknown"

    @classmethod
    def from_wilink(cls, value: int) -> Mode:
        return {0: cls.AUTO, 1: cls.MANUAL, 2: cls.STANDBY}.get(value, cls.UNKNOWN)

    def to_wilink(self) -> int:
        mapping = {self.AUTO: 0, self.MANUAL: 1, self.STANDBY: 2}
        if self not in mapping:
            raise ValueError(f"Mode {self} cannot be sent to the pad")
        return mapping[self]


class BeltState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    STARTING = "starting"
    STANDBY = "standby"
    PAUSED = "paused"
    STOPPED = "stopped"
    UNKNOWN = "unknown"

    @classmethod
    def from_wilink(cls, value: int) -> BeltState:
        return {
            0: cls.IDLE,
            1: cls.RUNNING,
            5: cls.STANDBY,
            9: cls.STARTING,
        }.get(value, cls.UNKNOWN)

    @property
    def is_moving(self) -> bool:
        return self in {BeltState.RUNNING, BeltState.STARTING}


@dataclass(slots=True)
class SpeedRange:
    min_kmh: float = 0.5
    max_kmh: float = 6.0
    step_kmh: float = 0.1


@dataclass(slots=True)
class PadStatus:
    connected: bool = False
    protocol: ProtocolType | None = None
    address: str | None = None
    name: str | None = None
    firmware: str | None = None
    belt_state: BeltState = BeltState.UNKNOWN
    mode: Mode = Mode.UNKNOWN
    speed_kmh: float = 0.0
    target_speed_kmh: float | None = None
    distance_km: float = 0.0
    steps: int = 0
    elapsed_s: int = 0
    calories: float | None = None
    incline_percent: float | None = None
    child_lock: bool | None = None
    min_speed_kmh: float = 0.5
    max_speed_kmh: float = 6.0
    speed_step_kmh: float = 0.1

    def to_dict(self) -> dict[str, Any]:
        return {
            "connected": self.connected,
            "protocol": self.protocol.value if self.protocol else None,
            "address": self.address,
            "name": self.name,
            "firmware": self.firmware,
            "belt_state": self.belt_state.value,
            "mode": self.mode.value,
            "speed_kmh": round(self.speed_kmh, 2),
            "target_speed_kmh": (
                round(self.target_speed_kmh, 2) if self.target_speed_kmh is not None else None
            ),
            "distance_km": round(self.distance_km, 3),
            "steps": self.steps,
            "elapsed_s": self.elapsed_s,
            "calories": None if self.calories is None else round(self.calories, 1),
            "incline_percent": self.incline_percent,
            "child_lock": self.child_lock,
            "min_speed_kmh": self.min_speed_kmh,
            "max_speed_kmh": self.max_speed_kmh,
            "speed_step_kmh": self.speed_step_kmh,
            "moving": self.belt_state.is_moving,
        }


@dataclass(slots=True)
class DiscoveredPad:
    address: str
    name: str | None
    rssi: int | None = None
    service_uuids: list[str] = field(default_factory=list)
