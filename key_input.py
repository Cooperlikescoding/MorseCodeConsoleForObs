"""Key-input abstraction.

The rest of the app (audio + decoder + UI) only ever talks to the
`KeyInput` interface: "tell me when the key goes down, tell me when it
goes up". Two backends implement it:

- `KeyboardKeyInput`: a keyboard key (default: spacebar) stands in for the
  Morse key on a dev machine. Bound via Tkinter events, so it needs a
  Tk widget to bind to.
- `GpioKeyInput`: a real momentary switch on a GPIO pin via gpiozero, for
  the Raspberry Pi. Wired to GND with the internal pull-up enabled, so a
  press pulls the pin low (active-low).

`create_key_input()` picks the right one from `config.settings`, so
swapping dev <-> Pi is a config change, not a code change.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable

Callback = Callable[[], None]


class KeyInput(ABC):
    """Abstract Morse key. Call `bind()` once, then `start()`/`stop()`."""

    @abstractmethod
    def bind(self, on_press: Callback, on_release: Callback) -> None:
        """Register callbacks fired on key-down and key-up. No arguments,
        no debouncing/timing logic here -- that belongs to the decoder.
        """

    @abstractmethod
    def start(self) -> None:
        """Begin listening. Safe to call once bind() has been called."""

    @abstractmethod
    def stop(self) -> None:
        """Stop listening and release any hardware resources."""


class KeyboardKeyInput(KeyInput):
    """Dev-machine stand-in: a keyboard key (default spacebar) acts as the
    Morse key. Requires a Tk widget to bind key events to.
    """

    def __init__(self, tk_widget, keysym: str = "space"):
        self._widget = tk_widget
        self._keysym = keysym
        self._on_press: Callback | None = None
        self._on_release: Callback | None = None
        self._is_down = False
        self._pending_release_id: str | None = None

    def bind(self, on_press: Callback, on_release: Callback) -> None:
        self._on_press = on_press
        self._on_release = on_release

    def start(self) -> None:
        self._widget.bind_all(f"<KeyPress-{self._keysym}>", self._handle_press)
        self._widget.bind_all(f"<KeyRelease-{self._keysym}>", self._handle_release)

    def stop(self) -> None:
        self._widget.unbind_all(f"<KeyPress-{self._keysym}>")
        self._widget.unbind_all(f"<KeyRelease-{self._keysym}>")

    def _handle_press(self, _event) -> None:
        # OS key-repeat sends a stream of Press/Release while a key is held.
        # If a release is still pending when a new press arrives, it's a
        # repeat -- cancel the pending release instead of treating it as a
        # fresh key-up/key-down pair.
        if self._pending_release_id is not None:
            self._widget.after_cancel(self._pending_release_id)
            self._pending_release_id = None
            return
        if self._is_down:
            return
        self._is_down = True
        if self._on_press:
            self._on_press()

    def _handle_release(self, _event) -> None:
        # Defer the release slightly: a genuine key-up has no matching press
        # queued right behind it, but an OS auto-repeat release does.
        self._pending_release_id = self._widget.after(1, self._confirm_release)

    def _confirm_release(self) -> None:
        self._pending_release_id = None
        if not self._is_down:
            return
        self._is_down = False
        if self._on_release:
            self._on_release()


class GpioKeyInput(KeyInput):
    """Real Morse key wired to a GPIO pin on the Raspberry Pi, wired to
    GND with the internal pull-up enabled (active-low).
    """

    def __init__(self, pin: int):
        self._pin = pin
        self._button = None
        self._on_press: Callback | None = None
        self._on_release: Callback | None = None

    def bind(self, on_press: Callback, on_release: Callback) -> None:
        self._on_press = on_press
        self._on_release = on_release

    def start(self) -> None:
        # Imported lazily so dev machines without gpiozero/RPi.GPIO
        # installed can still import this module.
        from gpiozero import Button

        self._button = Button(self._pin, pull_up=True, bounce_time=0.01)
        if self._on_press:
            self._button.when_pressed = self._on_press
        if self._on_release:
            self._button.when_released = self._on_release

    def stop(self) -> None:
        if self._button is not None:
            self._button.close()
            self._button = None


def create_key_input(tk_widget=None) -> KeyInput:
    """Build the configured KeyInput backend. `tk_widget` is required for
    the keyboard backend (it needs something to bind key events to).
    """
    from config import settings

    backend = settings.resolve_backend()
    if backend == "gpio":
        return GpioKeyInput(settings.gpio_pin)
    if backend == "keyboard":
        if tk_widget is None:
            raise ValueError("KeyboardKeyInput requires a Tk widget to bind to")
        return KeyboardKeyInput(tk_widget, settings.dev_key)
    raise ValueError(f"Unknown key backend: {backend!r}")
