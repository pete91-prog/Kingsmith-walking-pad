from pathlib import Path


def test_vendored_library_is_present() -> None:
    root = Path(__file__).resolve().parents[1]
    vendor = root / "custom_components" / "kingsmith_walkingpad" / "kingsmith_walkingpad"
    assert (vendor / "pad.py").is_file()
    assert (vendor / "protocol" / "wilink.py").is_file()
    assert (vendor / "protocol" / "ftms.py").is_file()
