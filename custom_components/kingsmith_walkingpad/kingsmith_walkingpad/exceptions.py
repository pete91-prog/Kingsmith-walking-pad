"""Errors raised by the WalkingPad client."""


class WalkingPadError(Exception):
    """Base error for local WalkingPad control."""


class PadNotFoundError(WalkingPadError):
    """No matching treadmill was discovered."""


class ProtocolError(WalkingPadError):
    """The pad spoke an unexpected or unsupported protocol."""


class CommandError(WalkingPadError):
    """A control command was rejected or timed out."""
