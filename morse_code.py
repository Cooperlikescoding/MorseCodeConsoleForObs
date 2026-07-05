"""International Morse code tables and simple encode/decode helpers.

Patterns use '.' for dit and '-' for dah, matching what the rest of the
app (decoder, tap-to-learn popup) expects.
"""

from __future__ import annotations

LETTERS: dict[str, str] = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".",
    "F": "..-.", "G": "--.", "H": "....", "I": "..", "J": ".---",
    "K": "-.-", "L": ".-..", "M": "--", "N": "-.", "O": "---",
    "P": ".--.", "Q": "--.-", "R": ".-.", "S": "...", "T": "-",
    "U": "..-", "V": "...-", "W": ".--", "X": "-..-", "Y": "-.--",
    "Z": "--..",
}

DIGITS: dict[str, str] = {
    "0": "-----", "1": ".----", "2": "..---", "3": "...--", "4": "....-",
    "5": ".....", "6": "-....", "7": "--...", "8": "---..", "9": "----.",
}

PUNCTUATION: dict[str, str] = {
    ".": ".-.-.-", ",": "--..--", "?": "..--..", "'": ".----.",
    "!": "-.-.--", "/": "-..-.", "(": "-.--.", ")": "-.--.-",
    "&": ".-...", ":": "---...", ";": "-.-.-.", "=": "-...-",
    "+": ".-.-.", "-": "-....-", "_": "..--.-", '"': ".-..-.",
    "@": ".--.-.",
}

# Combined lookup: character -> morse pattern.
CHAR_TO_MORSE: dict[str, str] = {**LETTERS, **DIGITS, **PUNCTUATION}

# Reverse lookup: morse pattern -> character.
MORSE_TO_CHAR: dict[str, str] = {v: k for k, v in CHAR_TO_MORSE.items()}


def encode(text: str) -> str:
    """Encode text into a space-separated Morse string. Unknown characters
    (and whitespace) become a '/' word-separator token, mirroring convention.
    """
    words = text.upper().split()
    encoded_words = []
    for word in words:
        symbols = [CHAR_TO_MORSE[ch] for ch in word if ch in CHAR_TO_MORSE]
        encoded_words.append(" ".join(symbols))
    return " / ".join(encoded_words)


def decode_symbol(pattern: str) -> str | None:
    """Look up a single dit/dah pattern (e.g. '.-') -> character, or None."""
    return MORSE_TO_CHAR.get(pattern)
