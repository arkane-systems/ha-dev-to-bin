# ![icon](assets/ha-dev-to-bin-32px.png) ha-dev-to-bin

A Home Assistant helper integration that exposes a device tracker entity as a binary
sensor. The binary sensor is **on** (true) when the tracker reports `home`, and **off**
(false) for any other state (e.g. `not_home` or a named zone). The original device
tracker is hidden while the helper is active and restored when the helper is removed.

This is useful when you have a network integration which presents device online presence
as device trackers, while what you really want to have are connectivity sensors.

## Use cases

- **Network device monitoring.** Router and network-scanner integrations (e.g. Nmap,
  UniFi, Fritz!Box, ping) report "is this device on the network?" as a device tracker.
  Wrapping one with the `connectivity` device class gives you a proper
  *Connected/Disconnected* sensor for servers, printers, cameras or IoT devices.
- **Simple presence.** Wrap a phone's tracker with the `presence` or `occupancy` device
  class to get a *Home/Away* sensor that fits naturally into binary-sensor based
  groups, alarm panels or dashboards.
- **Anywhere that takes a binary sensor.** Some cards, blueprints and integrations accept
  only `binary_sensor` entities; this helper lets a tracker be used there.

## Supported devices and functionality

Any entity in the `device_tracker` domain is supported, whether it comes from a GPS-based
integration (e.g. the companion app), a router or network scanner, or a legacy
`known_devices.yaml` tracker. There is no device-specific code.

Each helper provides exactly one entity: a **binary sensor** that

- is on when the tracker is `home` and off for every other state;
- is unavailable when the tracker is `unavailable` or `unknown` (or has no state);
- uses the device class you choose;
- joins the tracker's device (if it has one) and copies its name and entity category, so
  it sits where the tracker used to be.

The integration provides no service actions, triggers or conditions of its own; use the
standard state triggers and conditions on the binary sensor.

## How data is updated

The binary sensor is push-updated: it subscribes to the wrapped tracker's state changes
and updates immediately whenever the tracker changes. It never polls, makes no network
requests and adds no load beyond the source integration. How quickly a change shows up
therefore depends entirely on how often the source integration updates its tracker
(for example, a network scanner's scan interval or a router's "consider home" delay).

## Installation

### HACS (recommended)

Add this repository as a custom repository in HACS, then install *Device Tracker as
Binary Sensor*.

### Manual

Copy the `custom_components/device_tracker_to_binary` directory into the
`custom_components` directory of your Home Assistant configuration folder, then restart
Home Assistant.

## Setup

1. Go to **Settings → Devices & Services → Helpers → Create Helper**.
2. Choose **Device Tracker as Binary Sensor**.
3. Select the device tracker entity you want to wrap.
4. Optionally choose the binary sensor device class (defaults to **connectivity**).
5. Click **Submit**.

The helper creates a binary sensor whose state mirrors the presence of the tracked
device:

| Device tracker state | Binary sensor |
|----------------------|---------------|
| `home`               | on (true)     |
| `not_home` / zone    | off (false)   |
| unavailable / unknown | unavailable  |

## Configuration parameters

| Parameter | Required | Set during | Description |
|-----------|----------|------------|-------------|
| **Device tracker** | yes | setup | The `device_tracker` entity to wrap. Each tracker can be wrapped by only one helper. While the helper exists the tracker is hidden; the binary sensor joins the tracker's device (if it has one) and takes its name and entity category. |
| **Binary sensor device class** | no (default **connectivity**) | setup, *Configure* | The [binary sensor device class](https://www.home-assistant.io/integrations/binary_sensor/#device-class), which controls how the on/off states are labelled (e.g. *Connected/Disconnected*, *Home/Away* for `presence`) and the icon shown. |

## Options

After creation you can change the **device class** at any time via the integration's
*Configure* button in **Settings → Devices & Services**. Saving reloads the helper
immediately; no restart is needed.

## Reconfiguring

To wrap a different device tracker without deleting the helper (and so keep the binary
sensor's entity ID, name and any automations that use it), open the helper in
**Settings → Devices & Services → Helpers**, open the menu (⋮) and choose
**Reconfigure**. The previous tracker is un-hidden and the newly selected one is hidden.

If the wrapped tracker's entity ID is renamed, the helper follows it automatically. If
the wrapped tracker is deleted, the helper is deleted with it.

## Examples

Notify when a server drops off the network for five minutes:

```yaml
automation:
  - alias: "NAS offline"
    triggers:
      - trigger: state
        entity_id: binary_sensor.nas
        to: "off"
        for: "00:05:00"
    actions:
      - action: notify.notify
        data:
          message: "The NAS has been disconnected for 5 minutes."
```

Turn the hallway light on when someone arrives home (with the `presence` device class):

```yaml
automation:
  - alias: "Welcome home"
    triggers:
      - trigger: state
        entity_id: binary_sensor.alice_phone
        from: "off"
        to: "on"
    conditions:
      - condition: sun
        after: sunset
    actions:
      - action: light.turn_on
        target:
          entity_id: light.hallway
```

## Known limitations

- Only the `home` state counts as on. Being in any other zone (e.g. `work`) is off; the
  sensor cannot be configured to treat other zones as on.
- The binary sensor copies the tracker's custom name only when it is first created.
  Renaming the tracker later does not rename the binary sensor (rename it directly).
- Each device tracker can be wrapped by only one helper.
- The wrapped tracker is hidden, not disabled: it keeps updating and remains usable in
  automations, and you can un-hide it yourself if you want to see both.
- Tracker attributes (GPS coordinates, IP address, etc.) are not copied to the binary
  sensor.

## Troubleshooting

- **The binary sensor is unavailable.** The wrapped tracker is `unavailable` or
  `unknown`. Check the source integration; the helper only mirrors its state.
- **The helper shows "Failed to set up" and there is a repair issue.** The wrapped
  tracker no longer exists in the entity registry. Use **Reconfigure** to pick another
  tracker, or delete the helper.
- **"This device tracker is already wrapped" when creating a helper.** Another helper
  already wraps that tracker. Find it under **Settings → Devices & Services → Helpers**.
- **The sensor is slow to change.** The helper updates as soon as the tracker does; see
  [How data is updated](#how-data-is-updated) and check the source integration's update
  or "consider home" settings.
- **Reporting a problem.** Download diagnostics from the helper's menu (⋮ →
  *Download diagnostics*) and attach them to an
  [issue](https://github.com/arkane-systems/ha-dev-to-bin/issues). Location and network
  identifiers are redacted automatically.

## Removal

1. Go to **Settings → Devices & Services → Helpers**.
2. Select the *Device Tracker as Binary Sensor* helper you want to remove.
3. Open the menu (⋮) and choose **Delete**.

Removing the helper deletes its binary sensor and un-hides the original device tracker.
Any automations, scripts or dashboards that reference the binary sensor will need to be
updated to use the device tracker (or another entity) instead. No restart is required.
If you installed via HACS and no longer need the integration at all, you can then remove
it from HACS and restart Home Assistant.
