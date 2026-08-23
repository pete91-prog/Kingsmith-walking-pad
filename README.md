# KingSmith WalkingPad — offline

Local control for KingSmith / WalkingPad treadmills. No KS Fit account, no
KingSmith cloud, and no phone app after the first Bluetooth pairing window.

The treadmill still speaks **Bluetooth** for start/stop/speed/telemetry. Dual-radio
models also have **Wi-Fi**, but that radio is cloud-bound. This project keeps the
BLE link on a nearby host and then exposes **your** LAN (HTTP, MQTT, Home
Assistant) so the rest of the house can use Wi-Fi.

```
phone / HA / automations
        │  HTTP or MQTT on your LAN
        ▼
  this project (Pi, NUC, Home Assistant)
        │  Bluetooth LE
        ▼
     WalkingPad
```

## What you get

- Auto-detect of classic **WiLink** (`0xFE00`) and modern **FTMS** (`0x1826`)
- KingSmith **supplement unlock** (Z1 / `KS-HD-*`) and **MC-21 ODM** pre-amble
- CLI: scan, start, stop, speed, mode
- Local HTTP API and control page
- MQTT bridge with Home Assistant discovery
- Home Assistant custom integration (HACS-compatible)
- `--demo` mode so you can try the UI without hardware

Remote start can move the belt. Keep people and pets clear.

## Install

```bash
python3 -m pip install -e .
```

Needs Python 3.11+, a Bluetooth adapter (or an ESPHome Bluetooth proxy when used
from Home Assistant), and the KS Fit app **disconnected**.

```bash
walkingpad scan
walkingpad status --address AA:BB:CC:DD:EE:FF
walkingpad start --address AA:BB:CC:DD:EE:FF --speed 2.0
walkingpad speed --address AA:BB:CC:DD:EE:FF 2.5
walkingpad stop --address AA:BB:CC:DD:EE:FF
```

### Local web UI (offline Wi-Fi for the house)

```bash
walkingpad serve --address AA:BB:CC:DD:EE:FF --host 0.0.0.0 --port 8080
```

Open `http://<host>:8080`. From another room this is ordinary Wi-Fi; the host
holds the BLE session.

Try it without a treadmill:

```bash
walkingpad serve --demo
```

### MQTT

```bash
walkingpad mqtt --address AA:BB:CC:DD:EE:FF --broker 192.168.1.10
```

Topics (device id is the MAC without colons):

| Topic | Direction |
| --- | --- |
| `walkingpad/<id>/status` | JSON telemetry |
| `walkingpad/<id>/set/command` | `start` / `stop` / `pause` |
| `walkingpad/<id>/set/speed` | km/h |
| `walkingpad/<id>/set/mode` | `auto` / `manual` / `standby` |

Home Assistant MQTT discovery is published automatically.

### The pad's own Wi-Fi

```bash
walkingpad wifi-probe 192.168.1.50
```

See [docs/wifi.md](docs/wifi.md). Expected result: no local control API.

## Home Assistant (HACS)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=pete91-prog&repository=Kingsmith-walking-pad&category=integration)

### Install from HACS

1. Install [HACS](https://www.hacs.xyz/) if you do not have it yet.
2. Open **HACS → Integrations**.
3. Menu (⋮) → **Custom repositories**.
4. Add `https://github.com/pete91-prog/Kingsmith-walking-pad` as type **Integration**.
5. Search for **KingSmith WalkingPad (Offline)** and download it.
6. Restart Home Assistant.
7. **Settings → Devices & services → Add integration → KingSmith WalkingPad (Offline)**.

The My Home Assistant badge above jumps straight to step 4 on a machine that
already has HACS.

### Manual install

Copy `custom_components/kingsmith_walkingpad` into `<config>/custom_components/`
and restart, then add the integration from the UI.

Requirements:

- Home Assistant 2024.1 or newer
- A Bluetooth adapter **or** an ESPHome Bluetooth proxy with `active: true`
- KS Fit not connected

Entities: belt switch, speed, mode, stop button, distance, steps, calories,
elapsed time, current speed, belt state, protocol.

Turn off **Allow remote start / speed** in the integration options if you only
want telemetry.

## Docker

```bash
docker compose up --build
```

The image defaults to `--demo`. On a host with Bluetooth, override the command
with `--address` and keep `network_mode: host` plus the D-Bus mount.

## Supported families

| Family | Transport |
| --- | --- |
| WalkingPad A1 / A1 Pro / C1 / C2 / R1 / R2 and other `0xFE00` units | WiLink |
| `KS-HD-*` (Z1 and similar) | FTMS after supplement unlock |
| `KS-MC21-*`, `KS-SMC21C-*`, `ZP-ZEALR1-*` | FTMS after ODM pre-amble |

Wire format: [docs/protocol.md](docs/protocol.md).

## Safety

- Only one BLE client can be connected.
- Do not start the belt unless someone is ready to step on or clear it.
- Physical stop on the pad / remote still wins. Use it.

KingSmith, WalkingPad, and KS Fit are trademarks of their owners. This project
is not affiliated with KingSmith.
