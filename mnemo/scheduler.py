"""The SM-2 scheduling functions: pure, date-injected, exactly the published algorithm."""

from dataclasses import replace
from datetime import date, timedelta

from mnemo.errors import MnemoError
from mnemo.models import Card, EASE_FLOOR, GRADE_MAX, GRADE_MIN, parse_iso_date

MATURE_INTERVAL_DAYS = 21
GRADE_WORDS = {"again": 1, "hard": 3, "good": 4, "easy": 5}


def grade_from_text(text: object) -> int:
    """A grade from one digit 0-5, or from the words again, hard, good and easy."""
    answer = text.strip().lower() if isinstance(text, str) else ""
    if answer in GRADE_WORDS:
        return GRADE_WORDS[answer]
    if answer.isdigit() and GRADE_MIN <= int(answer) <= GRADE_MAX:
        return int(answer)
    raise MnemoError(
        f"'{text}' is not a grade.",
        "a review is graded from 0 (blank) to 5 (perfect), by digit or by word.",
        "answer with a digit 0-5, or with again, hard, good or easy.",
    )


def _ease_after(ease: float, quality: int) -> float:
    """The published SM-2 ease update, never dropping below the floor."""
    return max(EASE_FLOOR, ease + (0.1 - quality * (0.08 + quality * 0.02)))


def next_state(card: Card, quality: int, today: str) -> Card:
    """The card exactly as the published SM-2 leaves it after one graded answer."""
    if isinstance(quality, bool) or not isinstance(quality, int) \
            or not GRADE_MIN <= quality <= GRADE_MAX:
        raise MnemoError(
            f"quality {quality!r} is out of range.",
            f"SM-2 grades are the integers {GRADE_MIN} to {GRADE_MAX}.",
            f"grade the answer with a value in {GRADE_MIN}..{GRADE_MAX}.",
        )
    parse_iso_date(today, "today")
    ease = _ease_after(card.ease, quality)
    if quality < 3:
        repetitions = 0
        interval_days = 1
        lapses = card.lapses + 1
    else:
        repetitions = card.repetitions + 1
        interval_days = (1 if repetitions == 1 else 6 if repetitions == 2
                         else round(card.interval_days * ease))
        lapses = card.lapses
    due = (date.fromisoformat(today) + timedelta(days=interval_days)).isoformat()
    return replace(card, ease=ease, repetitions=repetitions, interval_days=interval_days,
                   lapses=lapses, due=due)


def is_due(card: Card, today: str) -> bool:
    """Whether the card's due day is `today` or has already passed."""
    return card.due <= parse_iso_date(today, "today")


def maturity(card: Card) -> str:
    """The card's stage: new, learning, or mature at 21 days of interval."""
    if card.repetitions == 0:
        return "new"
    if card.interval_days < MATURE_INTERVAL_DAYS:
        return "learning"
    return "mature"
