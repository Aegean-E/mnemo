"""End-to-end tests of the command-line interface through `main`."""

import io
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from mnemo.cli import main


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="mnemo-cli-"))
        self.addCleanup(shutil.rmtree, self.temp_dir, ignore_errors=True)
        self.db = str(self.temp_dir / "mnemo.json")

    def run_cli(self, *arguments):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(["--db", self.db, *arguments])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_add_then_list(self):
        code, output, _ = self.run_cli("add", "What is SM-2?", "--back",
                                       "a spaced-repetition scheduling algorithm")
        self.assertEqual(code, 0)
        self.assertIn("Added #1", output)
        self.assertIn("What is SM-2?", output)

        code, output, _ = self.run_cli("list")
        self.assertEqual(code, 0)
        self.assertIn("#1", output)
        self.assertIn("What is SM-2?", output)
        self.assertIn("a spaced-repetition scheduling algorithm", output)

    def test_add_without_back_fails_with_the_triad(self):
        code, _, stderr = self.run_cli("add", "Orphan front")
        self.assertEqual(code, 1)
        self.assertIn("Error:", stderr)
        self.assertIn("Why:", stderr)
        self.assertIn("Fix:", stderr)

    def test_list_on_an_empty_deck(self):
        code, output, _ = self.run_cli("list")
        self.assertEqual(code, 0)
        self.assertIn("No cards yet", output)

    def test_add_increments_ids(self):
        self.run_cli("add", "one", "--back", "1")
        self.run_cli("add", "two", "--back", "2")
        code, output, _ = self.run_cli("list")
        self.assertEqual(code, 0)
        self.assertIn("#1", output)
        self.assertIn("#2", output)

    def test_add_labels_the_deck(self):
        self.run_cli("add", "hiragana a", "--back", "あ", "--deck", "Japanese")
        code, output, _ = self.run_cli("list")
        self.assertEqual(code, 0)
        self.assertIn("[japanese]", output)

    def test_nested_db_path_is_created(self):
        nested = str(self.temp_dir / "deep" / "vault" / "mnemo.json")
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(["--db", nested, "add", "front", "--back", "back"])
        self.assertEqual(code, 0)
        self.assertTrue(Path(nested).is_file())

    def test_list_shows_maturity(self):
        self.run_cli("add", "fresh", "--back", "card")
        code, output, _ = self.run_cli("list")
        self.assertEqual(code, 0)
        self.assertIn(" new ", output)

    def test_list_due_hides_cards_scheduled_for_later(self):
        self.run_cli("add", "front", "--back", "back")
        deck_json = self.temp_dir / "mnemo.json"
        import json
        document = json.loads(deck_json.read_text(encoding="utf-8"))
        document["cards"][0]["due"] = "2099-01-01"
        deck_json.write_text(json.dumps(document), encoding="utf-8")
        code, output, _ = self.run_cli("list", "--due")
        self.assertEqual(code, 0)
        self.assertNotIn("front", output)
        self.assertIn("No cards due", output)

    def test_study_runs_a_scripted_session(self):
        from unittest import mock
        self.run_cli("add", "What is SM-2?", "--back", "a scheduling algorithm")
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch("builtins.input", side_effect=["", "4"]):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = main(["--db", self.db, "study"])
        self.assertEqual(code, 0)
        output = stdout.getvalue()
        self.assertIn("What is SM-2?", output)
        self.assertIn("a scheduling algorithm", output)
        self.assertIn("1 reviewed", output)

        code, output, _ = self.run_cli("list", "--due")
        self.assertEqual(code, 0)
        self.assertIn("No cards due", output)

    def test_study_on_an_empty_deck(self):
        code, output, _ = self.run_cli("study")
        self.assertEqual(code, 0)
        self.assertIn("No cards yet", output)

    def test_study_rejects_a_non_positive_limit(self):
        code, _, stderr = self.run_cli("study", "--limit", "0")
        self.assertEqual(code, 1)
        self.assertIn("Error:", stderr)
        self.assertIn("Fix:", stderr)

    def test_stats_renders_the_deck_summary(self):
        self.run_cli("add", "one", "--back", "1")
        self.run_cli("add", "two", "--back", "2")
        code, output, _ = self.run_cli("stats")
        self.assertEqual(code, 0)
        self.assertIn("cards: 2", output)
        self.assertIn("due today", output)
        self.assertIn("retention", output)

    def test_stats_after_a_session_reports_full_retention(self):
        from unittest import mock
        self.run_cli("add", "one", "--back", "1")
        with mock.patch("builtins.input", side_effect=["", "4"]):
            stdout, stderr = io.StringIO(), io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = main(["--db", self.db, "study"])
        self.assertEqual(code, 0)
        code, output, _ = self.run_cli("stats")
        self.assertEqual(code, 0)
        self.assertIn("retention: 100%", output)
        self.assertIn("reviews logged: 1", output)

    def test_edit_updates_the_given_fields(self):
        self.run_cli("add", "old front", "--back", "old back")
        code, output, _ = self.run_cli("edit", "1", "--back", "new back",
                                       "--deck", "Japanese")
        self.assertEqual(code, 0)
        self.assertIn("Updated #1", output)
        self.assertIn("new back", output)
        code, output, _ = self.run_cli("list")
        self.assertEqual(code, 0)
        self.assertIn("new back", output)
        self.assertIn("[japanese]", output)
        self.assertIn("old front", output)

    def test_edit_without_fields_fails_with_the_triad(self):
        self.run_cli("add", "front", "--back", "back")
        code, _, stderr = self.run_cli("edit", "1")
        self.assertEqual(code, 1)
        self.assertIn("Error:", stderr)
        self.assertIn("Fix:", stderr)

    def test_edit_missing_card_fails(self):
        self.run_cli("add", "front", "--back", "back")
        code, _, stderr = self.run_cli("edit", "9", "--back", "new")
        self.assertEqual(code, 1)
        self.assertIn("There is no card #9", stderr)

    def test_remove_deletes_the_card(self):
        self.run_cli("add", "keep", "--back", "1")
        self.run_cli("add", "gone", "--back", "2")
        code, output, _ = self.run_cli("remove", "2")
        self.assertEqual(code, 0)
        self.assertIn("Removed #2", output)
        code, output, _ = self.run_cli("list")
        self.assertEqual(code, 0)
        self.assertNotIn("gone", output)
        self.assertIn("keep", output)

    def test_remove_missing_card_fails(self):
        code, _, stderr = self.run_cli("remove", "1")
        self.assertEqual(code, 1)
        self.assertIn("There is no card #1", stderr)

    def test_list_filter_by_deck(self):
        self.run_cli("add", "kana", "--back", "あ", "--deck", "japanese")
        self.run_cli("add", "der die das", "--back", "the", "--deck", "german")
        code, output, _ = self.run_cli("list", "--deck", "japanese")
        self.assertEqual(code, 0)
        self.assertIn("kana", output)
        self.assertNotIn("der die das", output)

    def test_study_filter_by_deck(self):
        from unittest import mock
        self.run_cli("add", "alpha front", "--back", "a", "--deck", "alpha")
        self.run_cli("add", "beta front", "--back", "b", "--deck", "beta")
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch("builtins.input", side_effect=["", "4"]):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = main(["--db", self.db, "study", "--deck", "alpha"])
        self.assertEqual(code, 0)
        output = stdout.getvalue()
        self.assertIn("alpha front", output)
        self.assertNotIn("beta front", output)

    def test_stats_filter_by_deck(self):
        self.run_cli("add", "kana", "--back", "あ", "--deck", "japanese")
        self.run_cli("add", "der die das", "--back", "the", "--deck", "german")
        code, output, _ = self.run_cli("stats", "--deck", "japanese")
        self.assertEqual(code, 0)
        self.assertIn("cards: 1", output)


if __name__ == "__main__":
    unittest.main()
