"""The Nuki MQTT Events integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_AUTHORIZATION_NAMES,
    CONF_CODE_NAMES,
    DATA_AUTHORIZATION_NAMES,
    DATA_CODE_NAMES,
    DOMAIN,
    PLATFORMS,
)

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Optional(DOMAIN): vol.Schema(
            {
                vol.Optional(CONF_AUTHORIZATION_NAMES, default={}): {
                    vol.Coerce(str): cv.string
                },
                vol.Optional(CONF_CODE_NAMES, default={}): {
                    vol.Coerce(str): cv.string
                },
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the integration from YAML configuration."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    yaml_config = config.get(DOMAIN, {})
    domain_data[DATA_AUTHORIZATION_NAMES] = dict(
        yaml_config.get(CONF_AUTHORIZATION_NAMES, {})
    )
    domain_data[DATA_CODE_NAMES] = dict(yaml_config.get(CONF_CODE_NAMES, {}))
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Nuki MQTT Events from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {}
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an Nuki MQTT Events config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
