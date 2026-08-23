"""Emergency stop."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import WalkingPadCoordinator
from .entity import WalkingPadEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: WalkingPadCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WalkingPadStopButton(coordinator)])


class WalkingPadStopButton(WalkingPadEntity, ButtonEntity):
    _attr_name = "Stop"
    _attr_icon = "mdi:stop-circle"

    def __init__(self, coordinator: WalkingPadCoordinator) -> None:
        super().__init__(coordinator, "stop")

    async def async_press(self) -> None:
        if self.coordinator.pad is None:
            return
        await self.coordinator.pad.stop()
