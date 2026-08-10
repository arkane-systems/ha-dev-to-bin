# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Home Assistant custom integration (installable via HACS or manual copy into
`custom_components/`) that wraps a `device_tracker` entity as a `binary_sensor`. It is
registered as a "helper" integration (`integration_type: helper` in manifest.json), so
users create instances via **Settings → Devices & Services → Helpers**, not through
the normal integration discovery/setup flow.

There is no build system, package manifest, or linter config in this repo — it's pure
Python source consumed directly by a Home Assistant instance. There is a lightweight
smoke-test suite (see below); beyond that, changes are validated by installing the
component into a running Home Assistant and exercising it there, or by reasoning about
the Home Assistant core APIs being called.

## Testing

```sh
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements_test.txt
pytest
```

`tests/test_smoke.py` uses `pytest-homeassistant-custom-component` to spin up a real
(in-memory) Home Assistant instance and covers the two things most likely to silently
break on a core upgrade: the tracker-state-to-binary-sensor mapping in
`binary_sensor.py` (home/away/zone/unavailable, and live state-change tracking), and the
config-flow side effects in `__init__.py`/`config_flow.py` (hiding the wrapped tracker
on creation, unhiding it on removal). This is intentionally a smoke suite, not full
coverage — it exists because those two behaviors are non-obvious and easy to regress,
not as a general testing mandate for this small, feature-frozen integration.

## Behavior

- The binary sensor mirrors the wrapped device tracker: **on** when the tracker state is
  `home`, **off** for any other state (e.g. `not_home` or a zone name), and unavailable
  when the tracker is `unavailable`/`unknown`.
- The device class of the binary sensor is user-configurable (defaults to
  `connectivity`) and can be changed later via the entry's *Configure* (options) flow.
- On creation, the wrapped device tracker entity is hidden (`hidden_by =
  RegistryEntryHider.INTEGRATION`); on removal of the helper, it is unhidden.
- The binary sensor's custom name is copied from the wrapped entity on first creation
  only (`_is_new_entity` check in `binary_sensor.py`), so subsequent renames of the
  source entity don't propagate.

## Architecture (`custom_components/device_tracker_to_binary/`)

- **`__init__.py`** — config entry setup/unload/removal. Uses
  `homeassistant.helpers.helper_integration.async_handle_source_entity_changes` to keep
  the helper in sync with its source entity: if the source entity's ID changes, the
  config entry options are updated and the entry is reloaded; if the source entity is
  removed entirely, the config entry itself is removed. `async_remove_entry` handles
  unhiding the wrapped tracker entity when the helper is deleted.
- **`config_flow.py`** — uses Home Assistant's generic `SchemaConfigFlowHandler` /
  `SchemaFlowFormStep` machinery (not a hand-rolled `ConfigFlow` subclass) for both the
  initial config flow and the options flow. `options_flow_reloads = True` means changing
  the device class reloads the entry automatically. The entry title is derived via
  `wrapped_entity_config_entry_title`, and the source entity is hidden as a side effect
  of `async_config_entry_title`.
- **`binary_sensor.py`** — the single platform. `DeviceTrackerBinarySensor` tracks the
  source entity via `async_track_state_change_event` and pushes state with
  `async_write_ha_state`. It also copies device/entity-category/name metadata from the
  wrapped tracker's registry entry at construction time.
- **`const.py`** — `DOMAIN`, the `device_class` option key, and its default
  (`connectivity`).
- **`strings.json`** / **`translations/en.json`** — must be kept in sync manually; the
  translations file is a copy of `strings.json` with `[%key:...%]` references resolved
  to literal text (see the `device_class` options step, which references the `config`
  step's string in `strings.json`).

## Versioning

`manifest.json` has both `version` (semantic version, bump on release) and
`config_flow.VERSION` / `MINOR_VERSION` (config entry schema version, only bump on
breaking changes to the stored options schema) — these serve different purposes and
should not be confused.
