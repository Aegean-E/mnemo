"""Tests of the study session engine over scripted input and captured output."""

import shutil
import tempfile
import unittest
from pathlib import Path

from mnemo.deck import Deck
from mnemo.storage import StateStore
from mnemo.study import run_session


class ScriptedInput:
    """A read_line double that replays lines and reports EOF as None."""

    def __init__(self, lines):
        self.lines = list(lines)

    def __call__(self):
        return self.lines.pop(0) if self.lines else None


class CaptureOutput:
    """A write_line double that collects every line the session prints."""

    def __init__(self):
        self.lines = []

    def __call__(self, text):
        self.lines.append(text)

    def text(self):
        return "\n".join(self.lines)


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="mnemo-study-"))
        self.addCleanup(shutil.rmtree, self.temp_dir, ignore_errors=True)
        self.deck = Deck(StateStore(self.temp_dir / "mnemo.json"))

    def script(self, *lines):
        return ScriptedInput(lines)

    def test_session_grades_and_schedules_every_card(self):
        self.deck.add_card("front 1", "back 1", "default", "2026-10-21")
        self.deck.add_card("front 2", "back 2", "default", "2026-10-21")
        output = CaptureOutput()
        report = run_session(self.deck, "2026-10-21", 20, self.script("", "4", "", "3"), output)
        self.assertEqual((report.reviewed, report.passed, report.lapsed, report.quit_early),
                         (2, 2, 0, False))
        self.assertEqual(len(self.deck.entries()), 2)
        self.assertEqual(self.deck.find(1).due, "2026-10-22")
        self.assertEqual(self.deck.find(2).due, "2026-10-22")
        self.assertEqual(len(self.deck.store.read().reviews), 2)

    def test_quit_at_the_first_reveal_reviews_nothing(self):
        self.deck.add_card("front", "back", "default", "2026-10-21")
        output = CaptureOutput()
        report = run_session(self.deck, "2026-10-21", 20, self.script("q"), output)
        self.assertEqual((report.reviewed, report.quit_early), (0, True))
        self.assertEqual(self.deck.store.read().reviews, [])

    def test_eof_quits_gracefully(self):
        self.deck.add_card("front", "back", "default", "2026-10-21")
        output = CaptureOutput()
        report = run_session(self.deck, "2026-10-21", 20, self.script(), output)
        self.assertEqual((report.reviewed, report.quit_early), (0, True))
        self.assertIn("front", output.text())

    def test_quit_mid_session_keeps_finished_reviews(self):
        self.deck.add_card("front 1", "back 1", "default", "2026-10-21")
        self.deck.add_card("front 2", "back 2", "default", "2026-10-21")
        output = CaptureOutput()
        report = run_session(self.deck, "2026-10-21", 20, self.script("", "4", "q"), output)
        self.assertEqual((report.reviewed, report.quit_early), (1, True))
        self.assertEqual(len(self.deck.store.read().reviews), 1)

    def test_invalid_grade_reprompts_until_valid(self):
        self.deck.add_card("front", "back", "default", "2026-10-21")
        output = CaptureOutput()
        report = run_session(self.deck, "2026-10-21", 20,
                             self.script("", "banana", "", "good"), output)
        self.assertEqual((report.reviewed, report.passed), (1, 1))
        self.assertIn("Not a grade", output.text())

    def test_limit_caps_the_session(self):
        for number in range(3):
            self.deck.add_card(f"front {number}", "back", "default", "2026-10-21")
        output = CaptureOutput()
        report = run_session(self.deck, "2026-10-21", 2, self.script("", "4", "", "4"), output)
        self.assertEqual(report.reviewed, 2)
        self.assertIn("still due today", output.text())

    def test_summary_names_the_next_due_day(self):
        self.deck.add_card("front", "back", "default", "2026-10-21")
        output = CaptureOutput()
        run_session(self.deck, "2026-10-21", 20, self.script("", "4"), output)
        self.assertIn("Next session: 2026-10-22", output.text())

    def test_session_without_due_cards_says_so(self):
        self.deck.add_card("front", "back", "default", "2026-10-21")
        self.deck.record_review(1, 4, "2026-10-21")
        output = CaptureOutput()
        report = run_session(self.deck, "2026-10-21", 20, self.script(), output)
        self.assertEqual(report.reviewed, 0)
        self.assertIn("No cards due today", output.text())
        self.assertIn("2026-10-22", output.text())


if __name__ == "__main__":
    unittest.main()
