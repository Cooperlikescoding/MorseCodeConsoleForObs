import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import display_control


def _reset():
    display_control._device = None


def test_no_backlight_device_returns_false(tmp_path, monkeypatch):
    _reset()
    monkeypatch.setattr(display_control, "BACKLIGHT_GLOB", str(tmp_path / "*"))
    assert display_control.set_backlight_brightness(80) is False


def test_finds_nonstandard_device_and_scales_to_its_max(tmp_path, monkeypatch):
    _reset()
    # Touch Display 2 style: an I2C-address device name, max_brightness != 255
    dev = tmp_path / "10-0045"
    dev.mkdir()
    (dev / "max_brightness").write_text("31")
    (dev / "brightness").write_text("31")
    monkeypatch.setattr(display_control, "BACKLIGHT_GLOB", str(tmp_path / "*"))

    assert display_control.set_backlight_brightness(50) is True
    assert (dev / "brightness").read_text().strip() == "16"  # round(31 * 0.5)


def test_clamps_out_of_range_percent(tmp_path, monkeypatch):
    _reset()
    dev = tmp_path / "rpi_backlight"
    dev.mkdir()
    (dev / "max_brightness").write_text("255")
    (dev / "brightness").write_text("255")
    monkeypatch.setattr(display_control, "BACKLIGHT_GLOB", str(tmp_path / "*"))

    display_control.set_backlight_brightness(500)
    assert (dev / "brightness").read_text().strip() == "255"
    display_control.set_backlight_brightness(-20)
    assert (dev / "brightness").read_text().strip() == "0"


def test_missing_max_brightness_falls_back_to_255(tmp_path, monkeypatch):
    _reset()
    dev = tmp_path / "backlight0"
    dev.mkdir()
    (dev / "brightness").write_text("0")  # no max_brightness file
    monkeypatch.setattr(display_control, "BACKLIGHT_GLOB", str(tmp_path / "*"))

    assert display_control.set_backlight_brightness(100) is True
    assert (dev / "brightness").read_text().strip() == "255"


def teardown_function(_):
    _reset()
