"""Central, editable settings for the Morse practice console.

Everything a volunteer might want to tweak before an event lives here.
Most of it can also be adjusted live from the members' terminal (see
ui/terminal.py's command list) without touching this file at all.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from logging_setup import get_logger

_log = get_logger("config")


def _running_on_pi() -> bool:
    """Best-effort detection of 'this is a Raspberry Pi', for auto-picking
    the GPIO backend. Falls back to False (keyboard/software-tone
    backend) anywhere else.
    """
    try:
        with open("/proc/device-tree/model", "r") as f:
            return "raspberry pi" in f.read().lower()
    except OSError:
        return False


def hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()


# Default PIN is "7373" -- change it by replacing `admin_pin_hash` below
# with the output of: python -c "import config; print(config.hash_pin('NEWPIN'))"
DEFAULT_PIN_HASH = hash_pin("7373")

DEFAULT_PRACTICE_WORDS = [
    "SOS", "CQ", "HI", "73", "HAM", "QTH", "RADIO", "MARS", "MORSE", "MOON",
]


def _lerp(t: float, lo: float, hi: float) -> float:
    t = max(0.0, min(100.0, t))
    return lo + (hi - lo) * (t / 100)


@dataclass
class Settings:
    # --- Hardware backend ------------------------------------------------
    # "auto" picks real GPIO hardware on a detected Raspberry Pi (physical
    # key on GPIO 17, passive buzzer on GPIO 18); otherwise falls back to
    # the dev-machine stand-ins (spacebar key, software sine tone).
    hardware_backend: str = "auto"
    gpio_pin: int = 17
    buzzer_pin: int = 18
    dev_key: str = "space"  # Tkinter keysym used as the stand-in Morse key

    # --- Morse timing --------------------------------------------------------
    # Speed in Words Per Minute using the PARIS standard (1 unit = 1200/wpm ms).
    # Kept beginner-friendly by default -- adjustable live via `wpm <n>`.
    wpm: int = 8

    # Single "how forgiving" knob (0-100), adjustable live via `tol <n>`.
    # Kids key sloppily, so the default leans generous. The decoder's
    # actual tolerance ratios are derived from this one number.
    tolerance_percent: int = 60

    @property
    def unit_seconds(self) -> float:
        """Duration of one Morse 'unit' at the current WPM (PARIS standard)."""
        return 1.2 / self.wpm

    @property
    def dot_dash_ratio(self) -> float:
        # Standard dot/dash boundary (2 units); not part of the
        # generosity knob since it's what actually distinguishes a dit
        # from a dah, not how patient the decoder is about pauses.
        return 2.0

    @property
    def letter_gap_ratio(self) -> float:
        return _lerp(self.tolerance_percent, 1.5, 4.0)

    @property
    def word_gap_ratio(self) -> float:
        return self.letter_gap_ratio * 2.5

    @property
    def min_press_ratio(self) -> float:
        return _lerp(self.tolerance_percent, 0.15, 0.4)

    @property
    def min_press_seconds(self) -> float:
        return self.unit_seconds * self.min_press_ratio

    # --- Audio ---------------------------------------------------------------
    tone_hz: float = 650.0
    sample_rate: int = 44100  # dev-machine software tone only
    volume: float = 0.5       # dev-machine software tone only, 0..1

    # --- Display ---------------------------------------------------------------
    brightness_percent: int = 100  # official Pi touchscreen only
    fullscreen: bool = True
    window_size: str = "1280x720"  # official Touch Display 2, landscape (native panel is 720x1280 portrait)

    # --- Terminal / admin ------------------------------------------------------
    admin_pin_hash: str = DEFAULT_PIN_HASH
    terminal_max_lines: int = 500
    terminal_idle_timeout_seconds: float = 60.0

    # --- Practice words ----------------------------------------------------------
    practice_words: list[str] = field(default_factory=lambda: list(DEFAULT_PRACTICE_WORDS))

    # --- Persisted extras --------------------------------------------------------
    # Active Catppuccin/Nord flavor name (see theme.py); kept here rather
    # than in theme.py so config.py doesn't need to import UI code.
    theme_name: str = "mocha"
    # Named settings profiles saved via the terminal's `presetsave`/
    # `presetload` commands, e.g. {"beginner": {"wpm": 5, "tone_hz": 600, "tolerance_percent": 80}}.
    presets: dict = field(default_factory=dict)

    def resolve_backend(self) -> str:
        if self.hardware_backend == "auto":
            return "gpio" if _running_on_pi() else "keyboard"
        return self.hardware_backend


settings = Settings()

# Fields saved to/loaded from disk so an event's tuning survives a
# restart. Deliberately excludes `fullscreen` -- a dev's `unfullscreen`
# toggle should never persist and leave the kiosk windowed after a reboot.
PERSISTED_FIELDS = (
    "wpm", "tone_hz", "tolerance_percent", "brightness_percent",
    "admin_pin_hash", "practice_words", "theme_name", "presets",
)

SETTINGS_FILE = Path(__file__).resolve().parent / "user_settings.json"


def save_settings(target: Settings = settings) -> None:
    data = {field_name: getattr(target, field_name) for field_name in PERSISTED_FIELDS}
    try:
        SETTINGS_FILE.write_text(json.dumps(data, indent=2))
    except OSError as exc:
        _log.warning("could not save settings: %s", exc)


def load_settings_into(target: Settings = settings) -> bool:
    """Apply any previously saved settings onto `target` in place.
    Returns True if a saved file was found and applied."""
    if not SETTINGS_FILE.exists():
        return False
    try:
        data = json.loads(SETTINGS_FILE.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        _log.warning("could not load saved settings: %s", exc)
        return False
    for field_name in PERSISTED_FIELDS:
        if field_name in data:
            setattr(target, field_name, data[field_name])
    return True


load_settings_into(settings)
