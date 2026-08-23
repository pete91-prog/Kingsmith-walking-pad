from kingsmith_walkingpad.models import BeltState, Mode
from kingsmith_walkingpad.protocol.wilink import (
    extract_wilink_frames,
    parse_wilink_last_status,
    parse_wilink_status,
    request_status,
    set_mode,
    set_speed,
    start_belt,
    stop_belt,
    wilink_checksum,
    wilink_frame,
)


def test_known_status_request_frame() -> None:
    assert request_status() == bytes.fromhex("F7 A2 00 00 A2 FD")


def test_set_speed_2kmh() -> None:
    assert set_speed(2.0) == bytes.fromhex("F7 A2 01 14 B7 FD")


def test_set_manual_mode() -> None:
    assert set_mode(Mode.MANUAL) == bytes.fromhex("F7 A2 02 01 A5 FD")


def test_start_and_stop() -> None:
    assert start_belt() == bytes.fromhex("F7 A2 04 01 A7 FD")
    assert stop_belt() == bytes.fromhex("F7 A2 01 00 A3 FD")


def test_checksum_is_sum_of_body() -> None:
    body = bytes([0xA2, 0x01, 0x14])
    assert wilink_checksum(body) == 0xB7
    frame = wilink_frame(0xA2, 0x01, bytes([0x14]))
    assert frame[0] == 0xF7 and frame[-1] == 0xFD
    assert frame[-2] == 0xB7


def test_parse_status() -> None:
    # idle, 2.0 km/h, manual, 66s, 0.12 km, 180 steps
    frame = bytearray([0xF8, 0xA2, 0, 20, 1])
    frame.extend((66).to_bytes(3, "big"))
    frame.extend((12).to_bytes(3, "big"))
    frame.extend((180).to_bytes(3, "big"))
    frame.extend([0, 0, 0, 0, 0, 0xFD])
    parsed = parse_wilink_status(bytes(frame))
    assert parsed is not None
    assert parsed.belt_state is BeltState.IDLE
    assert parsed.speed_kmh == 2.0
    assert parsed.mode is Mode.MANUAL
    assert parsed.elapsed_s == 66
    assert parsed.distance_km == 0.12
    assert parsed.steps == 180


def test_parse_last_status() -> None:
    frame = bytearray([0xF8, 0xA7, 0, 0, 0, 0, 0, 0])
    frame.extend((120).to_bytes(3, "big"))
    frame.extend((25).to_bytes(3, "big"))
    frame.extend((400).to_bytes(3, "big"))
    frame.extend([0, 0xFD])
    parsed = parse_wilink_last_status(bytes(frame))
    assert parsed is not None
    assert parsed.elapsed_s == 120
    assert parsed.distance_km == 0.25
    assert parsed.steps == 400


def test_extract_coalesced_frames() -> None:
    first = bytes.fromhex("F8 A2 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 FD")
    second = bytes.fromhex("F8 A7 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 FD")
    buf = bytearray(b"\x00\x11" + first + second[:6])
    frames = extract_wilink_frames(buf)
    assert frames == [first]
    buf.extend(second[6:])
    frames = extract_wilink_frames(buf)
    assert frames == [second]
    assert buf == bytearray()
