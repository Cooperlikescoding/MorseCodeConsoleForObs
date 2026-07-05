"""Touch-friendly on-screen QWERTY keyboard, used only in the members'
Terminal for typing commands/chat. `highlight()` flashes a key when the
physical Morse key decodes that letter while the Terminal is active, so
kids can still see feedback if they key instead of type.
"""

from __future__ import annotations

import tkinter as tk
from typing import Callable

import theme
from theme import mono_font
from ui.widgets import RoundedButton

ROWS = [
    list("1234567890"),
    list("QWERTYUIOP"),
    list("ASDFGHJKL"),
    list("ZXCVBNM"),
]


class OnScreenKeyboard(tk.Frame):
    def __init__(self, parent, on_tap: Callable[[str], None],
                 extra_keys: list[tuple[str, str]] | None = None, **kwargs):
        """extra_keys: additional (label, token) special buttons appended
        to the bottom row, e.g. [("ENTER", "ENTER")] for the terminal.
        """
        super().__init__(parent, bg=theme.current.mantle, **kwargs)
        self._on_tap = on_tap
        self._extra_keys = extra_keys or []
        self._buttons: dict[str, RoundedButton] = {}
        self._highlight_jobs: dict[str, str] = {}
        self._build()

    def _build(self) -> None:
        for row_index, row in enumerate(ROWS):
            row_frame = tk.Frame(self, bg=theme.current.mantle)
            row_frame.grid(row=row_index, column=0, sticky="nsew", pady=2)
            self.grid_rowconfigure(row_index, weight=1)
            for col_index, char in enumerate(row):
                row_frame.grid_columnconfigure(col_index, weight=1)
                btn = self._make_key(row_frame, char, char, theme.current.surface0)
                btn.grid(row=0, column=col_index, sticky="nsew", padx=2, pady=2)
                self._buttons[char] = btn

        bottom = tk.Frame(self, bg=theme.current.mantle)
        bottom.grid(row=len(ROWS), column=0, sticky="nsew", pady=2)
        self.grid_rowconfigure(len(ROWS), weight=1)
        specials = [("CLEAR", "CLEAR"), ("SPACE", "SPACE"), ("⌫ BACK", "BACKSPACE"), *self._extra_keys]
        for i, (label, token) in enumerate(specials):
            bottom.grid_columnconfigure(i, weight=1)
            btn = self._make_key(bottom, label, token, theme.current.surface1)
            btn.grid(row=0, column=i, sticky="nsew", padx=2, pady=2)

    def _make_key(self, parent, label: str, token: str, bg: str) -> RoundedButton:
        return RoundedButton(
            parent, text=label, font=mono_font(18, "bold"), bg=bg,
            radius=8, padx=14, pady=12, stretch=True, command=lambda t=token: self._on_tap(t),
        )

    def highlight(self, letter: str, ms: int = 500) -> None:
        """Flash a letter's button to show it was just decoded from the
        physical key. Safe to call for letters not on the keyboard (e.g.
        None from an unrecognized pattern) -- it's simply ignored.
        """
        letter = (letter or "").upper()
        btn = self._buttons.get(letter)
        if btn is None:
            return

        # Cancel any pending un-highlight so rapid repeats don't flicker.
        existing_job = self._highlight_jobs.pop(letter, None)
        if existing_job is not None:
            btn.after_cancel(existing_job)

        btn.set_colors(bg=theme.current.mauve, fg=theme.current.mantle)
        job = btn.after(ms, lambda: self._unhighlight(letter))
        self._highlight_jobs[letter] = job

    def _unhighlight(self, letter: str) -> None:
        self._highlight_jobs.pop(letter, None)
        btn = self._buttons.get(letter)
        if btn is not None:
            btn.set_colors(bg=theme.current.surface0, fg=theme.current.text)
