import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import theme


def test_all_expected_flavors_present():
    assert set(theme.FLAVORS) == {"mocha", "macchiato", "frappe", "latte", "nord"}


def test_nord_matches_requested_accent_colors():
    nord = theme.FLAVORS["nord"]
    assert nord.base == "#2e3440"
    assert nord.surface0 == "#3b4252"
    assert nord.text == "#eceff4"
    assert nord.mauve == "#b48ead"
    assert nord.blue == "#81a1c1"
    assert nord.green == "#a3be8c"
    assert nord.red == "#bf616a"
    assert nord.yellow == "#ebcb8b"
    assert nord.teal == "#88c0d0"


def test_set_flavor_switches_current_and_rejects_unknown():
    try:
        assert theme.set_flavor("latte") is True
        assert theme.current.name == "latte"
        assert theme.set_flavor("does-not-exist") is False
        assert theme.current.name == "latte"  # unchanged on failure
    finally:
        theme.set_flavor("mocha")  # restore default so other tests aren't affected


def test_shade_lightens_and_darkens():
    assert theme.shade("#808080", 16) == "#909090"
    assert theme.shade("#808080", -16) == "#707070"


def test_shade_clamps_at_bounds():
    assert theme.shade("#ffffff", 50) == "#ffffff"
    assert theme.shade("#000000", -50) == "#000000"
