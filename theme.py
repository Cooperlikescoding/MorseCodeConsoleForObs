"""Catppuccin palette (all four official flavors) + small styling helpers
shared across every screen, so the whole app looks like one consistent,
modern piece of software rather than default Tkinter grey.

`current` is the active palette; the terminal's `theme <flavor>` command
swaps it and asks the app to rebuild its screens from scratch, since
Tkinter widgets don't recolor themselves -- code that needs a color must
read it live via `theme.current.xxx` (a fresh attribute lookup) rather
than importing a color as a bare name, or it would keep referencing
whatever flavor was active at import time.

Plain Tkinter widgets can't do real rounded corners or box-shadows, so
"modern" here means: a consistent palette, a monospace font used
everywhere, flat borderless buttons with a lighten-on-hover /
darken-on-press feel, and generous padding. Where a rounded, chip-like
look genuinely matters (the practice-word letters, tap-to-learn's
dot/dash shapes), see `ui/shapes.py` for canvas-drawn rounded rects.
"""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    name: str
    base: str
    mantle: str
    crust: str
    surface0: str
    surface1: str
    surface2: str
    text: str
    subtext: str
    overlay: str
    mauve: str
    blue: str
    green: str
    red: str
    yellow: str
    teal: str


def _clamp(value: int) -> int:
    return max(0, min(255, value))


def shade(hex_color: str, amount: int) -> str:
    """Lighten (amount > 0) or darken (amount < 0) a hex color."""
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    r, g, b = _clamp(r + amount), _clamp(g + amount), _clamp(b + amount)
    return f"#{r:02x}{g:02x}{b:02x}"


# https://catppuccin.com/palette -- the four official flavors.
MOCHA = Palette(
    name="mocha", base="#1e1e2e", mantle="#181825", crust="#11111b",
    surface0="#313244", surface1="#45475a", surface2="#585b70",
    text="#cdd6f4", subtext="#a6adc8", overlay="#6c7086",
    mauve="#cba6f7", blue="#89b4fa", green="#a6e3a1",
    red="#f38ba8", yellow="#f9e2af", teal="#94e2d5",
)
MACCHIATO = Palette(
    name="macchiato", base="#24273a", mantle="#1e2030", crust="#181926",
    surface0="#363a4f", surface1="#494d64", surface2="#5b6078",
    text="#cad3f5", subtext="#a5adcb", overlay="#6e738d",
    mauve="#c6a0f6", blue="#8aadf4", green="#a6da95",
    red="#ed8796", yellow="#eed49f", teal="#8bd5ca",
)
FRAPPE = Palette(
    name="frappe", base="#303446", mantle="#292c3c", crust="#232634",
    surface0="#414559", surface1="#51576d", surface2="#626880",
    text="#c6d0f5", subtext="#a5adce", overlay="#737994",
    mauve="#ca9ee6", blue="#8caaee", green="#a6d189",
    red="#e78284", yellow="#e5c890", teal="#81c8be",
)
LATTE = Palette(
    name="latte", base="#eff1f5", mantle="#e6e9ef", crust="#dce0e8",
    surface0="#ccd0da", surface1="#bcc0cc", surface2="#acb0be",
    text="#4c4f69", subtext="#6c6f85", overlay="#9ca0b0",
    mauve="#8839ef", blue="#1e66f5", green="#40a02b",
    red="#d20f39", yellow="#df8e1d", teal="#179299",
)
# https://www.nordtheme.com -- not a Catppuccin flavor, but shares the
# same "dark base + soft accents" spirit and was requested alongside them.
# Nord doesn't define anything darker than its base color, so mantle/crust
# are derived by shading base down rather than using an official hex.
_NORD_BASE = "#2e3440"
NORD = Palette(
    name="nord", base=_NORD_BASE, mantle=shade(_NORD_BASE, -8), crust=shade(_NORD_BASE, -16),
    surface0="#3b4252", surface1="#434c5e", surface2="#4c566a",
    text="#eceff4", subtext="#d8dee9", overlay="#9aa5b1",
    mauve="#b48ead", blue="#81a1c1", green="#a3be8c",
    red="#bf616a", yellow="#ebcb8b", teal="#88c0d0",
)

FLAVORS: dict[str, Palette] = {p.name: p for p in (MOCHA, MACCHIATO, FRAPPE, LATTE, NORD)}

current: Palette = MOCHA


def set_flavor(name: str) -> bool:
    """Switch the active palette. Returns False if `name` isn't a known
    flavor (current palette is left unchanged)."""
    global current
    flavor = FLAVORS.get(name.lower())
    if flavor is None:
        return False
    current = flavor
    return True


_FONT_CANDIDATES = ["JetBrains Mono", "Fira Code", "Cascadia Mono", "Consolas", "DejaVu Sans Mono", "Courier New"]
_resolved_family: str | None = None


def mono_font(size: int, weight: str = "normal") -> tuple[str, int, str]:
    """The best available monospace font on this machine, cached after
    the first lookup (querying installed fonts needs a live Tk root).
    """
    global _resolved_family
    if _resolved_family is None:
        available = set(tkfont.families())
        _resolved_family = next((f for f in _FONT_CANDIDATES if f in available), "Courier New")
    return (_resolved_family, size, weight)


def style_flat_button(btn: tk.Button, bg: str | None = None, fg: str | None = None, hover_amount: int = 18) -> None:
    """Flat, borderless button with hover (lighter) and press (darker)
    feedback -- the closest plain Tkinter gets to a "modern" button
    without a rounded-corner canvas widget.
    """
    bg = bg if bg is not None else current.surface0
    fg = fg if fg is not None else current.text
    hover_bg = shade(bg, hover_amount)
    press_bg = shade(bg, -hover_amount)
    btn.configure(
        bg=bg, fg=fg, activebackground=press_bg, activeforeground=fg,
        bd=0, relief="flat", highlightthickness=0, cursor="hand2",
        padx=12, pady=8,
    )
    btn.bind("<Enter>", lambda e: btn.configure(bg=hover_bg))
    btn.bind("<Leave>", lambda e: btn.configure(bg=bg))
