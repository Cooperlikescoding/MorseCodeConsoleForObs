"""The open-to-everyone practice screen. Letters only enter the feedback
log by keying the physical Morse key (or the dev spacebar stand-in) --
there is no on-screen keyboard here, that lives only in the members'
Terminal. A practice-word panel above shows a target word as tappable
letter chips for reference/learning (tap-to-learn); it never types.
"""

from __future__ import annotations

import tkinter as tk
from typing import Callable

import theme
from audio import ToneOutput
from config import settings
from theme import mono_font
from ui.keyed_display import UNRECOGNIZED_PLACEHOLDER, KeyedTextDisplay
from ui.key_indicator import KeyIndicator
from ui.practice_word import PracticeWordPanel
from ui.tap_to_learn import TapToLearnPopup
from ui.widgets import RoundedButton, RoundedPanel


class HomeScreen(tk.Frame):
    def __init__(self, parent, tone: ToneOutput, on_open_terminal: Callable[[], None],
                 on_open_learn: Callable[[], None], **kwargs):
        super().__init__(parent, bg=theme.current.base, **kwargs)
        self._tone = tone
        self._on_open_terminal = on_open_terminal
        self._on_open_learn = on_open_learn
        self._tap_to_learn_popup: TapToLearnPopup | None = None
        self._build()

    def _build(self) -> None:
        self.practice_panel = PracticeWordPanel(
            self, on_letter_tap=self._show_tap_to_learn, words=settings.practice_words,
        )
        self.practice_panel.pack(fill="x", padx=16, pady=(16, 8))

        row = tk.Frame(self, bg=theme.current.base)
        row.pack(fill="x", padx=16, pady=(0, 4))
        tk.Label(
            row, text="KEYED SO FAR", font=mono_font(11, "bold"),
            bg=theme.current.base, fg=theme.current.subtext,
        ).pack(side="left")
        self.key_indicator = KeyIndicator(row, height=28)
        self.key_indicator.pack(side="right")

        # A rounded, slightly-lighter "card" behind the feedback log gives
        # it visual depth against the base background.
        card = RoundedPanel(self, bg=theme.current.surface0)
        card.pack(fill="both", expand=True, padx=16, pady=(0, 8))
        self.display = KeyedTextDisplay(card.body, bg=theme.current.surface0)
        self.display.pack(fill="both", expand=True, padx=10, pady=10)

        footer = tk.Frame(self, bg=theme.current.base)
        footer.pack(fill="x", padx=16, pady=(0, 16))

        self.wpm_label = tk.Label(
            footer, text=f"Speed: {settings.wpm} WPM",
            bg=theme.current.base, fg=theme.current.subtext, font=mono_font(11),
        )
        self.wpm_label.pack(side="left")

        button_row = tk.Frame(footer, bg=theme.current.base)
        button_row.pack(side="right")

        # Plain text, deliberately no emoji: color-emoji glyphs (lock/book/
        # etc) need a color-emoji font that isn't installed on every Pi
        # image and render as a tofu box without one.
        terminal_btn = RoundedButton(
            button_row, text="Terminal (PIN)", font=mono_font(11, "bold"),
            command=self._on_open_terminal,
        )
        terminal_btn.pack(side="right")

        learn_btn = RoundedButton(
            button_row, text="Learn", font=mono_font(11, "bold"),
            command=self._on_open_learn,
        )
        learn_btn.pack(side="right", padx=(0, 8))

        delete_word_btn = RoundedButton(
            button_row, text="⌫ Word", font=mono_font(11), command=self.display.delete_last_word,
        )
        delete_word_btn.pack(side="right", padx=(0, 8))

        clear_btn = RoundedButton(button_row, text="Clear", font=mono_font(11), command=self.display.clear)
        clear_btn.pack(side="right", padx=(0, 8))

    def refresh_wpm_label(self) -> None:
        self.wpm_label.configure(text=f"Speed: {settings.wpm} WPM")

    def refresh_practice_words(self) -> None:
        self.practice_panel.set_words(settings.practice_words)

    # --- decoder callbacks (routed here by the app while this screen is active) ---

    def on_key_down(self) -> None:
        self.key_indicator.start_growing()

    def on_key_up(self) -> None:
        self.key_indicator.stop_growing()

    def on_decoded_letter(self, letter: str | None, pattern: str) -> None:
        text = letter if letter else UNRECOGNIZED_PLACEHOLDER
        self.display.append(text)
        self.display.flash_last(length=len(text))

    def on_decoded_word_space(self) -> None:
        self.display.append(" ")

    def _show_tap_to_learn(self, character: str) -> None:
        if self._tap_to_learn_popup is not None:
            self._tap_to_learn_popup.close()
        self._tap_to_learn_popup = TapToLearnPopup(self, self._tone, character)
