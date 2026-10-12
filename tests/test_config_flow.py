"""Tests for the config and options flows."""

from __future__ import annotations

from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    STATE_HOME,
    STATE_NOT_HOME,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.device_tracker_to_binary.const import DOMAIN

from .common import get_state


async def test_user_flow_unregistered_tracker(hass: HomeAssistant) -> None:
    """A tracker with no registry entry is accepted and titled from its state."""
    hass.states.async_set(
        "device_tracker.legacy", STATE_HOME, {"friendly_name": "Legacy phone"}
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"entity_id": "device_tracker.legacy"}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Legacy phone"
    assert result["options"] == {
        "entity_id": "device_tracker.legacy",
        "device_class": "connectivity",
    }


async def test_user_flow_aborts_on_duplicate_tracker(hass: HomeAssistant) -> None:
    """The same tracker cannot be wrapped by two helpers."""
    hass.states.async_set("device_tracker.test", STATE_HOME)
    MockConfigEntry(
        domain=DOMAIN,
        options={"entity_id": "device_tracker.test", "device_class": "connectivity"},
        title="Test",
    ).add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"entity_id": "device_tracker.test"}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_user_flow_keeps_user_hidden_tracker(hass: HomeAssistant) -> None:
    """A tracker the user already hid is not re-marked as hidden by the integration."""
    registry = er.async_get(hass)
    tracker_entry = registry.async_get_or_create(
        "device_tracker", "test", "unique789", suggested_object_id="hidden"
    )
    registry.async_update_entity(
        tracker_entry.entity_id, hidden_by=er.RegistryEntryHider.USER
    )
    hass.states.async_set(tracker_entry.entity_id, STATE_HOME)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"entity_id": tracker_entry.entity_id}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    entry = registry.async_get(tracker_entry.entity_id)
    assert entry is not None
    assert entry.hidden_by == er.RegistryEntryHider.USER


async def test_options_flow_changes_device_class(hass: HomeAssistant) -> None:
    """Changing the device class in the options flow reloads the binary sensor."""
    hass.states.async_set("device_tracker.test", STATE_HOME)
    entry = MockConfigEntry(
        domain=DOMAIN,
        options={"entity_id": "device_tracker.test", "device_class": "connectivity"},
        title="Test",
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    sensor_id = registry.async_get_entity_id("binary_sensor", DOMAIN, entry.entry_id)
    assert sensor_id is not None
    assert get_state(hass, sensor_id).attributes[ATTR_DEVICE_CLASS] == "connectivity"

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"device_class": "presence"}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {
        "entity_id": "device_tracker.test",
        "device_class": "presence",
    }
    assert get_state(hass, sensor_id).attributes[ATTR_DEVICE_CLASS] == "presence"


async def _setup_wrapping(
    hass: HomeAssistant, registry: er.EntityRegistry, unique_id: str, object_id: str
) -> tuple[MockConfigEntry, str]:
    """Create a hidden registered tracker and a loaded helper wrapping it."""
    tracker = registry.async_get_or_create(
        "device_tracker", "test", unique_id, suggested_object_id=object_id
    )
    registry.async_update_entity(
        tracker.entity_id, hidden_by=er.RegistryEntryHider.INTEGRATION
    )
    hass.states.async_set(tracker.entity_id, STATE_HOME)
    entry = MockConfigEntry(
        domain=DOMAIN,
        options={"entity_id": tracker.entity_id, "device_class": "connectivity"},
        title=object_id,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry, tracker.entity_id


async def test_reconfigure_switches_tracker(hass: HomeAssistant) -> None:
    """Reconfiguring swaps which tracker is hidden and wrapped."""
    registry = er.async_get(hass)
    entry, old_id = await _setup_wrapping(hass, registry, "old", "old_phone")
    new = registry.async_get_or_create(
        "device_tracker",
        "test",
        "new",
        suggested_object_id="new_phone",
        original_name="New",
    )
    hass.states.async_set(new.entity_id, STATE_NOT_HOME)
    sensor_id = registry.async_get_entity_id("binary_sensor", DOMAIN, entry.entry_id)
    assert sensor_id is not None
    assert get_state(hass, sensor_id).state == STATE_ON

    result = await entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"entity_id": new.entity_id}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.options == {"entity_id": new.entity_id, "device_class": "connectivity"}
    assert entry.title == "New"

    old_entry = registry.async_get(old_id)
    new_entry = registry.async_get(new.entity_id)
    assert old_entry is not None and old_entry.hidden_by is None
    assert new_entry is not None
    assert new_entry.hidden_by == er.RegistryEntryHider.INTEGRATION
    assert get_state(hass, sensor_id).state == STATE_OFF


async def test_reconfigure_same_tracker(hass: HomeAssistant) -> None:
    """Resubmitting the current tracker leaves it hidden."""
    registry = er.async_get(hass)
    entry, tracker_id = await _setup_wrapping(hass, registry, "same", "same_phone")

    result = await entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"entity_id": tracker_id}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    tracker = registry.async_get(tracker_id)
    assert tracker is not None
    assert tracker.hidden_by == er.RegistryEntryHider.INTEGRATION


async def test_reconfigure_aborts_on_tracker_wrapped_elsewhere(
    hass: HomeAssistant,
) -> None:
    """A tracker already wrapped by another helper cannot be chosen."""
    registry = er.async_get(hass)
    entry, first_id = await _setup_wrapping(hass, registry, "first", "first_phone")
    _, second_id = await _setup_wrapping(hass, registry, "second", "second_phone")

    result = await entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"entity_id": second_id}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.options["entity_id"] == first_id
    first = registry.async_get(first_id)
    assert first is not None
    assert first.hidden_by == er.RegistryEntryHider.INTEGRATION
