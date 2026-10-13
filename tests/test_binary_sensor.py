"""Tests for the binary sensor platform."""

from __future__ import annotations

import pytest
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_FRIENDLY_NAME,
    STATE_HOME,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    EntityCategory,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.device_tracker_to_binary.const import DOMAIN

from .common import get_state


async def _setup_helper(
    hass: HomeAssistant, tracker_entity_id: str, device_class: str = "connectivity"
) -> tuple[MockConfigEntry, str]:
    """Set up a helper wrapping the tracker and return (entry, sensor entity_id)."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        options={"entity_id": tracker_entity_id, "device_class": device_class},
        title="Fallback title",
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    sensor_id = er.async_get(hass).async_get_entity_id(
        "binary_sensor", DOMAIN, entry.entry_id
    )
    assert sensor_id is not None
    return entry, sensor_id


async def test_unknown_tracker_state_is_unavailable(hass: HomeAssistant) -> None:
    """An unknown tracker state makes the binary sensor unavailable."""
    hass.states.async_set("device_tracker.test", STATE_UNKNOWN)
    _, sensor_id = await _setup_helper(hass, "device_tracker.test")
    assert get_state(hass, sensor_id).state == STATE_UNAVAILABLE


async def test_missing_tracker_state_is_unavailable(hass: HomeAssistant) -> None:
    """A tracker with no state at all makes the binary sensor unavailable."""
    _, sensor_id = await _setup_helper(hass, "device_tracker.nothing")
    assert get_state(hass, sensor_id).state == STATE_UNAVAILABLE


async def test_invalid_device_class_falls_back(hass: HomeAssistant) -> None:
    """An unrecognised stored device class falls back to connectivity."""
    hass.states.async_set("device_tracker.test", STATE_HOME)
    _, sensor_id = await _setup_helper(hass, "device_tracker.test", "not_a_class")
    assert get_state(hass, sensor_id).attributes[ATTR_DEVICE_CLASS] == "connectivity"


async def test_unregistered_tracker_uses_entry_title(hass: HomeAssistant) -> None:
    """Without a registry entry the sensor is named after the config entry."""
    hass.states.async_set("device_tracker.test", STATE_HOME)
    _, sensor_id = await _setup_helper(hass, "device_tracker.test")
    assert get_state(hass, sensor_id).attributes[ATTR_FRIENDLY_NAME] == (
        "Fallback title"
    )


async def test_metadata_copied_from_device_tracker(hass: HomeAssistant) -> None:
    """Device, entity category and naming are copied from the wrapped tracker."""
    source_entry = MockConfigEntry(domain="test")
    source_entry.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=source_entry.entry_id,
        identifiers={("test", "phone")},
        name="Phone",
    )
    registry = er.async_get(hass)
    tracker = registry.async_get_or_create(
        "device_tracker",
        "test",
        "phone_tracker",
        config_entry=source_entry,
        device_id=device.id,
        entity_category=EntityCategory.DIAGNOSTIC,
        has_entity_name=True,
        original_name="Wi-Fi",
    )
    hass.states.async_set(tracker.entity_id, STATE_HOME)

    _, sensor_id = await _setup_helper(hass, tracker.entity_id)

    sensor = registry.async_get(sensor_id)
    assert sensor is not None
    assert sensor.device_id == device.id
    assert sensor.entity_category is EntityCategory.DIAGNOSTIC
    assert get_state(hass, sensor_id).attributes[ATTR_FRIENDLY_NAME] == "Phone Wi-Fi"


@pytest.mark.parametrize("original_name", ["", None])
async def test_device_named_tracker_names_sensor_after_device(
    hass: HomeAssistant, original_name: str | None
) -> None:
    """A tracker named after its device alone yields a sensor named the same way."""
    source_entry = MockConfigEntry(domain="test")
    source_entry.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=source_entry.entry_id,
        identifiers={("test", "client")},
        name="00:80:04:06:00:02",
    )
    tracker = er.async_get(hass).async_get_or_create(
        "device_tracker",
        "test",
        "client_tracker",
        config_entry=source_entry,
        device_id=device.id,
        has_entity_name=True,
        original_name=original_name,
    )
    hass.states.async_set(tracker.entity_id, STATE_HOME)

    _, sensor_id = await _setup_helper(hass, tracker.entity_id)

    assert get_state(hass, sensor_id).attributes[ATTR_FRIENDLY_NAME] == (
        "00:80:04:06:00:02"
    )


async def test_custom_name_copied_only_on_creation(hass: HomeAssistant) -> None:
    """The tracker's custom name is copied once, not on later reloads."""
    registry = er.async_get(hass)
    tracker = registry.async_get_or_create(
        "device_tracker", "test", "named", original_name="Tracker"
    )
    registry.async_update_entity(tracker.entity_id, name="My phone")
    hass.states.async_set(tracker.entity_id, STATE_HOME)

    entry, sensor_id = await _setup_helper(hass, tracker.entity_id)
    sensor = registry.async_get(sensor_id)
    assert sensor is not None
    assert sensor.name == "My phone"

    registry.async_update_entity(tracker.entity_id, name="Renamed phone")
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    sensor = registry.async_get(sensor_id)
    assert sensor is not None
    assert sensor.name == "My phone"
