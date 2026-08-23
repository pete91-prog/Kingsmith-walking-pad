"""Workout telemetry."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import WalkingPadCoordinator
from .entity import WalkingPadEntity
from .kingsmith_walkingpad.models import PadStatus


@dataclass(frozen=True, kw_only=True)
class PadSensorDescription(SensorEntityDescription):
    value_fn: Callable[[PadStatus], float | int | str | None]


SENSORS: tuple[PadSensorDescription, ...] = (
    PadSensorDescription(
        key="distance",
        name="Distance",
        icon="mdi:map-marker-distance",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda s: round(s.distance_km, 3),
    ),
    PadSensorDescription(
        key="steps",
        name="Steps",
        icon="mdi:shoe-print",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda s: s.steps,
    ),
    PadSensorDescription(
        key="calories",
        name="Calories",
        icon="mdi:fire",
        native_unit_of_measurement="kcal",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda s: None if s.calories is None else round(s.calories, 1),
    ),
    PadSensorDescription(
        key="elapsed",
        name="Elapsed time",
        icon="mdi:timer-outline",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda s: s.elapsed_s,
    ),
    PadSensorDescription(
        key="current_speed",
        name="Current speed",
        icon="mdi:speedometer",
        native_unit_of_measurement="km/h",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: round(s.speed_kmh, 2),
    ),
    PadSensorDescription(
        key="belt_state",
        name="Belt state",
        icon="mdi:information-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.belt_state.value,
    ),
    PadSensorDescription(
        key="protocol",
        name="Protocol",
        icon="mdi:bluetooth",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.protocol.value if s.protocol else None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: WalkingPadCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(WalkingPadSensor(coordinator, desc) for desc in SENSORS)


class WalkingPadSensor(WalkingPadEntity, SensorEntity):
    entity_description: PadSensorDescription

    def __init__(self, coordinator: WalkingPadCoordinator, description: PadSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description
        self._attr_name = description.name

    @property
    def native_value(self) -> float | int | str | None:
        if not self.coordinator.data:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
