# Project Handoff — Morse Code Console

> Written for a fresh Claude Code session (e.g. after switching to a new plan/machine)
> to pick up this project with zero prior conversation context. Read this first, then
> verify anything you're about to rely on against the actual code — this doc is a
> point-in-time snapshot, not live state.

## What this is

An **offline** Morse-code practice console (Python + Tkinter) built as a kiosk app for a
children's **radio-themed event**. A kid keys Morse on a physical button, hears it on a
buzzer, and sees decoded letters on a touchscreen. There's a guided Learn mode (A–Z) and
a hidden, PIN-gated "mini-OS" terminal with a full command shell for the operator (you/the
event host) to tweak settings, run diagnostics, and mess about with radio-flavour easter
eggs.

Everything runs **fully offline** — no network calls anywhere.

## Hardware & power

- **Raspberry Pi 5 (8GB)** running the app in kiosk fullscreen.
- **Official Raspberry Pi Touch Display 2** — native panel is 720×1280 portrait, used as
  **1280×720 landscape**. `config.settings.window_size = "1280x720"`.
- **Morse key** = a 10mm tactile button on **GPIO 17** (to GND, internal pull-up,
  active-low).
- **Audio** = passive piezo buzzer on **GPIO 18** via `gpiozero.TonalBuzzer`, 650 Hz square
  wave.
- **Power** = an **Anker Solix** portable power station with AC wall sockets — the Pi's
  normal USB-C PSU plugs straight into it, no special DC/USB-PD wiring.

## How to run it

**On the dev machine (Windows):** `python main.py` — runs windowed. Tkinter, pygame
(for tone synthesis on desktop), and pytest are the deps (`requirements.txt`).

**On the Pi:**
```bash
cd ~/MorseCodeConsoleForObs
git pull
source .venv/bin/activate
python main.py
```
The Pi's venv was created with `--system-site-packages` so it can see the system
`gpiozero`; it installs `requirements-pi.txt`.

## Deployment workflow — READ THIS, it bit us once

Deployment is **git pull**, and there are **two machines** that both commit: the Windows
dev box and the Pi itself (the user runs Claude Code on both). GitHub repo:
`Cooperlikescoding/MorseCodeConsoleForObs`.

**The rule that avoids conflicts: `git pull` BEFORE you start editing, `git push` when
you're done.** We once had both machines edit the terminal's scroll code simultaneously
without pulling first and had to resolve a merge conflict. Fast-forwards are the normal
case; conflicts only happen when both sides edit the same region between pulls.

`.gitignore` excludes `user_settings.json`, `morse_console.log`, `__pycache__`, `.venv`,
`.claude/settings.local.json`. `.gitattributes` normalizes line endings to LF.

## Architecture

All screens live in `ui/` and are built in `ui/app.py`'s `_build_screens()`, swapped via
`MorseApp._switch_to(screen)` (which calls optional `.leave()`/`.enter()` hooks).

| Screen | File | Purpose |
|---|---|---|
| Boot | `ui/boot.py` | One-time fake boot log at startup. Tap or wait ~1.6s → Home. Not re-shown on theme rebuild. |
| Home | `ui/home.py` | **Keying only, NO keyboard.** Practice-word chips (tap → tap-to-learn), keyed-text feedback log, live key indicator, footer buttons (Clear, ⌫ Word, Learn, Terminal). |
| Learn | `ui/learn.py` | Guided A–Z. Shows a letter; you key it; advances on match; loops after Z. Tap the letter to hear/see its pattern. |
| Terminal | `ui/terminal.py` | **PIN-gated** (via `ui/pin_dialog.py`, SHA-256 hash compare). The **only** on-screen keyboard in the app. Full command shell. |

**Key modules (non-UI):**
- `morse_code.py` — the Morse alphabet / letter tables.
- `decoder.py` — turns key up/down timings into letters (wpm, tolerance).
- `key_input.py` — physical GPIO key (Pi) / keyboard fallback (desktop).
- `audio.py` — tone/buzzer output + scheduled message playback.
- `config.py` — settings dataclass, `save_settings()`/`load_settings_into()`,
  `PERSISTED_FIELDS`, `hash_pin()`.
- `display_control.py` — screen brightness (globs `/sys/class/backlight/*`).
- `chat_responses.py` — scripted "chat" replies for non-command terminal input.
- `theme.py` — 5 palettes, `theme.current` active one.
- `logging_setup.py` — logger to stderr + `morse_console.log` (the `logs` command tails it).

## Key design decisions & constraints (don't accidentally undo these)

1. **Home is keying-only.** Do NOT add a typing keyboard to Home — that was tried early
   and explicitly reversed. The on-screen keyboard lives **only** in the Terminal.
   Tap-to-learn is triggered from the **practice-word chips**, not the keyed-text log.

