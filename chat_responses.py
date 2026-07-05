"""Scripted, offline chat-style responses for the members' terminal.

(Named chat_responses rather than plain "responses" to avoid shadowing
the popular third-party `responses` library on sys.path.)

Fully pattern-matched -- no network, no LLM, works entirely offline.
Add, remove, or edit entries in RULES to change what the console says;
each rule's `triggers` are checked as whole words/phrases (case
insensitive) anywhere in the message, first match wins. Nothing matches?
`DEFAULT_RESPONSES` is used instead.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence


@dataclass
class Rule:
    triggers: Sequence[str]
    responses: Sequence[str]


# Ham-radio flavoured, kid-friendly scripted replies. Edit freely -- this
# is the one file a volunteer should need to touch to change the "chat".
RULES: list[Rule] = [
    Rule(["HELLO OM", "HI", "HELLO"], [
        "HELLO OM, GREAT TO HEAR YOU",
        "HI THERE, GOOD SIGNAL!",
        "HELLO! 73 FROM THE SHACK",
    ]),
    Rule(["CQ"], [
        "CQ CQ CQ DE PRACTICE STATION, GO AHEAD",
        "CQ RECEIVED, THIS IS THE PRACTICE STATION",
    ]),
    Rule(["SOS"], [
        "SOS RECEIVED -- DON'T WORRY, THIS IS ONLY PRACTICE!",
    ]),
    Rule(["QTH"], [
        "MY QTH IS THE RADIO SHACK, WHERE'S YOURS?",
    ]),
    Rule(["QRZ"], [
        "QRZ? THIS IS THE PRACTICE STATION, GO AHEAD",
    ]),
    Rule(["NAME"], [
        "MY NAME IS SPARKY, THE PRACTICE ROBOT",
    ]),
    Rule(["HOW ARE YOU", "HW"], [
        "FB (FINE BUSINESS), THANKS! HW ABOUT YOU?",
    ]),
    Rule(["TEST", "TESTING"], [
        "LOUD AND CLEAR, TEST RECEIVED",
    ]),
    Rule(["TNX", "THANKS", "THANK YOU"], [
        "TNX FOR THE QSO, 73!",
    ]),
    Rule(["73"], [
        "73 TO YOU TOO, GOOD DX!",
        "73 OM, CU AGAIN",
    ]),
    Rule(["BYE", "GOODBYE", "CUL"], [
        "73 AND CU LATER, GOOD DX!",
    ]),
]

DEFAULT_RESPONSES = [
    "QSL? PLEASE REPEAT, DIDN'T COPY",
    "COPY? SAY AGAIN",
    "HI THERE, KEEP PRACTICING YOUR CODE!",
]


def _matches(trigger: str, text: str) -> bool:
    pattern = r"\b" + re.escape(trigger) + r"\b"
    return re.search(pattern, text) is not None


def get_response(message: str, rng=None) -> str:
    """Find a scripted reply for `message` (already-decoded/typed text).

    `rng` is an optional object with a `.choice(seq)` method (e.g. the
    `random` module, or a fixed stand-in for deterministic tests).
    """
    if rng is None:
        import random as rng

    text = message.strip().upper()
    if not text:
        return rng.choice(DEFAULT_RESPONSES)

    for rule in RULES:
        if any(_matches(trigger, text) for trigger in rule.triggers):
            return rng.choice(rule.responses)

    return rng.choice(DEFAULT_RESPONSES)
