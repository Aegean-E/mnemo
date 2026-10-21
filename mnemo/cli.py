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
from mnemo.storage import StateStore

DEFAULT_DB = "mnemo.json"


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


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run one command; user errors print the Why/Fix triad and exit 1."""
    args = build_parser().parse_args(argv)
    deck = Deck(StateStore(Path(args.db)))
    try:
        if args.command == "add":
            run_add(deck, args)
        else:
            run_list(deck, args)
    except MnemoError as error:
        print(error.render(), file=sys.stderr)
        return 1
    return 0
