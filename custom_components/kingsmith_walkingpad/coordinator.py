"""Stay connected to the WalkingPad and push status into Home Assistant."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_ADDRESS, CONF_WEIGHT, DEFAULT_WEIGHT, DOMAIN
from .kingsmith_walkingpad.ble.transport import BleakTransport
from .kingsmith_walkingpad.models import PadStatus
from .kingsmith_walkingpad.pad import WalkingPad

_LOGGER = logging.getLogger(__name__)


class WalkingPadCoordinator(DataUpdateCoordinator[PadStatus]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=entry.title,
            update_interval=timedelta(seconds=15),
        )
        self.entry = entry
        self.address: str = entry.data[CONF_ADDRESS]
        self.pad: WalkingPad | None = None

    async def async_connect(self) -> None:
        device = bluetooth.async_ble_device_from_address(self.hass, self.address, True)
        transport = BleakTransport(device or self.address, name=self.entry.title)
        weight = self.entry.options.get(CONF_WEIGHT, self.entry.data.get(CONF_WEIGHT, DEFAULT_WEIGHT))
        self.pad = WalkingPad(transport=transport, weight_kg=float(weight))
        self.pad.on_status(self._on_status)
        await self.pad.connect()
        self.async_set_updated_data(self.pad.status)

    def _on_status(self, status: PadStatus) -> None:
        self.hass.loop.call_soon_threadsafe(self.async_set_updated_data, status)

    async def _async_update_data(self) -> PadStatus:
        if self.pad is None:
            raise UpdateFailed("WalkingPad is not connected")
        if not self.pad.status.connected:
            try:
                await self.async_connect()
            except Exception as err:  # noqa: BLE001
                raise UpdateFailed(f"Reconnect failed: {err}") from err
        try:
            return await self.pad.refresh()
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(str(err)) from err

    async def async_shutdown(self) -> None:
        if self.pad is not None:
            await self.pad.disconnect()
            self.pad = None


async def async_get_coordinator(hass: HomeAssistant, entry: ConfigEntry) -> WalkingPadCoordinator:
    return hass.data[DOMAIN][entry.entry_id]
