"""Config flow: Bluetooth discovery or a manual MAC address."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.selector import BooleanSelector, NumberSelector, NumberSelectorConfig

from .const import (
    CONF_ADDRESS,
    CONF_ALLOW_CONTROL,
    CONF_NAME,
    CONF_WEIGHT,
    DEFAULT_ALLOW_CONTROL,
    DEFAULT_WEIGHT,
    DOMAIN,
)
from .kingsmith_walkingpad.protocol.detect import looks_like_walkingpad

_WEIGHT = NumberSelector(NumberSelectorConfig(min=30, max=200, step=0.5, mode="box"))


class WalkingPadConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._discovery: BluetoothServiceInfoBleak | None = None

    async def async_step_bluetooth(self, discovery_info: BluetoothServiceInfoBleak) -> ConfigFlowResult:
        if not looks_like_walkingpad(discovery_info.name, list(discovery_info.service_uuids)):
            return self.async_abort(reason="not_supported")
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self._discovery = discovery_info
        self.context["title_placeholders"] = {
            "name": discovery_info.name or "WalkingPad",
            "address": discovery_info.address,
        }
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        assert self._discovery is not None
        if user_input is not None:
            return self._create(self._discovery.address, self._discovery.name, user_input)
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={
                "name": self._discovery.name or "WalkingPad",
                "address": self._discovery.address,
            },
        )

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        current = {info.address for info in self._async_current_entries()}
        discovered: dict[str, str] = {}
        for info in bluetooth.async_discovered_service_info(self.hass, connectable=True):
            if info.address in current:
                continue
            if looks_like_walkingpad(info.name, list(info.service_uuids)):
                discovered[info.address] = info.name or info.address

        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address.upper())
            self._abort_if_unique_id_configured()
            return self._create(address, user_input.get(CONF_NAME) or discovered.get(address), user_input)

        if not discovered and user_input is None:
            schema = vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): str,
                    vol.Optional(CONF_NAME): str,
                    vol.Optional(CONF_WEIGHT, default=DEFAULT_WEIGHT): _WEIGHT,
                    vol.Optional(CONF_ALLOW_CONTROL, default=DEFAULT_ALLOW_CONTROL): BooleanSelector(),
                }
            )
            return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

        schema = vol.Schema(
            {
                vol.Required(CONF_ADDRESS): vol.In(discovered) if discovered else str,
                vol.Optional(CONF_WEIGHT, default=DEFAULT_WEIGHT): _WEIGHT,
                vol.Optional(CONF_ALLOW_CONTROL, default=DEFAULT_ALLOW_CONTROL): BooleanSelector(),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    def _create(self, address: str, name: str | None, user_input: dict[str, Any]) -> ConfigFlowResult:
        return self.async_create_entry(
            title=name or address,
            data={
                CONF_ADDRESS: address,
                CONF_NAME: name or "WalkingPad",
                CONF_WEIGHT: user_input.get(CONF_WEIGHT, DEFAULT_WEIGHT),
                CONF_ALLOW_CONTROL: user_input.get(CONF_ALLOW_CONTROL, DEFAULT_ALLOW_CONTROL),
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return WalkingPadOptionsFlow()


class WalkingPadOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        entry = self.config_entry
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_WEIGHT,
                        default=entry.options.get(
                            CONF_WEIGHT, entry.data.get(CONF_WEIGHT, DEFAULT_WEIGHT)
                        ),
                    ): _WEIGHT,
                    vol.Optional(
                        CONF_ALLOW_CONTROL,
                        default=entry.options.get(
                            CONF_ALLOW_CONTROL,
                            entry.data.get(CONF_ALLOW_CONTROL, DEFAULT_ALLOW_CONTROL),
                        ),
                    ): BooleanSelector(),
                }
            ),
        )
