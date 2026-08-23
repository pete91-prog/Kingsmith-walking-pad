from aiohttp.test_utils import TestClient, TestServer

from kingsmith_walkingpad.demo import demo_pad
from kingsmith_walkingpad.server.http_api import build_app


async def test_status_and_start_stop() -> None:
    pad = demo_pad()
    await pad.connect()
    try:
        app = build_app(pad)
        async with TestClient(TestServer(app)) as client:
            res = await client.get("/api/status")
            assert res.status == 200
            body = await res.json()
            assert body["connected"] is True
            assert body["protocol"] == "wilink"

            page = await client.get("/")
            assert page.status == 200
            html = await page.text()
            assert "WalkingPad" in html
            assert "Local control only" in html

            started = await client.post("/api/start", json={"speed": 2.0})
            assert started.status == 200
            data = await started.json()
            assert data["mode"] == "manual"

            sped = await client.post("/api/speed", json={"kmh": 2.5})
            assert (await sped.json())["target_speed_kmh"] == 2.5

            stopped = await client.post("/api/stop", json={})
            assert (await stopped.json())["belt_state"] in {"stopped", "idle"}
    finally:
        await pad.disconnect()


async def test_mode_validation() -> None:
    pad = demo_pad()
    await pad.connect()
    try:
        async with TestClient(TestServer(build_app(pad))) as client:
            bad = await client.post("/api/mode", json={"mode": "warp"})
            assert bad.status == 400
    finally:
        await pad.disconnect()
