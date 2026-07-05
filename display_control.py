"""Screen brightness control for the Raspberry Pi touchscreen.

No-ops (returns False) everywhere else -- there's no generic
cross-platform way to dim an arbitrary monitor, and this console only
needs to dim the one screen it ships on.

The original 7" display exposed its backlight as
`/sys/class/backlight/rpi_backlight`, but the Touch Display 2 (and other
panels) use a different, hardware-dependent device name (e.g. an I2C
address like `10-0045`). So rather than hardcode a path, we discover
whatever backlight device the kernel actually registered under
`/sys/class/backlight/` and read its own `max_brightness` for the scale
(which is NOT always 255).
"""

from __future__ import annotations

import glob
import os

from logging_setup import get_logger

_log = get_logger("display")

BACKLIGHT_GLOB = "/sys/class/backlight/*"

# Cache the discovered device so we only scan sysfs once. None means
# "not looked yet"; a (brightness_path, max_value) tuple or False (no
# device found) once resolved.
_device: tuple[str, int] | bool | None = None


def _find_backlight() -> tuple[str, int] | bool:
    global _device
    if _device is not None:
        return _device

    for base in sorted(glob.glob(BACKLIGHT_GLOB)):
        brightness_path = os.path.join(base, "brightness")
        if not os.path.exists(brightness_path):
            continue
        max_value = 255
        try:
            with open(os.path.join(base, "max_brightness")) as f:
                max_value = int(f.read().strip()) or 255
        except (OSError, ValueError):
            pass
        _device = (brightness_path, max_value)
        _log.info("using backlight device %s (max %d)", base, max_value)
        return _device

    _log.warning("no backlight device found under /sys/class/backlight")
    _device = False
    return _device


def set_backlight_brightness(percent: int) -> bool:
    """Set brightness to `percent` (0-100). Returns True if applied,
    False if no backlight control is available on this machine.
    """
    device = _find_backlight()
    if not device:
        return False
    brightness_path, max_value = device
    percent = max(0, min(100, percent))
    value = round(max_value * percent / 100)
    try:
        with open(brightness_path, "w") as f:
            f.write(str(value))
        return True
    except OSError as exc:
        _log.warning("brightness control unavailable: %s", exc)
        return False
