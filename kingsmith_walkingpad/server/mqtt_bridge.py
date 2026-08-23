"""Publish pad telemetry and accept commands on a local MQTT broker.

Home Assistant MQTT discovery is emitted so the pad appears as a local device
without the KingSmith cloud or the official app.
"""

from __future__ import annotations

import asyncio
import json
import logging
import ssl
from typing import Any

import paho.mqtt.client as mqtt

from ..models import Mode, PadStatus
from ..pad import WalkingPad

logger = logging.getLogger(__name__)


class MqttBridge:
    def __init__(
        self,
        pad: WalkingPad,
        host: str,
        port: int = 1883,
        *,
        username: str | None = None,
        password: str | None = None,
        topic_prefix: str = "walkingpad",
        discovery_prefix: str = "homeassistant",
        client_id: str = "kingsmith-walkingpad",
        tls: bool = False,
    ) -> None:
        self.pad = pad
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.topic_prefix = topic_prefix.rstrip("/")
        self.discovery_prefix = discovery_prefix.rstrip("/")
        self.tls = tls
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
        if username:
            self._client.username_pw_set(username, password)
        if tls:
            self._client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._loop: asyncio.AbstractEventLoop | None = None
        self._device_id = "walkingpad"

    def _base(self) -> str:
        return f"{self.topic_prefix}/{self._device_id}"

    def _on_connect(
        self,
        client: mqtt.Client,
        _userdata: Any,
        _flags: Any,
        reason_code: Any,
        _properties: Any = None,
    ) -> None:
        logger.info("MQTT connected: %s", reason_code)
        client.subscribe(f"{self._base()}/set/#")
        self._publish_discovery()
        self._publish_status(self.pad.status)

    def _on_message(self, _client: mqtt.Client, _userdata: Any, message: mqtt.MQTTMessage) -> None:
        if self._loop is None:
            return
        payload = message.payload.decode("utf-8", errors="replace").strip()
        asyncio.run_coroutine_threadsafe(self._handle(message.topic, payload), self._loop)

    async def _handle(self, topic: str, payload: str) -> None:
        key = topic.rsplit("/", 1)[-1]
        try:
            if key == "command":
                cmd = payload.lower()
                if cmd == "start":
                    await self.pad.start()
                elif cmd == "stop":
                    await self.pad.stop()
                elif cmd == "pause":
                    await self.pad.pause()
            elif key == "speed":
                await self.pad.set_speed(float(payload))
            elif key == "mode":
                await self.pad.set_mode(Mode(payload.lower()))
            elif key == "child_lock":
                await self.pad.set_child_lock(payload.lower() in {"1", "true", "on", "lock"})
        except Exception:
            logger.exception("MQTT command %s=%s failed", topic, payload)

    def _publish(self, topic: str, payload: str | dict[str, Any], retain: bool = False) -> None:
        body = payload if isinstance(payload, str) else json.dumps(payload)
        self._client.publish(topic, body, qos=0, retain=retain)

    def _publish_status(self, status: PadStatus) -> None:
        self._publish(f"{self._base()}/status", status.to_dict())
        self._publish(f"{self._base()}/state", "ON" if status.belt_state.is_moving else "OFF")
        self._publish(f"{self._base()}/speed", f"{status.speed_kmh:.2f}")

    def _publish_discovery(self) -> None:
        ident = self.pad.status.address or self._device_id
        device = {
            "identifiers": [ident],
            "name": self.pad.status.name or "WalkingPad",
            "manufacturer": "KingSmith",
            "model": self.pad.status.name or "WalkingPad",
            "connections": [["mac", ident]] if ":" in ident else [],
        }
        origin = {"name": "kingsmith-walkingpad", "sw": "0.1.0"}
        entities = [
            (
                "switch",
                "belt",
                {
                    "name": "Belt",
                    "command_topic": f"{self._base()}/set/command",
                    "state_topic": f"{self._base()}/state",
                    "payload_on": "start",
                    "payload_off": "stop",
                    "icon": "mdi:treadmill",
                },
            ),
            (
                "number",
                "speed",
                {
                    "name": "Speed",
                    "command_topic": f"{self._base()}/set/speed",
                    "state_topic": f"{self._base()}/speed",
                    "min": self.pad.status.min_speed_kmh,
                    "max": self.pad.status.max_speed_kmh,
                    "step": self.pad.status.speed_step_kmh,
                    "unit_of_measurement": "km/h",
                    "icon": "mdi:speedometer",
                },
            ),
            (
                "sensor",
                "distance",
                {
                    "name": "Distance",
                    "state_topic": f"{self._base()}/status",
                    "value_template": "{{ value_json.distance_km }}",
                    "unit_of_measurement": "km",
                    "icon": "mdi:map-marker-distance",
                },
            ),
            (
                "sensor",
                "steps",
                {
                    "name": "Steps",
                    "state_topic": f"{self._base()}/status",
                    "value_template": "{{ value_json.steps }}",
                    "icon": "mdi:shoe-print",
                },
            ),
            (
                "sensor",
                "calories",
                {
                    "name": "Calories",
                    "state_topic": f"{self._base()}/status",
                    "value_template": "{{ value_json.calories }}",
                    "unit_of_measurement": "kcal",
                    "icon": "mdi:fire",
                },
            ),
            (
                "sensor",
                "elapsed",
                {
                    "name": "Elapsed",
                    "state_topic": f"{self._base()}/status",
                    "value_template": "{{ value_json.elapsed_s }}",
                    "unit_of_measurement": "s",
                    "icon": "mdi:timer-outline",
                },
            ),
        ]
        for platform, uid, extra in entities:
            payload = {
                "uniq_id": f"{ident}_{uid}",
                "device": device,
                "origin": origin,
                "availability_topic": f"{self._base()}/availability",
                **extra,
            }
            topic = f"{self.discovery_prefix}/{platform}/walkingpad_{uid}/config"
            self._publish(topic, payload, retain=True)
        self._publish(f"{self._base()}/availability", "online", retain=True)

    async def run(self) -> None:
        self._loop = asyncio.get_running_loop()
        await self.pad.connect()
        self._device_id = (self.pad.status.address or "walkingpad").replace(":", "").lower()
        self.pad.on_status(self._publish_status)
        self._client.will_set(f"{self._base()}/availability", "offline", retain=True)
        self._client.connect(self.host, self.port, keepalive=30)
        self._client.loop_start()
        try:
            await asyncio.Event().wait()
        finally:
            self._publish(f"{self._base()}/availability", "offline", retain=True)
            self._client.loop_stop()
            self._client.disconnect()
            await self.pad.disconnect()
