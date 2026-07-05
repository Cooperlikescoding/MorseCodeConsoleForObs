"""Canvas-drawing helpers for rounded shapes -- used by the practice-word
letter chips and the tap-to-learn dot/dash mnemonics, since plain Tkinter
widgets have no native rounded-rect support.
"""

from __future__ import annotations


def rounded_rect_points(x0: float, y0: float, x1: float, y1: float, radius: float) -> list[float]:
    """Point list for `canvas.create_polygon(..., smooth=True)` that
    renders as a rounded rectangle (or a full capsule/stadium shape when
    `radius` is half the height).
    """
    radius = min(radius, (x1 - x0) / 2, (y1 - y0) / 2)
    return [
        x0 + radius, y0,
        x1 - radius, y0,
        x1, y0,
        x1, y0 + radius,
        x1, y1 - radius,
        x1, y1,
        x1 - radius, y1,
        x0 + radius, y1,
        x0, y1,
        x0, y1 - radius,
        x0, y0 + radius,
        x0, y0,
    ]
