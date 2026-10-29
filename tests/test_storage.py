"""Fault-injection tests for the atomic deck store (PRINCIPLE-013)."""

import errno
import io
import json
import shutil
import tempfile
import threading
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

from mnemo import storage
from mnemo.errors import MnemoError
from mnemo.models import Card, Review
from mnemo.storage import DeckState, StateStore


def sample_card(card_id: int) -> Card:
    return Card(id=card_id, front=f"front {card_id}", back=f"back {card_id}",
                deck="default", due="2026-10-21", added="2026-10-21")


def sample_state(card_id: int) -> DeckState:
    return DeckState(cards=[sample_card(card_id)],
                     reviews=[Review(card_id=card_id, date="2026-10-21", quality=4)])


class StoreFaultTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="mnemo-store-"))
        self.addCleanup(shutil.rmtree, self.temp_dir, ignore_errors=True)
        self.path = self.temp_dir / "mnemo.json"
        self.store = StateStore(self.path)

    def _write(self, state: DeckState) -> None:
        self.store.update(lambda _current: state)

    def test_missing_file_reads_empty(self):
        self.assertEqual(self.store.read(), DeckState(cards=[], reviews=[]))

    def test_cards_and_reviews_round_trip(self):
        self._write(sample_state(1))
        state = self.store.read()
        self.assertEqual(state.cards, [sample_card(1)])
        self.assertEqual(state.reviews, [Review(card_id=1, date="2026-10-21", quality=4)])

    def test_second_save_keeps_a_backup(self):
        self._write(DeckState(cards=[], reviews=[]))
        self._write(DeckState(cards=[], reviews=[]))
        self.assertTrue(self.path.with_name("mnemo.json.bak").exists())

    def test_malformed_json_recovers_from_backup(self):
        self._write(sample_state(1))
        self._write(sample_state(1))
        self.path.write_text("{broken", encoding="utf-8")
        self.assertEqual([card.id for card in self.store.read().cards], [1])

    def test_recovery_restores_the_deck_file_in_place(self):
        self._write(sample_state(1))
        self._write(sample_state(1))
        self.path.write_text("{broken", encoding="utf-8")
        self.store.read()
        self.assertTrue(self.path.exists())
        self.assertEqual([card.id for card in self.store.read().cards], [1])
        self.assertTrue(any(name.startswith(".corrupt_") for name in
                            (entry.name for entry in self.temp_dir.iterdir())))

    def test_restore_failure_returns_the_recovered_state(self):
        self._write(sample_state(1))
        self._write(sample_state(1))
        self.path.write_text("{broken", encoding="utf-8")
        with mock.patch.object(self.store, "_restore", side_effect=OSError("disk full")):
            with redirect_stderr(io.StringIO()) as stderr:
                state = self.store.read()
        self.assertEqual([card.id for card in state.cards], [1])
        self.assertIn("Could not restore", stderr.getvalue())
        self.assertIn("recovered mnemo.json in memory", stderr.getvalue())

    def test_zero_byte_file_recovers_from_backup(self):
        self._write(sample_state(1))
        self._write(sample_state(1))
        self.path.write_text("", encoding="utf-8")
        self.assertEqual([card.id for card in self.store.read().cards], [1])

    def test_unknown_version_is_refused_in_place(self):
        original = json.dumps({"version": 99, "cards": [], "reviews": []})
        self.path.write_text(original, encoding="utf-8")
        with self.assertRaises(MnemoError):
            self.store.read()
        self.assertEqual(self.path.read_text(encoding="utf-8"), original)

    def test_insufficient_disk_space_writes_nothing(self):
        self._write(DeckState(cards=[], reviews=[]))
        usage = shutil.disk_usage(self.temp_dir)
        before = self.path.read_text(encoding="utf-8")
        with mock.patch("mnemo.storage.shutil.disk_usage",
                        return_value=type(usage)(usage.total, usage.used, 0)):
            with self.assertRaises(MnemoError):
                self._write(DeckState(cards=[], reviews=[]))
        self.assertEqual(self.path.read_text(encoding="utf-8"), before)

    def test_concurrent_writers_lose_no_cards(self):
        def add(number: int) -> None:
            self.store.update(
                lambda current: DeckState(
                    cards=current.cards + [sample_card(number)], reviews=current.reviews)
            )

        threads = [threading.Thread(target=add, args=(number,)) for number in range(1, 7)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(len(self.store.read().cards), 6)

    def test_replace_retries_a_permission_error_then_succeeds(self):
        with mock.patch("mnemo.storage.os.replace",
                        side_effect=[PermissionError("busy"), PermissionError("busy"), None]) as replace:
            with mock.patch("mnemo.storage.time.sleep"):
                self.store._replace(self.temp_dir / "temp.json")
        self.assertEqual(replace.call_count, 3)

    def test_replace_does_not_retry_a_non_transient_error(self):
        with mock.patch("mnemo.storage.os.replace",
                        side_effect=OSError(errno.ENOSPC, "No space left on device")) as replace:
            with mock.patch("mnemo.storage.time.sleep"):
                with self.assertRaises(MnemoError):
                    self.store._replace(self.temp_dir / "temp.json")
        self.assertEqual(replace.call_count, 1)

    def test_stale_lock_is_broken(self):
        self._write(DeckState(cards=[], reviews=[]))
        self.store.lock_path.write_text("0", encoding="ascii")
        import os
        import time
        stale = time.time() - 120
        os.utime(self.store.lock_path, (stale, stale))
        self._write(sample_state(1))
        self.assertEqual([card.id for card in self.store.read().cards], [1])

    def test_fsync_directory_failure_is_reported(self):
        error = io.StringIO()
        with mock.patch.object(storage.os, "name", "posix"):
            with mock.patch("mnemo.storage.os.open", side_effect=OSError("unsupported")):
                with redirect_stderr(error):
                    self.store._fsync_directory(self.temp_dir)
        self.assertIn("[WARN]", error.getvalue())
        self.assertIn("Could not fsync directory", error.getvalue())


if __name__ == "__main__":
    unittest.main()
