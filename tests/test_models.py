from kingsmith_walkingpad.models import BeltState, Mode, PadStatus, ProtocolType


def test_status_to_dict() -> None:
    status = PadStatus(
        connected=True,
        protocol=ProtocolType.WILINK,
        address="AA:BB:CC:DD:EE:FF",
        belt_state=BeltState.RUNNING,
        mode=Mode.MANUAL,
        speed_kmh=2.46,
        distance_km=0.1234,
        steps=200,
        elapsed_s=80,
        calories=4.44,
    )
    data = status.to_dict()
    assert data["moving"] is True
    assert data["speed_kmh"] == 2.46
    assert data["distance_km"] == 0.123
    assert data["calories"] == 4.4
    assert data["protocol"] == "wilink"


def test_mode_roundtrip() -> None:
    assert Mode.from_wilink(1) is Mode.MANUAL
    assert Mode.AUTO.to_wilink() == 0
