"""The Device Tracker as Binary Sensor integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ENTITY_ID, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers import entity_registry as er, issue_registry as ir
from homeassistant.helpers.helper_integration import async_handle_source_entity_changes

from .const import DOMAIN
from .helpers import async_unhide_source

_PLATFORMS = [Platform.BINARY_SENSOR]


def _source_missing_issue_id(entry: ConfigEntry) -> str:
    """Return the repair issue ID for an entry whose source entity is missing."""
    return f"source_entity_missing_{entry.entry_id}"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a config entry."""
    entity_registry = er.async_get(hass)

    try:
        entity_id = er.async_validate_entity_id(
            entity_registry, entry.options[CONF_ENTITY_ID]
        )
    except vol.Invalid as err:
        ir.async_create_issue(
            hass,
            DOMAIN,
            _source_missing_issue_id(entry),
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="source_entity_missing",
            translation_placeholders={
                "title": entry.title,
                "entity_id": entry.options[CONF_ENTITY_ID],
            },
        )
        raise ConfigEntryError(
            translation_domain=DOMAIN,
            translation_key="source_entity_not_found",
            translation_placeholders={"entity_id": entry.options[CONF_ENTITY_ID]},
        ) from err

    ir.async_delete_issue(hass, DOMAIN, _source_missing_issue_id(entry))

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

    Unhides the wrapped device tracker entity and clears any repair issue.
    """
    ir.async_delete_issue(hass, DOMAIN, _source_missing_issue_id(entry))
    async_unhide_source(hass, entry.options[CONF_ENTITY_ID])
