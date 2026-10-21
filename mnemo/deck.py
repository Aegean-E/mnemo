"""Deck operations: adding, finding, listing, due selection and review recording."""

from typing import List

from mnemo.errors import MnemoError
from mnemo.models import Card, EASE_DEFAULT, Review, parse_iso_date
from mnemo.scheduler import is_due, next_state
from mnemo.storage import DeckState, StateStore


class Deck:
    """The card operations one command needs, backed by one deck file."""

    def __init__(self, store: StateStore):
        self.store = store

    def add_card(self, front: str, back: str, deck: str, today: str) -> Card:
        """Record a new card, due today, and return it with its assigned id."""
        parse_iso_date(today, "today")
        created: List[Card] = []

        def mutate(state: DeckState) -> DeckState:
            card = Card(
                id=max((existing.id for existing in state.cards), default=0) + 1,
                front=front,
                back=back,
                deck=deck,
                due=today,
                added=today,
                ease=EASE_DEFAULT,
            )
            created.append(card)
            return DeckState(cards=state.cards + [card], reviews=state.reviews)

        self.store.update(mutate)
        return created[0]

    def entries(self) -> List[Card]:
        """Every card, sorted by id."""
        return sorted(self.store.read().cards, key=lambda card: card.id)

    def due_cards(self, today: str) -> List[Card]:
        """Every card due on `today` or earlier, earliest due first."""
        due = [card for card in self.store.read().cards if is_due(card, today)]
        return sorted(due, key=lambda card: (card.due, card.id))

    def find(self, card_id: int) -> Card:
        """One card by id, or the Why/Fix triad when it is absent."""
        for card in self.entries():
            if card.id == card_id:
                return card
        raise MnemoError(
            f"There is no card #{card_id}.",
            "commands that address one card need an id the deck actually holds.",
            "run `mnemo list`, then pass one of the ids it prints.",
        )

    def record_review(self, card_id: int, quality: int, today: str) -> Card:
        """Grade one answer: persist the card's next SM-2 state and append the log entry."""
        parse_iso_date(today, "today")
        updated: List[Card] = []

        def mutate(state: DeckState) -> DeckState:
            target = next((card for card in state.cards if card.id == card_id), None)
            if target is None:
                raise MnemoError(
                    f"There is no card #{card_id}.",
                    "a review is recorded against a card the deck actually holds.",
                    "run `mnemo list`, then grade one of the ids it prints.",
                )
            card = next_state(target, quality, today)
            updated.append(card)
            reviews = state.reviews + [Review(card_id=card_id, date=today, quality=quality)]
            return DeckState(
                cards=[card if existing.id == card_id else existing for existing in state.cards],
                reviews=reviews,
            )

        self.store.update(mutate)
        return updated[0]
