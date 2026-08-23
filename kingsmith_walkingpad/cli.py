"""Command-line interface for local WalkingPad control."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging

from .ble.scanner import scan_pads
from .demo import demo_pad
from .models import Mode, ProtocolType
from .pad import WalkingPad
from .wifi import probe_host


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="walkingpad",
        description="Offline KingSmith WalkingPad control (Bluetooth + local LAN bridge).",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("scan", help="Discover nearby WalkingPads over BLE")

    p_status = sub.add_parser("status", help="Connect and print one status snapshot")
    p_status.add_argument("--address", required=True)

    p_start = sub.add_parser("start", help="Start the belt")
    p_start.add_argument("--address", required=True)
    p_start.add_argument("--speed", type=float, default=2.0)

    p_stop = sub.add_parser("stop", help="Stop the belt")
    p_stop.add_argument("--address", required=True)

    p_speed = sub.add_parser("speed", help="Set speed in km/h")
    p_speed.add_argument("--address", required=True)
    p_speed.add_argument("kmh", type=float)

    p_mode = sub.add_parser("mode", help="Set auto / manual / standby")
    p_mode.add_argument("--address", required=True)
    p_mode.add_argument("mode", choices=[m.value for m in Mode if m is not Mode.UNKNOWN])

    p_serve = sub.add_parser("serve", help="Local HTTP API + control page")
    p_serve.add_argument("--address")
    p_serve.add_argument("--host", default="0.0.0.0")
    p_serve.add_argument("--port", type=int, default=8080)
    p_serve.add_argument("--demo", action="store_true", help="Run against an in-process simulator")
    p_serve.add_argument("--protocol", choices=["wilink", "ftms"], default="wilink")
    p_serve.add_argument("--weight-kg", type=float, default=75.0)

    p_mqtt = sub.add_parser("mqtt", help="Local MQTT bridge with Home Assistant discovery")
    p_mqtt.add_argument("--address")
    p_mqtt.add_argument("--broker", required=True)
    p_mqtt.add_argument("--port", type=int, default=1883)
    p_mqtt.add_argument("--username")
    p_mqtt.add_argument("--password")
    p_mqtt.add_argument("--demo", action="store_true")
    p_mqtt.add_argument("--protocol", choices=["wilink", "ftms"], default="wilink")
    p_mqtt.add_argument("--weight-kg", type=float, default=75.0)

    p_wifi = sub.add_parser("wifi-probe", help="See if the pad's Wi-Fi IP exposes a local API")
    p_wifi.add_argument("host")

    return parser


def _pad_from_args(args: argparse.Namespace) -> WalkingPad:
    if getattr(args, "demo", False):
        proto = ProtocolType.FTMS if getattr(args, "protocol", "wilink") == "ftms" else ProtocolType.WILINK
        return demo_pad(proto)
    if not getattr(args, "address", None):
        raise SystemExit("Pass --address or --demo")
    return WalkingPad(args.address, weight_kg=getattr(args, "weight_kg", 75.0))


async def _run(args: argparse.Namespace) -> int:
    if args.cmd == "scan":
        pads = await scan_pads()
        if not pads:
            print("No WalkingPads found. Power the belt on and quit KS Fit.")
            return 1
        for pad in pads:
            print(f"{pad.address}\t{pad.name or 'unknown'}\trssi={pad.rssi}\t{','.join(pad.service_uuids)}")
        return 0

    if args.cmd == "wifi-probe":
        result = await probe_host(args.host)
        print(json.dumps({"host": result.host, "open_ports": result.open_ports, "notes": result.notes}, indent=2))
        return 0

    if args.cmd == "serve":
        from .server.http_api import serve_http

        pad = _pad_from_args(args)
        await serve_http(pad, host=args.host, port=args.port)
        return 0

    if args.cmd == "mqtt":
        from .server.mqtt_bridge import MqttBridge

        pad = _pad_from_args(args)
        bridge = MqttBridge(
            pad,
            args.broker,
            port=args.port,
            username=args.username,
            password=args.password,
        )
        await bridge.run()
        return 0

    pad = WalkingPad(args.address)
    async with pad:
        if args.cmd == "status":
            await asyncio.sleep(1.2)
            print(json.dumps(pad.status.to_dict(), indent=2))
        elif args.cmd == "start":
            await pad.start(args.speed)
            await asyncio.sleep(1.0)
            print(json.dumps(pad.status.to_dict(), indent=2))
        elif args.cmd == "stop":
            await pad.stop()
            print(json.dumps(pad.status.to_dict(), indent=2))
        elif args.cmd == "speed":
            await pad.set_speed(args.kmh)
            print(json.dumps(pad.status.to_dict(), indent=2))
        elif args.cmd == "mode":
            await pad.set_mode(Mode(args.mode))
            print(json.dumps(pad.status.to_dict(), indent=2))
    return 0


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        raise SystemExit(asyncio.run(_run(args)))
    except KeyboardInterrupt:
        raise SystemExit(0)


if __name__ == "__main__":
    main()
