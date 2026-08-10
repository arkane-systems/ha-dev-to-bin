# ![icon](assets/ha-dev-to-bin-32px.png) ha-dev-to-bin

A Home Assistant helper integration that exposes a device tracker entity as a binary
sensor. The binary sensor is **on** (true) when the tracker reports `home`, and **off**
(false) for any other state (e.g. `not_home` or a named zone). The original device
tracker is hidden while the helper is active and restored when the helper is removed.

This is useful when you have a network integration which presents device online presence
as device trackers, while what you really want to have are connectivity sensors.

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

## Options

After creation you can change the **device class** at any time via the integration's
*Configure* button in **Settings → Devices & Services**.
