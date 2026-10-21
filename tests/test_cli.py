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


if __name__ == "__main__":
    unittest.main()
