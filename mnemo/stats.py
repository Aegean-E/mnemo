"""Deck statistics: pure counts, retention and forecast over cards, reviews and one day."""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Optional, Sequence, Tuple

from mnemo.models import Card, Review, parse_iso_date
from mnemo.scheduler import is_due, maturity

FORECAST_DAYS = 7


@dataclass(frozen=True)
class DeckStats:
    """One deck's position on a day, as the `stats` command reports it."""

    total: int
    due_today: int
    new_cards: int
    learning: int
    mature: int
    reviews_logged: int
    retention: Optional[float]
    forecast: List[Tuple[str, int]]


def summarize(cards: Sequence[Card], reviews: Sequence[Review], today: str) -> DeckStats:
    """The deck's counts, retention and seven-day due forecast for `today`."""
    day = parse_iso_date(today, "today")
    stages = [maturity(card) for card in cards]
    forecast = []
    for offset in range(FORECAST_DAYS):
        due_day = (date.fromisoformat(day) + timedelta(days=offset)).isoformat()
        forecast.append((due_day, sum(1 for card in cards if card.due == due_day)))
    passed = sum(1 for review in reviews if review.quality >= 3)
    retention = passed / len(reviews) if reviews else None
    return DeckStats(
        total=len(cards),
        due_today=sum(1 for card in cards if is_due(card, day)),
        new_cards=stages.count("new"),
        learning=stages.count("learning"),
        mature=stages.count("mature"),
        reviews_logged=len(reviews),
        retention=retention,
        forecast=forecast,
    )
