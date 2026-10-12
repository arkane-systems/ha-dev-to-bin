# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Home Assistant custom integration (installable via HACS or manual copy into
`custom_components/`) that wraps a `device_tracker` entity as a `binary_sensor`. It is
registered as a "helper" integration (`integration_type: helper` in manifest.json), so
users create instances via **Settings → Devices & Services → Helpers**, not through
the normal integration discovery/setup flow.

There is no build system or package manifest in this repo — it's pure Python source
consumed directly by a Home Assistant instance. It is held to the Home Assistant
[integration quality scale](https://developers.home-assistant.io/docs/core/integration-quality-scale/rules)
at Platinum tier as a self-imposed yardstick (HA doesn't grade custom integrations).
Per-rule status and exemption rationale live in
`custom_components/device_tracker_to_binary/quality_scale.yaml`; keep it current when
behavior changes. Beyond the test suite and type check (see below), changes are
validated by installing the component into a running Home Assistant.

## Testing

```sh
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements_test.txt
pytest --cov=custom_components.device_tracker_to_binary --cov-report=term-missing --cov-fail-under=95
mypy
```

Tests use `pytest-homeassistant-custom-component` to spin up a real (in-memory) Home
Assistant instance. CI enforces ≥95% coverage (currently 100%) and `mypy` in strict
mode over both `custom_components/` and `tests/` (config in `mypy.ini`, mirroring
core's strict settings). Use `tests/common.py:get_state` rather than dereferencing
`hass.states.get(...)` directly so tests stay type-clean. Test files are split by
module: `test_config_flow.py` (user/options/reconfigure flows), `test_init.py`
(setup/unload/removal, source rename/removal, repair issue), `test_binary_sensor.py`
(state mapping and metadata copying), `test_diagnostics.py`; `test_smoke.py` is the
original smoke suite.

## Behavior

- The binary sensor mirrors the wrapped device tracker: **on** when the tracker state is
  `home`, **off** for any other state (e.g. `not_home` or a zone name), and unavailable
  when the tracker is `unavailable`/`unknown`.
- The device class of the binary sensor is user-configurable (defaults to
  `connectivity`) and can be changed later via the entry's *Configure* (options) flow.
- On creation, the wrapped device tracker entity is hidden (`hidden_by =
  RegistryEntryHider.INTEGRATION`); on removal of the helper, it is unhidden (only if
  this integration hid it). A tracker can be wrapped by only one helper.
- The wrapped tracker can be swapped via the *Reconfigure* flow, which unhides the old
  tracker and hides the new one.
- The sensor mirrors the tracker's `has_entity_name`/name (like core's `switch_as_x`);
  this is a deliberate `has-entity-name` exemption, not an oversight.
- The binary sensor's custom name is copied from the wrapped entity on first creation
  only (`_is_new_entity` check in `binary_sensor.py`), so subsequent renames of the
  source entity don't propagate.

## Architecture (`custom_components/device_tracker_to_binary/`)

- **`__init__.py`** — config entry setup/unload/removal. Uses
  `homeassistant.helpers.helper_integration.async_handle_source_entity_changes` to keep
  the helper in sync with its source entity: if the source entity's ID changes, the
  config entry options are updated and the entry is reloaded; if the source entity is
  removed entirely, the config entry itself is removed. If the stored source can't be
  resolved at setup, it raises a translated `ConfigEntryError` and creates a
  `source_entity_missing` repair issue (cleared on successful setup or removal).
  `async_remove_entry` unhides the wrapped tracker entity when the helper is deleted.
- **`config_flow.py`** — uses Home Assistant's generic `SchemaConfigFlowHandler` /
  `SchemaFlowFormStep` machinery (not a hand-rolled `ConfigFlow` subclass) for both the
  initial config flow and the options flow. `options_flow_reloads = True` means changing
  the device class reloads the entry automatically. The entry title is derived via
  `wrapped_entity_config_entry_title`, and the source entity is hidden as a side effect
  of `async_config_entry_title`. The user step's `validate_user_input` aborts with
  `already_configured` for a tracker that's already wrapped. `async_step_reconfigure`
  is hand-written (the schema-flow machinery only generates steps listed in
  `CONFIG_FLOW`, and would create a new entry rather than update one).
- **`helpers.py`** — `async_hide_source` / `async_unhide_source`, shared by the config
  flow, reconfigure step and `async_remove_entry`.
- **`diagnostics.py`** — config entry diagnostics; redacts GPS and network-identity
  attributes from tracker state.
- **`binary_sensor.py`** — the single platform. `DeviceTrackerBinarySensor` tracks the
  source entity via `async_track_state_change_event` and pushes state with
  `async_write_ha_state`. It also copies device/entity-category/name metadata from the
  wrapped tracker's registry entry at construction time.
- **`const.py`** — `DOMAIN`, the `device_class` option key, and its default
  (`connectivity`).
- **`strings.json`** / **`translations/en.json`** — must be kept in sync manually; the
  translations file is a copy of `strings.json` with `[%key:...%]` references resolved
  to literal text (e.g. the options and reconfigure steps reference the `user` step's
  strings, and `reconfigure_successful` references the common string). HA strips a
  trailing period from exception messages, so `exceptions` strings omit it.

## Versioning

`manifest.json` has both `version` (semantic version, bump on release) and
`config_flow.VERSION` / `MINOR_VERSION` (config entry schema version, only bump on
breaking changes to the stored options schema) — these serve different purposes and
should not be confused.
