"""Crash-resilient JSON storage for the deck (PRINCIPLE-013).

A save copies the current file to `.bak`, writes a unique temporary file, fsyncs it, then
replaces the deck atomically. A read that meets malformed JSON quarantines the file and falls
back to the backup, while a file declaring an unknown schema version is refused in place.
Every read-modify-write holds an advisory `.lock` file with a bounded wait.
"""

import json
import os
import shutil
import sys
import tempfile
import time
from contextlib import closing, contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterator, List, Optional

from mnemo.errors import MnemoError
from mnemo.models import Card, Review

STATE_VERSION = 1
MIN_FREE_BYTES = 10 * 1024 * 1024
LOCK_TIMEOUT_SECONDS = 3.0
LOCK_STALE_SECONDS = 30.0
REPLACE_ATTEMPTS = 5


@dataclass(frozen=True)
class DeckState:
    """The whole deck file: every card and every logged review."""

    cards: List[Card]
    reviews: List[Review]


class StateStore:
    """The deck file, its backup and its lock, addressed by one path."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.backup_path = self.path.with_name(self.path.name + ".bak")
        self.lock_path = self.path.with_name(self.path.name + ".lock")

    def read(self) -> DeckState:
        """Every card and review; a missing deck is an empty one."""
        return self._load()

    def update(self, mutate: Callable[[DeckState], DeckState]) -> DeckState:
        """Apply `mutate` to the deck and persist its result under one held lock."""
        with self._lock():
            state = self._load()
            updated = mutate(state)
            self._save(updated)
            return updated

    def _load(self) -> DeckState:
        """Parse the deck, recovering from a readable backup before giving up on it."""
        if not self.path.exists():
            return DeckState(cards=[], reviews=[])
        try:
            text = self.path.read_text(encoding="utf-8")
            data = json.loads(text)
        except OSError as exc:
            return self._backup_or_empty(f"could not read {self.path}: {exc}", quarantine=False)
        except ValueError:
            return self._backup_or_empty(f"{self.path} is not valid JSON", quarantine=True)
        return self._decode(data)

    def _backup_or_empty(self, reason: str, quarantine: bool) -> DeckState:
        """Use the backup when it parses, restoring it in place; else start empty."""
        if quarantine:
            self._quarantine()
        backup = self._read_backup()
        if backup is not None:
            state = self._decode(backup)
            restored = False
            try:
                self._restore(state)
                restored = True
            except (MnemoError, OSError) as error:
                detail = error.message if isinstance(error, MnemoError) else str(error)
                print(f"[WARN] Could not restore {self.path.name}: {detail}",
                      file=sys.stderr)
            if restored:
                print(f"[WARN] {reason}; restored {self.path.name} from "
                      f"{self.backup_path.name}.", file=sys.stderr)
            else:
                print(f"[WARN] {reason}; recovered {self.path.name} in memory from "
                      f"{self.backup_path.name}.", file=sys.stderr)
            return state
        print(f"[WARN] {reason}; starting with an empty deck.", file=sys.stderr)
        return DeckState(cards=[], reviews=[])

    def _read_backup(self) -> Optional[Dict[str, object]]:
        """The parsed backup, or None when it is absent or unreadable."""
        if not self.backup_path.exists():
            return None
        try:
            data = json.loads(self.backup_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return data if isinstance(data, dict) else None

    def _decode(self, data: object) -> DeckState:
        """Validate the document envelope and rebuild every card and review."""
        if not isinstance(data, dict):
            raise MnemoError(
                f"{self.path} does not hold a deck object.",
                "the deck is one JSON object with a version, a cards list and a reviews list.",
                f"restore {self.backup_path.name}, or delete the file to start a new deck.",
            )
        version = data.get("version")
        if version != STATE_VERSION:
            raise MnemoError(
                f"{self.path} declares deck version {version!r}; this build supports {STATE_VERSION}.",
                "a newer or unknown format could be misread and its data lost.",
                "use the mnemo version that wrote it, or migrate the file by hand.",
            )
        records = data.get("cards")
        if not isinstance(records, list):
            raise MnemoError(
                f"{self.path} has no 'cards' list.",
                "the deck is one JSON object with a version, a cards list and a reviews list.",
                f"restore {self.backup_path.name}, or delete the file to start a new deck.",
            )
        logged = data.get("reviews", [])
        if not isinstance(logged, list):
            raise MnemoError(
                f"{self.path} has a 'reviews' value that is not a list.",
                "the review log is a list of graded answers, one object each.",
                f"restore {self.backup_path.name}, or drop the reviews list to empty.",
            )
        return DeckState(cards=[Card.from_dict(record) for record in records],
                         reviews=[Review.from_dict(record) for record in logged])

    def _save(self, state: DeckState) -> None:
        """Write the deck atomically, keeping the previous version as a backup."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_free_space()
        if self.path.exists():
            try:
                shutil.copy2(self.path, self.backup_path)
            except OSError as exc:
                print(
                    f"[WARN] Could not write backup {self.backup_path.name}: {exc}",
                    file=sys.stderr,
                )
        self._write_atomic(self._payload(state))

    def _restore(self, state: DeckState) -> None:
        """Put recovered state back at the deck path so later commands see it."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._write_atomic(self._payload(state))

    @staticmethod
    def _payload(state: DeckState) -> str:
        """The deck as the text one atomic write stores."""
        return json.dumps(
            {"version": STATE_VERSION, "cards": [card.as_dict() for card in state.cards],
             "reviews": [review.as_dict() for review in state.reviews]},
            indent=2,
            ensure_ascii=False,
        )

    def _ensure_free_space(self) -> None:
        """Refuse a write that leaves too little room for the next recovery."""
        free = shutil.disk_usage(self.path.parent).free
        if free < MIN_FREE_BYTES:
            raise MnemoError(
                f"Only {free} bytes are free next to {self.path}.",
                "a deck write needs at least 10 MB of headroom to stay crash-safe.",
                "free disk space, or point --db at another volume.",
            )

    def _write_atomic(self, payload: str) -> None:
        """Write the payload through a temporary file, fsync and replace."""
        descriptor, temp_name = tempfile.mkstemp(
            dir=self.path.parent, prefix=f".{self.path.name}.tmp_"
        )
        temp_path = Path(temp_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            self._replace(temp_path)
            self._fsync_directory(self.path.parent)
        finally:
            temp_path.unlink(missing_ok=True)

    def _replace(self, temp_path: Path) -> None:
        """Replace the deck, retrying only transient sharing violations on Windows."""
        last_error: Optional[OSError] = None
        for attempt in range(REPLACE_ATTEMPTS):
            try:
                os.replace(temp_path, self.path)
                return
            except PermissionError as exc:
                last_error = exc
                if attempt < REPLACE_ATTEMPTS - 1:
                    time.sleep(0.02 * (2 ** attempt))
            except OSError as exc:
                last_error = exc
                break
        raise MnemoError(
            f"Could not replace {self.path}: {last_error}",
            "another program may hold the deck open, or the disk may be full or read-only.",
            "close programs using the file, check free space and permissions, then retry; "
            "the previous deck is still intact.",
        )

    @staticmethod
    def _fsync_directory(directory: Path) -> None:
        """Flush the directory entry on POSIX; Windows cannot fsync a directory handle."""
        if os.name == "nt":
            return
        try:
            with closing(os.open(str(directory), os.O_RDONLY)) as descriptor:  # hygiene: allow raw directory descriptor closed by closing()
                os.fsync(descriptor)
        except OSError as exc:
            print(f"[WARN] Could not fsync directory {directory}: {exc}", file=sys.stderr)

    def _quarantine(self) -> None:
        """Move a corrupt deck aside so it can neither block reads nor be overwritten."""
        destination = self.path.with_name(f".corrupt_{self.path.name}_{time.time_ns()}")
        try:
            os.replace(self.path, destination)
            print(f"[WARN] Moved unreadable deck to {destination.name}.", file=sys.stderr)
        except OSError as exc:
            print(f"[WARN] Could not quarantine {self.path}: {exc}", file=sys.stderr)

    @contextmanager
    def _lock(self) -> Iterator[None]:
        """Hold the advisory lock file for one read-modify-write."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        token = f"{os.getpid()}:{time.time_ns()}"
        deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
        acquired = False
        while not acquired:
            try:
                with self.lock_path.open("x", encoding="ascii") as handle:
                    handle.write(token)
                acquired = True
            except FileExistsError:
                self._break_stale_lock()
                if time.monotonic() >= deadline:
                    raise MnemoError(
                        f"Timed out waiting for {self.lock_path.name}.",
                        "another mnemo process is changing the deck.",
                        "wait for it to finish, then run the command again.",
                    )
                time.sleep(0.05)
            except OSError as exc:
                raise MnemoError(
                    f"Could not create {self.lock_path.name}: {exc}",
                    "every deck write needs the lock to avoid losing cards.",
                    "check the folder's permissions, then run the command again.",
                ) from exc
        try:
            yield
        finally:
            try:
                if self.lock_path.read_text(encoding="ascii") == token:
                    self.lock_path.unlink(missing_ok=True)
            except (OSError, UnicodeDecodeError) as exc:
                print(f"[WARN] Could not release lock {self.lock_path.name}: {exc}",
                      file=sys.stderr)

    def _break_stale_lock(self) -> None:
        """Break a lock older than 30 seconds by atomically renaming it aside."""
        try:
            age = time.time() - self.lock_path.stat().st_mtime
        except FileNotFoundError:
            return
        if age <= LOCK_STALE_SECONDS:
            return
        stale = self.lock_path.with_name(
            f"{self.lock_path.name}.stale_{time.time_ns()}"
        )
        try:
            os.replace(self.lock_path, stale)
        except FileNotFoundError:
            return
        except OSError as exc:
            print(f"[WARN] Could not break stale lock {self.lock_path.name}: {exc}", file=sys.stderr)
