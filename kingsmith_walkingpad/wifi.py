"""What the treadmill's own Wi-Fi radio can and cannot do offline.

KingSmith dual-radio WalkingPads (KS Fit "Wi-Fi + Bluetooth" models) join your
2.4 GHz network so the official app can reach KingSmith cloud. They do not
expose a documented local HTTP, TCP, or Tuya LAN API for belt control.

This module is a best-effort LAN probe so you can see whether a given unit
answers on common vendor ports. Control stays on Bluetooth; use the HTTP/MQTT
bridge in :mod:`kingsmith_walkingpad.server` for house-wide Wi-Fi access.
"""

from __future__ import annotations

import asyncio
import socket
from dataclasses import dataclass

COMMON_PORTS = (
    80,
    443,
    6668,  # Tuya LAN
    8080,
    8886,
    8888,
    9000,
)


@dataclass(slots=True)
class WifiProbeResult:
    host: str
    open_ports: list[int]
    notes: str


async def probe_host(host: str, ports: tuple[int, ...] = COMMON_PORTS, timeout: float = 0.6) -> WifiProbeResult:
    open_ports: list[int] = []

    async def _check(port: int) -> None:
        try:
            _reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout)
        except (TimeoutError, OSError, socket.gaierror):
            return
        open_ports.append(port)
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:  # noqa: BLE001
            pass

    await asyncio.gather(*(_check(port) for port in ports))
    open_ports.sort()
    if open_ports:
        notes = (
            "The host accepted TCP on one or more ports. That is not enough to "
            "prove a local WalkingPad API exists — KingSmith units typically "
            "only phone home. Prefer Bluetooth plus this project's LAN bridge."
        )
    else:
        notes = (
            "No common local-control ports answered. Expected for KS Fit Wi-Fi "
            "models: the radio is cloud-bound. Use Bluetooth for the pad and "
            "the HTTP/MQTT bridge for the rest of the LAN."
        )
    return WifiProbeResult(host=host, open_ports=open_ports, notes=notes)
