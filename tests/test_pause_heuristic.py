import asyncio

from kingsmith_walkingpad.demo import demo_pad
from kingsmith_walkingpad.models import BeltState, ProtocolType


async def test_pause_stays_paused_when_speed_reported() -> None:
    pad = demo_pad(ProtocolType.WILINK)
    await pad.connect()
    try:
        await pad.start(2.0)
        await asyncio.sleep(0.05)
        await pad.pause()
        await asyncio.sleep(0.05)
        assert pad.status.belt_state is BeltState.PAUSED
        assert pad.status.speed_kmh > 0
    finally:
        await pad.disconnect()
