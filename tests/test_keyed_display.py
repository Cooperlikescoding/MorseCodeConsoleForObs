import sys
import tkinter as tk
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ui.keyed_display import KeyedTextDisplay


def test_removes_last_word_only():
    assert KeyedTextDisplay._without_last_word("SOS HI MARS") == "SOS HI"


def test_trailing_space_before_call_is_ignored():
    assert KeyedTextDisplay._without_last_word("SOS HI MARS ") == "SOS HI"


def test_single_word_becomes_empty():
    assert KeyedTextDisplay._without_last_word("SOS") == ""


def test_empty_text_stays_empty():
    assert KeyedTextDisplay._without_last_word("") == ""


def test_double_space_does_not_leave_stray_space():
    assert KeyedTextDisplay._without_last_word("SOS  HI") == "SOS"


def test_in_progress_letters_with_no_space_are_treated_as_one_word():
    # mid-word mis-keying with no completed word boundary yet -> clears all
    assert KeyedTextDisplay._without_last_word("SHEE") == ""


@pytest.fixture
def tk_root():
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("no display available")
    root.withdraw()
    yield root
    root.destroy()


def test_is_not_a_text_widget(tk_root):
    # Regression: it used to be a tk.Text, whose I-beam cursor / focus
    # grabbing interfered with touch taps on nearby buttons.
    display = KeyedTextDisplay(tk_root)
    assert not isinstance(display, tk.Text)
    assert isinstance(display, tk.Label)
    assert str(display.cget("takefocus")) in ("0", "")


def test_append_and_delete_last_word(tk_root):
    display = KeyedTextDisplay(tk_root)
    display.append("SOS")
    display.append(" ")
    display.append("HI")
    assert display._text == "SOS HI"
    display.delete_last_word()
    assert display._text == "SOS"
    display.clear()
    assert display._text == ""
