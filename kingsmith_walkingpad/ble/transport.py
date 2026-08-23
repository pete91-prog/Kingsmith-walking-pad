"""Bleak-backed GATT transport."""

from __future__ import annotations

import logging
from typing import Any

from bleak import BleakClient
from bleak.backends.device import BLEDevice

from .backend import GattChar, GattService, NotifyCallback

logger = logging.getLogger(__name__)


class BleakTransport:
    def __init__(self, address: str | BLEDevice, name: str | None = None) -> None:
        if isinstance(address, BLEDevice):
            self.address = address.address
            self.name = address.name or name
            self._target: str | BLEDevice = address
        else:
            self.address = address
            self.name = name
            self._target = address
        self._client: BleakClient | None = None

    async def connect(self) -> None:
        self._client = BleakClient(self._target, timeout=20.0)
        await self._client.connect()
        if self._client.name:
            self.name = self._client.name

    async def disconnect(self) -> None:
        if self._client and self._client.is_connected:
            await self._client.disconnect()
        self._client = None

    def is_connected(self) -> bool:
        return bool(self._client and self._client.is_connected)

    def _require(self) -> BleakClient:
        if not self._client or not self._client.is_connected:
            raise RuntimeError("Not connected to the WalkingPad")
        return self._client

    async def services(self) -> list[GattService]:
        client = self._require()
        out: list[GattService] = []
        for service in client.services:
            chars = [
                GattChar(uuid=char.uuid.lower(), properties=list(char.properties))
                for char in service.characteristics
            ]
            out.append(GattService(uuid=service.uuid.lower(), characteristics=chars))
        return out

    async def read(self, uuid: str) -> bytes:
        return bytes(await self._require().read_gatt_char(uuid))

    async def write(self, uuid: str, data: bytes, response: bool = False) -> None:
        await self._require().write_gatt_char(uuid, data, response=response)

    async def start_notify(self, uuid: str, callback: NotifyCallback) -> None:
        async def _wrapped(_sender: Any, data: bytearray) -> None:
            result = callback(bytes(data))
            if hasattr(result, "__await__"):
                await result  # type: ignore[misc]

        await self._require().start_notify(uuid, _wrapped)

    async def stop_notify(self, uuid: str) -> None:
        try:
            await self._require().stop_notify(uuid)
        except Exception as exc:  # noqa: BLE001 — disconnect paths are best-effort
            logger.debug("stop_notify %s failed: %s", uuid, exc)
