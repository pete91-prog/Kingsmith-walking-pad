# KingSmith WalkingPad (Offline)

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=pete91-prog&repository=Kingsmith-walking-pad&category=integration)
[![Validate](https://github.com/pete91-prog/Kingsmith-walking-pad/actions/workflows/validate.yml/badge.svg)](https://github.com/pete91-prog/Kingsmith-walking-pad/actions/workflows/validate.yml)

Home Assistant custom integration for KingSmith / WalkingPad treadmills.
Local Bluetooth only — no KS Fit account and no KingSmith cloud.

The pad’s own Wi-Fi radio is cloud-bound. This integration holds the BLE
session (from Home Assistant or an ESPHome Bluetooth proxy) so the rest of
the house can automate over your LAN.

Remote start can move the belt. Keep people and pets clear. Force-quit KS Fit
first — the treadmill accepts only one BLE client.

## Install with HACS

1. Install [HACS](https://www.hacs.xyz/) if you do not already have it.
2. Click the My badge above, **or**:
   - Open **HACS**
   - Top-right **⋮ → Custom repositories**
   - Repository: `https://github.com/pete91-prog/Kingsmith-walking-pad`
   - Type: **Integration**
   - **Add**
3. Search for **KingSmith WalkingPad (Offline)** and **Download**.
4. Restart Home Assistant.
5. [Add the integration](https://my.home-assistant.io/redirect/config_flow_start/?domain=kingsmith_walkingpad)
   (**Settings → Devices & services → Add integration → KingSmith WalkingPad (Offline)**).

After download you should see a WalkingPad discovery notification if the belt
is on and in range.

### Manual install (without HACS)

Copy `custom_components/kingsmith_walkingpad` into
`<config>/custom_components/` and restart Home Assistant, then add the
integration from the UI.

## Requirements

- Home Assistant 2024.1 or newer
- [HACS](https://www.hacs.xyz/) (recommended)
- A Bluetooth adapter on the HA host, **or** an ESPHome Bluetooth proxy with `active: true`
- KS Fit disconnected

## Entities

| Entity | Purpose |
| --- | --- |
| Switch **Belt** | Start / stop |
| Number **Speed** | km/h |
| Select **Mode** | auto / manual / standby |
| Button **Stop** | Immediate stop |
| Sensors | distance, steps, calories, elapsed time, current speed, belt state, protocol |

Turn off **Allow remote start / speed** in the integration options if you only
want telemetry.

## Supported families

| Family | Transport |
| --- | --- |
| WalkingPad A1 / A1 Pro / C1 / C2 / R1 / R2 and other `0xFE00` units | WiLink |
| `KS-HD-*` (Z1 and similar) | FTMS after supplement unlock |
| `KS-MC21-*`, `KS-SMC21C-*`, `ZP-ZEALR1-*` | FTMS after ODM pre-amble |

## ESPHome Bluetooth proxy

```yaml
bluetooth_proxy:
  active: true
```

A passive proxy is not enough. The proxy needs to be in the same room as the pad.

## Optional: CLI / MQTT on a Pi

The same repository also ships a standalone Python package if you want a
local HTTP page or MQTT bridge instead of (or in addition to) the Home
Assistant integration.

```bash
python3 -m pip install -e .
walkingpad scan
walkingpad serve --address AA:BB:CC:DD:EE:FF
walkingpad mqtt --address AA:BB:CC:DD:EE:FF --broker 192.168.1.10
```

`walkingpad serve --demo` runs the UI without hardware.

See [docs/wifi.md](docs/wifi.md) and [docs/protocol.md](docs/protocol.md).

## Safety

- Only one BLE client can be connected.
- Do not start the belt unless someone is ready to step on or clear it.
- The physical stop on the pad / remote still wins.

KingSmith, WalkingPad, and KS Fit are trademarks of their owners. This project
is not affiliated with KingSmith.
