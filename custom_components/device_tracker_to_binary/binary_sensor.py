"""Binary sensor platform for Device Tracker as Binary Sensor."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.components.device_tracker import DOMAIN as DEVICE_TRACKER_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_ENTITY_ID,
    STATE_HOME,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import CONF_DEVICE_CLASS, DEFAULT_DEVICE_CLASS, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the binary sensor platform from a config entry."""
    registry = er.async_get(hass)
    entity_id = er.async_validate_entity_id(
        registry, config_entry.options[CONF_ENTITY_ID]
    )
    device_class_value = config_entry.options.get(CONF_DEVICE_CLASS, DEFAULT_DEVICE_CLASS)

    async_add_entities(
        [
            DeviceTrackerBinarySensor(
                hass=hass,
                config_entry_title=config_entry.title,
                tracker_entity_id=entity_id,
                device_class_value=device_class_value,
                unique_id=config_entry.entry_id,
            )
        ]
    )


class DeviceTrackerBinarySensor(BinarySensorEntity):
    """A binary sensor that wraps a device tracker entity.

    Maps the device tracker's 'home' state to True (on) and any other state
    (typically 'not_home' or a zone name) to False (off).
    """

    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_title: str,
        tracker_entity_id: str,
        device_class_value: str,
        unique_id: str,
    ) -> None:
        """Initialize the binary sensor."""
        self.hass = hass

        registry = er.async_get(hass)
        device_registry = dr.async_get(hass)

        tracker_entry = registry.async_get(tracker_entity_id)
        device_id = tracker_entry.device_id if tracker_entry else None
        entity_category = tracker_entry.entity_category if tracker_entry else None
        has_entity_name = tracker_entry.has_entity_name if tracker_entry else False

        name: str | None = config_entry_title
        if tracker_entry and tracker_entry.original_name:
            name = tracker_entry.original_name

        if device_id and (device := device_registry.async_get(device_id)):
            self.device_entry = device

        self._attr_entity_category = entity_category
        self._attr_has_entity_name = has_entity_name
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._tracker_entity_id = tracker_entity_id

        # Set device class from the configured value.
        try:
            self._attr_device_class = BinarySensorDeviceClass(device_class_value)
        except ValueError:
            self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

        # Track whether this is a newly created entity so we can copy settings.
        self._is_new_entity = (
            registry.async_get_entity_id(
                "binary_sensor", DOMAIN, unique_id
            )
            is None
        )

    @callback
    def _handle_tracker_state_change(
        self, event: Event[EventStateChangedData] | None = None
    ) -> None:
        """Respond to device tracker state changes."""
        state = self.hass.states.get(self._tracker_entity_id)

        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            self._attr_available = False
            self._attr_is_on = None
        else:
            self._attr_available = True
            self._attr_is_on = state.state == STATE_HOME

        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Register state-change listener and initialise state."""
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self._tracker_entity_id],
                self._handle_tracker_state_change,
            )
        )

        # Initialise state immediately.
        self._handle_tracker_state_change()

        # Copy the custom name from the wrapped entity if this is a new entity.
        if not self._is_new_entity:
            return

        registry = er.async_get(self.hass)
        if not (tracker_entry := registry.async_get(self._tracker_entity_id)):
            return

        if tracker_entry.name is not None:
            registry.async_update_entity(self.entity_id, name=tracker_entry.name)
