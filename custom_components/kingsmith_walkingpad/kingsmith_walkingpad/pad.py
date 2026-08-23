"""Unified WalkingPad client. Auto-detects WiLink, FTMS, and vendor unlocks."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from .ble.backend import BleTransport, GattService
from .ble.transport import BleakTransport
from .calories import SessionCalories
from .const import (
    COLD_START_WAIT_S,
    DEFAULT_MAX_SPEED,
    DEFAULT_MIN_SPEED,
    DEFAULT_SPEED_STEP,
    DEFAULT_WEIGHT_KG,
    DEVICE_INFO_SERVICE,
    FTMS_CMD_GAP_S,
    FTMS_CONTROL_POINT,
    FTMS_MACHINE_STATUS,
    FTMS_SPEED_RANGE,
    FTMS_TREADMILL_DATA,
    MODEL_NUMBER,
    ODM_PREAMBLE,
    ODM_WRITE,
    SOFTWARE_REVISION,
    STATUS_POLL_S,
    SUPPLEMENT_CMD_GAP_S,
    SUPPLEMENT_NOTIFY,
    SUPPLEMENT_SERVICE,
    SUPPLEMENT_WRITE,
    WILINK_CMD_GAP_S,
    WILINK_NOTIFY,
    WILINK_WRITE,
)
from .exceptions import CommandError, ProtocolError
from .models import BeltState, Mode, PadStatus, ProtocolType
from .protocol import (
    extract_wilink_frames,
    is_unlock_ok,
    parse_speed_range,
    parse_treadmill_data,
    parse_wilink_last_status,
    parse_wilink_status,
    pick_protocol,
    unlock_frame,
)
from .protocol import ftms as ftms_proto
from .protocol import wilink as wilink_proto

logger = logging.getLogger(__name__)

StatusCallback = Callable[[PadStatus], Awaitable[None] | None]


def _has_char(services: list[GattService], uuid: str) -> bool:
    target = uuid.lower()
    return any(any(c.uuid == target for c in svc.characteristics) for svc in services)


def _has_service(services: list[GattService], uuid: str) -> bool:
    target = uuid.lower()
    return any(svc.uuid == target for svc in services)


class WalkingPad:
    """Local, cloud-free WalkingPad controller.

    The last mile is always Bluetooth. Use :mod:`kingsmith_walkingpad.server`
    if you want HTTP or MQTT on your LAN.
    """

    def __init__(
        self,
        address: str | None = None,
        *,
        transport: BleTransport | None = None,
        name: str | None = None,
        weight_kg: float = DEFAULT_WEIGHT_KG,
    ) -> None:
        if transport is None and not address:
            raise ValueError("Provide a BLE address or a transport")
        self._transport: BleTransport = transport or BleakTransport(address, name=name)
        self._weight_kg = weight_kg
        self._calories = SessionCalories(weight_kg)
        self._status = PadStatus(address=self._transport.address, name=name or self._transport.name)
        self._callbacks: list[StatusCallback] = []
        self._wilink_buf = bytearray()
        self._last_write = 0.0
        self._protocol: ProtocolType | None = None
        self._has_supplement = False
        self._has_odm = False
        self._poll_task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()
        self._lock = asyncio.Lock()
        self._unlocked = False

    @property
    def status(self) -> PadStatus:
        return self._status

    @property
    def protocol(self) -> ProtocolType | None:
        return self._protocol

    def on_status(self, callback: StatusCallback) -> None:
        self._callbacks.append(callback)

    async def connect(self) -> PadStatus:
        await self._transport.connect()
        services = await self._transport.services()
        uuids = [svc.uuid for svc in services]
        name = self._transport.name or self._status.name
        chosen = pick_protocol(name, uuids)
        if chosen is None:
            await self._transport.disconnect()
            raise ProtocolError(
                f"No WalkingPad protocol on {self._transport.address} "
                f"(name={name!r} services={uuids})"
            )
        self._protocol = chosen
        self._has_supplement = _has_service(services, SUPPLEMENT_SERVICE) or _has_char(
            services, SUPPLEMENT_WRITE
        )
        self._has_odm = _has_char(services, ODM_WRITE)
        self._status.connected = True
        self._status.protocol = chosen
        self._status.address = self._transport.address
        self._status.name = name
        await self._read_device_info(services)

        if chosen == ProtocolType.FTMS:
            await self._setup_ftms()
        elif chosen == ProtocolType.WILINK:
            await self._setup_wilink()
        self._stop.clear()
        if chosen == ProtocolType.WILINK:
            self._poll_task = asyncio.create_task(self._wilink_poll_loop(), name="wilink-poll")
        await self._emit()
        return self._status

    async def disconnect(self) -> None:
        self._stop.set()
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
            self._poll_task = None
        await self._transport.disconnect()
        self._status.connected = False
        await self._emit()

    async def start(self, speed_kmh: float | None = None) -> None:
        async with self._lock:
            if self._protocol == ProtocolType.WILINK:
                await self._write_wilink(wilink_proto.set_mode(Mode.MANUAL))
                await self._write_wilink(wilink_proto.start_belt())
            elif self._protocol == ProtocolType.FTMS:
                await self._ftms_command(ftms_proto.start_resume())
            elif self._protocol == ProtocolType.DEMO:
                await self._write_wilink(b"")  # pragma: no cover - demo overrides
            if speed_kmh is not None:
                await self._set_speed_locked(speed_kmh, wait_for_motion=True)
            self._status.belt_state = BeltState.STARTING
            self._status.mode = Mode.MANUAL
            await self._emit()

    async def stop(self) -> None:
        async with self._lock:
            if self._protocol == ProtocolType.WILINK:
                await self._write_wilink(wilink_proto.stop_belt())
            elif self._protocol == ProtocolType.FTMS:
                await self._ftms_command(ftms_proto.stop())
            self._status.belt_state = BeltState.STOPPED
            self._status.speed_kmh = 0.0
            self._status.target_speed_kmh = 0.0
            await self._emit()

    async def pause(self) -> None:
        async with self._lock:
            if self._protocol == ProtocolType.WILINK:
                await self._write_wilink(wilink_proto.pause_belt())
            elif self._protocol == ProtocolType.FTMS:
                await self._ftms_command(ftms_proto.pause())
            self._status.belt_state = BeltState.PAUSED
            await self._emit()

    async def set_speed(self, speed_kmh: float) -> None:
        async with self._lock:
            await self._set_speed_locked(speed_kmh, wait_for_motion=self._status.belt_state == BeltState.STARTING)

    async def set_mode(self, mode: Mode | str) -> None:
        resolved = Mode(mode) if isinstance(mode, str) else mode
        async with self._lock:
            if self._protocol == ProtocolType.WILINK:
                await self._write_wilink(wilink_proto.set_mode(resolved))
                self._status.mode = resolved
                await self._emit()
            elif resolved == Mode.STANDBY:
                await self.stop()
            else:
                self._status.mode = resolved
                await self._emit()

    async def set_child_lock(self, enabled: bool) -> None:
        async with self._lock:
            if self._protocol == ProtocolType.WILINK:
                await self._write_wilink(wilink_proto.set_pref_child_lock(enabled))
            self._status.child_lock = enabled
            await self._emit()

    async def refresh(self) -> PadStatus:
        if self._protocol == ProtocolType.WILINK and self._transport.is_connected():
            await self._write_wilink(wilink_proto.request_status())
        return self._status

    async def _set_speed_locked(self, speed_kmh: float, wait_for_motion: bool) -> None:
        speed = max(self._status.min_speed_kmh, min(self._status.max_speed_kmh, round(speed_kmh, 2)))
        if wait_for_motion:
            await self._wait_until_moving()
        if self._protocol == ProtocolType.WILINK:
            await self._write_wilink(wilink_proto.set_speed(speed))
        elif self._protocol == ProtocolType.FTMS:
            await self._ftms_command(ftms_proto.set_target_speed(speed))
        self._status.target_speed_kmh = speed
        if speed <= 0:
            self._status.belt_state = BeltState.STOPPED
        await self._emit()

    async def _wait_until_moving(self) -> None:
        deadline = time.monotonic() + COLD_START_WAIT_S
        while time.monotonic() < deadline:
            if self._status.speed_kmh > 0 or self._status.belt_state == BeltState.RUNNING:
                return
            await asyncio.sleep(0.25)

    async def _read_device_info(self, services: list[GattService]) -> None:
        if not _has_service(services, DEVICE_INFO_SERVICE) and not _has_char(services, SOFTWARE_REVISION):
            return
        for uuid, attr in ((SOFTWARE_REVISION, "firmware"), (MODEL_NUMBER, "name")):
            if not _has_char(services, uuid):
                continue
            try:
                value = (await self._transport.read(uuid)).decode("utf-8", errors="ignore").strip()
            except Exception as exc:  # noqa: BLE001
                logger.debug("read %s failed: %s", uuid, exc)
                continue
            if value:
                if attr == "firmware":
                    self._status.firmware = value
                elif not self._status.name:
                    self._status.name = value

    async def _setup_wilink(self) -> None:
        if not self._transport.is_connected():
            raise ProtocolError("Disconnected before WiLink setup")
        await self._transport.start_notify(WILINK_NOTIFY, self._on_wilink_bytes)
        await asyncio.sleep(0.05)
        await self._write_wilink(wilink_proto.request_status())

    async def _setup_ftms(self) -> None:
        if self._has_supplement:
            await self._unlock_supplement()
        try:
            raw_range = await self._transport.read(FTMS_SPEED_RANGE)
            rng = parse_speed_range(raw_range)
            self._status.min_speed_kmh = rng.min_kmh or DEFAULT_MIN_SPEED
            self._status.max_speed_kmh = rng.max_kmh or DEFAULT_MAX_SPEED
            self._status.speed_step_kmh = rng.step_kmh or DEFAULT_SPEED_STEP
        except Exception as exc:  # noqa: BLE001
            logger.debug("speed range read failed: %s", exc)
            self._status.min_speed_kmh = DEFAULT_MIN_SPEED
            self._status.max_speed_kmh = DEFAULT_MAX_SPEED
            self._status.speed_step_kmh = DEFAULT_SPEED_STEP

        await self._transport.start_notify(FTMS_TREADMILL_DATA, self._on_ftms_data)
        await asyncio.sleep(0.15)
        try:
            await self._transport.start_notify(FTMS_MACHINE_STATUS, self._on_ftms_machine_status)
            await asyncio.sleep(0.15)
        except Exception as exc:  # noqa: BLE001
            logger.debug("machine status subscribe failed: %s", exc)
        try:
            await self._transport.start_notify(FTMS_CONTROL_POINT, self._on_ftms_control)
            await asyncio.sleep(0.15)
        except Exception as exc:  # noqa: BLE001
            logger.debug("control point indicate failed: %s", exc)
        # Request control; some KingSmith firmwares reject this and still accept
        # later commands after the vendor unlock / ODM pre-amble.
        try:
            await self._ftms_command(ftms_proto.request_control(), tolerate_failure=True)
        except CommandError:
            logger.info("FTMS REQUEST_CONTROL rejected; continuing after vendor handshake")

    async def _unlock_supplement(self) -> None:
        name = self._status.name or self._transport.name or ""
        unlocked = asyncio.Event()

        def _on_supp(data: bytes) -> None:
            if is_unlock_ok(data):
                unlocked.set()

        await self._transport.start_notify(SUPPLEMENT_NOTIFY, _on_supp)
        await asyncio.sleep(0.05)
        await self._pace(SUPPLEMENT_CMD_GAP_S)
        try:
            await self._transport.write(SUPPLEMENT_WRITE, unlock_frame(name), response=False)
        except Exception as exc:
            raise ProtocolError(f"Supplement unlock write failed: {exc}") from exc
        try:
            await asyncio.wait_for(unlocked.wait(), timeout=10.0)
            self._unlocked = True
            logger.info("KingSmith supplement unlock accepted")
        except TimeoutError:
            logger.warning("No supplement unlock reply; FTMS commands may be ignored")

    async def _ftms_command(self, payload: bytes, tolerate_failure: bool = False) -> None:
        if self._has_odm:
            await self._pace(FTMS_CMD_GAP_S)
            try:
                await self._transport.write(ODM_WRITE, ODM_PREAMBLE, response=False)
            except Exception as exc:  # noqa: BLE001
                logger.debug("ODM preamble write failed: %s", exc)
        await self._pace(FTMS_CMD_GAP_S)
        try:
            await self._transport.write(FTMS_CONTROL_POINT, payload, response=True)
        except Exception as exc:
            if tolerate_failure:
                logger.debug("FTMS command %s ignored: %s", payload.hex(), exc)
                return
            raise CommandError(f"FTMS write failed: {exc}") from exc

    async def _write_wilink(self, payload: bytes) -> None:
        if not payload:
            return
        await self._pace(WILINK_CMD_GAP_S)
        await self._transport.write(WILINK_WRITE, payload, response=False)

    async def _pace(self, gap: float) -> None:
        wait = gap - (time.monotonic() - self._last_write)
        if wait > 0:
            await asyncio.sleep(wait)
        self._last_write = time.monotonic()

    async def _wilink_poll_loop(self) -> None:
        while not self._stop.is_set():
            if self._transport.is_connected():
                try:
                    await self._write_wilink(wilink_proto.request_status())
                except Exception as exc:  # noqa: BLE001
                    logger.debug("status poll failed: %s", exc)
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=STATUS_POLL_S)
            except TimeoutError:
                continue
            except asyncio.CancelledError:
                raise

    def _on_wilink_bytes(self, data: bytes) -> None:
        self._wilink_buf.extend(data)
        for frame in extract_wilink_frames(self._wilink_buf):
            status = parse_wilink_status(frame)
            if status:
                if status.belt_state is BeltState.IDLE and status.speed_kmh > 0:
                    self._status.belt_state = BeltState.PAUSED
                else:
                    self._status.belt_state = status.belt_state
                self._status.speed_kmh = status.speed_kmh
                self._status.mode = status.mode
                self._status.elapsed_s = status.elapsed_s
                self._status.distance_km = status.distance_km
                self._status.steps = status.steps
                self._status.calories = self._calories.update(status.speed_kmh, status.elapsed_s)
                self._schedule_emit()
                continue
            last = parse_wilink_last_status(frame)
            if last:
                self._status.elapsed_s = last.elapsed_s
                self._status.distance_km = last.distance_km
                self._status.steps = last.steps
                self._schedule_emit()

    def _on_ftms_data(self, data: bytes) -> None:
        parsed = parse_treadmill_data(data)
        if parsed.speed_kmh is not None:
            self._status.speed_kmh = parsed.speed_kmh
            if parsed.speed_kmh > 0:
                self._status.belt_state = BeltState.RUNNING
        if parsed.distance_m is not None:
            self._status.distance_km = parsed.distance_m / 1000.0
        if parsed.elapsed_s is not None:
            self._status.elapsed_s = parsed.elapsed_s
        if parsed.steps is not None:
            self._status.steps = parsed.steps
        if parsed.incline_percent is not None:
            self._status.incline_percent = parsed.incline_percent
        if parsed.calories is not None:
            self._status.calories = float(parsed.calories)
        else:
            self._status.calories = self._calories.update(self._status.speed_kmh, self._status.elapsed_s)
        self._schedule_emit()

    def _on_ftms_machine_status(self, data: bytes) -> None:
        if not data:
            return
        code = data[0]
        if code == ftms_proto.MachineStatus.STARTED:
            self._status.belt_state = BeltState.RUNNING
        elif code in {ftms_proto.MachineStatus.STOPPED, ftms_proto.MachineStatus.STOPPED_SAFETY}:
            self._status.belt_state = BeltState.STOPPED
            self._status.speed_kmh = 0.0
        elif code == ftms_proto.MachineStatus.RESET:
            self._status.belt_state = BeltState.IDLE
        self._schedule_emit()

    def _on_ftms_control(self, data: bytes) -> None:
        parsed = ftms_proto.parse_control_response(data)
        if parsed:
            opcode, result = parsed
            logger.debug("FTMS response op=%s result=%s", opcode, result)

    def _schedule_emit(self) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        loop.create_task(self._emit())

    async def _emit(self) -> None:
        snapshot = self._status
        for callback in list(self._callbacks):
            try:
                result = callback(snapshot)
                if hasattr(result, "__await__"):
                    await result  # type: ignore[misc]
            except Exception:  # noqa: BLE001
                logger.exception("status callback failed")

    async def __aenter__(self) -> WalkingPad:
        await self.connect()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.disconnect()
