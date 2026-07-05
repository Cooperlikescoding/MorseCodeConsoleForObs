# Morse Code Practice Console

An offline, touchscreen-friendly Morse code practice kiosk built for a
Raspberry Pi 5 (8GB) + official Touch Display 2 (1280x720 landscape),
for a children's radio-themed event. No internet or physical keyboard
is needed at runtime. Themed in Catppuccin (Mocha/Macchiato/Frappé/Latte)
or Nord, switchable live.

## Features

- **Physical Morse key** on GPIO 17 (a 10mm tactile button to GND,
  internal pull-up, active-low), abstracted behind a `KeyInput` interface
  so the same app runs on a dev machine using the spacebar as a stand-in
  key. Confirmed working on a Raspberry Pi 5 (8GB) with the official
  Touch Display 2.
- **Passive piezo buzzer** on GPIO 18 via PWM (`gpiozero.TonalBuzzer`),
  650Hz by default, tone on while the key is held, off on release. On a
  dev machine without a buzzer, a software **square-wave** tone plays
  through the default audio device instead (matching what the real
  PWM-driven buzzer actually sounds like, not a smooth sine) -- same
  `ToneOutput` interface either way.
- **Forgiving Morse decoder**: dits/dahs -> letters, with a single
  "tolerance" knob (0-100) driving generous default timing windows for
  sloppy kid-keying. A `calibrate` command auto-tunes both speed and
  tolerance to how a specific key/kid actually feels.
- **Beginner-friendly default speed** (8 WPM), adjustable live from the
  terminal, and **persisted** across restarts (along with tone,
  tolerance, brightness, theme, PIN, and the practice word list).
- **Live dit/dah visual feedback**: a shape grows from a dot into a dash
  while the key is held, on both the Home and Learn screens.
- **Touchscreen-only UI** (Tkinter), with three screens plus a boot log:
  - **Boot**: a few lines of skippable fake boot text, then straight
    into Home.
  - **Home** (open to everyone, boots here by default): a **practice
    word** panel shows a target word (e.g. "MARS") as tappable letter
    chips -- tapping a letter opens tap-to-learn (its dot/dash pattern,
    drawn and played) but never types anything. The physical key is the
    only way to enter text here; decoded letters appear in a read-only
    feedback log below.
  - **Learn** (open to everyone): a guided mode that steps through the
    alphabet A-Z one letter at a time, checking what you key against the
    right answer before moving on.
  - **Terminal** (members-only): a command-style shell with an on-screen
    keyboard -- the only on-screen keyboard in the app, used only here.
- **Scripted, offline chat** with ham-radio-flavoured canned replies
  (e.g. typing or keying "HI" -> "HELLO OM, GREAT TO HEAR YOU"). Fully
  pattern-matched, no network, no LLM. Anything typed into the terminal
  that isn't a recognized command is treated as a chat message.
- **PIN-gated terminal**, hashed with `hashlib` (the plaintext PIN is
  never stored), auto-locks back to Home after a period of inactivity.
- **Power-on self-test** (`test`/`selftest`): confirms the key and
  buzzer both work, with specific wiring diagnostics and a low-pitch
  error tone if either doesn't respond.
- **Reverse playback** (`send <word>`): plays a typed word out audibly
  in Morse, so a kid can hear it before trying to key it themselves.
- **Named presets** (`presetsave`/`presetload`/`presetlist`) for
  quickly switching wpm/tone/tolerance between different skill levels.
- **Real troubleshooting tools**: `kitty` and `htop` launch the actual
  system programs (Linux only); `logs` tails the console's own log file.
- **Mini-OS flavour**: a `motd` on terminal login, `man <command>` help
  pages, and a fake `ps`/`top` process list -- all just for fun.

## Project layout

