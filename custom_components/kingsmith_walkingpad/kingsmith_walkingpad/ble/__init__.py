"""Bluetooth transport for KingSmith WalkingPads."""

from .scanner import scan_pads
from .transport import BleakTransport

__all__ = ["BleakTransport", "scan_pads"]
