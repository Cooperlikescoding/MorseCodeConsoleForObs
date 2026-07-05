import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from morse_code import CHAR_TO_MORSE, MORSE_TO_CHAR, decode_symbol, encode


def test_tables_are_reversible():
    for char, pattern in CHAR_TO_MORSE.items():
        assert MORSE_TO_CHAR[pattern] == char


def test_known_letters():
    assert CHAR_TO_MORSE["S"] == "..."
    assert CHAR_TO_MORSE["O"] == "---"
    assert CHAR_TO_MORSE["H"] == "...."
    assert CHAR_TO_MORSE["I"] == ".."


def test_decode_symbol():
    assert decode_symbol("...") == "S"
    assert decode_symbol("---") == "O"
    assert decode_symbol("xyz-not-morse") is None


def test_encode_word():
    assert encode("SOS") == "... --- ..."


def test_encode_sentence_with_word_gap():
    assert encode("HI OM") == ".... .. / --- --"
