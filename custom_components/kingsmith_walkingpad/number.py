"""Speed setpoint."""

from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfSpeed
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_ALLOW_CONTROL, DEFAULT_ALLOW_CONTROL, DOMAIN
from .coordinator import WalkingPadCoordinator
from .entity import WalkingPadEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: WalkingPadCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WalkingPadSpeedNumber(coordinator)])


class WalkingPadSpeedNumber(WalkingPadEntity, NumberEntity):
    _attr_name = "Speed"
    _attr_icon = "mdi:speedometer"
    _attr_device_class = NumberDeviceClass.SPEED
    _attr_native_unit_of_measurement = UnitOfSpeed.KILOMETERS_PER_HOUR
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: WalkingPadCoordinator) -> None:
        super().__init__(coordinator, "speed")

    @property
    def native_min_value(self) -> float:
        return self.coordinator.data.min_speed_kmh if self.coordinator.data else 0.5

    @property
    def native_max_value(self) -> float:
        return self.coordinator.data.max_speed_kmh if self.coordinator.data else 6.0

    @property
    def native_step(self) -> float:
        return self.coordinator.data.speed_step_kmh if self.coordinator.data else 0.1

    @property
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.target_speed_kmh or self.coordinator.data.speed_kmh

    async def async_set_native_value(self, value: float) -> None:
        entry = self.coordinator.entry
        allowed = entry.options.get(
            CONF_ALLOW_CONTROL, entry.data.get(CONF_ALLOW_CONTROL, DEFAULT_ALLOW_CONTROL)
        )
        if not allowed or self.coordinator.pad is None:
            return
        await self.coordinator.pad.set_speed(value)
