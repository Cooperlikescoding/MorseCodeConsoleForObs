"""Members-only command-style terminal. Reached only through the PIN
gate in app.py -- this screen assumes it's already unlocked by the time
it's shown, and re-locks itself (back to Home) after a period of
inactivity or when told to.

Text is composed via the on-screen keyboard (the only place in the app
that has one) or by keying the physical Morse key -- both feed the same
input line. Anything that isn't a recognized command is treated as a
scripted chat message.
"""

from __future__ import annotations

import platform
import random
import time
import tkinter as tk
from typing import Callable

import theme
from audio import schedule_message_playback
from config import hash_pin, settings
from logging_setup import LOG_FILE
from chat_responses import get_response
from theme import mono_font
from ui.keyboard import OnScreenKeyboard
from ui.keyed_display import UNRECOGNIZED_PLACEHOLDER
from ui.widgets import RoundedButton, RoundedPanel

PROMPT_HOST = "sherwood@morse"
PROMPT_ARROW = "❯"


def _prompt(now_hhmm: str | None = None) -> str:
    """The shell prompt, with the current time tucked in just behind the
    arrow: 'sherwood@morse 14:30 ❯ '."""
    if now_hhmm is None:
        now_hhmm = time.strftime("%H:%M")
    return f"{PROMPT_HOST} {now_hhmm} {PROMPT_ARROW} "

# A tiny hand-built pixel font, just for the letters "MORSE" -- built
# programmatically rather than hand-drawn as one block of ASCII art so
# every row is guaranteed to line up (a hand-drawn attempt at this
# previously came out unreadable).
_BANNER_FONT: dict[str, list[str]] = {
    "M": ["#   #", "## ##", "# # #", "#   #", "#   #"],
    "O": [" ### ", "#   #", "#   #", "#   #", " ### "],
    "R": ["#### ", "#   #", "#### ", "#  # ", "#   #"],
    "S": [" ####", "#    ", " ### ", "    #", "#### "],
    "E": ["#####", "#    ", "#### ", "#    ", "#####"],
}


def _render_banner(word: str, gap: str = "  ") -> str:
    rows = ["" for _ in _BANNER_FONT[word[0]]]
    for i, letter in enumerate(word):
        glyph = _BANNER_FONT[letter]
        for r, line in enumerate(glyph):
            rows[r] += line + (gap if i != len(word) - 1 else "")
    return "\n".join(rows)


BANNER = _render_banner("MORSE")

NEOFETCH_LOGO = [
    "     /\\     ",
    "    /  \\    ",
    "   /----\\   ",
    "  /  ||  \\  ",
    " '   ||   ' ",
    "     ||     ",
    "    [==]    ",
    "    [==]    ",
    "   [====]   ",
]

SELFTEST_TIMEOUT_S = 8.0
CALIBRATE_TAP_COUNT = 5
CALIBRATE_TIMEOUT_S = 20.0

MOTD_MESSAGES = [
    "Tip: the buzzer likes to be heard, not seen.",
    "Remember: dits are short, dahs are long, patience is everything.",
    "73 de morse-shell -- best regards!",
    "Fun fact: SOS is '... --- ...' -- and it reads the same either way.",
    "A good operator sends as well as they receive.",
    "Tip: try 'calibrate' if the key feels too twitchy or too slow.",
    "88 to the family, 73 to the gang -- happy keying!",
    "CQ CQ CQ -- the airwaves are calling, is anybody listening?",
    "The best DX is the friend you make on the other end.",
    "Slow is smooth, smooth is fast. Key at your own pace.",
    "Old-timer's secret: everyone was once a beginner sending '?'.",
    "QRT? Never. There's always one more contact to make.",
    "Dah-di-dah-dit dah-dah-di-dah -- that's 'CQ', now you know!",
    "Static is just the universe saying hello. Key back.",
    "Fun fact: 'E' is a single dit -- the fastest letter to send.",
    "A steady fist beats a fast one. Rhythm is everything.",
    "Tip: tap a letter in the practice word to hear how it sounds.",
    "Real radios have knobs. This one has you. Go make some noise!",
    "Elmers welcome newcomers -- pass on what you learn.",
    "73 means 'best regards'. 88 means 'love and kisses'. Choose wisely!",
]

