"""Pick a BLE protocol from advertised name and GATT services."""

from __future__ import annotations

from ..const import (
    FTMS_NAME_PREFIXES,
    FTMS_SERVICE,
    NAME_PREFIXES,
    WILINK_SERVICE,
)
from ..models import ProtocolType


def _norm(uuid: str) -> str:
    return uuid.lower()


def looks_like_walkingpad(name: str | None, service_uuids: list[str] | None = None) -> bool:
    uuids = {_norm(u) for u in (service_uuids or [])}
    if FTMS_SERVICE in uuids or WILINK_SERVICE in uuids:
        return True
    if not name:
        return False
    return any(name.startswith(prefix) or prefix.lower() in name.lower() for prefix in NAME_PREFIXES)


def pick_protocol(
    name: str | None,
    service_uuids: list[str] | None = None,
) -> ProtocolType | None:
    uuids = {_norm(u) for u in (service_uuids or [])}
    if FTMS_SERVICE in uuids:
        return ProtocolType.FTMS
    if WILINK_SERVICE in uuids:
        return ProtocolType.WILINK
    if name:
        if any(name.startswith(prefix) for prefix in FTMS_NAME_PREFIXES):
            return ProtocolType.FTMS
        if looks_like_walkingpad(name):
            return ProtocolType.WILINK
    return None
