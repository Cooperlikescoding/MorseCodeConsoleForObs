"""Entry point for the Morse code practice console."""

from ui.app import MorseApp


def main() -> None:
    app = MorseApp()
    app.mainloop()


if __name__ == "__main__":
    main()
