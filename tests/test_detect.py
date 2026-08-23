from kingsmith_walkingpad.const import FTMS_SERVICE, WILINK_SERVICE
from kingsmith_walkingpad.models import ProtocolType
from kingsmith_walkingpad.protocol.detect import looks_like_walkingpad, pick_protocol


def test_pick_ftms_from_service() -> None:
    assert pick_protocol("whatever", [FTMS_SERVICE]) is ProtocolType.FTMS


def test_pick_wilink_from_service() -> None:
    assert pick_protocol("whatever", [WILINK_SERVICE]) is ProtocolType.WILINK


def test_pick_ftms_from_name() -> None:
    assert pick_protocol("KS-HD-Z1D", []) is ProtocolType.FTMS
    assert pick_protocol("KS-MC21-D06BFD", []) is ProtocolType.FTMS


def test_pick_wilink_from_name() -> None:
    assert pick_protocol("WalkingPad", []) is ProtocolType.WILINK
    assert pick_protocol("KS-R1AC", []) is ProtocolType.WILINK


def test_looks_like_walkingpad() -> None:
    assert looks_like_walkingpad("WalkingPad C2")
    assert looks_like_walkingpad(None, [FTMS_SERVICE])
    assert not looks_like_walkingpad("Pixel Buds", [])
