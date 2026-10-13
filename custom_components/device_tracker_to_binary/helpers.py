"""Helpers for hiding and unhiding the wrapped device tracker."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er


@callback
def async_hide_source(hass: HomeAssistant, entity_id: str) -> None:
    """Hide the wrapped tracker, unless it is unregistered or already hidden."""
    registry = er.async_get(hass)
    entity_entry = registry.async_get(entity_id)
    if entity_entry is not None and not entity_entry.hidden:
        registry.async_update_entity(
            entity_id, hidden_by=er.RegistryEntryHider.INTEGRATION
        )


@callback
def async_unhide_source(hass: HomeAssistant, entity_id_or_uuid: str) -> None:
    """Unhide the wrapped tracker if this integration hid it."""
    registry = er.async_get(hass)

    try:
        entity_id = er.async_validate_entity_id(registry, entity_id_or_uuid)
    except vol.Invalid:
        # The source entity has been removed from the entity registry.
        return

    if not (entity_entry := registry.async_get(entity_id)):
        return

    if entity_entry.hidden_by == er.RegistryEntryHider.INTEGRATION:
        registry.async_update_entity(entity_id, hidden_by=None)
