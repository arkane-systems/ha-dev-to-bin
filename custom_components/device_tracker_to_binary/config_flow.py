"""Config flow for Device Tracker as Binary Sensor."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.const import CONF_ENTITY_ID
from homeassistant.helpers import entity_registry as er, selector
from homeassistant.helpers.schema_config_entry_flow import (
    SchemaConfigFlowHandler,
    SchemaFlowFormStep,
    wrapped_entity_config_entry_title,
)

from .const import CONF_DEVICE_CLASS, DEFAULT_DEVICE_CLASS, DOMAIN

_DEVICE_CLASS_OPTIONS = [dc.value for dc in BinarySensorDeviceClass]

CONFIG_FLOW: dict[str, SchemaFlowFormStep] = {
    "user": SchemaFlowFormStep(
        vol.Schema(
            {
                vol.Required(CONF_ENTITY_ID): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="device_tracker"),
                ),
                vol.Optional(
                    CONF_DEVICE_CLASS, default=DEFAULT_DEVICE_CLASS
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=_DEVICE_CLASS_OPTIONS,
                        translation_key="device_class",
                    ),
                ),
            }
        )
    ),
}

OPTIONS_FLOW: dict[str, SchemaFlowFormStep] = {
    "init": SchemaFlowFormStep(
        vol.Schema(
            {
                vol.Required(CONF_DEVICE_CLASS): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=_DEVICE_CLASS_OPTIONS,
                        translation_key="device_class",
                    ),
                ),
            }
        )
    ),
}


class DeviceTrackerToBinaryConfigFlowHandler(SchemaConfigFlowHandler, domain=DOMAIN):
    """Handle a config flow for Device Tracker as Binary Sensor."""

    config_flow = CONFIG_FLOW
    options_flow = OPTIONS_FLOW
    options_flow_reloads = True

    VERSION = 1
    MINOR_VERSION = 1

    def async_config_entry_title(self, options: Mapping[str, Any]) -> str:
        """Return config entry title and hide the wrapped entity if registered."""
        registry = er.async_get(self.hass)
        entity_entry = registry.async_get(options[CONF_ENTITY_ID])
        if entity_entry is not None and not entity_entry.hidden:
            registry.async_update_entity(
                options[CONF_ENTITY_ID],
                hidden_by=er.RegistryEntryHider.INTEGRATION,
            )

        return wrapped_entity_config_entry_title(self.hass, options[CONF_ENTITY_ID])
