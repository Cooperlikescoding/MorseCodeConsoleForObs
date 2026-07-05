import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from decoder import MorseDecoder


@dataclass
class FakeSettings:
    wpm: int = 60  # unit = 1.2/60 = 0.02s, easy round numbers for tests
    dot_dash_ratio: float = 2.0
    letter_gap_ratio: float = 2.0
    word_gap_ratio: float = 5.0
    min_press_seconds: float = 0.005

    @property
    def unit_seconds(self) -> float:
        return 1.2 / self.wpm


def make_decoder():
    settings = FakeSettings()
    symbols = []
    letters = []
    word_spaces = []
    decoder = MorseDecoder(
        settings,
        on_symbol=lambda s: symbols.append(s),
        on_letter=lambda letter, pattern: letters.append((letter, pattern)),
        on_word_space=lambda: word_spaces.append(True),
    )
    return decoder, settings, symbols, letters, word_spaces


def key_tap(decoder, start, duration):
    decoder.key_down(start)
    decoder.key_up(start + duration)
    return start + duration


def test_decodes_dot_and_dash_by_duration():
    decoder, settings, symbols, letters, word_spaces = make_decoder()
    unit = settings.unit_seconds

    t = 0.0
    t = key_tap(decoder, t, unit * 0.5)  # short press -> dot
    assert symbols == ["."]
    t += unit  # short inter-symbol gap, well under letter_gap
    t = key_tap(decoder, t, unit * 3)  # long press -> dash
    assert symbols == [".", "-"]


def test_full_letter_s_from_three_dots():
    decoder, settings, symbols, letters, word_spaces = make_decoder()
    unit = settings.unit_seconds

    t = 0.0
    for _ in range(3):
        t = key_tap(decoder, t, unit * 0.3)
        t += unit * 0.5  # gap between dots, shorter than letter gap

    assert letters == []  # not yet closed
    # advance past the letter-gap threshold without any new key event
    decoder.poll(t + unit * settings.letter_gap_ratio + 0.001)
    assert letters == [("S", "...")]


def test_word_space_after_letter_gap_and_longer_pause():
    decoder, settings, symbols, letters, word_spaces = make_decoder()
    unit = settings.unit_seconds

    t = key_tap(decoder, 0.0, unit * 0.3)  # single dot -> "E"
    letter_gap = unit * settings.letter_gap_ratio
    word_gap = unit * settings.word_gap_ratio

    decoder.poll(t + letter_gap + 0.001)
    assert letters == [("E", ".")]
    assert word_spaces == []  # letter closed, but not a word gap yet

    decoder.poll(t + word_gap + 0.001)
    assert word_spaces == [True]

    # word space should only fire once per pause, not on every poll
    decoder.poll(t + word_gap + 0.5)
    assert word_spaces == [True]


def test_unknown_pattern_reports_none():
    decoder, settings, symbols, letters, word_spaces = make_decoder()
    unit = settings.unit_seconds

    # 7 dots isn't a valid letter in the table
    t = 0.0
    for _ in range(7):
        t = key_tap(decoder, t, unit * 0.3)
        t += unit * 0.5
    decoder.poll(t + unit * settings.letter_gap_ratio + 0.001)
    assert letters == [(None, ".......")]


def test_tiny_bounce_is_ignored():
    decoder, settings, symbols, letters, word_spaces = make_decoder()
    bounce = settings.min_press_seconds * 0.5
    key_tap(decoder, 0.0, bounce)
    assert symbols == []


def test_flush_forces_incomplete_letter_closed():
    decoder, settings, symbols, letters, word_spaces = make_decoder()
    unit = settings.unit_seconds
    key_tap(decoder, 0.0, unit * 0.3)
    assert letters == []
    decoder.flush()
    assert letters == [("E", ".")]


def test_reset_clears_state():
    decoder, settings, symbols, letters, word_spaces = make_decoder()
    unit = settings.unit_seconds
    key_tap(decoder, 0.0, unit * 0.3)
    decoder.reset()
    decoder.flush()
    assert letters == []  # nothing pending after reset
