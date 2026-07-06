"""Touch-only numeric PIN pad, gating access to the members' terminal.

No physical keyboard is available at runtime, so PIN entry has to be a
touch keypad rather than a text entry box. The entered PIN is hashed
(SHA-256) and compared against `settings.admin_pin_hash` -- the
plaintext PIN is never stored anywhere.
"""

from __future__ import annotations

import tkinter as tk
from typing import Callable

import theme
from config import hash_pin, settings
from theme import mono_font
from ui.widgets import RoundedButton


class PinDialog(tk.Toplevel):
    def __init__(self, parent, on_success: Callable[[], None],
                 on_cancel: Callable[[], None] | None = None, max_length: int = 8):
        super().__init__(parent)
        self._on_success = on_success
        self._on_cancel = on_cancel
        self._max_length = max_length
        self._entry = ""

        self.title("Members Terminal")
        self.configure(bg=theme.current.base)
        self.transient(parent)
        self.attributes("-topmost", True)
        # The main window runs override-redirected for fullscreen (see
        # app.py's _apply_fullscreen) -- on a bare kiosk session with no/
        # minimal window manager, override-redirect windows sit above
        # normal WM-managed ones regardless of "-topmost", so a plain
        # Toplevel here could be created successfully but rendered behind
        # the fullscreen main window, making the PIN pad invisible.
        # Override-redirecting this dialog too keeps it in the same
        # unmanaged stacking class, so it can actually appear on top.
        self.overrideredirect(True)
        self.grab_set()  # modal: block interaction with the rest of the app

        self._build()
        # Size the window to what its widgets actually need, not a guessed
        # pixel constant -- fonts/padding render differently across
        # platforms, and a fixed size previously clipped the bottom rows.
        self.update_idletasks()
        self._center_over(parent)
        self.lift()
        self.focus_force()

        self.protocol("WM_DELETE_WINDOW", self._cancel)

    def _center_over(self, parent) -> None:
        parent.update_idletasks()
        width, height = self.winfo_reqwidth(), self.winfo_reqheight()
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        x = px + (pw - width) // 2
        y = py + (ph - height) // 2
        self.geometry(f"{width}x{height}+{max(x, 0)}+{max(y, 0)}")

    def _build(self) -> None:
        tk.Label(
            self, text="Enter PIN", font=mono_font(18, "bold"),
            bg=theme.current.base, fg=theme.current.green,
        ).pack(pady=(15, 5))

        self.display_var = tk.StringVar(value="")
        tk.Label(
            self, textvariable=self.display_var, font=mono_font(26),
            bg=theme.current.mantle, fg=theme.current.green, width=10,
        ).pack(pady=(0, 5))

        self.error_var = tk.StringVar(value="")
        tk.Label(
            self, textvariable=self.error_var, font=mono_font(11),
            bg=theme.current.base, fg=theme.current.red,
        ).pack()

        pad = tk.Frame(self, bg=theme.current.base)
        pad.pack(pady=10)
        keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "⌫", "0", "OK"]
        for i, label in enumerate(keys):
            row, col = divmod(i, 3)
            pad.grid_columnconfigure(col, weight=1)
            btn = RoundedButton(
                pad, text=label, font=mono_font(20, "bold"), width=70, height=56,
                command=lambda l=label: self._press(l),
            )
            btn.grid(row=row, column=col, padx=4, pady=4)

        cancel_btn = RoundedButton(self, text="Cancel", font=mono_font(13, "bold"), command=self._cancel)
        cancel_btn.pack(pady=(5, 15))

    def _press(self, label: str) -> None:
        if label == "⌫":
            self._entry = self._entry[:-1]
        elif label == "OK":
            self._submit()
            return
        elif len(self._entry) < self._max_length:
            self._entry += label
        self.display_var.set("•" * len(self._entry))

    def _submit(self) -> None:
        if hash_pin(self._entry) == settings.admin_pin_hash:
            self.destroy()
            self._on_success()
        else:
            self.error_var.set("Incorrect PIN, try again")
            self._entry = ""
            self.display_var.set("")

    def _cancel(self) -> None:
        self.destroy()
        if self._on_cancel:
            self._on_cancel()
