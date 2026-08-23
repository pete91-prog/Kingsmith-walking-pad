"""On-wire codecs for KingSmith WalkingPad BLE protocols."""

from .detect import looks_like_walkingpad, pick_protocol
from .ftms import (
    FtmsControl,
    FtmsResult,
    parse_speed_range,
    parse_treadmill_data,
)
from .supplement import (
    is_unlock_ok,
    parse_supplement_frame,
    supplement_frame,
    unlock_frame,
)
from .wilink import (
    WilinkCommand,
    extract_wilink_frames,
    parse_wilink_last_status,
    parse_wilink_status,
    wilink_checksum,
    wilink_frame,
)

__all__ = [
    "FtmsControl",
    "FtmsResult",
    "WilinkCommand",
    "extract_wilink_frames",
    "is_unlock_ok",
    "looks_like_walkingpad",
    "parse_speed_range",
    "parse_supplement_frame",
    "parse_treadmill_data",
    "parse_wilink_last_status",
    "parse_wilink_status",
    "pick_protocol",
    "supplement_frame",
    "unlock_frame",
    "wilink_checksum",
    "wilink_frame",
]
