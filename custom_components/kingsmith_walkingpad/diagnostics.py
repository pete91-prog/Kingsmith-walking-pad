"""Diagnostics for the offline WalkingPad integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_ADDRESS, CONF_ALLOW_CONTROL, CONF_WEIGHT, DOMAIN
from .coordinator import WalkingPadCoordinator


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    coordinator: WalkingPadCoordinator = hass.data[DOMAIN][entry.entry_id]
    status = coordinator.data
    return {
        "entry": {
            "title": entry.title,
            "address": entry.data.get(CONF_ADDRESS),
            "allow_control": entry.options.get(
                CONF_ALLOW_CONTROL, entry.data.get(CONF_ALLOW_CONTROL)
            ),
            "weight_kg": entry.options.get(CONF_WEIGHT, entry.data.get(CONF_WEIGHT)),
        },
        "status": None if status is None else status.to_dict(),
    }