```
config.py             All the settings a volunteer would want to tweak
                       (WPM, tolerance, GPIO pins, PIN hash, audio, words,
                       theme, presets) -- also handles save/load to disk.
theme.py               Catppuccin (x4) + Nord palettes, font/button styling.
logging_setup.py        Shared logger -> morse_console.log (see `logs` command).
morse_code.py          Morse code tables + encode/decode helpers.
key_input.py           KeyInput interface + KeyboardKeyInput (dev) and
                       GpioKeyInput (Pi) implementations.
audio.py               ToneOutput interface + PygameToneOutput (dev
                       square-wave tone) and BuzzerToneOutput (Pi passive
                       buzzer), plus playback helpers (tap-to-learn, `send`).
display_control.py     Pi touchscreen backlight brightness control.
decoder.py             Pure timing-based state machine: press/release
                       timestamps -> dots/dashes -> letters -> word spaces.
chat_responses.py      Scripted chat replies (edit this to change the "chat").
ui/
  app.py               Main window: owns the shared hardware, switches
                       screens, exposes the settings/admin actions the
                       terminal's commands call into.
  boot.py               Skippable fake boot log shown once at startup.
  home.py               Open practice screen: keying-only + the practice-word panel.
  learn.py               Guided A-Z mode: shows a letter, checks what's keyed.
  practice_word.py       Tappable letter-chip panel (tap-to-learn trigger).
  keyed_display.py        Read-only feedback log of what's been keyed.
  key_indicator.py         Live growing dot/dash while the key is held.
  shapes.py               Canvas rounded-rect/capsule drawing helper.
  widgets.py              RoundedButton / RoundedPanel -- shared rounded,
                       touch-styled (press/release, no hover) widgets.
  terminal.py            PIN-gated command-style terminal (has the keyboard).
  pin_dialog.py           Touch numeric keypad for PIN entry (hashed compare).
  keyboard.py             Reusable on-screen QWERTY keyboard (Terminal only).
  tap_to_learn.py         Popup: draws + plays a letter's Morse pattern.
tests/                  Unit tests for the decoder, morse tables, config,
                       persistence, theme, and scripted responses (no
                       display needed to run these).
main.py                 Entry point.
```

## Running on a dev machine (Windows/Mac/Linux)

```
python -m venv .venv
.venv\Scripts\activate        # (or `source .venv/bin/activate` on Mac/Linux)
pip install -r requirements.txt
python main.py
```

Hold the **spacebar** to key Morse (it stands in for the physical key) --
decoded letters appear in the Home feedback log; tap a letter in the
practice word above it to open tap-to-learn. Tap the lock icon and enter
the PIN to reach the Terminal, type `help` for the command list. The
default PIN is `7373`.

Run the test suite any time with:

```
pytest tests/
```

## Running on the Raspberry Pi 5