2. **Touch, not mouse.** No hover states. Two touch-specific bugs are already fixed and
   must stay fixed:
   - `ui/widgets.py` `RoundedButton._on_release` fires on *any* release (no pixel-bounds
     check) — finger drift between touch-down/up was silently swallowing taps on small
     buttons. Tk's implicit grab guarantees correct targeting.
   - `KeyedTextDisplay` (`ui/keyed_display.py`) is a `tk.Label`, not `tk.Text` — a
     focus-grabbing Text widget was stealing touch events from nearby buttons. The
     terminal's output log *has* to stay a `tk.Text` (needs colored tags) but has
     `takefocus=0, cursor="arrow"`.
   - Terminal scrollback has **two** touch-scroll methods: a wide always-visible
     scrollbar (26px thumb) *and* finger drag-to-scroll (`scan_mark`/`scan_dragto`, with
     `"break"` returned to suppress text-selection). Both intentional.

3. **No color emoji.** The Pi image has no color-emoji font, so 🔒📖🎉-style glyphs render
   as tofu boxes. Use plain text/BMP symbols only. Plain Unicode like `❯ ⌫ ↻` renders
   fine. There's a regression test (`test_no_color_emoji_in_home_or_learn_button_labels`)
   that fails if any codepoint ≥ U+1F000 appears in `ui/home.py`/`ui/learn.py`.

4. **Fullscreen uses `overrideredirect()` + explicit screen-size geometry**, NOT the
   `-fullscreen` WM attribute — the bare kiosk X session has no EWMH-compliant window
   manager to honor the hint. See `ui/app.py` `_apply_fullscreen()`. `fullscreen` is
   deliberately **excluded** from persisted settings so a dev `unfullscreen` never
   survives a reboot.

5. **PINs are SHA-256 hashed, never plaintext** (`config.hash_pin`). `pin set <cur> <new>`
   changes it; `pin undo <cur>` reverts to the previous hash. Both require the current PIN.
   The echoed scrollback redacts digit args (`_redact_for_echo`).

6. **Theming rebuilds the whole UI.** Switching theme destroys and rebuilds every screen.
   Therefore always read colors live as `theme.current.xxx` — never
   `from theme import BASE` (a bare import freezes at whatever flavor loaded first).

7. **Adding an admin setting** = `config.py` field + `set_*` method on `MorseApp` +
   `_cmd_*` handler in `ui/terminal.py`, following the existing pairing pattern. Add it to
   the `help` text and a `man` page too.

## Testing methodology

Two layers, both run before considering anything done:
1. **pytest** — `python -m pytest tests/ -q` (currently 54 pass, 2 skip when no display).
2. **Live Tkinter smoke tests** — driven programmatically (fake events, simulated key
   timings, simulated PIN entry) against a real `MorseApp`. Written to the session
   scratchpad dir, not committed.

**Gotchas learned the hard way:**
- `MorseApp` *is* a `tk.Tk` root. Creating a second `tk.Tk()` in the same process is
  unreliable — consolidate multi-step Tk tests into one function/instance.
- After any smoke test: kill stray `python.exe` processes (they lock `morse_console.log`),
  then delete `user_settings.json`, `morse_console.log`, `__pycache__`, `.pytest_cache`
  before committing. This cleanup is mandatory.
- Windows console is cp1252 — printing `❯` etc. raises `UnicodeEncodeError`. That's a
  test-harness quirk, not an app bug; ASCII-encode before printing or set
  `PYTHONIOENCODING=utf-8`.

## Working preferences (from the user)

- **Run safe commands (reads, tests, smoke scripts) without pausing to ask.** Only confirm
  before things that are hard to reverse or outward-facing (e.g. `git push`).
- Each `git push` so far has been individually confirmed with a "yes please" — present the
  change and offer to push rather than assuming standing permission.
- The user likes the ham-radio flavour (MOTDs like `73 de morse-shell -- best regards!`).

## Current state

Clean. `main` at commit `efeae7e` (touch drag-to-scroll), everything pushed. All tests
pass. Recent fix history:
- `efeae7e` touch drag-to-scroll on terminal log (alongside scrollbar)
- `afd5308` tap-to-learn popup was hidden behind the fullscreen kiosk window — fixed
- `5cc57cd` PIN dialog hidden on kiosk boot — fixed; added terminal scrollbar
- `7840684` emoji tofu, CQ-not-CK MOTD typo, Learn tap-to-learn, fullscreen toggle

**No open tasks.** Last thing verified working: touch scrolling (both methods) in the
terminal. Pull on the Pi (`git pull`) to sync it to `efeae7e`.
