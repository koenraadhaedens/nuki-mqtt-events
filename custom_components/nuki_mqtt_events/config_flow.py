"""Config flow for the Nuki MQTT Events integration."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_TOPIC, DEFAULT_TOPIC, DOMAIN


class NukiMqttEventsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Nuki MQTT Events."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")

        return self.async_create_entry(
            title="Nuki MQTT Events",
            data={CONF_TOPIC: DEFAULT_TOPIC},
        )


class NukiMqttEventsOptionsFlow(config_entries.OptionsFlow):
    """Handle Nuki MQTT Events options."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the integration options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_TOPIC,
                        default=self.config_entry.options.get(CONF_TOPIC, DEFAULT_TOPIC),
                    ): str,
                }
            ),
        )
