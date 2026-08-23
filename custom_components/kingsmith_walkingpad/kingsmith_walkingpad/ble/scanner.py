"""Discover nearby KingSmith WalkingPads over BLE."""

from __future__ import annotations

from bleak import BleakScanner

from ..const import FTMS_SERVICE, WILINK_SERVICE
from ..models import DiscoveredPad
from ..protocol.detect import looks_like_walkingpad


async def scan_pads(timeout: float = 6.0) -> list[DiscoveredPad]:
    devices = await BleakScanner.discover(timeout=timeout, return_adv=True)
    found: list[DiscoveredPad] = []
    for device, adv in devices.values():
        uuids = list(adv.service_uuids or [])
        if not looks_like_walkingpad(device.name, uuids):
            # Also accept devices that only advertise the well-known services
            # without a useful name (some OS stacks strip local names).
            lowered = {u.lower() for u in uuids}
            if FTMS_SERVICE not in lowered and WILINK_SERVICE not in lowered:
                continue
        found.append(
            DiscoveredPad(
                address=device.address,
                name=device.name,
                rssi=adv.rssi,
                service_uuids=uuids,
            )
        )
    found.sort(key=lambda d: d.rssi if d.rssi is not None else -999, reverse=True)
    return found
