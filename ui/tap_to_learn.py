"""Tap-to-learn popup: shown when a letter in the practice word is
tapped. Draws the character's Morse pattern as dot/dash shapes (a round
bead for a dit, a rounded bar for a dah) -- a simple mnemonic in the
spirit of Google's "Hello Morse" project -- and plays it audibly,
highlighting each shape in time with the tone.
"""

from __future__ import annotations

import tkinter as tk

import theme
from audio import ToneOutput, schedule_pattern_playback
from config import settings
from morse_code import CHAR_TO_MORSE
from theme import mono_font
from ui.shapes import rounded_rect_points
from ui.widgets import RoundedButton

CANVAS_WIDTH = 380
CANVAS_HEIGHT = 90
DOT_SIZE = 30
DASH_WIDTH = 70
SHAPE_GAP = 18


class TapToLearnPopup(tk.Toplevel):
    def __init__(self, parent, tone: ToneOutput, character: str):
        super().__init__(parent)
        self._tone = tone
        self.character = character.upper()
        self.pattern = CHAR_TO_MORSE.get(self.character, "")
        self._shapes: list[int] = []

        self.configure(bg=theme.current.base)
        self.transient(parent)
        self.attributes("-topmost", True)
        # The main window runs override-redirected for fullscreen (see
        # app.py's _apply_fullscreen) -- on a bare kiosk session with no/
        # minimal window manager, override-redirect windows sit above
        # normal WM-managed ones regardless of "-topmost", so a plain
        # Toplevel here could be created successfully but rendered behind
        # the fullscreen main window (see the same fix in pin_dialog.py).
        self.overrideredirect(True)

        self._build()
        # Size the window to what its widgets actually need, not a guessed
        # pixel constant -- fonts/padding render differently across
        # platforms, and a fixed size previously clipped the Close button.
        self.update_idletasks()
        self._center_over(parent)
        self.lift()
        self.focus_force()

        self.protocol("WM_DELETE_WINDOW", self.close)
        self.after(150, self._play)

    def _center_over(self, parent) -> None:
        parent.update_idletasks()
        width, height = self.winfo_reqwidth(), self.winfo_reqheight()
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        x = px + (pw - width) // 2
        y = py + (ph - height) // 2
        self.geometry(f"{width}x{height}+{max(x, 0)}+{max(y, 0)}")

    def _build(self) -> None:
        tk.Label(
            self, text=self.character, font=mono_font(72, "bold"),
            bg=theme.current.base, fg=theme.current.green,
        ).pack(pady=(20, 0))

        self.canvas = tk.Canvas(
            self, width=CANVAS_WIDTH, height=CANVAS_HEIGHT,
            bg=theme.current.base, highlightthickness=0,
        )
        self.canvas.pack(pady=20)
        self._shapes = self._draw_pattern()

        close_btn = RoundedButton(self, text="Close", font=mono_font(16, "bold"), command=self.close)
        close_btn.pack(pady=(0, 20))

    def _draw_pattern(self) -> list[int]:
        if not self.pattern:
            return []
        widths = [DOT_SIZE if symbol == "." else DASH_WIDTH for symbol in self.pattern]
        total_width = sum(widths) + SHAPE_GAP * (len(widths) - 1)
        x = (CANVAS_WIDTH - total_width) / 2
        mid_y = CANVAS_HEIGHT / 2
        top, bottom = mid_y - DOT_SIZE / 2, mid_y + DOT_SIZE / 2

        shapes = []
        for symbol, width in zip(self.pattern, widths):
            if symbol == ".":
                shape = self.canvas.create_oval(x, top, x + width, bottom, fill=theme.current.surface2, outline="")
            else:
                points = rounded_rect_points(x, top, x + width, bottom, DOT_SIZE / 2)
                shape = self.canvas.create_polygon(points, smooth=True, fill=theme.current.surface2, outline="")
            shapes.append(shape)
            x += width + SHAPE_GAP
        return shapes

    def _play(self) -> None:
        if not self.pattern:
            return
        schedule_pattern_playback(
            self, self._tone, self.pattern, settings.unit_seconds,
            on_symbol=self._highlight_symbol, on_done=self._clear_highlight,
        )

    def _highlight_symbol(self, index: int) -> None:
        for i, shape in enumerate(self._shapes):
            self.canvas.itemconfig(shape, fill=theme.current.mauve if i == index else theme.current.surface2)

    def _clear_highlight(self) -> None:
        for shape in self._shapes:
            self.canvas.itemconfig(shape, fill=theme.current.surface2)

    def close(self) -> None:
        self._tone.stop()
        self.destroy()
