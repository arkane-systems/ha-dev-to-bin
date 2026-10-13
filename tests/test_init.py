"""Tests for config entry setup, unload and removal."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.device_tracker_to_binary.const import DOMAIN


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
