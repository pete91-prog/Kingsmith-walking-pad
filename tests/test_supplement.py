from kingsmith_walkingpad.protocol.supplement import (
    is_unlock_ok,
    parse_supplement_frame,
    supplement_frame,
    unlock_frame,
    unlock_token,
)


def test_supplement_roundtrip() -> None:
    frame = supplement_frame(0x72, 0x00, b"\x00")
    assert frame == bytes.fromhex("72 00 01 00 73")
    assert parse_supplement_frame(frame) == (0x72, 0x00, b"\x00")


def test_unlock_token_z1() -> None:
    # KS-HD-Z1D last4 = "-Z1D" = 2D 5A 31 44 → +1 → 2E 5A 31 44
    assert unlock_token("KS-HD-Z1D") == bytes.fromhex("2e 5a 31 44")
    assert unlock_frame("KS-HD-Z1D") == bytes.fromhex("71 00 05 01 2e 5a 31 44 74")


def test_unlock_ok() -> None:
    reply = supplement_frame(0x71, 0x80)
    assert is_unlock_ok(reply)
    assert not is_unlock_ok(supplement_frame(0x71, 0x00, b"\x01"))


def test_bad_checksum_rejected() -> None:
    frame = bytearray(supplement_frame(0x71, 0x80))
    frame[-1] ^= 0xFF
    assert parse_supplement_frame(bytes(frame)) is None
