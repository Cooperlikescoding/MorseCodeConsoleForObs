"""Read-only feedback display for text built up by keying the physical
Morse key (or the dev spacebar stand-in).

Implemented as a plain `tk.Label`, deliberately NOT a `tk.Text`: a Text
widget is interactive even when read-only (it shows an I-beam cursor,
takes keyboard focus, and handles pointer selection), and on the
touchscreen that interfered with taps reaching the surrounding buttons.
A Label has none of that -- it's purely a display.

Tap-to-learn lives in ui/practice_word.py instead, on the reference word
above this; this widget isn't tappable.
"""

from __future__ import annotations

import tkinter as tk

import theme
from theme import mono_font

# Placeholder shown for a keyed pattern that didn't match any known
# character. Deliberately not a real Morse punctuation mark (unlike "?",
# which IS a valid character) so it's never confused with a real one.
UNRECOGNIZED_PLACEHOLDER = "#"


class KeyedTextDisplay(tk.Label):
    def __init__(self, parent, max_chars: int = 200, bg: str | None = None, **kwargs):
        self._bg = bg if bg is not None else theme.current.base
        self._var = tk.StringVar(value="")
        self._flash_job: str | None = None
        super().__init__(
            parent, textvariable=self._var, anchor="nw", justify="left",
            bg=self._bg, fg=theme.current.text, font=mono_font(22),
            bd=0, highlightthickness=0, takefocus=0, cursor="arrow", **kwargs,
        )
        self._max_chars = max_chars
        # Wrap to the widget's width so long runs flow onto new lines
        # instead of overflowing off the side.
        self.bind("<Configure>", lambda e: self.configure(wraplength=max(e.width - 4, 1)))

    @property
    def _text(self) -> str:
        return self._var.get()

    def append(self, text: str) -> None:
        self._var.set((self._text + text)[-self._max_chars:])

    def flash_last(self, length: int = 1, ms: int = 400) -> None:
        """Briefly tint the whole display to signal a new letter arrived.
        (A Label can't colour just part of its text the way a Text widget
        could, so this flashes the whole readout rather than only the last
        character -- close enough as an 'input registered' cue.)"""
        if self._flash_job is not None:
            self.after_cancel(self._flash_job)
        self.configure(fg=theme.current.mauve)
        self._flash_job = self.after(ms, self._end_flash)

    def _end_flash(self) -> None:
        self._flash_job = None
        self.configure(fg=theme.current.text)

    def clear(self) -> None:
        self._var.set("")

    def delete_last_word(self) -> None:
        """Remove the most recent word (or in-progress letters) so a
        mis-keyed attempt doesn't force clearing the whole display."""
        self._var.set(self._without_last_word(self._text))

    @staticmethod
    def _without_last_word(text: str) -> str:
        stripped = text.rstrip(" ")
        last_space = stripped.rfind(" ")
        return stripped[:last_space].rstrip(" ") if last_space != -1 else ""
