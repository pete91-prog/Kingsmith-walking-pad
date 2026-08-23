"""Operating mode (auto / manual / standby)."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import WalkingPadCoordinator
from .entity import WalkingPadEntity
from .kingsmith_walkingpad.models import Mode


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: WalkingPadCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WalkingPadModeSelect(coordinator)])


class WalkingPadModeSelect(WalkingPadEntity, SelectEntity):
    _attr_name = "Mode"
    _attr_icon = "mdi:cog"
    _attr_options = [Mode.AUTO.value, Mode.MANUAL.value, Mode.STANDBY.value]

    def __init__(self, coordinator: WalkingPadCoordinator) -> None:
        super().__init__(coordinator, "mode")

    @property
    def current_option(self) -> str | None:
        if not self.coordinator.data:
            return None
        mode = self.coordinator.data.mode.value
        return mode if mode in self._attr_options else None

    async def async_select_option(self, option: str) -> None:
        if self.coordinator.pad is None:
            return
        await self.coordinator.pad.set_mode(Mode(option))
