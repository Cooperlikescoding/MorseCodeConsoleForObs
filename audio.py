"""Tone output abstraction.

Mirrors key_input.py's KeyInput split: the rest of the app only ever
talks to the `ToneOutput` interface ("start the tone", "stop it", "set
its pitch"). Two backends implement it:

- `PygameToneOutput`: a software square-wave tone through the default
  audio device, for a dev machine. Square, not sine, so it previews
  what the real buzzer actually sounds like -- a passive piezo buzzer
  driven by GPIO PWM (as `BuzzerToneOutput` does) produces a square
  wave, not a smooth sine.
- `BuzzerToneOutput`: a real passive piezo buzzer on GPIO 18, driven by
  PWM via gpiozero.TonalBuzzer, for the Raspberry Pi.

`create_tone_output()` picks the right one from config.settings, using
the same hardware-backend resolution as key_input.create_key_input().
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np
import pygame

from logging_setup import get_logger

_log = get_logger("audio")


class ToneOutput(ABC):
    @abstractmethod
    def start(self) -> None:
        """Begin the tone. Safe to call repeatedly while already playing."""

    @abstractmethod
    def stop(self) -> None:
        """Stop the tone."""

    @abstractmethod
    def set_frequency(self, hz: float) -> None:
        """Change the tone's pitch, taking effect immediately if playing."""

    def close(self) -> None:
        """Release any exclusively-held hardware (e.g. the buzzer's GPIO
        claim) before the process exits or re-execs itself -- important
        for `restart`, which replaces the process image via os.execv and
        so never runs normal Python object cleanup. Default no-op; only
        `BuzzerToneOutput` needs to override this."""
        self.stop()


class PygameToneOutput(ToneOutput):
    """If no audio device is available (missing sound card, headless test
    environment), silently becomes a no-op instead of crashing the whole
    console -- keying still works, it just won't beep.
    """

    def __init__(self, frequency: float = 650.0, sample_rate: int = 44100,
                 volume: float = 0.5, fadeout_ms: int = 15):
        self._frequency = frequency
        self._sample_rate = sample_rate
        self._volume = volume
        self._fadeout_ms = fadeout_ms
        self._enabled = True
        self._sound = None
        self._channel: pygame.mixer.Channel | None = None
        self._playing = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=sample_rate, size=-16, channels=1)
            self._rebuild()
        except Exception as exc:  # pygame.error, or a mixer/array mismatch (see below)
            self._enabled = False
            _log.warning("no sound device available, running silently: %s", exc)

    def _rebuild(self) -> None:
        self._sound = self._build_tone(self._frequency, self._sample_rate, self._volume)

    @staticmethod
    def _build_tone(frequency: float, sample_rate: int, volume: float) -> pygame.mixer.Sound:
        # Round to a whole number of cycles close to 40ms so the buffer
        # loops seamlessly (a full cycle ends back at the same phase).
        cycles = max(1, round(frequency * 0.04))
        duration = cycles / frequency
        n_samples = int(sample_rate * duration)
        t = np.linspace(0, duration, n_samples, endpoint=False)
        # Square wave (sign of the sine), matching the real passive
        # buzzer's PWM-driven sound rather than a smooth sine tone.
        waveform = np.sign(np.sin(2 * np.pi * frequency * t))
        amplitude = int(max(0.0, min(1.0, volume)) * 32767)
        samples = (waveform * amplitude).astype(np.int16)

        # The actual mixer may have ignored our requested channel count
        # (e.g. the system default output is stereo-only) -- match
        # whatever it actually opened with rather than assuming mono.
        init = pygame.mixer.get_init()
        channels = init[2] if init else 1
        if channels > 1:
            samples = np.repeat(samples.reshape(-1, 1), channels, axis=1)
        return pygame.sndarray.make_sound(samples)

    def start(self) -> None:
        if not self._enabled:
            return
        if self._channel is None or not self._channel.get_busy():
            self._channel = self._sound.play(loops=-1)
        self._playing = True

    def stop(self) -> None:
        if not self._enabled:
            return
        if self._channel is not None:
            self._channel.fadeout(self._fadeout_ms)
            self._channel = None
        self._playing = False

    def set_frequency(self, hz: float) -> None:
        self._frequency = hz
        if not self._enabled:
            return
        self._rebuild()
        if self._playing:
            self.start()  # swap the looping sound to the new pitch


