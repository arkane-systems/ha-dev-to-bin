"""Smoke tests covering the config flow and tracker-to-binary-sensor mapping."""

from __future__ import annotations

from homeassistant.const import STATE_HOME, STATE_NOT_HOME, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.device_tracker_to_binary.const import DOMAIN

TRACKER_ENTITY_ID = "device_tracker.test"


async def _setup_entry(hass: HomeAssistant, tracker_state: str) -> str:
    """Set the tracker to a state and set up the helper, returning the sensor entity_id."""
    hass.states.async_set(TRACKER_ENTITY_ID, tracker_state)

    entry = MockConfigEntry(
        domain=DOMAIN,
        options={"entity_id": TRACKER_ENTITY_ID, "device_class": "connectivity"},
        title="Test",
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id("binary_sensor", DOMAIN, entry.entry_id)
    assert entity_id is not None
    return entity_id


async def test_binary_sensor_on_when_tracker_home(hass: HomeAssistant) -> None:
    """The binary sensor is on when the tracker reports home."""
    entity_id = await _setup_entry(hass, STATE_HOME)
    assert hass.states.get(entity_id).state == "on"


async def test_binary_sensor_off_when_tracker_away(hass: HomeAssistant) -> None:
    """The binary sensor is off when the tracker reports not_home."""
    entity_id = await _setup_entry(hass, STATE_NOT_HOME)
    assert hass.states.get(entity_id).state == "off"


async def test_binary_sensor_off_when_tracker_in_named_zone(
    hass: HomeAssistant,
) -> None:
    """The binary sensor is off when the tracker reports a named zone."""
    entity_id = await _setup_entry(hass, "work")
    assert hass.states.get(entity_id).state == "off"


async def test_binary_sensor_unavailable_when_tracker_unavailable(
    hass: HomeAssistant,
) -> None:
    """The binary sensor becomes unavailable when the tracker is unavailable."""
    entity_id = await _setup_entry(hass, STATE_UNAVAILABLE)
    assert hass.states.get(entity_id).state == STATE_UNAVAILABLE


async def test_binary_sensor_tracks_state_changes(hass: HomeAssistant) -> None:
    """The binary sensor updates live as the tracker's state changes."""
    entity_id = await _setup_entry(hass, STATE_HOME)
    assert hass.states.get(entity_id).state == "on"

    hass.states.async_set(TRACKER_ENTITY_ID, STATE_NOT_HOME)
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "off"


async def test_config_flow_creates_entry_and_hides_source(
    hass: HomeAssistant,
) -> None:
    """The user config flow creates an entry and hides the wrapped tracker."""
    registry = er.async_get(hass)
    tracker_entry = registry.async_get_or_create(
        "device_tracker", "test", "unique123", suggested_object_id="test"
    )
    hass.states.async_set(tracker_entry.entity_id, STATE_HOME)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"entity_id": tracker_entry.entity_id, "device_class": "presence"},
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].options["device_class"] == "presence"

    updated_tracker_entry = registry.async_get(tracker_entry.entity_id)
    assert updated_tracker_entry.hidden_by == er.RegistryEntryHider.INTEGRATION


async def test_remove_entry_unhides_source(hass: HomeAssistant) -> None:
    """Removing the helper entry unhides the wrapped tracker entity."""
    registry = er.async_get(hass)
    tracker_entry = registry.async_get_or_create(
        "device_tracker", "test", "unique456", suggested_object_id="test2"
    )
    registry.async_update_entity(
        tracker_entry.entity_id, hidden_by=er.RegistryEntryHider.INTEGRATION
    )
    hass.states.async_set(tracker_entry.entity_id, STATE_HOME)

    entry = MockConfigEntry(
        domain=DOMAIN,
        options={"entity_id": tracker_entry.entity_id, "device_class": "connectivity"},
        title="Test",
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()

    updated_tracker_entry = registry.async_get(tracker_entry.entity_id)
    assert updated_tracker_entry.hidden_by is None
