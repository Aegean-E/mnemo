"""Tests of the SM-2 scheduling functions, pinned to exact dates and values."""

import unittest

from mnemo.errors import MnemoError
from mnemo.models import Card
from mnemo.scheduler import grade_from_text, is_due, maturity, next_state


def make_card(**overrides) -> Card:
    fields = dict(id=1, front="front", back="back", deck="default",
                  due="2026-10-21", added="2026-10-01")
    fields.update(overrides)
    return Card(**fields)


class GradeParsingTests(unittest.TestCase):
    def test_grade_from_text_accepts_digits(self):
        for digit in "012345":
            self.assertEqual(grade_from_text(digit), int(digit))

    def test_grade_from_text_accepts_words_case_insensitively(self):
        self.assertEqual(grade_from_text("again"), 1)
        self.assertEqual(grade_from_text("Hard"), 3)
        self.assertEqual(grade_from_text("GOOD"), 4)
        self.assertEqual(grade_from_text("easy"), 5)

    def test_grade_from_text_rejects_other_answers(self):
        for bad in ("6", "-1", "later", "", "  "):
            with self.assertRaises(MnemoError) as raised:
                grade_from_text(bad)
            self.assertIn("Fix:", raised.exception.render())


class NextStateTests(unittest.TestCase):
    def test_first_successful_review(self):
        updated = next_state(make_card(), quality=4, today="2026-10-21")
        self.assertEqual(updated.repetitions, 1)
        self.assertEqual(updated.interval_days, 1)
        self.assertEqual(updated.due, "2026-10-22")
        self.assertAlmostEqual(updated.ease, 1.96)

    def test_second_successful_review_uses_six_days(self):
        once = next_state(make_card(), quality=4, today="2026-10-20")
        updated = next_state(once, quality=4, today="2026-10-21")
        self.assertEqual(updated.repetitions, 2)
        self.assertEqual(updated.interval_days, 6)
        self.assertEqual(updated.due, "2026-10-27")
        self.assertAlmostEqual(updated.ease, 1.42)

    def test_third_review_multiplies_interval_by_updated_ease(self):
        card = make_card(repetitions=2, interval_days=6, ease=2.0)
        updated = next_state(card, quality=4, today="2026-10-21")
        self.assertEqual(updated.repetitions, 3)
        self.assertEqual(updated.interval_days, 9)
        self.assertEqual(updated.due, "2026-10-30")
        self.assertAlmostEqual(updated.ease, 1.46)

    def test_failed_review_resets_the_streak(self):
        card = make_card(repetitions=3, interval_days=20, ease=2.5, lapses=0)
        updated = next_state(card, quality=1, today="2026-10-21")
        self.assertEqual(updated.repetitions, 0)
        self.assertEqual(updated.interval_days, 1)
        self.assertEqual(updated.lapses, 1)
        self.assertEqual(updated.due, "2026-10-22")
        self.assertAlmostEqual(updated.ease, 2.5)

    def test_zero_grade_keeps_the_published_formula(self):
        updated = next_state(make_card(ease=2.5), quality=0, today="2026-10-21")
        self.assertAlmostEqual(updated.ease, 2.6)

    def test_ease_never_drops_below_the_floor(self):
        card = make_card(ease=1.31)
        updated = next_state(card, quality=2, today="2026-10-21")
        self.assertAlmostEqual(updated.ease, 1.3)

    def test_out_of_range_quality_is_refused(self):
        for quality in (-1, 6):
            with self.assertRaises(MnemoError):
                next_state(make_card(), quality=quality, today="2026-10-21")

    def test_identity_fields_survive_and_input_is_untouched(self):
        card = make_card(repetitions=2, interval_days=6)
        updated = next_state(card, quality=5, today="2026-10-21")
        self.assertEqual((updated.id, updated.front, updated.back, updated.deck, updated.added),
                         (card.id, card.front, card.back, card.deck, card.added))
        self.assertEqual(card.repetitions, 2)
        self.assertEqual(updated.lapses, card.lapses)


class DueAndMaturityTests(unittest.TestCase):
    def test_is_due_compares_iso_dates(self):
        self.assertTrue(is_due(make_card(due="2026-10-21"), "2026-10-21"))
        self.assertTrue(is_due(make_card(due="2026-10-20"), "2026-10-21"))
        self.assertFalse(is_due(make_card(due="2026-10-22"), "2026-10-21"))

    def test_maturity_splits_new_learning_and_mature(self):
        self.assertEqual(maturity(make_card(repetitions=0)), "new")
        self.assertEqual(maturity(make_card(repetitions=2, interval_days=6)), "learning")
        self.assertEqual(maturity(make_card(repetitions=4, interval_days=21)), "mature")


if __name__ == "__main__":
    unittest.main()