# Fictional process table for `ps`/`top` -- flavour only, not real stats
# (use `htop` for that). (pid, name, status, cpu%)
FAKE_PROCESSES = [
    (1, "morsed", "running", "0.3"),
    (2, "decoder.py", "running", "0.1"),
    (3, "tonegen", "sleeping", "0.0"),
    (4, "keywatch", "running", "0.2"),
    (5, "terminal-shell", "running", "1.2"),
]

HELP_TEXT = """\
wpm <n>        set keying speed in words per minute
tone <hz>      set tone/buzzer pitch in Hz
tol <n>        set decode tolerance 0-100 (higher = more forgiving)
bright <n>     set screen brightness 0-100 (Pi only)
theme <name>   switch palette: mocha/macchiato/frappe/latte/nord
fullscreen     enter fullscreen
unfullscreen   exit fullscreen (dev only)
test / selftest  run the power-on self-test (key then buzzer)
test key       watch physical key press/release events for 5s
test buzzer    sound the tone/buzzer briefly
calibrate      key a few dots to auto-tune wpm/tolerance to your key
pin set <current> <new>      change the terminal PIN
pin undo <current>           revert to the previous PIN
reset          reset wpm/tone/tolerance/brightness to defaults
stats          show session statistics
sysinfo        plain settings/system summary
neofetch       show a fun system/session summary
kitty          launch a real Kitty terminal (Linux only)
htop           launch real htop (Linux only)
logs [n]       show the last n lines of the console's log file
send <word>    play a word out in Morse through the buzzer
presetsave <n> save current wpm/tone/tolerance as a named preset
presetload <n> load a named preset
presetlist     list saved presets
word add <t>   add a practice word
word list      list practice words
word del <t>   remove a practice word
motd           show a random tip of the day
man <cmd>      show a manual page for a command
ps / top       list the console's own (fictional) processes
exit / lock    return to the game screen
shutdown       power off the console
restart        restart the console app itself (not the OS)
help           show this list\
"""

MAN_PAGES: dict[str, tuple[str, str]] = {
    "wpm": ("wpm <n>", "Set keying speed in words per minute (3-40). Affects all Morse timing."),
    "tone": ("tone <hz>", "Set the tone/buzzer pitch in Hz (200-2000)."),
    "tol": ("tol <n>", "Set decode tolerance 0-100. Higher is more forgiving of sloppy timing."),
    "bright": ("bright <n>", "Set touchscreen brightness 0-100. Raspberry Pi only."),
    "theme": ("theme <name>", "Switch the color palette: mocha, macchiato, frappe, latte, or nord."),
    "fullscreen": ("fullscreen", "Enter fullscreen mode."),
    "unfullscreen": ("unfullscreen", "Exit fullscreen mode. Development use only."),
    "test": ("test [key|buzzer]", "Run the power-on self-test, or test a single component."),
    "selftest": ("selftest", "Alias for 'test' with no arguments."),
    "calibrate": ("calibrate", "Key a few dots to auto-tune wpm and tolerance to your key's feel."),
    "pin": ("pin set <current> <new> | pin undo <current>",
            "Change the terminal PIN (3-8 digits), or revert to the previous one. "
            "Both require the current PIN. Only PIN hashes are stored, never the plaintext."),
    "reset": ("reset", "Reset wpm, tone, tolerance, and brightness to their defaults."),
    "stats": ("stats", "Show session statistics: uptime, letters decoded, words completed."),
    "sysinfo": ("sysinfo", "Show a plain-text settings/system summary."),
    "neofetch": ("neofetch", "Show a fun ASCII-art system/session summary."),
    "kitty": ("kitty", "Launch a real Kitty terminal, themed Catppuccin Mocha. Linux only."),
    "htop": ("htop", "Launch real htop to inspect CPU/memory/temperature. Linux only."),
    "logs": ("logs [n]", "Show the last n lines (default 20) of the console's log file."),
    "send": ("send <word>", "Play a word out audibly in Morse code through the buzzer."),
    "presetsave": ("presetsave <name>", "Save the current wpm/tone/tolerance as a named preset."),
    "presetload": ("presetload <name>", "Load a previously saved preset by name."),
    "presetlist": ("presetlist", "List all saved presets."),
    "word": ("word add|list|del <text>", "Manage the practice word bank shown on the Home screen."),
    "motd": ("motd", "Show a random message of the day (also shown automatically on login)."),
    "man": ("man <command>", "Show this manual page for a command."),
    "ps": ("ps", "List the console's own (fictional) processes, for flavour."),
    "top": ("top", "Like ps, styled like a live process monitor. Still just for flavour."),
    "exit": ("exit", "Return to the game screen (alias for 'lock')."),
    "lock": ("lock", "Return to the game screen, locking the terminal."),
    "shutdown": ("shutdown", "Power off the console. Linux only."),
    "restart": ("restart", "Restart the console app itself (not the OS)."),
    "help": ("help", "List all available commands."),
}


