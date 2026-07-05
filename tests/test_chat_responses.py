import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chat_responses import DEFAULT_RESPONSES, get_response


class FixedChoiceRng:
    """Deterministic stand-in for `random` -- always returns the first item."""

    @staticmethod
    def choice(seq):
        return seq[0]


def test_hi_triggers_greeting():
    assert get_response("HI", rng=FixedChoiceRng()) == "HELLO OM, GREAT TO HEAR YOU"


def test_matching_is_case_insensitive():
    assert get_response("hi", rng=FixedChoiceRng()) == get_response("HI", rng=FixedChoiceRng())


def test_word_boundary_avoids_false_positive():
    # "HI" must not match inside "THIS"
    assert get_response("THIS IS A TEST", rng=FixedChoiceRng()) != "HELLO OM, GREAT TO HEAR YOU"


def test_multi_word_trigger():
    assert get_response("HOW ARE YOU TODAY", rng=FixedChoiceRng()) == "FB (FINE BUSINESS), THANKS! HW ABOUT YOU?"


def test_unmatched_message_uses_default():
    result = get_response("ZQXW BLORP", rng=FixedChoiceRng())
    assert result in DEFAULT_RESPONSES


def test_empty_message_uses_default():
    result = get_response("", rng=FixedChoiceRng())
    assert result in DEFAULT_RESPONSES


def test_first_matching_rule_wins():
    # "SOS" appears, should hit the SOS rule not fall through to default
    assert "SOS" in get_response("SOS", rng=FixedChoiceRng()) or "PRACTICE" in get_response("SOS", rng=FixedChoiceRng())
