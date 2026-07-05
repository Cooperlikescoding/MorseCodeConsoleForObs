"""Fun, skippable fake boot log shown once at startup, before the game
loads. Purely cosmetic -- tapping anywhere skips straight to Home, and
it finishes on its own in under two seconds either way.
"""

from __future__ import annotations

import tkinter as tk
from typing import Callable

import theme
from theme import mono_font

BOOT_LINES = [
    '[  OK  ] Starting MorseOS 1.0 "Sherwood"...',
    "[  OK  ] Initializing GPIO subsystem...",
    "[  OK  ] Loading Morse code tables...",
    "[  OK  ] Calibrating tone generator...",
    "[  OK  ] Mounting practice word bank...",
    "[  OK  ] Starting morse-shell...",
    "",
    "Welcome aboard!",
]
LINE_DELAY_MS = 180
FINISH_DELAY_MS = 400


class BootScreen(tk.Frame):
    def __init__(self, parent, on_done: Callable[[], None], **kwargs):
        super().__init__(parent, bg=theme.current.base, **kwargs)
        self._on_done = on_done
        self._done = False
        self._build()
        self._bind_skip_everywhere(self)

    def _build(self) -> None:
        self.text = tk.Label(
            self, font=mono_font(14), bg=theme.current.base, fg=theme.current.green,
            justify="left", anchor="nw",
        )
        self.text.pack(fill="both", expand=True, padx=20, pady=20)
        tk.Label(
            self, text="(tap to skip)", font=mono_font(10),
            bg=theme.current.base, fg=theme.current.overlay,
        ).pack(side="bottom", pady=10)

    def _bind_skip_everywhere(self, widget) -> None:
        widget.bind("<Button-1>", lambda e: self._finish())
        for child in widget.winfo_children():
            self._bind_skip_everywhere(child)

    # --- lifecycle: called by app.py on screen switch ---

    def enter(self) -> None:
        self._done = False
        self.text.configure(text="")
        self._show_line(0)

    # --- decoder callbacks: no-ops, keying during boot shouldn't crash ---

    def on_key_down(self) -> None:
        pass

    def on_key_up(self) -> None:
        pass

    def on_decoded_letter(self, letter: str | None, pattern: str) -> None:
        pass

    def on_decoded_word_space(self) -> None:
        pass

    def _show_line(self, index: int) -> None:
        if self._done:
            return
        if index >= len(BOOT_LINES):
            self.after(FINISH_DELAY_MS, self._finish)
            return
        current = self.text.cget("text")
        self.text.configure(text=current + ("\n" if current else "") + BOOT_LINES[index])
        self.after(LINE_DELAY_MS, lambda: self._show_line(index + 1))

    def _finish(self) -> None:
        if self._done:
            return
        self._done = True
        self._on_done()
