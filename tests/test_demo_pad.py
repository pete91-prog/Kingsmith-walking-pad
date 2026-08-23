import asyncio

from kingsmith_walkingpad.demo import demo_pad
from kingsmith_walkingpad.models import BeltState, ProtocolType


async def test_demo_wilink_session() -> None:
    pad = demo_pad(ProtocolType.WILINK)
    await pad.connect()
    try:
        assert pad.status.connected
        assert pad.protocol is ProtocolType.WILINK
        await pad.start(2.0)
        await asyncio.sleep(0.05)
        assert pad.status.belt_state in {BeltState.RUNNING, BeltState.STARTING, BeltState.STOPPED}
        await pad.set_speed(2.4)
        assert pad.status.target_speed_kmh == 2.4
        await pad.stop()
        assert pad.status.speed_kmh == 0
    finally:
        await pad.disconnect()
        assert pad.status.connected is False


async def test_demo_ftms_unlock_path_not_required() -> None:
    pad = demo_pad(ProtocolType.FTMS)
    await pad.connect()
    try:
        assert pad.protocol is ProtocolType.FTMS
        await pad.start()
        await asyncio.sleep(0.05)
        await pad.set_speed(3.0)
        assert pad.status.target_speed_kmh == 3.0
    finally:
        await pad.disconnect()
