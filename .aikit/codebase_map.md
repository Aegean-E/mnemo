# Codebase Map & Symbol Catalog 🗺️

> **AUTO-GENERATED & VERIFIED BY `scripts/update_knowledge_base.py`**
> This document provides an automated, up-to-date registry of all modules, classes, and exported functions across this repository.

---

## 📊 Codebase Metrics
- **Total Python Modules**: `12`
- **Total Classes**: `12`
- **Total Top-Level Functions**: `13`
- **Total Class Methods**: `69`
- **Total Source Lines**: `975`

---

## 📦 Modules & Exported Symbols

### [`mnemo/__init__.py`](mnemo/__init__.py)
> *mnemo: a dependency-free, local-first spaced-repetition flashcard CLI (SM-2).*

**Size**: `1` lines (`84` bytes)

---

### [`mnemo/__main__.py`](mnemo/__main__.py)
> *`python -m mnemo` runs the CLI and exits with its code.*

**Size**: `8` lines (`151` bytes)

---

### [`mnemo/cli.py`](mnemo/cli.py)
> *Command-line interface: `add` and `list` over one deck file.*

**Size**: `72` lines (`2496` bytes)

**Functions:**
- `def build_parser()` - *The command grammar; `--db` selects the deck file for every command.*
- `def run_add(deck, args)` - *Validate the arguments, record the card and echo it.*
- `def run_list(deck, args)` - *Print one line per card, or say the deck is empty.*
- `def main(argv)` - *Run one command; user errors print the Why/Fix triad and exit 1.*

---

### [`mnemo/deck.py`](mnemo/deck.py)
> *Deck operations: adding, finding and listing cards over the atomic store.*

**Size**: `50` lines (`1756` bytes)

**Classes:**
- `class Deck` - *The card operations one command needs, backed by one deck file.*
  - Method `.__init__(store)`
  - Method `.add_card(front, back, deck, today)` - *Record a new card, due today, and return it with its assigned id.*
  - Method `.entries()` - *Every card, sorted by id.*
  - Method `.find(card_id)` - *One card by id, or the Why/Fix triad when it is absent.*

---

### [`mnemo/errors.py`](mnemo/errors.py)
> *Every user-facing failure carries a message, a reason and a repair (PRINCIPLE-011 R6).*

**Size**: `15` lines (`547` bytes)

**Classes:**
- `class MnemoError` - *A failure the CLI reports as `Error:` / `Why:` / `Fix:` without a traceback.*
  - Method `.__init__(message, why, fix)`
  - Method `.render()` - *The three-line report the CLI prints on stderr.*

---

### [`mnemo/models.py`](mnemo/models.py)
> *The card and review value objects, their schema bounds and their parsing rules.*

**Size**: `210` lines (`7975` bytes)

**Classes:**
- `class Card` - *One flashcard and its complete SM-2 scheduling state.*
  - Method `.__post_init__()`
  - Method `.as_dict()` - *The stored form of the card, including every defaulted field.*
  - Method `.from_dict(record)` - *Rebuild a card from its stored form, validating every field.*
- `class Review` - *One graded answer, the atom of the review log and of every statistic.*
  - Method `.__post_init__()`
  - Method `.as_dict()` - *The stored form of the review.*
  - Method `.from_dict(record)` - *Rebuild a review from its stored form, validating every field.*

**Functions:**
- `def _nonblank(value, field)` - *A stripped non-empty string, or the triad for a blank one.*
- `def parse_front(value)` - *The question side of a card, stripped and non-empty.*
- `def parse_back(value)` - *The answer side of a card, stripped and non-empty.*
- `def normalize_deck(value)` - *The deck label: stripped, lowercased, capped, defaulting to 'default'.*
- `def parse_card_id(value)` - *A positive integer card id, as shown by `list`.*
- `def parse_iso_date(value, field)` - *A strict YYYY-MM-DD string, validated by both shape and calendar.*
- `def _bounded_int(record, key, default, minimum)` - *An integer field of a stored record, defaulting when absent.*

---

### [`mnemo/storage.py`](mnemo/storage.py)
> *Crash-resilient JSON storage for the deck (PRINCIPLE-013).*

**Size**: `251` lines (`10703` bytes)

