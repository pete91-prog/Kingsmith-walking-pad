"""Transport interface so the pad client can run against Bleak or a demo."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable, Protocol

NotifyCallback = Callable[[bytes], Awaitable[None] | None]


@dataclass(frozen=True, slots=True)
class GattChar:
    uuid: str
    properties: list[str]


@dataclass(frozen=True, slots=True)
class GattService:
    uuid: str
    characteristics: list[GattChar]


class BleTransport(Protocol):
    address: str
    name: str | None

    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    def is_connected(self) -> bool: ...
    async def services(self) -> list[GattService]: ...
    async def read(self, uuid: str) -> bytes: ...
    async def write(self, uuid: str, data: bytes, response: bool = False) -> None: ...
    async def start_notify(self, uuid: str, callback: NotifyCallback) -> None: ...
    async def stop_notify(self, uuid: str) -> None: ...
