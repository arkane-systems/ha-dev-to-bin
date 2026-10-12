"""Shared test helpers."""

from __future__ import annotations

from homeassistant.core import HomeAssistant, State


def get_state(hass: HomeAssistant, entity_id: str) -> State:
    """Return an entity's state, failing the test if it has none."""
    state = hass.states.get(entity_id)
    assert state is not None
    return state
