"""Local HTTP API and control page. Binds on your LAN; never calls KingSmith cloud."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from aiohttp import web

from ..models import Mode
from ..pad import WalkingPad

logger = logging.getLogger(__name__)
WEB_ROOT = Path(__file__).resolve().parent.parent / "web"
PAD_KEY = web.AppKey("pad", WalkingPad)


def _status_response(pad: WalkingPad) -> dict[str, Any]:
    return pad.status.to_dict()


async def _read_json(request: web.Request) -> dict[str, Any]:
    if not request.can_read_body:
        return {}
    try:
        data = await request.json()
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def build_app(pad: WalkingPad) -> web.Application:
    app = web.Application()
    app[PAD_KEY] = pad

    async def status(_request: web.Request) -> web.Response:
        return web.json_response(_status_response(pad))

    async def start(request: web.Request) -> web.Response:
        body = await _read_json(request)
        speed = body.get("speed")
        await pad.start(float(speed) if speed is not None else None)
        return web.json_response(_status_response(pad))

    async def stop(_request: web.Request) -> web.Response:
        await pad.stop()
        return web.json_response(_status_response(pad))

    async def pause(_request: web.Request) -> web.Response:
        await pad.pause()
        return web.json_response(_status_response(pad))

    async def speed(request: web.Request) -> web.Response:
        body = await _read_json(request)
        if "kmh" not in body:
            raise web.HTTPBadRequest(text='JSON body must include "kmh"')
        await pad.set_speed(float(body["kmh"]))
        return web.json_response(_status_response(pad))

    async def mode(request: web.Request) -> web.Response:
        body = await _read_json(request)
        value = body.get("mode")
        if value not in {m.value for m in Mode}:
            raise web.HTTPBadRequest(text="mode must be auto, manual, or standby")
        await pad.set_mode(Mode(value))
        return web.json_response(_status_response(pad))

    async def index(_request: web.Request) -> web.FileResponse:
        return web.FileResponse(WEB_ROOT / "index.html")

    app.router.add_get("/", index)
    app.router.add_get("/api/status", status)
    app.router.add_post("/api/start", start)
    app.router.add_post("/api/stop", stop)
    app.router.add_post("/api/pause", pause)
    app.router.add_post("/api/speed", speed)
    app.router.add_post("/api/mode", mode)
    return app


async def serve_http(
    pad: WalkingPad,
    host: str = "0.0.0.0",
    port: int = 8080,
    *,
    already_connected: bool = False,
) -> None:
    if not already_connected:
        await pad.connect()
    app = build_app(pad)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info("Local WalkingPad HTTP API on http://%s:%s", host, port)
    try:
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()
        if not already_connected:
            await pad.disconnect()


