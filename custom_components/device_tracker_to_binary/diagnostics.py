"""Diagnostics support for Device Tracker as Binary Sensor."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_GPS_ACCURACY,
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    CONF_ENTITY_ID,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN

# Device tracker attributes that reveal a location or network identity.
TO_REDACT = {
    ATTR_GPS_ACCURACY,
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    "host_name",
    "hostname",
    "ip",
    "ip_address",
    "mac",
    "mac_address",
}


def _entity_diagnostics(
    hass: HomeAssistant, registry_entry: er.RegistryEntry | None, entity_id: str
) -> dict[str, Any]:
    """Return registry metadata and redacted state for an entity."""
    state = hass.states.get(entity_id)
    return {
        "entity_id": entity_id,
        "registry_entry": None
        if registry_entry is None
        else {
            "device_id": registry_entry.device_id,
            "disabled_by": registry_entry.disabled_by,
            "entity_category": registry_entry.entity_category,
            "has_entity_name": registry_entry.has_entity_name,
            "hidden_by": registry_entry.hidden_by,
            "original_name": registry_entry.original_name,
        },
        "state": None
        if state is None
        else {
            "state": state.state,
            "attributes": async_redact_data(dict(state.attributes), TO_REDACT),
            "last_changed": state.last_changed.isoformat(),
        },
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    registry = er.async_get(hass)

    source_id = entry.options[CONF_ENTITY_ID]
    source_entry = registry.async_get(source_id)
    source_entity_id = source_entry.entity_id if source_entry else source_id

    sensor_entity_id = registry.async_get_entity_id(
        "binary_sensor", DOMAIN, entry.entry_id
    )

    return {
        "entry": {
            "title": entry.title,
            "state": entry.state.value,
            "options": dict(entry.options),
        },
        "source": _entity_diagnostics(hass, source_entry, source_entity_id),
        "binary_sensor": None
        if sensor_entity_id is None
        else _entity_diagnostics(
            hass, registry.async_get(sensor_entity_id), sensor_entity_id
        ),
    }
