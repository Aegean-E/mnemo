"""Tests of deck operations over the atomic store."""

import shutil
import tempfile
import unittest
from pathlib import Path

from mnemo.deck import Deck
from mnemo.errors import MnemoError
from mnemo.storage import DeckState, StateStore


class DeckTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="mnemo-deck-"))
        self.addCleanup(shutil.rmtree, self.temp_dir, ignore_errors=True)
        self.path = self.temp_dir / "mnemo.json"
        self.deck = Deck(StateStore(self.path))

    def test_add_assigns_sequential_ids(self):
        first = self.deck.add_card("front 1", "back 1", "default", "2026-10-21")
        second = self.deck.add_card("front 2", "back 2", "default", "2026-10-21")
        self.assertEqual((first.id, second.id), (1, 2))

    def test_new_card_is_due_the_day_it_is_added(self):
        card = self.deck.add_card("front", "back", "default", "2026-10-21")
        self.assertEqual(card.due, "2026-10-21")
        self.assertEqual(card.added, "2026-10-21")
        self.assertEqual(card.deck, "default")

    def test_entries_are_sorted_by_id(self):
        self.deck.add_card("front 2", "back", "default", "2026-10-21")
        self.deck.add_card("front 1", "back", "default", "2026-10-21")
        self.assertEqual([card.front for card in self.deck.entries()], ["front 2", "front 1"])

    def test_add_and_edit_normalize_text_and_deck(self):
        card = self.deck.add_card("  front  ", "  back  ", " Japanese ", "2026-10-21")
        self.assertEqual((card.front, card.back, card.deck), ("front", "back", "japanese"))
        updated = self.deck.edit_card(1, front="  new front  ", deck=" Kana ")
        self.assertEqual((updated.front, updated.deck), ("new front", "kana"))

    def test_find_returns_the_card(self):
        self.deck.add_card("front", "back", "kana", "2026-10-21")
        self.assertEqual(self.deck.find(1).deck, "kana")

    def test_find_missing_card_raises_the_triad(self):
        with self.assertRaises(MnemoError) as raised:
            self.deck.find(5)
        rendered = raised.exception.render()
        self.assertIn("Why:", rendered)
        self.assertIn("Fix:", rendered)

    def test_state_persists_across_instances(self):
        self.deck.add_card("front", "back", "default", "2026-10-21")
        reopened = Deck(StateStore(self.path))
        self.assertEqual([card.front for card in reopened.entries()], ["front"])

    def test_due_cards_return_only_today_and_earlier(self):
        self.deck.add_card("later", "back", "default", "2026-10-21")
        self.deck.add_card("now", "back", "default", "2026-10-21")
        from dataclasses import replace
        StateStore(self.path).update(
            lambda state: DeckState(
                cards=[replace(state.cards[0], due="2026-10-25"), state.cards[1]],
                reviews=[])
        )
        due = self.deck.due_cards("2026-10-21")
        self.assertEqual([card.front for card in due], ["now"])

    def test_record_review_updates_card_and_log(self):
        self.deck.add_card("front", "back", "default", "2026-10-21")
        updated = self.deck.record_review(1, 4, "2026-10-21")
        self.assertEqual(updated.repetitions, 1)
        self.assertEqual(updated.due, "2026-10-22")
        self.assertEqual(self.deck.find(1).due, "2026-10-22")
        self.assertEqual(len(self.deck.store.read().reviews), 1)

    def test_record_review_missing_card_raises(self):
        with self.assertRaises(MnemoError):
            self.deck.record_review(9, 4, "2026-10-21")

    def test_edit_card_changes_only_the_given_fields(self):
        self.deck.add_card("front", "back", "default", "2026-10-21")
        self.deck.record_review(1, 4, "2026-10-21")
        updated = self.deck.edit_card(1, back="new back")
        self.assertEqual(updated.back, "new back")
        self.assertEqual(updated.front, "front")
        self.assertEqual(updated.deck, "default")
        self.assertEqual(updated.due, "2026-10-22")
        self.assertEqual(updated.ease, self.deck.find(1).ease)

    def test_edit_card_missing_raises(self):
        with self.assertRaises(MnemoError):
            self.deck.edit_card(9, back="new back")

    def test_remove_card_returns_it_and_frees_the_id(self):
        self.deck.add_card("front 1", "back", "default", "2026-10-21")
        self.deck.add_card("front 2", "back", "default", "2026-10-21")
        removed = self.deck.remove_card(2)
        self.assertEqual(removed.front, "front 2")
        self.assertEqual([card.id for card in self.deck.entries()], [1])
        rewritten = self.deck.add_card("front 3", "back", "default", "2026-10-21")
        self.assertEqual(rewritten.id, 2)

    def test_removing_a_reviewed_card_does_not_reuse_its_id(self):
        first = self.deck.add_card("front 1", "back", "default", "2026-10-21")
        self.deck.record_review(first.id, 4, "2026-10-21")
        self.deck.remove_card(first.id)
        new = self.deck.add_card("front 2", "back", "default", "2026-10-21")
        self.assertEqual(new.id, 2)
        self.assertEqual([review.card_id for review in self.deck.store.read().reviews], [1])

    def test_remove_card_missing_raises(self):
        with self.assertRaises(MnemoError):
            self.deck.remove_card(9)

    def test_entries_filter_by_deck(self):
        self.deck.add_card("alpha", "back", "alpha", "2026-10-21")
        self.deck.add_card("beta", "back", "beta", "2026-10-21")
        self.assertEqual([card.front for card in self.deck.entries(deck_name="alpha")], ["alpha"])
        self.assertEqual(len(self.deck.entries()), 2)

    def test_due_cards_filter_by_deck(self):
        self.deck.add_card("alpha", "back", "alpha", "2026-10-21")
        self.deck.add_card("beta", "back", "beta", "2026-10-21")
        due = self.deck.due_cards("2026-10-21", deck_name="beta")
        self.assertEqual([card.front for card in due], ["beta"])


if __name__ == "__main__":
    unittest.main()
