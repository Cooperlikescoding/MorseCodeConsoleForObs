"""Live visual feedback for the physical Morse key: a shape that grows
from a small dot into an elongated dash the longer the key is held, so
kids can see the short/long distinction forming in real time, matching
what they hear from the tone/buzzer.
"""

from __future__ import annotations

import tkinter as tk

import theme
from ui.shapes import rounded_rect_points

MIN_SIZE = 22
MAX_SIZE = 90
GROWTH_STEP = 3
GROWTH_MS = 15
SETTLE_MS = 150  # how long the final shape lingers after release before resetting


class KeyIndicator(tk.Canvas):
    def __init__(self, parent, height: int = 28, **kwargs):
        parent_bg = _infer_bg(parent)
        super().__init__(
            parent, width=MAX_SIZE + 10, height=height,
            bg=parent_bg, highlightthickness=0, bd=0, **kwargs,
        )
        self._height = height
        self._size = MIN_SIZE
        self._growing = False
        self._after_id: str | None = None
        self._draw(MIN_SIZE, active=False)

    def start_growing(self) -> None:
        if self._after_id is not None:
            self.after_cancel(self._after_id)
            self._after_id = None
        self._growing = True
        self._size = MIN_SIZE
        self._draw(self._size, active=True)
        self._tick()

    def stop_growing(self) -> None:
        self._growing = False
        if self._after_id is not None:
            self.after_cancel(self._after_id)
        self._after_id = self.after(SETTLE_MS, self._reset)

    def _reset(self) -> None:
        self._after_id = None
        self._size = MIN_SIZE
        self._draw(self._size, active=False)

    def _tick(self) -> None:
        if not self._growing:
            return
        self._size = min(MAX_SIZE, self._size + GROWTH_STEP)
        self._draw(self._size, active=True)
        if self._size < MAX_SIZE:
            self._after_id = self.after(GROWTH_MS, self._tick)

    def _draw(self, size: int, active: bool) -> None:
        self.delete("all")
        mid_y = self._height / 2
        top, bottom = mid_y - MIN_SIZE / 2, mid_y + MIN_SIZE / 2
        x0 = 4
        fill = theme.current.mauve if active else theme.current.surface1
        if size <= MIN_SIZE + 1:
            self.create_oval(x0, top, x0 + MIN_SIZE, bottom, fill=fill, outline="")
        else:
            points = rounded_rect_points(x0, top, x0 + size, bottom, MIN_SIZE / 2)
            self.create_polygon(points, smooth=True, fill=fill, outline="")


def _infer_bg(widget) -> str:
    try:
        return widget.cget("bg")
    except tk.TclError:
        return theme.current.base
