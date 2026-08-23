from kingsmith_walkingpad.models import SpeedRange
from kingsmith_walkingpad.protocol.ftms import (
    parse_control_response,
    parse_speed_range,
    parse_treadmill_data,
    pause,
    set_target_speed,
    start_resume,
    stop,
)


def test_control_opcodes() -> None:
    assert start_resume() == b"\x07"
    assert stop() == b"\x08\x01"
    assert pause() == b"\x08\x02"


def test_set_target_speed_little_endian() -> None:
    # 2.5 km/h = 250 = 0x00FA
    assert set_target_speed(2.5) == bytes([0x02, 0xFA, 0x00])
    # 4.0 km/h = 400 = 0x0190
    assert set_target_speed(4.0) == bytes([0x02, 0x90, 0x01])


def test_parse_speed_range() -> None:
    raw = (160).to_bytes(2, "little") + (640).to_bytes(2, "little") + (10).to_bytes(2, "little")
    rng = parse_speed_range(raw)
    assert rng == SpeedRange(min_kmh=1.6, max_kmh=6.4, step_kmh=0.1)


def test_parse_treadmill_data_with_ks_steps() -> None:
    flags = 0x0004 | 0x0400 | 0x2000
    raw = bytearray(flags.to_bytes(2, "little"))
    raw.extend((250).to_bytes(2, "little"))  # 2.50 km/h
    raw.extend((1234).to_bytes(3, "little"))  # meters
    raw.extend((90).to_bytes(2, "little"))  # seconds
    raw.extend((1800).to_bytes(2, "little"))  # steps
    parsed = parse_treadmill_data(bytes(raw))
    assert parsed.speed_kmh == 2.5
    assert parsed.distance_m == 1234
    assert parsed.elapsed_s == 90
    assert parsed.steps == 1800


def test_parse_control_response() -> None:
    assert parse_control_response(bytes([0x80, 0x00, 0x04])) == (0x00, 0x04)
    assert parse_control_response(b"\x01") is None
