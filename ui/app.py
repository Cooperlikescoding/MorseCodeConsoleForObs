"""Main application window.

Owns the hardware-facing singletons (tone output, key input, decoder)
and routes their events to whichever screen is currently visible. The
Home screen (free practice) and Learn screen (guided A-Z mode) are both
open to everyone; the Terminal screen is only reachable through the PIN
dialog.
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
import time
import tkinter as tk
from typing import Callable

import config
import theme
from audio import create_tone_output
from config import Settings, hash_pin, settings
from decoder import MorseDecoder
from display_control import set_backlight_brightness
from key_input import create_key_input
from logging_setup import get_logger
from ui.boot import BootScreen
from ui.home import HomeScreen
from ui.learn import LearnScreen
from ui.pin_dialog import PinDialog
from ui.terminal import TerminalScreen

_log = get_logger("app")

POLL_INTERVAL_MS = 30
KEY_TEST_TONE_MS = 350


class MorseApp(tk.Tk):
    def __init__(self):
        super().__init__()
        theme.set_flavor(settings.theme_name)  # restore last-saved palette before building anything
        self.title("Morse Code Practice Console")
        self.configure(bg=theme.current.base)
        # Always set a sane windowed geometry first -- on top of being the
        # non-fullscreen size, it's also what Tkinter falls back to if
        # fullscreen is toggled off (e.g. via Escape during development),
        # instead of shrinking to whatever the smallest widget layout fits.
        self._is_fullscreen = False
        self.geometry(settings.window_size)
        if settings.fullscreen:
            self._apply_fullscreen(True)

        self._session_start = self._now()
        self._stats = {"letters_decoded": 0, "letters_unrecognized": 0, "words_completed": 0}
        self._key_observers: list[tuple[Callable[[], None], Callable[[], None]]] = []

        self.tone = create_tone_output()
        self.decoder = MorseDecoder(
            settings,
            on_symbol=self._on_symbol,
            on_letter=self._on_decoded_letter,
            on_word_space=self._on_decoded_word_space,
        )

        self._build_screens()
        self._switch_to(self.boot)  # one-time skippable boot log, then falls through to Home
        self._apply_brightness(settings.brightness_percent)

        self.key_input = create_key_input(tk_widget=self)
        self.key_input.bind(self._on_key_press, self._on_key_release)
        self.key_input.start()
        self._poll_decoder()

        # Escape toggles fullscreen -- handy for development; the real
        # kiosk can leave this bound since kids have no keyboard to press it.
        self.bind("<Escape>", lambda e: self._toggle_fullscreen())
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_screens(self) -> None:
        """(Re)builds the Home/Terminal screens from scratch. Safe to call
        again later -- e.g. `rebuild_ui()` calls this after a theme change,
        since Tkinter widgets don't recolor themselves and the simplest
        correct way to re-skin everything is to tear it down and rebuild
        it reading the new palette.
        """
        if hasattr(self, "_screen_container"):
            self._screen_container.destroy()

        self._screen_container = tk.Frame(self, bg=theme.current.base)
        self._screen_container.pack(fill="both", expand=True)
        self._screen_container.grid_rowconfigure(0, weight=1)
        self._screen_container.grid_columnconfigure(0, weight=1)

        self.home = HomeScreen(
            self._screen_container, tone=self.tone,
            on_open_terminal=self._request_terminal_access, on_open_learn=self.show_learn,
        )
        self.terminal = TerminalScreen(self._screen_container, app=self, on_exit=self.show_home)
        self.learn = LearnScreen(self._screen_container, tone=self.tone, on_exit=self.show_home)
        self.boot = BootScreen(self._screen_container, on_done=self.show_home)
        for screen in (self.home, self.terminal, self.learn, self.boot):
            screen.grid(row=0, column=0, sticky="nsew")

        self._active_screen = self.home

    def rebuild_ui(self) -> None:
        self.configure(bg=theme.current.base)
        self._key_observers.clear()  # any pending `test key` observers belong to the old (destroyed) terminal
        self._build_screens()

    def set_theme(self, name: str) -> bool:
        """Switch the active Catppuccin/Nord flavor and rebuild the UI to
        match. Returns False (no-op) for an unrecognized flavor name.
        """
        if not theme.set_flavor(name):
            return False
        settings.theme_name = theme.current.name
        self.persist_settings()
        was_on_terminal = self._active_screen is self.terminal
        was_on_learn = self._active_screen is self.learn
        self.rebuild_ui()
        if was_on_terminal:
            self.show_terminal()
            self.terminal.show_message(f"Theme set to {name}", "success")
        elif was_on_learn:
            self.show_learn()
        else:
            self.show_home()
        return True

    @staticmethod
    def persist_settings() -> None:
        """Save the adjustable settings to disk so they survive a restart."""
        config.save_settings()

    def _switch_to(self, screen) -> None:
        self.decoder.reset()
        if hasattr(self._active_screen, "leave"):
            self._active_screen.leave()
        self._active_screen = screen
        screen.tkraise()
        if hasattr(screen, "enter"):
            screen.enter()

    def show_home(self) -> None:
        self._switch_to(self.home)

    def show_terminal(self) -> None:
        self._switch_to(self.terminal)

    def show_learn(self) -> None:
        self._switch_to(self.learn)

    def _request_terminal_access(self) -> None:
        PinDialog(self, on_success=self.show_terminal)

    @staticmethod
    def _now() -> float:
        return time.monotonic()

    def now(self) -> float:
        """Public alias used by TerminalScreen for its idle-lock clock."""
        return self._now()

    def _on_key_press(self) -> None:
        self.tone.start()
        self.decoder.key_down(self._now())
        self._active_screen.on_key_down()
        for on_press, _ in self._key_observers:
            on_press()

    def _on_key_release(self) -> None:
        self.tone.stop()
        self.decoder.key_up(self._now())
        self._active_screen.on_key_up()
        for _, on_release in self._key_observers:
            on_release()

    def _poll_decoder(self) -> None:
        self.decoder.poll(self._now())
        self.after(POLL_INTERVAL_MS, self._poll_decoder)

    def _on_symbol(self, symbol: str) -> None:
        pass  # reserved for a future "keying in progress" indicator

    def _on_decoded_letter(self, letter: str | None, pattern: str) -> None:
        if letter:
            self._stats["letters_decoded"] += 1
        else:
            self._stats["letters_unrecognized"] += 1
        self._active_screen.on_decoded_letter(letter, pattern)

    def _on_decoded_word_space(self) -> None:
        self._stats["words_completed"] += 1
        self._active_screen.on_decoded_word_space()

    def _toggle_fullscreen(self) -> None:
        self._apply_fullscreen(not self._is_fullscreen)

    def set_fullscreen(self, value: bool) -> None:
        """Dev convenience only -- deliberately not persisted (see
        config.PERSISTED_FIELDS) so the kiosk always boots fullscreen."""
        self._apply_fullscreen(value)

    def _apply_fullscreen(self, value: bool) -> None:
        """Uses overrideredirect + explicit screen-size geometry rather
        than the `-fullscreen` window attribute. `-fullscreen` asks a
        window manager to honor an EWMH fullscreen hint -- on a bare
        kiosk X session with no (or a minimal) window manager, that
        request is never actually processed, so runtime toggling did
        nothing even though the console *looked* fullscreen at boot
        (it's just borderless and sized to match the screen already).
        This approach doesn't depend on a window manager at all.
        """
        self._is_fullscreen = value
        self.withdraw()  # avoid a visible flicker while changing decorations
        self.overrideredirect(value)
        if value:
            width, height = self.winfo_screenwidth(), self.winfo_screenheight()
            self.geometry(f"{width}x{height}+0+0")
        else:
            self.geometry(settings.window_size)
        self.deiconify()
        self.update_idletasks()

    def on_close(self) -> None:
        self.key_input.stop()
        self.destroy()

    # --- settings/admin actions, invoked from the terminal's commands ---

    def set_wpm(self, n: int) -> None:
        settings.wpm = n
        self.home.refresh_wpm_label()
        self.persist_settings()

    def set_tone_hz(self, hz: float) -> None:
        settings.tone_hz = hz
        self.tone.set_frequency(hz)
        self.persist_settings()

    def set_tolerance_percent(self, n: int) -> None:
        settings.tolerance_percent = n
        self.persist_settings()

    def change_pin(self, new_pin: str) -> None:
        """Set a new admin PIN, remembering the old one so `pin undo` can
        toggle back. Only the hashes are stored, never the plaintext."""
        settings.previous_admin_pin_hash = settings.admin_pin_hash
        settings.admin_pin_hash = hash_pin(new_pin)
        self.persist_settings()

    def undo_pin(self) -> bool:
        """Swap the current and previous PIN hashes (so undo is itself
        undoable). Returns False if there's no previous PIN recorded."""
        if not settings.previous_admin_pin_hash:
            return False
        settings.admin_pin_hash, settings.previous_admin_pin_hash = (
            settings.previous_admin_pin_hash, settings.admin_pin_hash,
        )
        self.persist_settings()
        return True

    def set_brightness_percent(self, n: int) -> bool:
        settings.brightness_percent = n
        applied = self._apply_brightness(n)
        self.persist_settings()
        return applied

    @staticmethod
    def _apply_brightness(percent: int) -> bool:
        return set_backlight_brightness(percent)

    def reset_adjustable_settings(self) -> None:
        defaults = Settings()
        settings.wpm = defaults.wpm
        settings.tone_hz = defaults.tone_hz
        settings.tolerance_percent = defaults.tolerance_percent
        settings.brightness_percent = defaults.brightness_percent
        self.tone.set_frequency(settings.tone_hz)
        self._apply_brightness(settings.brightness_percent)
        self.home.refresh_wpm_label()
        self.persist_settings()

    def get_stats(self) -> dict:
        return {**self._stats, "uptime_seconds": self._now() - self._session_start}

    def run_buzzer_test(self) -> None:
        self.tone.start()
        self.after(KEY_TEST_TONE_MS, self.tone.stop)

    def start_key_test(self, duration_s: float, on_event: Callable[[str], None]) -> None:
        observer = (lambda: on_event("KEY DOWN"), lambda: on_event("KEY UP"))
        self._key_observers.append(observer)

        def remove():
            if observer in self._key_observers:
                self._key_observers.remove(observer)

        self.after(int(duration_s * 1000), remove)

    def wait_for_key_press(self, timeout_s: float, on_result: Callable[[bool], None]) -> None:
        """Call `on_result(True)` the next time the key is pressed within
        `timeout_s`, or `on_result(False)` if the timeout elapses first.
        Used by the self-test and calibration flows to wait on a real
        press without blocking the UI thread."""
        state = {"done": False}

        def finish(success: bool) -> None:
            if state["done"]:
                return
            state["done"] = True
            if observer in self._key_observers:
                self._key_observers.remove(observer)
            on_result(success)

        observer = (lambda: finish(True), lambda: None)
        self._key_observers.append(observer)
        self.after(int(timeout_s * 1000), lambda: finish(False))

    def collect_key_durations(self, count: int, timeout_s: float,
                               on_done: Callable[[list[float] | None], None]) -> None:
        """Collect `count` press+release durations from the physical key,
        calling `on_done(durations)` once that many are gathered, or
        `on_done(None)` if `timeout_s` elapses first. Used by `calibrate`."""
        durations: list[float] = []
        state = {"press_time": None, "done": False}

        def finish(result: list[float] | None) -> None:
            if state["done"]:
                return
            state["done"] = True
            if observer in self._key_observers:
                self._key_observers.remove(observer)
            on_done(result)

        def on_press() -> None:
            state["press_time"] = self._now()

        def on_release() -> None:
            if state["press_time"] is None:
                return
            durations.append(self._now() - state["press_time"])
            state["press_time"] = None
            if len(durations) >= count:
                finish(durations)

        observer = (on_press, on_release)
        self._key_observers.append(observer)
        self.after(int(timeout_s * 1000), lambda: finish(None))

    def play_error_tone(self, ms: int = 500) -> None:
        """A distinct low-pitched beep for self-test failures -- audible
        even if the screen isn't being watched."""
        original_hz = settings.tone_hz
        self.tone.set_frequency(220.0)
        self.tone.start()

        def restore():
            self.tone.stop()
            self.tone.set_frequency(original_hz)

        self.after(ms, restore)

    def shutdown_system(self) -> None:
        self.after(500, self._do_shutdown)

    @staticmethod
    def _do_shutdown() -> None:
        if platform.system() == "Linux":
            subprocess.run(["sudo", "shutdown", "-h", "now"])
        else:
            _log.info("shutdown requested (no-op outside Linux)")

    def restart_system(self) -> None:
        self.after(500, self._do_restart)

    def _do_restart(self) -> None:
        """Restart the console application itself (not the whole OS) by
        re-exec'ing the same Python process. Release hardware first --
        os.execv replaces the process image immediately, without running
        normal Python cleanup, so a still-claimed GPIO pin (the buzzer)
        would make the new process fail to start."""
        _log.info("restarting app")
        self.key_input.stop()
        self.tone.close()
        os.execv(sys.executable, [sys.executable] + sys.argv)

    @staticmethod
    def launch_kitty() -> bool:
        """Launch a real Kitty terminal (Catppuccin Mocha colors) for
        genuine troubleshooting -- Linux only."""
        if platform.system() != "Linux":
            return False
        try:
            subprocess.Popen([
                "kitty",
                "-o", "background=#1e1e2e", "-o", "foreground=#cdd6f4",
                "-o", "cursor=#f5e0dc", "-o", "selection_background=#585b70",
            ])
            return True
        except OSError as exc:
            _log.warning("could not launch kitty: %s", exc)
            return False

    @staticmethod
    def launch_htop() -> bool:
        """Launch real htop in a terminal emulator -- Linux only. Prefers
        kitty (themed to match); falls back to xterm if kitty isn't
        installed."""
        if platform.system() != "Linux":
            return False
        try:
            subprocess.Popen([
                "kitty", "-o", "background=#1e1e2e", "-o", "foreground=#cdd6f4", "htop",
            ])
            return True
        except OSError:
            pass
        try:
            subprocess.Popen(["xterm", "-e", "htop"])
            return True
        except OSError as exc:
            _log.warning("could not launch htop: %s", exc)
            return False
