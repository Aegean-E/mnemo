"""Command-line interface: `add` and `list` over one deck file."""

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import Optional, Sequence

from mnemo.deck import Deck, select_deck
from mnemo.errors import MnemoError
from mnemo.models import normalize_deck, parse_back, parse_card_id, parse_front
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
    listing.add_argument("--deck", "-d", default=None, help="only this deck")

    study = commands.add_parser("study", help="review due cards in a guided session")
    study.add_argument("--limit", "-l", type=int, default=DEFAULT_SESSION_LIMIT,
                       help=f"cards to review at most (default: {DEFAULT_SESSION_LIMIT})")
    study.add_argument("--deck", "-d", default=None, help="only this deck")

    stats = commands.add_parser("stats", help="deck counts, retention and a 7-day due forecast")
    stats.add_argument("--deck", "-d", default=None, help="only this deck")

    edit = commands.add_parser("edit", help="change fields of an existing card")
    edit.add_argument("card_id", help="id shown by list")
    edit.add_argument("--front", "-f", default=None, help="new front text")
    edit.add_argument("--back", "-b", default=None, help="new back text")
    edit.add_argument("--deck", "-d", default=None, help="new deck label")

    remove = commands.add_parser("remove", help="delete a card by id")
    remove.add_argument("card_id", help="id shown by list")
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
    deck_name = normalize_deck(args.deck) if args.deck else None
    cards = deck.entries(deck_name)
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


def run_edit(deck: Deck, args: argparse.Namespace) -> None:
    """Apply the given fields and echo the updated card."""
    if args.front is None and args.back is None and args.deck is None:
        raise MnemoError(
            "Nothing to change.",
            "`edit` changes only the fields you name, and no field was named.",
            "pass at least one of --front, --back or --deck.",
        )
    card = deck.edit_card(
        parse_card_id(args.card_id),
        front=parse_front(args.front) if args.front is not None else None,
        back=parse_back(args.back) if args.back is not None else None,
        deck=normalize_deck(args.deck) if args.deck is not None else None,
    )
    print(f"Updated #{card.id}: {card.front}  ->  {card.back}  [{card.deck}]")


def run_remove(deck: Deck, args: argparse.Namespace) -> None:
    """Delete one card and echo what was removed."""
    card = deck.remove_card(parse_card_id(args.card_id))
    print(f"Removed #{card.id}: {card.front}  ->  {card.back}  [{card.deck}]")


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

    run_session(deck, date.today().isoformat(), args.limit, read_line, print,
                deck_name=normalize_deck(args.deck) if args.deck else None)


def run_stats(deck: Deck, args: argparse.Namespace) -> None:
    """Print the deck's counts, retention and seven-day due forecast."""
    deck_name = normalize_deck(args.deck) if args.deck else None
    state = deck.snapshot()
    cards = select_deck(state.cards, deck_name)
    reviews = state.reviews if deck_name is None else [
        review for review in state.reviews
        if review.card_id in {card.id for card in cards}
    ]
    stats = summarize(cards, reviews, date.today().isoformat())
    retention = "n/a (no reviews yet)" if stats.retention is None else f"{stats.retention:.0%}"
    print(f"cards: {stats.total}  ({stats.due_today} due today)")
    print(f"new: {stats.new_cards}  learning: {stats.learning}  mature: {stats.mature}")
    print(f"reviews logged: {stats.reviews_logged}  retention: {retention}")
    print("due next 7 days:")
    for due_day, count in stats.forecast:
        print(f"  {due_day}  {count}")


def _utf8_streams() -> None:
    """Print UTF-8 on any console; a stream that cannot reconfigure keeps its own encoding."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            continue


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run one command; user errors print the Why/Fix triad and exit 1."""
    _utf8_streams()
    args = build_parser().parse_args(argv)
    deck = Deck(StateStore(Path(args.db)))
    try:
        if args.command == "add":
            run_add(deck, args)
        elif args.command == "study":
            run_study(deck, args)
        elif args.command == "stats":
            run_stats(deck, args)
        elif args.command == "edit":
            run_edit(deck, args)
        elif args.command == "remove":
            run_remove(deck, args)
        else:
            run_list(deck, args)
    except MnemoError as error:
        print(error.render(), file=sys.stderr)
        return 1
    return 0
