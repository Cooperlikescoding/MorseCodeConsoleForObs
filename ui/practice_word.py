"""Practice-word panel: shows a target word (e.g. "MARS") as individual,
tappable letter chips for reference/learning. Tapping a chip opens
tap-to-learn (pattern + tone) for that letter -- it never types anything
into anything. The physical Morse key is the only way to enter text on
the Home screen; this panel is purely a study aid.
"""

from __future__ import annotations

import random
import tkinter as tk
from typing import Callable

import theme
from morse_code import CHAR_TO_MORSE
from theme import mono_font
from ui.shapes import rounded_rect_points
from ui.widgets import RoundedButton

CHIP_SIZE = 56
CHIP_GAP = 10
CHIP_RADIUS = 14
CANVAS_HEIGHT = CHIP_SIZE + 20


class PracticeWordPanel(tk.Frame):
    def __init__(self, parent, on_letter_tap: Callable[[str], None], words: list[str], **kwargs):
        super().__init__(parent, bg=theme.current.base, **kwargs)
        self._on_letter_tap = on_letter_tap
        self._words = list(words)
        self._current_word = ""
        self._chips: list[tuple[int, str]] = []  # (canvas item id, letter)

        self._build()
        self.next_word()

    def _build(self) -> None:
        self.canvas = tk.Canvas(self, bg=theme.current.base, highlightthickness=0, height=CANVAS_HEIGHT)
        self.canvas.pack(fill="x", pady=(0, 6))
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Configure>", lambda e: self._draw_word())

        controls = tk.Frame(self, bg=theme.current.base)
        controls.pack(fill="x")
        tk.Label(
            controls, text="PRACTICE WORD", font=mono_font(11, "bold"),
            bg=theme.current.base, fg=theme.current.subtext,
        ).pack(side="left")

        self.next_button = RoundedButton(controls, text="New word ↻", font=mono_font(11, "bold"), command=self.next_word)
        self.next_button.pack(side="right")

    def next_word(self) -> None:
        choices = [w for w in self._words if w != self._current_word] or self._words
        self._current_word = random.choice(choices) if choices else ""
        self._draw_word()

    def set_words(self, words: list[str]) -> None:
        self._words = list(words)
        if self._current_word not in self._words:
            self.next_word()

    def _draw_word(self) -> None:
        self.canvas.delete("all")
        self._chips = []
        word = self._current_word
        if not word:
            return

        total_width = len(word) * CHIP_SIZE + (len(word) - 1) * CHIP_GAP
        canvas_width = max(self.canvas.winfo_width(), total_width + 20)
        x = (canvas_width - total_width) / 2
        y0, y1 = 10, 10 + CHIP_SIZE

        for letter in word:
            x0, x1 = x, x + CHIP_SIZE
            learnable = letter.upper() in CHAR_TO_MORSE
            fill = theme.current.surface1 if learnable else theme.current.surface0
            points = rounded_rect_points(x0, y0, x1, y1, CHIP_RADIUS)
            chip = self.canvas.create_polygon(points, smooth=True, fill=fill, outline="")
            self.canvas.create_text(
                (x0 + x1) / 2, (y0 + y1) / 2, text=letter,
                font=mono_font(24, "bold"), fill=theme.current.text if learnable else theme.current.subtext,
            )
            self._chips.append((chip, letter))
            x += CHIP_SIZE + CHIP_GAP

    def _on_click(self, event) -> None:
        # Pick the chip whose centre is closest to the tap rather than
        # requiring the tap to land exactly inside a chip's box -- on a
        # touchscreen, finger drift or a tap landing in the small gap
        # between chips would otherwise register as a miss. Only accept
        # the hit if it's reasonably close (within ~1.5 chip widths) so a
        # tap far from the word still does nothing.
        if not self._chips:
            return
        best_chip, best_letter, best_dist = None, None, None
        for chip_id, letter in self._chips:
            bbox = self.canvas.bbox(chip_id)
            if not bbox:
                continue
            cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
            dist = ((event.x - cx) ** 2 + (event.y - cy) ** 2) ** 0.5
            if best_dist is None or dist < best_dist:
                best_chip, best_letter, best_dist = chip_id, letter, dist
        if best_chip is not None and best_dist <= CHIP_SIZE * 1.5:
            if best_letter.upper() in CHAR_TO_MORSE:
                self._flash_chip(best_chip)
                self._on_letter_tap(best_letter.upper())

    def _flash_chip(self, chip_id: int, ms: int = 200) -> None:
        self.canvas.itemconfig(chip_id, fill=theme.current.mauve)
        self.canvas.after(ms, lambda: self.canvas.itemconfig(chip_id, fill=theme.current.surface1))
