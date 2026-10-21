"""Command-line interface: `add` and `list` over one deck file."""

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import Optional, Sequence

from mnemo.deck import Deck
from mnemo.errors import MnemoError
from mnemo.models import normalize_deck, parse_back, parse_front
from mnemo.scheduler import is_due, maturity
from mnemo.stats import summarize
from mnemo.storage import StateStore
from mnemo.study import run_session

DEFAULT_DB = "mnemo.json"
DEFAULT_SESSION_LIMIT = 20


def build_parser() -> argparse.ArgumentParser:
    """The command grammar; `--db` selects the deck file for every command."""
    parser = argparse.ArgumentParser(
        prog="mnemo",
        description="A dependency-free, local-first spaced-repetition flashcard CLI (SM-2).",
    )
    parser.add_argument(
        "--db",
        default=DEFAULT_DB,
        help=f"deck file to use (default: {DEFAULT_DB})",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    add = commands.add_parser("add", help="record a new flashcard")
    add.add_argument("front", help="the question side of the card")
    add.add_argument("--back", "-b", default=None, help="the answer side of the card")
    add.add_argument("--deck", "-d", default=None, help="deck label (default: default)")

    listing = commands.add_parser("list", help="list cards, oldest first")
    listing.add_argument("--due", action="store_true", help="only cards due today")

    study = commands.add_parser("study", help="review due cards in a guided session")
    study.add_argument("--limit", "-l", type=int, default=DEFAULT_SESSION_LIMIT,
                       help=f"cards to review at most (default: {DEFAULT_SESSION_LIMIT})")

    commands.add_parser("stats", help="deck counts, retention and a 7-day due forecast")
    return parser


def run_add(deck: Deck, args: argparse.Namespace) -> None:
    """Validate the arguments, record the card and echo it."""
    card = deck.add_card(
        front=parse_front(args.front),
        back=parse_back(args.back),
        deck=normalize_deck(args.deck),
        today=date.today().isoformat(),
    )
    print(f"Added #{card.id}: {card.front}  ->  {card.back}  [{card.deck}]")


def run_list(deck: Deck, args: argparse.Namespace) -> None:
    """Print one line per card, or say the deck is empty."""
    cards = deck.entries()
    if args.due:
        today = date.today().isoformat()
        cards = [card for card in cards if is_due(card, today)]
    if not cards:
        message = "No cards due today." if args.due else \
            "No cards yet. Add one with: mnemo add \"question\" --back \"answer\""
        print(message)
        return
    for card in cards:
        print(f"#{card.id:<3} due {card.due}  {maturity(card):<7}  "
              f"[{card.deck}]  {card.front}  ->  {card.back}")


def run_study(deck: Deck, args: argparse.Namespace) -> None:
    """Run one guided session over the due cards, reading stdin line by line."""
    if args.limit < 1:
        raise MnemoError(
            f"--limit is {args.limit}.",
            "a session reviews at least one card, so the limit is a positive integer.",
            "pass --limit 20, or drop the flag to use the default.",
        )

    def read_line():
        try:
            return input()
        except EOFError:
            return None

    run_session(deck, date.today().isoformat(), args.limit, read_line, print)


def run_stats(deck: Deck, args: argparse.Namespace) -> None:
    """Print the deck's counts, retention and seven-day due forecast."""
    state = deck.snapshot()
    stats = summarize(state.cards, state.reviews, date.today().isoformat())
    retention = "n/a (no reviews yet)" if stats.retention is None else f"{stats.retention:.0%}"
    print(f"cards: {stats.total}  ({stats.due_today} due today)")
    print(f"new: {stats.new_cards}  learning: {stats.learning}  mature: {stats.mature}")
    print(f"reviews logged: {stats.reviews_logged}  retention: {retention}")
    print("due next 7 days:")
    for due_day, count in stats.forecast:
        print(f"  {due_day}  {count}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run one command; user errors print the Why/Fix triad and exit 1."""
    args = build_parser().parse_args(argv)
    deck = Deck(StateStore(Path(args.db)))
    try:
        if args.command == "add":
            run_add(deck, args)
        elif args.command == "study":
            run_study(deck, args)
        elif args.command == "stats":
            run_stats(deck, args)
        else:
            run_list(deck, args)
    except MnemoError as error:
        print(error.render(), file=sys.stderr)
        return 1
    return 0
