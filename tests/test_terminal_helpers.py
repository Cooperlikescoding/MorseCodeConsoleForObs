import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ui.terminal import _redact_for_echo


def test_redacts_pin_set_digits():
    # The current and new PINs must not survive into the echoed scrollback.
    out = _redact_for_echo("pin set 7373 4242")
    assert "7373" not in out
    assert "4242" not in out
    assert out.startswith("pin set ")


def test_redacts_pin_undo_digits():
    out = _redact_for_echo("pin undo 7373")
    assert "7373" not in out
    assert out == "pin undo " + "•" * 4


def test_keeps_non_pin_commands_untouched():
    assert _redact_for_echo("wpm 12") == "wpm 12"
    assert _redact_for_echo("theme nord") == "theme nord"
    assert _redact_for_echo("send HELLO") == "send HELLO"


def test_subcommand_words_are_preserved():
    # only digit-bearing args get masked; the 'set'/'undo' verbs stay
    assert _redact_for_echo("pin set").startswith("pin set")
    assert "set" in _redact_for_echo("pin set 1234 5678")


def test_motd_does_not_contain_the_ck_typo():
    # CQ = -.-. --.- ; a fixed typo previously mislabeled this as 'CK'.
    import ui.terminal as terminal_module
    assert not any("'CK'" in m for m in terminal_module.MOTD_MESSAGES)
    assert any("'CQ'" in m for m in terminal_module.MOTD_MESSAGES)


def test_output_drag_scroll_does_not_raise():
    # Regression: Text.scan_dragto() in this Tkinter binding doesn't accept
    # a `gain` keyword at all (it's hardcoded to 10x internally), so the
    # touch-drag-to-scroll handler must call the underlying Tcl widget
    # command directly instead of the Python wrapper.
    import tkinter as tk
    import pytest

    from config import settings

    settings.fullscreen = False

    try:
        from ui.app import MorseApp
        app = MorseApp()
    except tk.TclError:
        pytest.skip("no display available")

    try:
        for i in range(50):
            app.terminal._print(f"line {i}", "response")
        app.update()

        class FakeEvent:
            def __init__(self, x, y):
                self.x, self.y = x, y

        app.terminal._start_output_scroll(FakeEvent(50, 300))
        app.terminal._drag_output_scroll(FakeEvent(50, 500))
    finally:
        app.on_close()


def test_no_color_emoji_in_home_or_learn_button_labels():
    # Color-emoji glyphs (lock/book/confetti) render as a tofu box on
    # Pi images without a color-emoji font; only plain text should be used.
    for path in ("ui/home.py", "ui/learn.py"):
        text = open(path, encoding="utf-8").read()
        codepoints = [ord(c) for c in text if ord(c) >= 0x1F000]
        assert not codepoints, f"{path} still contains emoji: {codepoints}"
