"""The card and review value objects, their schema bounds and their parsing rules."""

import re
from dataclasses import dataclass
from datetime import date
from typing import Dict, Optional

from mnemo.errors import MnemoError

EASE_DEFAULT = 2.5
EASE_FLOOR = 1.3
GRADE_MIN = 0
GRADE_MAX = 5
DECK_DEFAULT = "default"
MAX_DECK_CHARS = 64
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _nonblank(value: object, field: str) -> str:
    """A stripped non-empty string, or the triad for a blank one."""
    if not isinstance(value, str) or not value.strip():
        raise MnemoError(
            f"{field} is blank.",
            f"a card needs text on both sides; a blank {field} cannot be studied or scheduled.",
            f"pass a non-empty {field}, e.g. mnemo add \"What is SM-2?\" --back \"a scheduling algorithm\".",
        )
    return value.strip()


def parse_front(value: object) -> str:
    """The question side of a card, stripped and non-empty."""
    return _nonblank(value, "front")


def parse_back(value: object) -> str:
    """The answer side of a card, stripped and non-empty."""
    return _nonblank(value, "back")


def normalize_deck(value: Optional[str]) -> str:
    """The deck label: stripped, lowercased, capped, defaulting to 'default'."""
    if value is None:
        return DECK_DEFAULT
    if not isinstance(value, str) or not value.strip():
        raise MnemoError(
            "The deck name is blank.",
            "a card belongs to exactly one named deck, and a blank name cannot select one.",
            "pass a deck name such as --deck japanese, or drop --deck to use 'default'.",
        )
    return value.strip().lower()[:MAX_DECK_CHARS]


def parse_card_id(value: str) -> int:
    """A positive integer card id, as shown by `list`."""
    try:
        card_id = int(value)
    except (TypeError, ValueError):
        card_id = 0
    if card_id < 1:
        raise MnemoError(
            f"'{value}' is not a card id.",
            "commands that address one card need the id shown by `mnemo list`.",
            "run `mnemo list`, then pass one of the ids it prints, e.g. `mnemo remove 3`.",
        )
    return card_id


def parse_iso_date(value: object, field: str = "date") -> str:
    """A strict YYYY-MM-DD string, validated by both shape and calendar."""
    if not isinstance(value, str) or not _ISO_DATE.match(value):
        raise MnemoError(
            f"{value!r} is not a date.",
            "dates are strict ISO calendar days so scheduling stays unambiguous.",
            "write the date as YYYY-MM-DD, e.g. 2026-10-21.",
        )
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise MnemoError(
            f"{value!r} is not a real calendar date.",
            f"{exc}",
            "pick an existing day, e.g. 2026-10-21.",
        ) from exc
    return value


def _bounded_int(record: Dict[str, object], key: str, default: int, minimum: int = 0) -> int:
    """An integer field of a stored record, defaulting when absent."""
    value = record.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise MnemoError(
            f"stored {key} is {value!r}.",
            "the deck file's numbers must be plain integers at or above their floor.",
            f"restore the deck's .bak, or edit the file so {key} is an integer >= {minimum}.",
        )
    return value


@dataclass(frozen=True)
class Card:
    """One flashcard and its complete SM-2 scheduling state."""

    id: int
    front: str
    back: str
    deck: str
    due: str
    added: str
    ease: float = EASE_DEFAULT
    interval_days: int = 0
    repetitions: int = 0
    lapses: int = 0

    def __post_init__(self) -> None:
        if isinstance(self.id, bool) or not isinstance(self.id, int) or self.id < 1:
            raise MnemoError(
                f"card id is {self.id!r}.",
                "ids address cards in every command, so each is a positive integer.",
                "restore the deck's .bak, or edit the file so the id is a positive integer.",
            )
        if isinstance(self.ease, bool) or not isinstance(self.ease, (int, float)) \
                or self.ease < EASE_FLOOR:
            raise MnemoError(
                f"card {self.id} has ease {self.ease!r}.",
                f"the SM-2 ease factor never drops below {EASE_FLOOR}.",
                f"restore the deck's .bak, or edit the file so ease is >= {EASE_FLOOR}.",
            )
        parse_iso_date(self.due, "due")
        parse_iso_date(self.added, "added")

    def as_dict(self) -> Dict[str, object]:
        """The stored form of the card, including every defaulted field."""
        return {
            "id": self.id,
            "front": self.front,
            "back": self.back,
            "deck": self.deck,
            "due": self.due,
            "added": self.added,
            "ease": self.ease,
            "interval_days": self.interval_days,
            "repetitions": self.repetitions,
            "lapses": self.lapses,
        }

    @classmethod
    def from_dict(cls, record: object) -> "Card":
        """Rebuild a card from its stored form, validating every field."""
        if not isinstance(record, dict):
            raise MnemoError(
                "a stored card is not an object.",
                "each card is one JSON object with its text and scheduling fields.",
                "restore the deck's .bak, or remove the broken entry from the file.",
            )
        return cls(
            id=record.get("id", 0),
            front=_nonblank(record.get("front"), "front"),
            back=_nonblank(record.get("back"), "back"),
            deck=normalize_deck(record.get("deck")),
            due=parse_iso_date(record.get("due"), "due"),
            added=parse_iso_date(record.get("added"), "added"),
            ease=float(record.get("ease", EASE_DEFAULT)),
            interval_days=_bounded_int(record, "interval_days", 0),
            repetitions=_bounded_int(record, "repetitions", 0),
            lapses=_bounded_int(record, "lapses", 0),
        )


@dataclass(frozen=True)
class Review:
    """One graded answer, the atom of the review log and of every statistic."""

    card_id: int
    date: str
    quality: int

    def __post_init__(self) -> None:
        if isinstance(self.card_id, bool) or not isinstance(self.card_id, int) or self.card_id < 1:
            raise MnemoError(
                f"review names card {self.card_id!r}.",
                "a review belongs to one card id, a positive integer.",
                "restore the deck's .bak, or remove the broken entry from the file.",
            )
        if isinstance(self.quality, bool) or not isinstance(self.quality, int) \
                or not GRADE_MIN <= self.quality <= GRADE_MAX:
            raise MnemoError(
                f"review quality is {self.quality!r}.",
                f"grades are the SM-2 integers {GRADE_MIN} to {GRADE_MAX}.",
                f"restore the deck's .bak, or edit the file so quality is {GRADE_MIN}..{GRADE_MAX}.",
            )
        parse_iso_date(self.date, "date")

    def as_dict(self) -> Dict[str, object]:
        """The stored form of the review."""
        return {"card_id": self.card_id, "date": self.date, "quality": self.quality}

    @classmethod
    def from_dict(cls, record: object) -> "Review":
        """Rebuild a review from its stored form, validating every field."""
        if not isinstance(record, dict):
            raise MnemoError(
                "a stored review is not an object.",
                "each review is one JSON object with a card id, a date and a quality.",
                "restore the deck's .bak, or remove the broken entry from the file.",
            )
        return cls(
            card_id=record.get("card_id", 0),
            date=parse_iso_date(record.get("date"), "date"),
            quality=record.get("quality", -1),
        )
