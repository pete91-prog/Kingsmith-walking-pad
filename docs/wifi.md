# Wi-Fi on KingSmith WalkingPads

Dual-radio WalkingPads join your 2.4 GHz network so the KS Fit app can reach
KingSmith cloud. They do **not** expose a documented local HTTP, MQTT, or Tuya
LAN API for starting the belt or reading telemetry.

## What this project does instead

Bluetooth is the last mile to the motor controller. A host next to the pad
(Home Assistant, a Raspberry Pi, a NUC) keeps that BLE link and then offers
**your** LAN:

- HTTP API + control page (`walkingpad serve`)
- MQTT with Home Assistant discovery (`walkingpad mqtt`)
- Native Home Assistant custom component (BLE from HA or an ESPHome Bluetooth proxy)

From the rest of the house that looks like Wi-Fi. No packets go to KingSmith.

## Probe the pad's own IP anyway

If you already know the treadmill's DHCP address:

```bash
walkingpad wifi-probe 192.168.1.50
```

Open ports are reported, but an open port is not a local control API. Prefer
the BLE + bridge path.

## ESPHome Bluetooth proxy

If Home Assistant is out of BLE range, put an ESP32 in the same room:

```yaml
bluetooth_proxy:
  active: true
```

Active connections are required. A passive proxy is not enough.
