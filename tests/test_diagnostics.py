"""Tests for diagnostics."""

from __future__ import annotations

from homeassistant.components.diagnostics import REDACTED
from homeassistant.const import STATE_HOME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.device_tracker_to_binary.const import DOMAIN


async def test_entry_diagnostics(
    hass: HomeAssistant, hass_client: ClientSessionGenerator
) -> None:
    """Diagnostics include source and sensor details, with location redacted."""
    assert await async_setup_component(hass, "diagnostics", {})
    registry = er.async_get(hass)
    tracker = registry.async_get_or_create(
        "device_tracker", "test", "gps", suggested_object_id="phone"
    )
    hass.states.async_set(
        tracker.entity_id,
        STATE_HOME,
        {"latitude": 51.5, "longitude": -0.1, "gps_accuracy": 10, "source_type": "gps"},
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        options={"entity_id": tracker.entity_id, "device_class": "presence"},
        title="Phone",
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    diagnostics = await get_diagnostics_for_config_entry(hass, hass_client, entry)

    assert diagnostics["entry"] == {
        "title": "Phone",
        "state": "loaded",
        "options": {"entity_id": tracker.entity_id, "device_class": "presence"},
    }

    source = diagnostics["source"]
    assert source["entity_id"] == tracker.entity_id
    assert source["registry_entry"]["hidden_by"] is None
    assert source["state"]["state"] == STATE_HOME
    assert source["state"]["attributes"] == {
        "latitude": REDACTED,
        "longitude": REDACTED,
        "gps_accuracy": REDACTED,
        "source_type": "gps",
    }

    sensor = diagnostics["binary_sensor"]
    assert sensor["entity_id"].startswith("binary_sensor.")
    assert sensor["state"]["state"] == "on"
    assert sensor["state"]["attributes"]["device_class"] == "presence"


async def test_entry_diagnostics_unregistered_source(
    hass: HomeAssistant, hass_client: ClientSessionGenerator
) -> None:
    """Diagnostics cope with a source that has no registry entry or state."""
    assert await async_setup_component(hass, "diagnostics", {})
    entry = MockConfigEntry(
        domain=DOMAIN,
        options={"entity_id": "device_tracker.ghost", "device_class": "connectivity"},
        title="Ghost",
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    diagnostics = await get_diagnostics_for_config_entry(hass, hass_client, entry)

    assert diagnostics["source"] == {
        "entity_id": "device_tracker.ghost",
        "registry_entry": None,
        "state": None,
    }
    assert diagnostics["binary_sensor"]["state"]["state"] == "unavailable"
