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