class BuzzerToneOutput(ToneOutput):
    """Passive piezo buzzer on a GPIO pin, driven by PWM via gpiozero's
    TonalBuzzer. Degrades to a silent no-op if the GPIO hardware isn't
    available (e.g. permissions issue, wrong pin factory).
    """

    def __init__(self, pin: int = 18, frequency: float = 650.0):
        self._frequency = frequency
        self._playing = False
        self._buzzer = None
        self._gpio_tone_cls = None
        try:
            from gpiozero import TonalBuzzer
            from gpiozero.tones import Tone as GpioTone
            self._buzzer = TonalBuzzer(pin)
            self._gpio_tone_cls = GpioTone
        except Exception as exc:  # gpiozero raises its own error hierarchy
            _log.warning("buzzer unavailable on GPIO %s, running silently: %s", pin, exc)

    def start(self) -> None:
        if self._buzzer is None:
            return
        self._buzzer.play(self._gpio_tone_cls(frequency=self._frequency))
        self._playing = True

    def stop(self) -> None:
        if self._buzzer is None:
            return
        self._buzzer.stop()
        self._playing = False

    def set_frequency(self, hz: float) -> None:
        self._frequency = hz
        if self._playing:
            self.start()  # re-trigger at the new pitch

    def close(self) -> None:
        self.stop()
        if self._buzzer is not None:
            self._buzzer.close()
            self._buzzer = None


def create_tone_output() -> ToneOutput:
    from config import settings

    backend = settings.resolve_backend()
    if backend == "gpio":
        return BuzzerToneOutput(settings.buzzer_pin, settings.tone_hz)
    return PygameToneOutput(settings.tone_hz, settings.sample_rate, settings.volume)


def schedule_pattern_playback(widget, tone: ToneOutput, pattern: str,
                               unit_seconds: float, on_symbol=None, on_done=None) -> None:
    """Play a dot/dash pattern (e.g. '-.-.') audibly using Tk's event loop
    for timing, so nothing blocks the UI thread.

    on_symbol(index) is called (if given) as each symbol starts playing,
    useful for highlighting the dot/dash being sounded.
    on_done() is called once the whole pattern has finished.
    """
    dot = unit_seconds
    dash = unit_seconds * 3
    intra_gap = unit_seconds

    def play_symbol(index: int) -> None:
        if index >= len(pattern):
            if on_done:
                on_done()
            return
        symbol = pattern[index]
        length = dot if symbol == "." else dash
        if on_symbol:
            on_symbol(index)
        tone.start()
        widget.after(int(length * 1000), lambda: end_symbol(index))

    def end_symbol(index: int) -> None:
        tone.stop()
        widget.after(int(intra_gap * 1000), lambda: play_symbol(index + 1))

    play_symbol(0)


def schedule_message_playback(widget, tone: ToneOutput, text: str, unit_seconds: float,
                               on_letter=None, on_done=None) -> None:
    """Play a whole word/phrase audibly, letter by letter with standard
    inter-letter (3 units) and inter-word (7 units) gaps -- the reverse
    of decoding. Characters with no Morse mapping are skipped silently.
    Used by the terminal's `send <word>` command.

    on_letter(char) is called as each letter starts playing.
    on_done() is called once the whole message has finished.
    """
    from morse_code import CHAR_TO_MORSE

    letter_gap = unit_seconds * 3
    word_gap = unit_seconds * 7
    words = text.upper().split()

    def play_word(word_index: int) -> None:
        if word_index >= len(words):
            if on_done:
                on_done()
            return
        chars = [c for c in words[word_index] if c in CHAR_TO_MORSE]
        play_char(word_index, chars, 0)

    def play_char(word_index: int, chars: list[str], char_index: int) -> None:
        if char_index >= len(chars):
            widget.after(int(word_gap * 1000), lambda: play_word(word_index + 1))
            return
        char = chars[char_index]
        if on_letter:
            on_letter(char)

        def next_char() -> None:
            if char_index + 1 < len(chars):
                widget.after(int(letter_gap * 1000), lambda: play_char(word_index, chars, char_index + 1))
            else:
                play_char(word_index, chars, char_index + 1)  # falls through to the word-gap branch

        schedule_pattern_playback(widget, tone, CHAR_TO_MORSE[char], unit_seconds, on_done=next_char)

    play_word(0)
