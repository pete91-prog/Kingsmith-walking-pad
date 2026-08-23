"""Constants for the offline KingSmith WalkingPad Home Assistant integration."""

DOMAIN = "kingsmith_walkingpad"
PLATFORMS = ["switch", "number", "sensor", "select", "button"]

CONF_ADDRESS = "address"
CONF_NAME = "name"
CONF_WEIGHT = "weight_kg"
CONF_ALLOW_CONTROL = "allow_control"

DEFAULT_WEIGHT = 75.0
DEFAULT_ALLOW_CONTROL = True
