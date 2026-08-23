"""Shared entity base."""

from __future__ import annotations

from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import WalkingPadCoordinator


class WalkingPadEntity(CoordinatorEntity[WalkingPadCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: WalkingPadCoordinator, key: str) -> None:
        super().__init__(coordinator)
        address = coordinator.address
        self._attr_unique_id = f"{address}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, address)},
            connections={(CONNECTION_BLUETOOTH, address)},
            manufacturer="KingSmith",
            name=coordinator.entry.title,
            model=coordinator.data.name if coordinator.data else "WalkingPad",
            sw_version=coordinator.data.firmware if coordinator.data else None,
        )

    @property
    def available(self) -> bool:
        return super().available and bool(self.coordinator.data and self.coordinator.data.connected)
