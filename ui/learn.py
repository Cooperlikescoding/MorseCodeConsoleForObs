"""Structured LEARN mode: steps through the alphabet one letter at a
time, in order. Separate from the free-practice Home screen -- here
there's a specific right answer, checked as it's keyed, before moving on
to the next letter. Kept deliberately simple: no scoring, no branching,
just A to Z.
"""

from __future__ import annotations

import tkinter as tk
from typing import Callable

import theme
from morse_code import LETTERS
from theme import mono_font
from ui.key_indicator import KeyIndicator
from ui.widgets import RoundedButton

ALPHABET = list(LETTERS.keys())
ADVANCE_DELAY_MS = 700
RESTART_DELAY_MS = 2000


class LearnScreen(tk.Frame):
    def __init__(self, parent, on_exit: Callable[[], None], **kwargs):
        super().__init__(parent, bg=theme.current.base, **kwargs)
        self._on_exit = on_exit
        self._index = 0
        self._build()

    def _build(self) -> None:
        header = tk.Frame(self, bg=theme.current.base)
        header.pack(fill="x", padx=16, pady=(16, 4))
        tk.Label(
            header, text="LEARN MODE", font=mono_font(11, "bold"),
            bg=theme.current.base, fg=theme.current.subtext,
        ).pack(side="left")
        self.progress_label = tk.Label(
            header, font=mono_font(11), bg=theme.current.base, fg=theme.current.subtext,
        )
        self.progress_label.pack(side="left", padx=(10, 0))
        back_btn = RoundedButton(
            header, text="← Back to Game", font=mono_font(11, "bold"), command=self._exit,
        )
        back_btn.pack(side="right")

        self.letter_label = tk.Label(
            self, font=mono_font(120, "bold"), bg=theme.current.base, fg=theme.current.green,
        )
        self.letter_label.pack(expand=True)

        self.feedback_label = tk.Label(
            self, font=mono_font(16, "bold"), bg=theme.current.base, fg=theme.current.subtext,
        )
        self.feedback_label.pack(pady=(0, 8))

        self.key_indicator = KeyIndicator(self, height=28)
        self.key_indicator.pack(pady=(0, 20))

    # --- lifecycle: called by app.py on screen switch ---

    def enter(self) -> None:
        self._index = 0
        self._show_current()

    # --- decoder callbacks (routed here by the app while this screen is active) ---

    def on_key_down(self) -> None:
        self.key_indicator.start_growing()

    def on_key_up(self) -> None:
        self.key_indicator.stop_growing()

    def on_decoded_letter(self, letter: str | None, pattern: str) -> None:
        target = ALPHABET[self._index]
        if letter == target:
            self.feedback_label.configure(text="Correct!", fg=theme.current.green)
            self.after(ADVANCE_DELAY_MS, self._advance)
        else:
            shown = letter if letter else "that pattern"
            self.feedback_label.configure(text=f"That was {shown} -- try again.", fg=theme.current.red)

    def on_decoded_word_space(self) -> None:
        pass  # not meaningful mid-letter in this mode

    def _show_current(self) -> None:
        letter = ALPHABET[self._index]
        self.letter_label.configure(text=letter)
        self.progress_label.configure(text=f"Letter {self._index + 1} of {len(ALPHABET)}")
        self.feedback_label.configure(text="Key this letter on the practice key.", fg=theme.current.subtext)

    def _advance(self) -> None:
        self._index += 1
        if self._index >= len(ALPHABET):
            self.letter_label.configure(text="\U0001F389")
            self.progress_label.configure(text=f"Letter {len(ALPHABET)} of {len(ALPHABET)}")
            self.feedback_label.configure(text="You learned the whole alphabet! Starting over...", fg=theme.current.green)
            self.after(RESTART_DELAY_MS, self.enter)
            return
        self._show_current()

    def _exit(self) -> None:
        self._on_exit()
