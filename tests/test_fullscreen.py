import sys
import tkinter as tk
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_fullscreen_toggle_uses_overrideredirect_not_wm_attribute():
    # Regression: `wm attributes -fullscreen` depends on a window manager
    # to honor an EWMH hint, which a bare kiosk X session may not have --
    # overrideredirect + explicit screen-size geometry doesn't need one.
    # Both directions are checked on a single app instance: creating a
    # second tk.Tk() root in the same process is unreliable even across
    # separate test functions, so this can't be split into two tests.
    from config import settings
    settings.fullscreen = False

    try:
        from ui.app import MorseApp
        app = MorseApp()
    except tk.TclError:
        pytest.skip("no display available")

    try:
        app.set_fullscreen(True)
        app.update()
        assert app._is_fullscreen is True
        assert bool(app.overrideredirect()) is True
        assert app.winfo_width() == app.winfo_screenwidth()
        assert app.winfo_height() == app.winfo_screenheight()

        app.set_fullscreen(False)
        app.update()
        assert app._is_fullscreen is False
        assert bool(app.overrideredirect()) is False
        expected_w, expected_h = (int(x) for x in settings.window_size.split("x"))
        assert app.winfo_width() == expected_w
        assert app.winfo_height() == expected_h
    finally:
        app.on_close()
