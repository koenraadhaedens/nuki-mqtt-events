"""Config flow for the Nuki MQTT Events integration."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_TOPIC, DEFAULT_TOPIC, DOMAIN


class NukiMqttEventsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Nuki MQTT Events."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            topic = user_input[CONF_TOPIC].strip()
            if topic:
                return self.async_create_entry(
                    title="Nuki MQTT Events",
                    data={CONF_TOPIC: topic},
                )
            errors["base"] = "invalid_topic"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TOPIC, default=DEFAULT_TOPIC): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @config_entries.HANDLERS.register(DOMAIN)
    def async_get_options_flow(config_entry):
        """Return options flow for this config entry."""
        return NukiMqttEventsOptionsFlow(config_entry)


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
