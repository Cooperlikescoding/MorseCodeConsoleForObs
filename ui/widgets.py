"""Reusable rounded-corner touch button, used throughout the app instead
of plain tk.Button for a more modern look. Plain Tkinter has no native
rounded corners, so this draws one on a small Canvas: a rounded-rect
background plus centered text, with press/release color feedback --
deliberately no hover state, since every screen here is touched, not
moused.
"""

from __future__ import annotations

import tkinter as tk
from typing import Callable

import theme
from theme import mono_font, shade
from ui.shapes import rounded_rect_points


class RoundedButton(tk.Canvas):
    def __init__(self, parent, text: str, command: Callable[[], None] | None = None,
                 font: tuple | None = None, bg: str | None = None, fg: str | None = None,
                 parent_bg: str | None = None, radius: int = 10,
                 padx: int = 16, pady: int = 10,
                 width: int | None = None, height: int | None = None,
                 stretch: bool = False, **kwargs):
        """stretch=True lets the button be resized by its geometry manager
        (e.g. grid(sticky="nsew") in a stretchy row/column) -- the rounded
        shape and centered text redraw to fit on every resize. Used by the
        on-screen keyboard, whose keys fill the available touchscreen width.
        """
        self._bg = bg if bg is not None else theme.current.surface0
        self._fg = fg if fg is not None else theme.current.text
        self._font = font if font is not None else mono_font(13, "bold")
        self._command = command
        self._radius = radius
        self._pressed_bg = shade(self._bg, -22)
        self._stretch = stretch
        parent_bg = parent_bg if parent_bg is not None else _infer_bg(parent)

        text_w, text_h = _measure_text(parent, text, self._font)
        self._width = width if width is not None else text_w + padx * 2
        self._height = height if height is not None else text_h + pady * 2

        super().__init__(
            parent, width=self._width, height=self._height,
            bg=parent_bg, highlightthickness=0, bd=0, **kwargs,
        )

        self._shape = self.create_polygon(
            rounded_rect_points(1, 1, self._width - 1, self._height - 1, radius),
            smooth=True, fill=self._bg, outline="",
        )
        self._label = self.create_text(
            self._width / 2, self._height / 2, text=text, font=self._font, fill=self._fg,
        )

        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        if self._stretch:
            self.bind("<Configure>", self._on_configure)

    def _redraw(self, width: int, height: int) -> None:
        self.coords(self._shape, rounded_rect_points(1, 1, width - 1, height - 1, self._radius))
        self.coords(self._label, width / 2, height / 2)

    def _on_configure(self, event) -> None:
        self._width, self._height = event.width, event.height
        self._redraw(self._width, self._height)

    def _on_press(self, _event) -> None:
        self.itemconfig(self._shape, fill=self._pressed_bg)

    def _on_release(self, event) -> None:
        self.itemconfig(self._shape, fill=self._bg)
        # Fire whenever this button received the press -- Tkinter's
        # implicit pointer grab guarantees the release is delivered to
        # the same widget that got the ButtonPress, so we don't re-check
        # coordinates. We used to require the release to land back inside
        # the button (a mouse "drag off to cancel" nicety), but on a
        # touchscreen small finger drift between touch-down and touch-up
        # made that silently swallow real taps -- worst on small buttons
        # like the PIN keypad.
        if self._command:
            self._command()

    def set_text(self, text: str) -> None:
        self.itemconfig(self._label, text=text)

    def set_colors(self, bg: str | None = None, fg: str | None = None) -> None:
        if bg is not None:
            self._bg = bg
            self._pressed_bg = shade(bg, -22)
            self.itemconfig(self._shape, fill=self._bg)
        if fg is not None:
            self._fg = fg
            self.itemconfig(self._label, fill=self._fg)


class RoundedPanel(tk.Frame):
    """A rounded-corner container: draws a rounded rect on a canvas and
    embeds a plain content Frame (`.body`) on top of it, so callers can
    pack/grid ordinary widgets inside without worrying about the canvas.
    Used for the "card" panels (Home's feedback log, Terminal's output
    log) so they read as distinct, layered surfaces rather than flat
    rectangles butted against the background.
    """

    def __init__(self, parent, bg: str | None = None, parent_bg: str | None = None,
                 radius: int = 14, **kwargs):
        self._bg = bg if bg is not None else theme.current.surface0
        parent_bg = parent_bg if parent_bg is not None else _infer_bg(parent)
        self._radius = radius
        super().__init__(parent, bg=parent_bg, **kwargs)

        self.canvas = tk.Canvas(self, bg=parent_bg, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self._shape = self.canvas.create_polygon(
            rounded_rect_points(0, 0, 1, 1, radius), smooth=True, fill=self._bg, outline="",
        )
        self.body = tk.Frame(self.canvas, bg=self._bg)
        self._window = self.canvas.create_window(0, 0, window=self.body, anchor="nw")
        self.canvas.bind("<Configure>", self._on_configure)

    def _on_configure(self, event) -> None:
        width, height = max(event.width, 1), max(event.height, 1)
        self.canvas.coords(self._shape, rounded_rect_points(1, 1, width - 1, height - 1, self._radius))
        self.canvas.itemconfig(self._window, width=width, height=height)


def _infer_bg(widget) -> str:
    try:
        return widget.cget("bg")
    except tk.TclError:
        return theme.current.base


def _measure_text(parent, text: str, font: tuple) -> tuple[int, int]:
    probe = tk.Label(parent, text=text, font=font)
    probe.update_idletasks()
    size = (probe.winfo_reqwidth(), probe.winfo_reqheight())
    probe.destroy()
    return size
