"""The study session engine: due queue, reveal, grade and summary, with injected I/O."""

from dataclasses import dataclass
from typing import Callable, Optional

from mnemo.deck import Deck
from mnemo.errors import MnemoError
from mnemo.scheduler import grade_from_text, is_due

REVEAL_PROMPT = "Press Enter to reveal (q quits)."
GRADE_PROMPT = "Grade 0-5 / again, hard, good, easy (q quits):"
GRADE_HINT = "Not a grade. Use a digit 0-5 or again, hard, good, easy."


@dataclass(frozen=True)
class SessionReport:
    """What one study session did, as its summary line reports it."""

    reviewed: int
    passed: int
    lapsed: int
    quit_early: bool


def _wants_quit(line: Optional[str]) -> bool:
    """Whether a read line is an explicit quit or the end of the input."""
    return line is None or line.strip().lower() == "q"


def _ask_grade(read_line: Callable[[], Optional[str]],
               write_line: Callable[[str], None]) -> Optional[int]:
    """Read grades until one is valid; None when the reader quits or ends."""
    while True:
        write_line(GRADE_PROMPT)
        line = read_line()
        if _wants_quit(line):
            return None
        try:
            return grade_from_text(line)
        except MnemoError:
            write_line(GRADE_HINT)


def _announce_empty(deck: Deck, write_line: Callable[[str], None]) -> None:
    """Say why no session can run: an empty deck or nothing due."""
    cards = deck.entries()
    if not cards:
        write_line("No cards yet. Add one first.")
        return
    write_line(f"No cards due today. Next due: {min(card.due for card in cards)}.")


def _summarize(deck: Deck, today: str, reviewed: int, passed: int, lapsed: int,
               write_line: Callable[[str], None]) -> None:
    """Close the session with its counts and what the deck waits for now."""
    write_line(f"Session done: {reviewed} reviewed, {passed} passed, {lapsed} lapsed.")
    cards = deck.entries()
    remaining = [card for card in cards if is_due(card, today)]
    if remaining:
        noun = "card" if len(remaining) == 1 else "cards"
        write_line(f"{len(remaining)} {noun} still due today.")
    elif cards:
        write_line(f"Next session: {min(card.due for card in cards)}.")


def run_session(deck: Deck, today: str, limit: int,
                read_line: Callable[[], Optional[str]],
                write_line: Callable[[str], None],
                deck_name: Optional[str] = None) -> SessionReport:
    """Run one bounded session over the due cards; q and end-of-input quit gracefully."""
    queue = deck.due_cards(today, deck_name)[:limit]
    if not queue:
        _announce_empty(deck, write_line)
        return SessionReport(reviewed=0, passed=0, lapsed=0, quit_early=False)
    reviewed = passed = lapsed = 0
    quit_early = False
    for position, card in enumerate(queue, start=1):
        write_line(f"Card #{card.id} [{card.deck}]  ({position}/{len(queue)})")
        write_line(f"  Q: {card.front}")
        write_line(REVEAL_PROMPT)
        if _wants_quit(read_line()):
            quit_early = True
            break
        write_line(f"  A: {card.back}")
        quality = _ask_grade(read_line, write_line)
        if quality is None:
            quit_early = True
            break
        deck.record_review(card.id, quality, today)
        reviewed += 1
        if quality >= 3:
            passed += 1
        else:
            lapsed += 1
    _summarize(deck, today, reviewed, passed, lapsed, write_line)
    return SessionReport(reviewed=reviewed, passed=passed, lapsed=lapsed, quit_early=quit_early)
