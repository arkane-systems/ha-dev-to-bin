"""Tests for config entry setup, unload and removal."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_HOME, STATE_NOT_HOME, STATE_OFF, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er, issue_registry as ir
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.device_tracker_to_binary.const import DOMAIN

from .common import get_state


async def test_setup_fails_for_unknown_source_uuid(hass: HomeAssistant) -> None:
    """Setup errors out when the stored source entity registry ID no longer exists."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        options={
            "entity_id": "0123456789abcdef0123456789abcdef",
            "device_class": "connectivity",
        },
        title="Test",
    )
    entry.add_to_hass(hass)

    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_ERROR
    assert entry.reason == (
        "The wrapped device tracker 0123456789abcdef0123456789abcdef no longer exists"
    )

    issue_id = f"source_entity_missing_{entry.entry_id}"
    issue_registry = ir.async_get(hass)
    issue = issue_registry.async_get_issue(DOMAIN, issue_id)
    assert issue is not None
    assert issue.translation_key == "source_entity_missing"

    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert issue_registry.async_get_issue(DOMAIN, issue_id) is None


async def _setup_registered(
    hass: HomeAssistant, unique_id: str = "unique1"
) -> tuple[MockConfigEntry, str]:
    """Register a tracker, set up a helper for it and return (entry, tracker id)."""
    registry = er.async_get(hass)
    tracker = registry.async_get_or_create(
        "device_tracker", "test", unique_id, suggested_object_id="phone"
    )
    hass.states.async_set(tracker.entity_id, STATE_HOME)

    entry = MockConfigEntry(
        domain=DOMAIN,
        options={"entity_id": tracker.entity_id, "device_class": "connectivity"},
        title="Test",
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry, tracker.entity_id


async def test_unload_entry(hass: HomeAssistant) -> None:
    """A loaded entry unloads cleanly and its entity becomes unavailable."""
    entry, _ = await _setup_registered(hass)
    sensor_id = er.async_get(hass).async_get_entity_id(
        "binary_sensor", DOMAIN, entry.entry_id
    )
    assert sensor_id is not None

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert get_state(hass, sensor_id).state == STATE_UNAVAILABLE


async def test_source_entity_id_change_updates_entry(hass: HomeAssistant) -> None:
    """Renaming the source entity ID updates the options and reloads the helper."""
    entry, tracker_id = await _setup_registered(hass)
    registry = er.async_get(hass)
    sensor_id = registry.async_get_entity_id("binary_sensor", DOMAIN, entry.entry_id)
    assert sensor_id is not None

    registry.async_update_entity(tracker_id, new_entity_id="device_tracker.renamed")
    await hass.async_block_till_done()

    assert entry.options["entity_id"] == "device_tracker.renamed"
    assert entry.state is ConfigEntryState.LOADED

    hass.states.async_set("device_tracker.renamed", STATE_NOT_HOME)
    await hass.async_block_till_done()
    assert get_state(hass, sensor_id).state == STATE_OFF


async def test_source_entity_removed_removes_entry(hass: HomeAssistant) -> None:
    """Removing the source entity removes the helper config entry."""
    entry, tracker_id = await _setup_registered(hass)

    er.async_get(hass).async_remove(tracker_id)
    await hass.async_block_till_done()

    assert hass.config_entries.async_get_entry(entry.entry_id) is None


async def test_remove_entry_with_unknown_source_uuid(hass: HomeAssistant) -> None:
    """Removing an entry whose source registry ID is gone does not fail."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        options={
            "entity_id": "0123456789abcdef0123456789abcdef",
            "device_class": "connectivity",
        },
        title="Test",
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.config_entries.async_get_entry(entry.entry_id) is None


async def test_remove_entry_with_unregistered_source(hass: HomeAssistant) -> None:
    """Removing an entry for a tracker with no registry entry does not fail."""
    hass.states.async_set("device_tracker.legacy", STATE_HOME)
    entry = MockConfigEntry(
        domain=DOMAIN,
        options={"entity_id": "device_tracker.legacy", "device_class": "connectivity"},
        title="Test",
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.config_entries.async_get_entry(entry.entry_id) is None


async def test_remove_entry_keeps_user_hidden_source(hass: HomeAssistant) -> None:
    """Removing the helper leaves a tracker hidden by the user hidden."""
    entry, tracker_id = await _setup_registered(hass)
    registry = er.async_get(hass)
    registry.async_update_entity(tracker_id, hidden_by=er.RegistryEntryHider.USER)

    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()

    tracker = registry.async_get(tracker_id)
    assert tracker is not None
    assert tracker.hidden_by == er.RegistryEntryHider.USER
