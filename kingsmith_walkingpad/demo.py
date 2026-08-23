"""In-process WalkingPad used by `walkingpad serve --demo` and tests."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from .ble.backend import GattChar, GattService, NotifyCallback
from .const import (
    FTMS_CONTROL_POINT,
    FTMS_MACHINE_STATUS,
    FTMS_SERVICE,
    FTMS_SPEED_RANGE,
    FTMS_TREADMILL_DATA,
    WILINK_NOTIFY,
    WILINK_SERVICE,
    WILINK_WRITE,
)
from .models import BeltState, Mode, ProtocolType
from .pad import WalkingPad
from .protocol import ftms as ftms_proto
from .protocol import wilink as wilink_proto

NotifyFn = Callable[[bytes], Awaitable[None] | None]


class DemoTransport:
    """GATT-shaped fake that speaks WiLink or FTMS without a radio."""

    def __init__(self, protocol: ProtocolType = ProtocolType.WILINK, name: str = "WalkingPad-Demo") -> None:
        self.address = "AA:BB:CC:DD:EE:FF"
        self.name = name
        self.protocol = protocol
        self._connected = False
        self._notifiers: dict[str, NotifyCallback] = {}
        self.speed = 0.0
        self.mode = Mode.STANDBY
        self.belt = BeltState.IDLE
        self.elapsed = 0
        self.distance_m = 0.0
        self.steps = 0
        self._tick_task: asyncio.Task[None] | None = None

    async def connect(self) -> None:
        self._connected = True
        self._tick_task = asyncio.create_task(self._tick(), name="demo-tick")

    async def disconnect(self) -> None:
        self._connected = False
        if self._tick_task:
            self._tick_task.cancel()
            try:
                await self._tick_task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
            self._tick_task = None

    def is_connected(self) -> bool:
        return self._connected

    async def services(self) -> list[GattService]:
        if self.protocol == ProtocolType.FTMS:
            return [
                GattService(
                    uuid=FTMS_SERVICE,
                    characteristics=[
                        GattChar(FTMS_TREADMILL_DATA, ["notify"]),
                        GattChar(FTMS_CONTROL_POINT, ["write", "indicate"]),
                        GattChar(FTMS_MACHINE_STATUS, ["notify"]),
                        GattChar(FTMS_SPEED_RANGE, ["read"]),
                    ],
                )
            ]
        return [
            GattService(
                uuid=WILINK_SERVICE,
                characteristics=[
                    GattChar(WILINK_NOTIFY, ["notify"]),
                    GattChar(WILINK_WRITE, ["write-without-response"]),
                ],
            )
        ]

    async def read(self, uuid: str) -> bytes:
        if uuid.lower() == FTMS_SPEED_RANGE:
            return (50).to_bytes(2, "little") + (600).to_bytes(2, "little") + (10).to_bytes(2, "little")
        return b""

    async def write(self, uuid: str, data: bytes, response: bool = False) -> None:
        del response
        if uuid.lower() == WILINK_WRITE:
            self._handle_wilink(data)
        elif uuid.lower() == FTMS_CONTROL_POINT:
            self._handle_ftms(data)

    async def start_notify(self, uuid: str, callback: NotifyCallback) -> None:
        self._notifiers[uuid.lower()] = callback

    async def stop_notify(self, uuid: str) -> None:
        self._notifiers.pop(uuid.lower(), None)

    def _handle_wilink(self, data: bytes) -> None:
        if len(data) < 4 or data[1] != 0xA2:
            return
        opcode = data[2]
        if opcode == wilink_proto.WilinkCommand.SET_MODE and len(data) > 3:
            self.mode = Mode.from_wilink(data[3])
        elif opcode == wilink_proto.WilinkCommand.START:
            self.belt = BeltState.RUNNING
            self.mode = Mode.MANUAL
            if self.speed <= 0:
                self.speed = 0.5
        elif opcode == wilink_proto.WilinkCommand.SET_SPEED and len(data) > 3:
            self.speed = data[3] / 10.0
            self.belt = BeltState.STOPPED if self.speed <= 0 else BeltState.RUNNING
        elif opcode == wilink_proto.WilinkCommand.PAUSE:
            self.belt = BeltState.PAUSED
        self._emit_wilink()

    def _handle_ftms(self, data: bytes) -> None:
        if not data:
            return
        op = data[0]
        if op == ftms_proto.FtmsControl.START_RESUME:
            self.belt = BeltState.RUNNING
            if self.speed <= 0:
                self.speed = 1.6
            self._notify(FTMS_MACHINE_STATUS, bytes([ftms_proto.MachineStatus.STARTED]))
        elif op == ftms_proto.FtmsControl.STOP_PAUSE:
            kind = data[1] if len(data) > 1 else 1
            self.belt = BeltState.PAUSED if kind == 2 else BeltState.STOPPED
            if kind != 2:
                self.speed = 0.0
            self._notify(FTMS_MACHINE_STATUS, bytes([ftms_proto.MachineStatus.STOPPED]))
        elif op == ftms_proto.FtmsControl.SET_TARGET_SPEED and len(data) >= 3:
            self.speed = int.from_bytes(data[1:3], "little") / 100.0
            self.belt = BeltState.RUNNING if self.speed > 0 else BeltState.STOPPED
        self._emit_ftms()

    def _emit_wilink(self) -> None:
        dist = int(round(self.distance_m / 10.0))  # 0.01 km units
        payload = bytearray(
            [
                0xF8,
                0xA2,
                {BeltState.IDLE: 0, BeltState.RUNNING: 1, BeltState.STANDBY: 5, BeltState.STARTING: 9}.get(
                    self.belt, 0
                ),
                int(round(self.speed * 10)),
                self.mode.to_wilink() if self.mode != Mode.UNKNOWN else 2,
            ]
        )
        payload.extend(self.elapsed.to_bytes(3, "big"))
        payload.extend(dist.to_bytes(3, "big"))
        payload.extend(int(self.steps).to_bytes(3, "big"))
        payload.extend([0, 0, 0, 0])
        checksum = sum(payload[1:]) & 0xFF
        payload.extend([checksum, 0xFD])
        self._notify(WILINK_NOTIFY, bytes(payload))

    def _emit_ftms(self) -> None:
        flags = 0x0004 | 0x0400 | 0x2000  # distance, elapsed, steps; speed present (bit0 clear)
        raw = bytearray(flags.to_bytes(2, "little"))
        raw.extend(int(round(self.speed * 100)).to_bytes(2, "little"))
        raw.extend(int(self.distance_m).to_bytes(3, "little"))
        raw.extend(int(self.elapsed).to_bytes(2, "little"))
        raw.extend(int(self.steps).to_bytes(2, "little"))
        self._notify(FTMS_TREADMILL_DATA, bytes(raw))

    def _notify(self, uuid: str, data: bytes) -> None:
        callback = self._notifiers.get(uuid.lower())
        if callback is None:
            return
        result = callback(data)
        if hasattr(result, "__await__"):
            asyncio.create_task(result)  # type: ignore[arg-type]

    async def _tick(self) -> None:
        while self._connected:
            await asyncio.sleep(1.0)
            if self.belt == BeltState.RUNNING and self.speed > 0:
                self.elapsed += 1
                self.distance_m += self.speed * 1000.0 / 3600.0
                # Rough 0.75 m stride at typical walking speeds.
                self.steps = int(self.distance_m / 0.75)
            if self.protocol == ProtocolType.FTMS:
                self._emit_ftms()
            else:
                self._emit_wilink()


def demo_pad(protocol: ProtocolType = ProtocolType.WILINK) -> WalkingPad:
    transport = DemoTransport(protocol=protocol)
    return WalkingPad(transport=transport, name=transport.name)