**Classes:**
- `class DeckState` - *The whole deck file: every card and every logged review.*
- `class StateStore` - *The deck file, its backup and its lock, addressed by one path.*
  - Method `.__init__(path)`
  - Method `.read()` - *Every card and review; a missing deck is an empty one.*
  - Method `.update(mutate)` - *Apply `mutate` to the deck and persist its result under one held lock.*
  - Method `._load()` - *Parse the deck, recovering from a readable backup before giving up on it.*
  - Method `._backup_or_empty(reason, quarantine)` - *Use the backup when it parses; otherwise quarantine the bad file and start empty.*
  - Method `._read_backup()` - *The parsed backup, or None when it is absent or unreadable.*
  - Method `._decode(data)` - *Validate the document envelope and rebuild every card and review.*
  - Method `._save(state)` - *Write the deck atomically, keeping the previous version as a backup.*
  - Method `._replace(temp_path)` - *Replace the deck, retrying only transient sharing violations on Windows.*
  - Method `._fsync_directory(directory)` - *Flush the directory entry on POSIX; Windows cannot fsync a directory handle.*
  - Method `._quarantine()` - *Move a corrupt deck aside so it can neither block reads nor be overwritten.*
  - Method `._lock()` - *Hold the advisory lock file for one read-modify-write.*
  - Method `._break_stale_lock()` - *Break a lock older than 30 seconds by atomically renaming it aside.*

---

### [`tests/__init__.py`](tests/__init__.py)
**Size**: `0` lines (`0` bytes)

---

### [`tests/test_cli.py`](tests/test_cli.py)
> *End-to-end tests of the command-line interface through `main`.*

**Size**: `74` lines (`2728` bytes)

**Classes:**
- `class CliTests`
  - Method `.setUp()`
  - Method `.run_cli(*arguments)`
  - Method `.test_add_then_list()`
  - Method `.test_add_without_back_fails_with_the_triad()`
  - Method `.test_list_on_an_empty_deck()`
  - Method `.test_add_increments_ids()`
  - Method `.test_add_labels_the_deck()`
  - Method `.test_nested_db_path_is_created()`

---

### [`tests/test_deck.py`](tests/test_deck.py)
> *Tests of deck operations over the atomic store.*

**Size**: `54` lines (`2087` bytes)

**Classes:**
- `class DeckTests`
  - Method `.setUp()`
  - Method `.test_add_assigns_sequential_ids()`
  - Method `.test_new_card_is_due_the_day_it_is_added()`
  - Method `.test_entries_are_sorted_by_id()`
  - Method `.test_find_returns_the_card()`
  - Method `.test_find_missing_card_raises_the_triad()`
  - Method `.test_state_persists_across_instances()`

---

### [`tests/test_models.py`](tests/test_models.py)
> *Tests of the card and review value objects and their parsing rules.*

**Size**: `107` lines (`3956` bytes)

**Classes:**
- `class ParseTests`
  - Method `.test_parse_front_strips_surrounding_space()`
  - Method `.test_parse_front_rejects_blank()`
  - Method `.test_parse_back_rejects_blank()`
  - Method `.test_normalize_deck_defaults_lowercases_and_caps_length()`
  - Method `.test_normalize_deck_rejects_blank()`
  - Method `.test_parse_card_id_accepts_positive_integers()`
  - Method `.test_parse_card_id_rejects_non_positive_or_garbled()`
  - Method `.test_parse_iso_date_round_trips_valid_dates()`
  - Method `.test_parse_iso_date_rejects_non_dates()`
- `class CardTests`
  - Method `.test_new_card_defaults()`
  - Method `.test_card_round_trips_through_dicts()`
  - Method `.test_card_from_dict_fills_absent_optional_fields()`
  - Method `.test_card_from_dict_rejects_bad_records()`
- `class ReviewTests`
  - Method `.test_review_round_trips_through_dicts()`
  - Method `.test_review_rejects_out_of_range_quality()`

---

### [`tests/test_storage.py`](tests/test_storage.py)
> *Fault-injection tests for the atomic deck store (PRINCIPLE-013).*

**Size**: `133` lines (`5485` bytes)

**Classes:**
- `class StoreFaultTests`
  - Method `.setUp()`
  - Method `._write(state)`
  - Method `.test_missing_file_reads_empty()`
  - Method `.test_cards_and_reviews_round_trip()`
  - Method `.test_second_save_keeps_a_backup()`
  - Method `.test_malformed_json_recovers_from_backup()`
  - Method `.test_zero_byte_file_recovers_from_backup()`
  - Method `.test_unknown_version_is_refused_in_place()`
  - Method `.test_insufficient_disk_space_writes_nothing()`
  - Method `.test_concurrent_writers_lose_no_cards()`
  - Method `.test_replace_retries_a_permission_error_then_succeeds()`
  - Method `.test_replace_does_not_retry_a_non_transient_error()`
  - Method `.test_stale_lock_is_broken()`
  - Method `.test_fsync_directory_failure_is_reported()`

**Functions:**
- `def sample_card(card_id)`
- `def sample_state(card_id)`

---
