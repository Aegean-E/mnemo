"""Tests of the pure deck statistics over cards, reviews and a fixed day."""

import unittest

from mnemo.models import Card, Review
from mnemo.stats import summarize


def make_card(card_id: int, **overrides) -> Card:
    fields = dict(id=card_id, front=f"front {card_id}", back="back", deck="default",
                  due="2026-10-21", added="2026-10-01")
    fields.update(overrides)
    return Card(**fields)


class SummarizeTests(unittest.TestCase):
    def test_counts_by_maturity_and_due(self):
        cards = [
            make_card(1),
            make_card(2, repetitions=2, interval_days=6),
            make_card(3, repetitions=4, interval_days=30),
            make_card(4, due="2026-10-22"),
        ]
        stats = summarize(cards, [], "2026-10-21")
        self.assertEqual(stats.total, 4)
        self.assertEqual(stats.due_today, 3)
        self.assertEqual((stats.new_cards, stats.learning, stats.mature), (2, 1, 1))

    def test_retention_from_the_review_log(self):
        reviews = [Review(card_id=1, date="2026-10-20", quality=4),
                   Review(card_id=1, date="2026-10-20", quality=3),
                   Review(card_id=1, date="2026-10-21", quality=1),
                   Review(card_id=1, date="2026-10-21", quality=5)]
        stats = summarize([], reviews, "2026-10-21")
        self.assertEqual(stats.reviews_logged, 4)
        self.assertAlmostEqual(stats.retention, 0.75)

    def test_retention_is_absent_without_reviews(self):
        stats = summarize([], [], "2026-10-21")
        self.assertIsNone(stats.retention)

    def test_forecast_covers_seven_days_from_today(self):
        cards = [
            make_card(1),
            make_card(2, due="2026-10-22"),
            make_card(3, due="2026-10-27"),
            make_card(4, due="2026-10-28"),
        ]
        stats = summarize(cards, [], "2026-10-21")
        self.assertEqual([count for _day, count in stats.forecast],
                         [1, 1, 0, 0, 0, 0, 1])
        self.assertEqual(stats.forecast[0][0], "2026-10-21")

    def test_empty_deck(self):
        stats = summarize([], [], "2026-10-21")
        self.assertEqual(stats.total, 0)
        self.assertEqual(stats.due_today, 0)
        self.assertEqual([count for _day, count in stats.forecast], [0] * 7)


if __name__ == "__main__":
    unittest.main()
