"""Belt on/off."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_ALLOW_CONTROL, DEFAULT_ALLOW_CONTROL, DOMAIN
from .coordinator import WalkingPadCoordinator
from .entity import WalkingPadEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: WalkingPadCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WalkingPadBeltSwitch(coordinator)])


class WalkingPadBeltSwitch(WalkingPadEntity, SwitchEntity):
    _attr_name = "Belt"
    _attr_icon = "mdi:treadmill"

    def __init__(self, coordinator: WalkingPadCoordinator) -> None:
        super().__init__(coordinator, "belt")

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data and self.coordinator.data.belt_state.is_moving)

    async def async_turn_on(self, **kwargs) -> None:  # noqa: ANN003
        if not self._allowed():
            return
        assert self.coordinator.pad is not None
        await self.coordinator.pad.start()

    async def async_turn_off(self, **kwargs) -> None:  # noqa: ANN003
        if self.coordinator.pad is None:
            return
        await self.coordinator.pad.stop()

    def _allowed(self) -> bool:
        entry = self.coordinator.entry
        return entry.options.get(
            CONF_ALLOW_CONTROL, entry.data.get(CONF_ALLOW_CONTROL, DEFAULT_ALLOW_CONTROL)
        )
