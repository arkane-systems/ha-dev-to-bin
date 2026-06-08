"""The Device Tracker as Binary Sensor integration."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ENTITY_ID, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.helper_integration import async_handle_source_entity_changes

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

_PLATFORMS = [Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a config entry."""
    entity_registry = er.async_get(hass)

    try:
        entity_id = er.async_validate_entity_id(
            entity_registry, entry.options[CONF_ENTITY_ID]
        )
    except vol.Invalid:
        _LOGGER.error(
            "Failed to set up device_tracker_to_binary for unknown entity %s",
            entry.options[CONF_ENTITY_ID],
        )
        return False

    tracker_entry = entity_registry.async_get(entity_id)
    source_device_id = tracker_entry.device_id if tracker_entry else None

    def set_source_entity_id_or_uuid(source_entity_id: str) -> None:
        hass.config_entries.async_update_entry(
            entry,
            options={**entry.options, CONF_ENTITY_ID: source_entity_id},
        )
        hass.config_entries.async_schedule_reload(entry.entry_id)

    async def source_entity_removed() -> None:
        await hass.config_entries.async_remove(entry.entry_id)

    entry.async_on_unload(
        async_handle_source_entity_changes(
            hass,
            add_helper_config_entry_to_device=False,
            helper_config_entry_id=entry.entry_id,
            set_source_entity_id_or_uuid=set_source_entity_id_or_uuid,
            source_device_id=source_device_id,
            source_entity_id_or_uuid=entry.options[CONF_ENTITY_ID],
            source_entity_removed=source_entity_removed,
        )
    )

    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove a config entry.

    Unhides the wrapped device tracker entity and restores assistant expose settings.
    """
    registry = er.async_get(hass)

    try:
        tracker_entity_id = er.async_validate_entity_id(
            registry, entry.options[CONF_ENTITY_ID]
        )
    except vol.Invalid:
        # The source entity has been removed from the entity registry.
        return

    if not (tracker_entry := registry.async_get(tracker_entity_id)):
        return

    # Unhide the wrapped entity.
    if tracker_entry.hidden_by == er.RegistryEntryHider.INTEGRATION:
        registry.async_update_entity(tracker_entity_id, hidden_by=None)
