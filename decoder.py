"""Turns raw key press/release timing into dots, dashes, letters and word
spaces.

Design note: this class owns no timers or threads of its own. The caller
feeds it `key_down(now)` / `key_up(now)` on real key events, and calls
`poll(now)` periodically (e.g. every ~30ms from the UI's event loop) so it
can notice that a pause has gone on long enough to end a letter or a word.
That keeps the whole thing a pure function of timestamps -- easy to unit
test with fake clocks, and the only place real wall-clock time enters is
the caller.
"""

from __future__ import annotations

from typing import Callable, Optional

from morse_code import decode_symbol


class MorseDecoder:
    def __init__(self, settings,
                 on_symbol: Optional[Callable[[str], None]] = None,
                 on_letter: Optional[Callable[[Optional[str], str], None]] = None,
                 on_word_space: Optional[Callable[[], None]] = None):
        """
        settings: a config.Settings (or anything with the same timing
            fields) -- read live, so changing settings.wpm takes effect
            on the next event without recreating the decoder.
        on_symbol(symbol): called with '.' or '-' as each one is keyed.
        on_letter(letter, pattern): called when a letter's pause has
            elapsed. `letter` is None if the pattern didn't match any
            known character.
        on_word_space(): called once when a pause long enough to imply a
            word boundary has elapsed.
        """
        self._settings = settings
        self._on_symbol = on_symbol
        self._on_letter = on_letter
        self._on_word_space = on_word_space

        self._press_time: Optional[float] = None
        self._last_release_time: Optional[float] = None
        self._buffer = ""
        self._letter_closed = True
        self._word_gap_emitted = False

    def key_down(self, now: float) -> None:
        if self._press_time is not None:
            return  # already down; ignore a spurious duplicate press
        self._press_time = now

    def key_up(self, now: float) -> None:
        if self._press_time is None:
            return  # release with no matching press; ignore
        duration = now - self._press_time
        self._press_time = None
        if duration < self._settings.min_press_seconds:
            return  # too short to be a deliberate tap (switch bounce)

        unit = self._settings.unit_seconds
        symbol = "." if duration < unit * self._settings.dot_dash_ratio else "-"
        self._buffer += symbol
        self._letter_closed = False
        self._word_gap_emitted = False
        self._last_release_time = now
        if self._on_symbol:
            self._on_symbol(symbol)

    def poll(self, now: float) -> None:
        """Call periodically (not just on key events) so a long pause can
        end a letter/word even though nothing new has been keyed."""
        if self._press_time is not None:
            return  # key is currently held; nothing to time out yet
        if self._last_release_time is None:
            return
        unit = self._settings.unit_seconds
        gap = now - self._last_release_time

        if not self._letter_closed and gap >= unit * self._settings.letter_gap_ratio:
            self._emit_letter()

        if self._letter_closed and not self._word_gap_emitted and gap >= unit * self._settings.word_gap_ratio:
            self._word_gap_emitted = True
            if self._on_word_space:
                self._on_word_space()

    def flush(self) -> None:
        """Force-close whatever letter is in progress, e.g. when the user
        switches away from the keyer (screen change, admin PIN entry)."""
        if not self._letter_closed:
            self._emit_letter()

    def reset(self) -> None:
        self._press_time = None
        self._last_release_time = None
        self._buffer = ""
        self._letter_closed = True
        self._word_gap_emitted = False

    def _emit_letter(self) -> None:
        pattern = self._buffer
        self._buffer = ""
        self._letter_closed = True
        letter = decode_symbol(pattern)
        if self._on_letter:
            self._on_letter(letter, pattern)
