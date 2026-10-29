"""Tests of the card and review value objects and their parsing rules."""

import unittest

from mnemo.errors import MnemoError
from mnemo.models import (
    Card,
    Review,
    normalize_deck,
    parse_back,
    parse_card_id,
    parse_front,
    parse_iso_date,
)


class ParseTests(unittest.TestCase):
    def test_parse_front_strips_surrounding_space(self):
        self.assertEqual(parse_front("  What is SM-2? "), "What is SM-2?")

    def test_parse_front_rejects_blank(self):
        with self.assertRaises(MnemoError) as raised:
            parse_front("   ")
        self.assertIn("Why:", raised.exception.render())

    def test_parse_back_rejects_blank(self):
        with self.assertRaises(MnemoError):
            parse_back("")

    def test_normalize_deck_defaults_lowercases_and_caps_length(self):
        self.assertEqual(normalize_deck(None), "default")
        self.assertEqual(normalize_deck("  Japanese "), "japanese")
        self.assertEqual(len(normalize_deck("x" * 80)), 64)

    def test_normalize_deck_rejects_blank(self):
        with self.assertRaises(MnemoError):
            normalize_deck("   ")

    def test_parse_card_id_accepts_positive_integers(self):
        self.assertEqual(parse_card_id("7"), 7)

    def test_parse_card_id_rejects_non_positive_or_garbled(self):
        for bad in ("0", "-3", "two", ""):
            with self.assertRaises(MnemoError):
                parse_card_id(bad)

    def test_parse_iso_date_round_trips_valid_dates(self):
        self.assertEqual(parse_iso_date("2026-10-21"), "2026-10-21")

    def test_parse_iso_date_rejects_non_dates(self):
        for bad in ("21-10-2026", "2026-2-3", "not-a-date", ""):
            with self.assertRaises(MnemoError):
                parse_iso_date(bad)


class CardTests(unittest.TestCase):
    def test_new_card_defaults(self):
        card = Card(id=1, front="front", back="back", deck="default",
                    due="2026-10-21", added="2026-10-21")
        self.assertEqual(card.ease, 2.5)
        self.assertEqual(card.interval_days, 0)
        self.assertEqual(card.repetitions, 0)
        self.assertEqual(card.lapses, 0)

    def test_card_round_trips_through_dicts(self):
        card = Card(id=3, front="front", back="back", deck="kana",
                    due="2026-10-21", added="2026-10-01", ease=2.2,
                    interval_days=6, repetitions=2, lapses=1)
        self.assertEqual(Card.from_dict(card.as_dict()), card)

    def test_card_from_dict_fills_absent_optional_fields(self):
        card = Card.from_dict({"id": 1, "front": "f", "back": "b", "deck": "default",
                               "due": "2026-10-21", "added": "2026-10-21"})
        self.assertEqual(card.ease, 2.5)
        self.assertEqual(card.interval_days, 0)
        self.assertEqual(card.repetitions, 0)
        self.assertEqual(card.lapses, 0)

    def test_card_from_dict_rejects_bad_records(self):
        base = {"id": 1, "front": "f", "back": "b", "deck": "default",
                "due": "2026-10-21", "added": "2026-10-21"}
        bad_records = [
            {**base, "ease": 1.0},
            {**base, "ease": "high"},
            {**base, "ease": None},
            {**base, "ease": float("nan")},
            {**base, "ease": float("inf")},
            {**base, "interval_days": -1},
            {**base, "repetitions": -2},
            {**base, "lapses": -1},
            {**base, "due": "tomorrow"},
            {k: v for k, v in base.items() if k != "front"},
        ]
        for record in bad_records:
            with self.assertRaises(MnemoError):
                Card.from_dict(record)

    def test_card_rejects_negative_or_boolean_scheduling_counters(self):
        base = dict(id=1, front="f", back="b", deck="default",
                    due="2026-10-21", added="2026-10-21")
        for field in ("interval_days", "repetitions", "lapses"):
            for value in (-1, True):
                with self.subTest(field=field, value=value):
                    with self.assertRaises(MnemoError):
                        Card(**base, **{field: value})


class ReviewTests(unittest.TestCase):
    def test_review_round_trips_through_dicts(self):
        review = Review(card_id=1, date="2026-10-21", quality=4)
        self.assertEqual(Review.from_dict(review.as_dict()), review)

    def test_review_rejects_out_of_range_quality(self):
        for quality in (-1, 6):
            with self.assertRaises(MnemoError):
                Review(card_id=1, date="2026-10-21", quality=quality).as_dict()


if __name__ == "__main__":
    unittest.main()
