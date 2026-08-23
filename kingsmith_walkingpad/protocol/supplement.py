"""KingSmith supplement / ODM vendor channel used as an FTMS unlock gate."""

from __future__ import annotations


def supplement_frame(cmd0: int, cmd1: int, data: bytes = b"") -> bytes:
    body = bytes([cmd0, cmd1, len(data)]) + data
    return body + bytes([sum(body) & 0xFF])


def parse_supplement_frame(raw: bytes) -> tuple[int, int, bytes] | None:
    if len(raw) < 4:
        return None
    cmd0, cmd1, length = raw[0], raw[1], raw[2]
    if len(raw) < 3 + length + 1:
        return None
    data = raw[3 : 3 + length]
    if (sum(raw[: 3 + length]) & 0xFF) != raw[3 + length]:
        return None
    return cmd0, cmd1, data


def unlock_token(device_name: str) -> bytes:
    last4 = device_name[-4:].encode("ascii", errors="replace")
    if len(last4) < 4:
        raise ValueError(f"device name {device_name!r} is too short for an unlock token")
    code = (int.from_bytes(last4, "little") + 1) & 0xFFFFFFFF
    return code.to_bytes(4, "little")


def unlock_frame(device_name: str) -> bytes:
    """Name-derived unlock: 71 00 05 01 <LE32(name[-4:])+1> CC."""
    return supplement_frame(0x71, 0x00, b"\x01" + unlock_token(device_name))


def is_unlock_ok(raw: bytes) -> bool:
    parsed = parse_supplement_frame(raw)
    return parsed is not None and parsed[0] == 0x71 and parsed[1] == 0x80


def sysinfo_frame(unix_time: int = 0, user_id: int = 0) -> bytes:
    return supplement_frame(
        0x71,
        0x01,
        unix_time.to_bytes(4, "little") + user_id.to_bytes(4, "little"),
    )


def setting_get_all() -> bytes:
    return supplement_frame(0x72, 0x00, b"\x00")


def vendor_start() -> bytes:
    return supplement_frame(0x77, 0x01, bytes([0x07]))


def vendor_stop() -> bytes:
    return supplement_frame(0x77, 0x01, bytes([0x08, 0x01]))


def vendor_set_speed(kmh: float) -> bytes:
    hundredths = max(0, min(65535, round(kmh * 100)))
    return supplement_frame(0x77, 0x01, bytes([0x02]) + hundredths.to_bytes(2, "little"))