class CommandError(Exception):
    pass


def _parse_int(value: str, lo: int, hi: int, name: str) -> int:
    try:
        n = int(value)
    except ValueError:
        raise CommandError(f"'{value}' is not a whole number")
    if not (lo <= n <= hi):
        raise CommandError(f"{name} must be between {lo} and {hi}")
    return n


def _redact_for_echo(message: str) -> str:
    """Mask the arguments of a `pin` command before echoing it into the
    visible scrollback, so a PIN typed in the clear doesn't linger on
    screen. Any argument containing a digit becomes bullets."""
    parts = message.split()
    if not parts or parts[0].lower() != "pin":
        return message
    masked = [parts[0]] + [
        ("•" * len(p) if any(c.isdigit() for c in p) else p) for p in parts[1:]
    ]
    return " ".join(masked)


class TerminalScreen(tk.Frame):
    def __init__(self, parent, app, on_exit: Callable[[], None], **kwargs):
        super().__init__(parent, bg=theme.current.base, **kwargs)
        self._app = app
        self._on_exit = on_exit
        self._input_buffer = ""
        self._idle_after_id: str | None = None
        self._last_activity = 0.0
        self._build()

    def _build(self) -> None:
        # A weighted grid (rather than pack()'s all-or-nothing expand) so
        # the keyboard gets a deliberately smaller *proportion* of the
        # screen than the output log -- big, comfortable touch targets on
        # the Touch Display 2's 1280x720 panel, without the keyboard
        # dominating the screen the way an even 50/50 split would.
        self.grid_rowconfigure(0, weight=0)  # header
        self.grid_rowconfigure(1, weight=3)  # output log
        self.grid_rowconfigure(2, weight=0)  # input line
        self.grid_rowconfigure(3, weight=2)  # keyboard
        self.grid_columnconfigure(0, weight=1)

        header = tk.Frame(self, bg=theme.current.mantle)
        header.grid(row=0, column=0, sticky="nsew")
        tk.Label(
            header, text="MEMBERS TERMINAL", font=mono_font(14, "bold"),
            bg=theme.current.mantle, fg=theme.current.mauve,
        ).pack(side="left", padx=12, pady=8)
        lock_btn = RoundedButton(
            header, text="Lock", font=mono_font(11, "bold"), command=self._exit,
            parent_bg=theme.current.mantle,
        )
        lock_btn.pack(side="right", padx=12, pady=8)

        # A rounded, slightly-lighter "card" behind the output log gives it
        # depth against the base background, echoing the Home screen's
        # feedback log.
        output_card = RoundedPanel(self, bg=theme.current.mantle)
        output_card.grid(row=1, column=0, sticky="nsew", padx=12, pady=(6, 6))
        # takefocus=0 + arrow cursor keep this read-only log from grabbing
        # keyboard focus or showing a text I-beam -- on the touchscreen a
        # focus-grabbing Text widget interfered with taps landing on the
        # on-screen keyboard below it.
        # Two ways to scroll on the touchscreen (no mouse wheel): a wide,
        # always-visible scrollbar whose thumb is a big touch target, plus
        # finger drag-to-scroll on the log itself (bound below). The
        # scrollbar is the discoverable fallback; the drag is the natural
        # phone-like gesture.
        scrollbar = tk.Scrollbar(
            output_card.body, orient="vertical", width=26, bd=0, highlightthickness=0,
            troughcolor=theme.current.mantle, bg=theme.current.surface1,
            activebackground=theme.current.surface2,
        )
        scrollbar.pack(side="right", fill="y", padx=(0, 8), pady=8)

        self.output = tk.Text(
            output_card.body, bg=theme.current.mantle, fg=theme.current.text, font=mono_font(13),
            state="disabled", wrap="word", bd=0, highlightthickness=0,
            takefocus=0, cursor="arrow", yscrollcommand=scrollbar.set,
        )
        self.output.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        scrollbar.configure(command=self.output.yview)
        # Drag-to-scroll: a Text widget's default drag behavior is to
        # select text, not scroll. scan_mark/scan_dragto is Tkinter's
        # built-in "drag to pan the view" mechanism; returning "break"
        # stops the default select-drag binding from also firing.
        self.output.bind("<ButtonPress-1>", self._start_output_scroll)
        self.output.bind("<B1-Motion>", self._drag_output_scroll)
        self.output.tag_configure("command", foreground=theme.current.mauve)
        self.output.tag_configure("success", foreground=theme.current.green)
        self.output.tag_configure("error", foreground=theme.current.red)
        self.output.tag_configure("response", foreground=theme.current.text)
        self.output.tag_configure("info", foreground=theme.current.blue)
        self.output.tag_configure("banner", foreground=theme.current.mauve)
        self.output.tag_configure("neofetch", foreground=theme.current.teal)
        self.output.tag_configure("motd", foreground=theme.current.teal)

        input_row = tk.Frame(self, bg=theme.current.base)
        input_row.grid(row=2, column=0, sticky="ew", padx=12)
        self.prompt_var = tk.StringVar(value=_prompt())
        tk.Label(
            input_row, textvariable=self.prompt_var, font=mono_font(14, "bold"),
            bg=theme.current.base, fg=theme.current.mauve,
        ).pack(side="left")
        self.input_var = tk.StringVar(value="")
        tk.Label(
            input_row, textvariable=self.input_var, anchor="w", font=mono_font(14),
            bg=theme.current.base, fg=theme.current.text,
        ).pack(side="left", fill="x", expand=True)

        self.keyboard = OnScreenKeyboard(self, on_tap=self._on_tap, extra_keys=[("⏎ ENTER", "ENTER")])
        self.keyboard.grid(row=3, column=0, sticky="nsew", padx=12, pady=(6, 12))

    # --- lifecycle: called by app.py on screen switch ---

    def enter(self) -> None:
        self.reset_input()
        self._print(BANNER, "banner")
        self._print("Type 'help' for a list of commands.", "info")
        self._print(random.choice(MOTD_MESSAGES), "motd")
        self._start_idle_watch()

    def leave(self) -> None:
        self._stop_idle_watch()

    def show_message(self, text: str, kind: str = "response") -> None:
        """Print a line into the output log -- used by app.py to confirm
        an action (e.g. a theme switch) that happened outside a command
        the user typed directly into this screen."""
        self._print(text, kind)

    def _start_output_scroll(self, event) -> str:
        self.output.scan_mark(event.x, event.y)
        return "break"

    def _drag_output_scroll(self, event) -> str:
        # gain=1 for a natural 1:1 "drag the content with your finger"
        # feel -- Tk's default gain (10x) is tuned for fast canvas panning
        # and would feel wildly oversensitive for reading text. Python's
        # Text.scan_dragto() wrapper hardcodes the default gain and
        # doesn't expose it as an argument, so call the underlying Tcl
        # command directly (the Tk widget command *does* take a gain).
        self.output.tk.call(self.output._w, "scan", "dragto", event.x, event.y, 1)
        return "break"

    def reset_input(self) -> None:
        self._input_buffer = ""
        self.input_var.set("")

    # --- decoder callbacks (routed here by the app while this screen is active) ---

    def on_key_down(self) -> None:
        pass  # the live growing dit/dah indicator is a Home-screen-only touch

    def on_key_up(self) -> None:
        pass

    def on_decoded_letter(self, letter: str | None, pattern: str) -> None:
        self._touch_activity()
        self._input_buffer += letter if letter else UNRECOGNIZED_PLACEHOLDER
        if letter:
            self.keyboard.highlight(letter)
        self.input_var.set(self._input_buffer)

    def on_decoded_word_space(self) -> None:
        self._touch_activity()
        self._input_buffer += " "
        self.input_var.set(self._input_buffer)

    # --- on-screen keyboard handling ---

    def _on_tap(self, token: str) -> None:
        self._touch_activity()
        if token == "CLEAR":
            self._input_buffer = ""
        elif token == "SPACE":
            self._input_buffer += " "
        elif token == "BACKSPACE":
            self._input_buffer = self._input_buffer[:-1]
        elif token == "ENTER":
            self._submit()
            return
        else:
            self._input_buffer += token
        self.input_var.set(self._input_buffer)

    def _submit(self) -> None:
        message = self._input_buffer.strip()
        self.reset_input()
        if not message:
            return
        self._print(f"{_prompt()}{_redact_for_echo(message)}", "command")
        self._dispatch(message)

    # --- command dispatch ---

    def _dispatch(self, message: str) -> None:
        parts = message.split()
        cmd = parts[0].lower()
        args = parts[1:]
        handlers = {
            "wpm": self._cmd_wpm,
            "tone": self._cmd_tone,
            "tol": self._cmd_tol,
            "bright": self._cmd_bright,
            "theme": self._cmd_theme,
            "fullscreen": self._cmd_fullscreen,
            "unfullscreen": self._cmd_unfullscreen,
            "test": self._cmd_test,
            "selftest": self._cmd_selftest,
            "calibrate": self._cmd_calibrate,
            "pin": self._cmd_pin,
            "reset": self._cmd_reset,
            "stats": self._cmd_stats,
            "sysinfo": self._cmd_sysinfo,
            "neofetch": self._cmd_neofetch,
            "fetch": self._cmd_neofetch,
            "kitty": self._cmd_kitty,
            "htop": self._cmd_htop,
            "logs": self._cmd_logs,
            "send": self._cmd_send,
            "presetsave": self._cmd_presetsave,
            "presetload": self._cmd_presetload,
            "presetlist": self._cmd_presetlist,
            "word": self._cmd_word,
            "motd": self._cmd_motd,
            "man": self._cmd_man,
            "ps": self._cmd_ps,
            "top": self._cmd_top,
            "exit": self._cmd_lock,
            "lock": self._cmd_lock,
            "shutdown": self._cmd_shutdown,
            "restart": self._cmd_restart,
            "help": self._cmd_help,
        }
        handler = handlers.get(cmd)
        if handler is None:
            # Not a recognized command -- treat it as a scripted chat message.
            self._print(get_response(message), "response")
            return
        try:
            handler(args)
        except CommandError as exc:
            self._print(str(exc), "error")

    def _cmd_wpm(self, args: list[str]) -> None:
        if not args:
            raise CommandError("usage: wpm <3-40>")
        n = _parse_int(args[0], 3, 40, "wpm")
        self._app.set_wpm(n)
        self._print(f"WPM set to {n}", "success")

    def _cmd_tone(self, args: list[str]) -> None:
        if not args:
            raise CommandError("usage: tone <200-2000>")
        try:
            hz = float(args[0])
        except ValueError:
            raise CommandError(f"'{args[0]}' is not a number")
        if not (200 <= hz <= 2000):
            raise CommandError("tone must be between 200 and 2000 Hz")
        self._app.set_tone_hz(hz)
        self._print(f"Tone set to {hz:.0f} Hz", "success")

    def _cmd_tol(self, args: list[str]) -> None:
        if not args:
            raise CommandError("usage: tol <0-100>")
        n = _parse_int(args[0], 0, 100, "tolerance")
        self._app.set_tolerance_percent(n)
        self._print(f"Tolerance set to {n}", "success")

    def _cmd_bright(self, args: list[str]) -> None:
        if not args:
            raise CommandError("usage: bright <0-100>")
        n = _parse_int(args[0], 0, 100, "brightness")
        if self._app.set_brightness_percent(n):
            self._print(f"Brightness set to {n}%", "success")
        else:
            self._print("Brightness control is only available on the Pi's screen.", "error")

    def _cmd_theme(self, args: list[str]) -> None:
        if not args:
            raise CommandError(f"usage: theme <{'|'.join(theme.FLAVORS)}>")
        name = args[0].lower()
        # set_theme() rebuilds the whole UI (including this TerminalScreen
        # instance) on success -- do NOT touch `self` after it returns True.
        # On failure (unknown name) nothing is rebuilt, so it's safe to
        # raise normally and let the dispatcher print the error here.
        if not self._app.set_theme(name):
            raise CommandError(f"unknown theme '{name}' -- choices: {', '.join(theme.FLAVORS)}")

    def _cmd_fullscreen(self, args: list[str]) -> None:
        self._app.set_fullscreen(True)
        self._print("Fullscreen on.", "success")

    def _cmd_unfullscreen(self, args: list[str]) -> None:
        self._app.set_fullscreen(False)
        self._print("Fullscreen off (dev only -- always boots fullscreen).", "success")

    def _cmd_test(self, args: list[str]) -> None:
        if not args:
            self._cmd_selftest(args)
            return
        if args[0].lower() not in ("key", "buzzer"):
            raise CommandError("usage: test [key|buzzer]  (no argument runs the full self-test)")
        what = args[0].lower()
        if what == "key":
            self._print("Press and release the tactile button now (5s)...", "info")
            self._app.start_key_test(5.0, lambda evt: self._print(evt, "info"))
        else:
            self._app.run_buzzer_test()
            self._print("Buzzer test: short tone played.", "success")

    def _cmd_selftest(self, args: list[str]) -> None:
        self._print("=== SELF-TEST ===", "info")
        self._selftest_key_step(retried=False)

    def _selftest_key_step(self, retried: bool) -> None:
        self._print("Please press the tactile button.", "info")
        self._app.wait_for_key_press(SELFTEST_TIMEOUT_S, lambda ok: self._selftest_key_result(ok, retried))

    def _selftest_key_result(self, ok: bool, retried: bool) -> None:
        if ok:
            self._print("Tactile button detected.", "success")
            self._selftest_buzzer_step(retried=False)
            return
        if not retried:
            self._print("No response, trying again...", "info")
            self._selftest_key_step(retried=True)
            return
        self._print("Tactile button not detected. Check: button -> GPIO 17 (pin 11), GND (pin 9).", "error")
        self._app.play_error_tone()

    def _selftest_buzzer_step(self, retried: bool) -> None:
        self._print("Did you hear a tone? Press the tactile button if yes.", "info")
        self._app.tone.start()
        self._app.wait_for_key_press(SELFTEST_TIMEOUT_S, lambda ok: self._selftest_buzzer_result(ok, retried))

    def _selftest_buzzer_result(self, ok: bool, retried: bool) -> None:
        self._app.tone.stop()
        if ok:
            self._print("Self-test passed.", "success")
            return
        if not retried:
            self._print("No response, trying again...", "info")
            self._selftest_buzzer_step(retried=True)
            return
        self._print("Buzzer not confirmed. Check: buzzer -> GPIO 18 (pin 12), GND (pin 14).", "error")
        self._app.play_error_tone()

    def _cmd_calibrate(self, args: list[str]) -> None:
        self._print(
            f"Calibration: key {CALIBRATE_TAP_COUNT} short, comfortable dots (dits) on the practice key.",
            "info",
        )
        self._app.collect_key_durations(CALIBRATE_TAP_COUNT, CALIBRATE_TIMEOUT_S, self._on_calibration_done)

    def _on_calibration_done(self, durations: list[float] | None) -> None:
        if not durations:
            self._print("Calibration timed out -- no changes made.", "error")
            return
        avg = sum(durations) / len(durations)
        spread = (max(durations) - min(durations)) / avg if avg > 0 else 0.0
        new_wpm = max(3, min(40, round(1.2 / avg))) if avg > 0 else settings.wpm
        new_tolerance = max(30, min(95, round(40 + spread * 100)))
        self._app.set_wpm(new_wpm)
        self._app.set_tolerance_percent(new_tolerance)
        self._print(
            f"Calibrated from avg dot {avg * 1000:.0f}ms -> wpm {new_wpm}, tolerance {new_tolerance}",
            "success",
        )

    def _cmd_pin(self, args: list[str]) -> None:
        usage = "usage: pin set <current> <new>  |  pin undo <current>"
        if not args:
            raise CommandError(usage)
        sub = args[0].lower()

        if sub == "set":
            if len(args) < 3:
                raise CommandError("usage: pin set <current> <new>")
            current, new = args[1], args[2]
            if hash_pin(current) != settings.admin_pin_hash:
                raise CommandError("current PIN is incorrect")
            if not (new.isdigit() and 3 <= len(new) <= 8):
                raise CommandError("new PIN must be 3 to 8 digits")
            if hash_pin(new) == settings.admin_pin_hash:
                raise CommandError("new PIN is the same as the current one")
            self._app.change_pin(new)
            self._print("PIN changed. Use 'pin undo <new-pin>' to revert.", "success")

        elif sub == "undo":
            if len(args) < 2:
                raise CommandError("usage: pin undo <current>")
            current = args[1]
            if hash_pin(current) != settings.admin_pin_hash:
                raise CommandError("current PIN is incorrect")
            if self._app.undo_pin():
                self._print("PIN reverted to the previous one.", "success")
            else:
                raise CommandError("no previous PIN to undo to")
        else:
            raise CommandError(usage)

    def _cmd_reset(self, args: list[str]) -> None:
        self._app.reset_adjustable_settings()
        self._print("Settings reset to defaults.", "success")

    def _cmd_stats(self, args: list[str]) -> None:
        stats = self._app.get_stats()
        self._print(f"Uptime: {stats['uptime_seconds']:.0f}s", "response")
        self._print(
            f"Letters decoded: {stats['letters_decoded']} "
            f"({stats['letters_unrecognized']} unrecognized)", "response",
        )
        self._print(f"Words completed: {stats['words_completed']}", "response")
        self._print(
            f"WPM: {settings.wpm}  Tone: {settings.tone_hz:.0f}Hz  Tolerance: {settings.tolerance_percent}",
            "response",
        )

    def _session_fields(self) -> list[tuple[str, str]]:
        stats = self._app.get_stats()
        return [
            ("os", 'MorseOS 1.0 "Sherwood"'),
            ("host", platform.node() or "practice-console"),
            ("backend", settings.resolve_backend()),
            ("theme", theme.current.name),
            ("uptime", f"{stats['uptime_seconds']:.0f}s"),
            ("wpm", str(settings.wpm)),
            ("tone", f"{settings.tone_hz:.0f}Hz"),
            ("tolerance", f"{settings.tolerance_percent}%"),
            ("brightness", f"{settings.brightness_percent}%"),
            ("words", str(len(settings.practice_words))),
            ("decoded", f"{stats['letters_decoded']} letters"),
            ("shell", "morse-shell 1.0"),
        ]

    def _cmd_neofetch(self, args: list[str]) -> None:
        fields = self._session_fields()
        logo_width = max(len(line) for line in NEOFETCH_LOGO)
        row_count = max(len(NEOFETCH_LOGO), len(fields))
        lines = []
        for i in range(row_count):
            logo_line = NEOFETCH_LOGO[i] if i < len(NEOFETCH_LOGO) else " " * logo_width
            info_line = f"{fields[i][0]}: {fields[i][1]}" if i < len(fields) else ""
            lines.append(f"{logo_line.ljust(logo_width)}  {info_line}")
        self._print("\n".join(lines), "neofetch")

    def _cmd_sysinfo(self, args: list[str]) -> None:
        width = max(len(key) for key, _ in self._session_fields())
        lines = [f"{key.ljust(width)} : {value}" for key, value in self._session_fields()]
        self._print("\n".join(lines), "response")

    def _cmd_kitty(self, args: list[str]) -> None:
        if self._app.launch_kitty():
            self._print("Launched kitty.", "success")
        else:
            self._print("kitty is not available on this system.", "error")

    def _cmd_htop(self, args: list[str]) -> None:
        if self._app.launch_htop():
            self._print("Launched htop.", "success")
        else:
            self._print("htop is not available on this system.", "error")

    def _cmd_logs(self, args: list[str]) -> None:
        n = 20
        if args:
            n = _parse_int(args[0], 1, 500, "lines")
        try:
            lines = LOG_FILE.read_text().splitlines()[-n:]
        except OSError:
            lines = []
        self._print("\n".join(lines) if lines else "(log file is empty)", "response")

    def _cmd_motd(self, args: list[str]) -> None:
        self._print(random.choice(MOTD_MESSAGES), "motd")

    def _cmd_man(self, args: list[str]) -> None:
        if not args:
            raise CommandError("usage: man <command>")
        name = args[0].lower()
        entry = MAN_PAGES.get(name)
        if entry is None:
            self._print(f"No manual entry for '{name}'.", "error")
            return
        synopsis, description = entry
        self._print(f"NAME\n    {name}\n\nSYNOPSIS\n    {synopsis}\n\nDESCRIPTION\n    {description}", "response")

    def _cmd_ps(self, args: list[str]) -> None:
        lines = ["PID   NAME              STATUS"]
        for pid, name, status, _cpu in FAKE_PROCESSES:
            marker = "  <- you are here" if name == "terminal-shell" else ""
            lines.append(f"{pid:<5} {name:<17} {status}{marker}")
        self._print("\n".join(lines), "response")

    def _cmd_top(self, args: list[str]) -> None:
        stats = self._app.get_stats()
        lines = [
            f"uptime: {stats['uptime_seconds']:.0f}s   tasks: {len(FAKE_PROCESSES)}   load average: 0.07, 0.03, 0.01",
            "",
            "PID   NAME              CPU%   STATUS",
        ]
        for pid, name, status, cpu in FAKE_PROCESSES:
            lines.append(f"{pid:<5} {name:<17} {cpu:<6} {status}")
        self._print("\n".join(lines), "response")

    def _cmd_send(self, args: list[str]) -> None:
        if not args:
            raise CommandError("usage: send <word>")
        text = " ".join(args)
        self._print(f"Sending: {text.upper()}", "info")
        schedule_message_playback(
            self, self._app.tone, text, settings.unit_seconds,
            on_done=lambda: self._print("Done.", "success"),
        )

    def _cmd_presetsave(self, args: list[str]) -> None:
        if not args:
            raise CommandError("usage: presetsave <name>")
        name = args[0].lower()
        settings.presets[name] = {
            "wpm": settings.wpm,
            "tone_hz": settings.tone_hz,
            "tolerance_percent": settings.tolerance_percent,
        }
        self._app.persist_settings()
        self._print(f"Saved preset '{name}'.", "success")

    def _cmd_presetload(self, args: list[str]) -> None:
        if not args:
            raise CommandError("usage: presetload <name>")
        name = args[0].lower()
        preset = settings.presets.get(name)
        if preset is None:
            raise CommandError(f"no such preset '{name}'")
        self._app.set_wpm(preset["wpm"])
        self._app.set_tone_hz(preset["tone_hz"])
        self._app.set_tolerance_percent(preset["tolerance_percent"])
        self._print(
            f"Loaded '{name}': wpm {preset['wpm']}, tone {preset['tone_hz']:.0f}Hz, "
            f"tolerance {preset['tolerance_percent']}", "success",
        )

    def _cmd_presetlist(self, args: list[str]) -> None:
        if not settings.presets:
            self._print("(no presets saved)", "response")
            return
        for name, p in settings.presets.items():
            self._print(
                f"{name}: wpm {p['wpm']}, tone {p['tone_hz']:.0f}Hz, tolerance {p['tolerance_percent']}",
                "response",
            )

    def _cmd_word(self, args: list[str]) -> None:
        if not args:
            raise CommandError("usage: word add|list|del <text>")
        sub = args[0].lower()
        if sub == "list":
            self._print(", ".join(settings.practice_words) or "(none)", "response")
            return
        if sub in ("add", "del") and len(args) < 2:
            raise CommandError(f"usage: word {sub} <text>")
        word = " ".join(args[1:]).upper()
        if sub == "add":
            if word in settings.practice_words:
                raise CommandError(f"'{word}' is already in the word list")
            settings.practice_words.append(word)
            self._app.home.refresh_practice_words()
            self._app.persist_settings()
            self._print(f"Added '{word}'", "success")
        elif sub == "del":
            if word not in settings.practice_words:
                raise CommandError(f"'{word}' is not in the word list")
            settings.practice_words.remove(word)
            self._app.home.refresh_practice_words()
            self._app.persist_settings()
            self._print(f"Removed '{word}'", "success")
        else:
            raise CommandError("usage: word add|list|del <text>")

    def _cmd_lock(self, args: list[str]) -> None:
        self._exit()

    def _cmd_shutdown(self, args: list[str]) -> None:
        self._print("Shutting down...", "error")
        self._app.shutdown_system()

    def _cmd_restart(self, args: list[str]) -> None:
        self._print("Restarting...", "error")
        self._app.restart_system()

    def _cmd_help(self, args: list[str]) -> None:
        self._print(HELP_TEXT, "response")

    # --- output + idle auto-lock ---

    def _print(self, text: str, tag: str = "response") -> None:
        self.output.configure(state="normal")
        self.output.insert("end", text + "\n", tag)
        self.output.see("end")
        line_count = int(self.output.index("end-1c").split(".")[0])
        overflow = line_count - settings.terminal_max_lines
        if overflow > 0:
            self.output.delete("1.0", f"{overflow + 1}.0")
        self.output.configure(state="disabled")

    def _touch_activity(self) -> None:
        self._last_activity = self._app.now()

    def _start_idle_watch(self) -> None:
        self._touch_activity()
        self._check_idle()

    def _stop_idle_watch(self) -> None:
        if self._idle_after_id is not None:
            self.after_cancel(self._idle_after_id)
            self._idle_after_id = None

    def _check_idle(self) -> None:
        # This 1s loop only runs while the terminal is on-screen, so it's
        # also a convenient tick for refreshing the prompt's live clock.
        self.prompt_var.set(_prompt())
        if self._app.now() - self._last_activity >= settings.terminal_idle_timeout_seconds:
            self._idle_after_id = None
            self._print("Session locked due to inactivity.", "info")
            self._exit()
            return
        self._idle_after_id = self.after(1000, self._check_idle)

    def _exit(self) -> None:
        self.reset_input()
        self._on_exit()
