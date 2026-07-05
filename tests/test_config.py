import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import Settings, hash_pin


def test_unit_seconds_scales_with_wpm():
    s = Settings(wpm=12)
    assert abs(s.unit_seconds - 0.1) < 1e-9


def test_tolerance_percent_bounds_are_monotonic():
    lo = Settings(tolerance_percent=0)
    hi = Settings(tolerance_percent=100)
    assert lo.letter_gap_ratio < hi.letter_gap_ratio
    assert lo.word_gap_ratio < hi.word_gap_ratio
    assert lo.min_press_ratio < hi.min_press_ratio


def test_tolerance_percent_is_clamped_outside_0_100():
    over = Settings(tolerance_percent=500)
    under = Settings(tolerance_percent=-500)
    assert over.letter_gap_ratio == Settings(tolerance_percent=100).letter_gap_ratio
    assert under.letter_gap_ratio == Settings(tolerance_percent=0).letter_gap_ratio


def test_word_gap_is_wider_than_letter_gap():
    s = Settings()
    assert s.word_gap_ratio > s.letter_gap_ratio


def test_hash_pin_is_deterministic_and_distinct():
    assert hash_pin("7373") == hash_pin("7373")
    assert hash_pin("7373") != hash_pin("0000")


def test_default_admin_pin_hash_matches_default_pin():
    s = Settings()
    assert s.admin_pin_hash == hash_pin("7373")


def test_practice_words_default_is_a_fresh_list_per_instance():
    a, b = Settings(), Settings()
    a.practice_words.append("ZZZZ")
    assert "ZZZZ" not in b.practice_words