1. Flash Raspberry Pi OS (Bookworm or later) and set up the official
   Touch Display 2 as normal (native panel is 720x1280 portrait; the UI
   here is built for 1280x720 landscape -- rotate the display in
   `config.txt`/`wayfire.ini` if it doesn't come up that way already).
2. Wire the Morse key (a 10mm tactile button works well): one leg to
   **GPIO 17**, the other leg to **GND** (physical pins 11 and 9). No
   external resistor needed -- `GpioKeyInput` uses the Pi's internal
   pull-up, so the pin reads HIGH when open and LOW when the key is
   pressed (active-low).
3. Wire the passive piezo buzzer: one leg to **GPIO 18**, the other to
   **GND** (physical pins 12 and 14; add a small series resistor, e.g.
   100Ω, if your buzzer's datasheet recommends one). This must be a
   *passive* buzzer (driven by a PWM tone) -- an active buzzer that only
   knows "on/off" won't produce a pitched tone.
4. Install dependencies:
   ```
   python -m venv .venv --system-site-packages
   source .venv/bin/activate
   pip install -r requirements-pi.txt
   ```
   > The Pi 5 uses a new GPIO chip (RP1) that the old `RPi.GPIO` backend
   > doesn't support -- `requirements-pi.txt` installs `lgpio` instead,
   > which `gpiozero` picks up automatically.
5. `config.py`'s `hardware_backend` defaults to `"auto"`, which detects
   the Pi via `/proc/device-tree/model` and switches to the real GPIO key
   + buzzer automatically -- no code changes needed versus the dev machine.
6. Run it: `python main.py`. It launches fullscreen by default
   (`settings.fullscreen = True`); press `Escape` during development to
   toggle out of fullscreen (there's no physical keyboard for a kid to
   press this by accident at the event).
7. Screen brightness (the `bright <n>` terminal command) uses the
   official touchscreen's sysfs backlight control
   (`/sys/class/backlight/rpi_backlight/brightness`) and is a no-op
   elsewhere, including on the dev machine.
8. Before the event, run `test` (or `selftest`) in the terminal once to
   confirm the key and buzzer are both wired correctly, and `calibrate`
   to tune the timing to the actual key you're using.

### Autostart on boot (kiosk mode)

Create a systemd user service (or a `~/.config/autostart/*.desktop`
entry) that launches `python /home/pi/MorseCodeConsoleForObs/main.py`
after the desktop session starts. Example systemd unit
(`~/.config/systemd/user/morse-console.service`):

```ini
[Unit]
Description=Morse Code Practice Console
After=graphical-session.target

[Service]
ExecStart=/home/pi/MorseCodeConsoleForObs/.venv/bin/python /home/pi/MorseCodeConsoleForObs/main.py
Restart=on-failure

[Install]
WantedBy=graphical-session.target
```

Then: `systemctl --user enable --now morse-console.service`.

For a cleaner kiosk look, also consider:
- Disabling screen blanking/DPMS (`raspi-config` -> Display Options, or
  `xset s off -dpms` in the autostart chain).
- Hiding the mouse cursor with `unclutter -idle 0`.
- Booting straight to the desktop with autologin enabled.
- The `shutdown` terminal command needs passwordless `sudo` for
  `shutdown` (typical on Raspberry Pi OS's default `pi` user) -- check
  `sudo -l` if it doesn't work. `restart` doesn't need `sudo` at all --
  it restarts the console app itself (re-execs the same Python process),
  not the OS, releasing the GPIO key/buzzer first so the fresh process
  can re-claim them.
- The `kitty`/`htop` terminal commands need those programs installed
  (`sudo apt install kitty htop`) -- they're optional real troubleshooting
  tools, not required for normal operation.

## The members' terminal

Reached from Home via the lock icon + PIN keypad. It's a small
command-style shell (prompt: `sherwood@morse 14:30 ❯`, with a live
clock), typed via the
on-screen keyboard or by keying Morse. Anything that isn't a recognized
command is treated as a scripted chat message (see `chat_responses.py`). A
random message-of-the-day is shown on login; `man <command>` gives a
short manual page for any command below.

| Command | Effect |
|---|---|
| `wpm <n>` | set keying speed (3-40 WPM) |
| `tone <hz>` | set tone/buzzer pitch (200-2000 Hz) |
| `tol <n>` | set decode tolerance 0-100 (higher = more forgiving) |
| `bright <n>` | set screen brightness 0-100 (Pi only) |
| `theme <name>` | switch palette: `mocha`/`macchiato`/`frappe`/`latte`/`nord` |
| `fullscreen` / `unfullscreen` | toggle fullscreen (dev convenience) |
| `test` / `selftest` | run the power-on self-test (key, then buzzer) |
| `test key` / `test buzzer` | test just one component |
| `calibrate` | key a few dots to auto-tune wpm/tolerance to your key |
| `pin set <current> <new>` | change the terminal PIN (3-8 digits; needs current PIN) |
| `pin undo <current>` | revert to the previous PIN (needs current PIN) |
| `reset` | reset wpm/tone/tolerance/brightness to defaults |
| `stats` | show session statistics |
| `sysinfo` | plain settings/system summary |
| `neofetch` (or `fetch`) | show a fun system/session summary |
| `kitty` / `htop` | launch the real program (Linux only) |
| `logs [n]` | show the last n lines of the console's log file |
| `send <word>` | play a word out in Morse through the buzzer |
| `presetsave <name>` | save current wpm/tone/tolerance as a named preset |
| `presetload <name>` | load a named preset |
| `presetlist` | list saved presets |
| `word add/list/del <text>` | manage the practice word bank shown on Home |
| `motd` | show a random tip of the day |
| `man <command>` | show a manual page for a command |
| `ps` / `top` | list the console's own (fictional) processes, for fun |
| `exit` / `lock` | return to the Home screen |
| `shutdown` | power off the console (Linux only) |
| `restart` | restart the console app itself (cross-platform) |
| `help` | show the command list |

The terminal auto-locks back to Home after `terminal_idle_timeout_seconds`
(default 60s) of no input.

## Customizing for your event

- **Timing/tolerance/speed**: `config.py` -> `Settings.wpm`,
  `Settings.tolerance_percent` (0-100 -- drives the decoder's dot/dash,
  letter-gap, and word-gap windows). Both are also adjustable live via
  the terminal's `wpm`/`tol` commands, or let `calibrate` set them for you.
- **Admin PIN**: easiest is the terminal's `pin set <current> <new>`
  command (persists across restarts). To set it from code instead, edit
  `config.py` -> `admin_pin_hash` with a fresh hash:
  ```
  python -c "import config; print(config.hash_pin('NEWPIN'))"
  ```
- **Practice words**: `config.py` -> `DEFAULT_PRACTICE_WORDS`, or add/remove
  them live during the event with the terminal's `word add`/`word del`.
- **Chat replies**: `chat_responses.py` -> `RULES`. Each rule is a list of
  trigger words/phrases and a list of possible replies (one is picked at
  random). Add, remove, or edit freely -- no code elsewhere needs to change.
- **Tone pitch/volume**: `config.py` -> `tone_hz` (or the terminal's
  `tone <hz>` command), `volume` (dev-machine software tone only).
- **Theme**: Catppuccin Mocha/Macchiato/Frappé/Latte and Nord are all
  built in -- switch live with the terminal's `theme <name>` command
  (rebuilds the UI in place, no restart needed), or change the default
  in `theme.py` (`current = MOCHA`, etc).
- **Skill-level presets**: use `presetsave <name>` after tuning wpm/tone/
  tolerance for e.g. a younger vs. more experienced kid, then
  `presetload <name>` to switch instantly between them during the event.
- **Persistence**: all of the above (except `fullscreen`, which always
  resets to the config default) is saved to `user_settings.json` next to
  the code and reloaded automatically on the next launch.

## Troubleshooting

- **Something's not working and you don't know what**: run `test` (or
  `selftest`) in the terminal -- it walks through confirming the key and
  buzzer both respond, and prints a specific wiring diagnostic
  (pin numbers included) if either doesn't.
- **No sound at all**: `audio.py`'s tone outputs fall back to silent
  no-op mode if no audio device / buzzer hardware is available (logged
  to `morse_console.log`, viewable with the terminal's `logs` command),
  so missing/misconfigured audio won't crash the console -- but check
  your wiring/output routing if you expect a beep.
- **Physical key does nothing on the Pi**: confirm wiring (GPIO 17 to
  one leg, GND to the other) and that `hardware_backend` resolved to
  `"gpio"` (force it explicitly in `config.py` if auto-detection ever
  guesses wrong on your hardware). Use the terminal's `test key` command
  to check live press/release events.
- **Kids keying too fast/slow or too sloppily**: run `calibrate` (or
  adjust `wpm`/`tol` directly) to match the timing to how they're
  actually keying.
- **Forgot the PIN**: `config.py` only stores the SHA-256 hash, not the
  plaintext -- if you don't remember it, replace `admin_pin_hash` with a
  freshly computed hash of a new PIN (see above) and redeploy.
- **Need to dig deeper on real Pi internals**: `kitty` and `htop` launch
  genuine Linux tools from the terminal, and `logs` tails the console's
  own log file, all without needing a separate SSH session.
