# Codebase Map & Symbol Catalog 🗺️

> **AUTO-GENERATED & VERIFIED BY `scripts/update_knowledge_base.py`**
> This document provides an automated, up-to-date registry of all modules, classes, and exported functions across this repository.

---

## 📊 Codebase Metrics
- **Total Python Modules**: `18`
- **Total Classes**: `21`
- **Total Top-Level Functions**: `28`
- **Total Class Methods**: `115`
- **Total Source Lines**: `1639`

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

**Size**: `124` lines (`4725` bytes)

**Functions:**
- `def build_parser()` - *The command grammar; `--db` selects the deck file for every command.*
- `def run_add(deck, args)` - *Validate the arguments, record the card and echo it.*
- `def run_list(deck, args)` - *Print one line per card, or say the deck is empty.*
- `def run_study(deck, args)` - *Run one guided session over the due cards, reading stdin line by line.*
- `def run_stats(deck, args)` - *Print the deck's counts, retention and seven-day due forecast.*
- `def main(argv)` - *Run one command; user errors print the Why/Fix triad and exit 1.*

---

### [`mnemo/deck.py`](mnemo/deck.py)
> *Deck operations: adding, finding, listing, due selection and review recording.*

**Size**: `84` lines (`3310` bytes)

**Classes:**
- `class Deck` - *The card operations one command needs, backed by one deck file.*
  - Method `.__init__(store)`
  - Method `.add_card(front, back, deck, today)` - *Record a new card, due today, and return it with its assigned id.*
  - Method `.snapshot()` - *Every card and every logged review, in one read.*
  - Method `.entries()` - *Every card, sorted by id.*
  - Method `.due_cards(today)` - *Every card due on `today` or earlier, earliest due first.*
  - Method `.find(card_id)` - *One card by id, or the Why/Fix triad when it is absent.*
  - Method `.record_review(card_id, quality, today)` - *Grade one answer: persist the card's next SM-2 state and append the log entry.*

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

### [`mnemo/scheduler.py`](mnemo/scheduler.py)
> *The SM-2 scheduling functions: pure, date-injected, exactly the published algorithm.*

**Size**: `68` lines (`2695` bytes)

**Functions:**
- `def grade_from_text(text)` - *A grade from one digit 0-5, or from the words again, hard, good and easy.*
- `def _ease_after(ease, quality)` - *The published SM-2 ease update, never dropping below the floor.*
- `def next_state(card, quality, today)` - *The card exactly as the published SM-2 leaves it after one graded answer.*
- `def is_due(card, today)` - *Whether the card's due day is `today` or has already passed.*
- `def maturity(card)` - *The card's stage: new, learning, or mature at 21 days of interval.*

---

### [`mnemo/stats.py`](mnemo/stats.py)
> *Deck statistics: pure counts, retention and forecast over cards, reviews and one day.*

**Size**: `46` lines (`1571` bytes)

**Classes:**
- `class DeckStats` - *One deck's position on a day, as the `stats` command reports it.*

**Functions:**
- `def summarize(cards, reviews, today)` - *The deck's counts, retention and seven-day due forecast for `today`.*

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

### [`mnemo/study.py`](mnemo/study.py)
> *The study session engine: due queue, reveal, grade and summary, with injected I/O.*

**Size**: `94` lines (`3483` bytes)

**Classes:**
- `class SessionReport` - *What one study session did, as its summary line reports it.*

**Functions:**
- `def _wants_quit(line)` - *Whether a read line is an explicit quit or the end of the input.*
- `def _ask_grade(read_line, write_line)` - *Read grades until one is valid; None when the reader quits or ends.*
- `def _announce_empty(deck, write_line)` - *Say why no session can run: an empty deck or nothing due.*
- `def _summarize(deck, today, reviewed, passed, lapsed, write_line)` - *Close the session with its counts and what the deck waits for now.*
- `def run_session(deck, today, limit, read_line, write_line)` - *Run one bounded session over the due cards; q and end-of-input quit gracefully.*

---

### [`tests/__init__.py`](tests/__init__.py)
**Size**: `0` lines (`0` bytes)

---

### [`tests/test_cli.py`](tests/test_cli.py)
> *End-to-end tests of the command-line interface through `main`.*

**Size**: `142` lines (`5638` bytes)

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
  - Method `.test_list_shows_maturity()`
  - Method `.test_list_due_hides_cards_scheduled_for_later()`
  - Method `.test_study_runs_a_scripted_session()`
  - Method `.test_study_on_an_empty_deck()`
  - Method `.test_study_rejects_a_non_positive_limit()`
  - Method `.test_stats_renders_the_deck_summary()`
  - Method `.test_stats_after_a_session_reports_full_retention()`

---

### [`tests/test_deck.py`](tests/test_deck.py)
> *Tests of deck operations over the atomic store.*

**Size**: `78` lines (`3213` bytes)

**Classes:**
- `class DeckTests`
  - Method `.setUp()`
  - Method `.test_add_assigns_sequential_ids()`
  - Method `.test_new_card_is_due_the_day_it_is_added()`
  - Method `.test_entries_are_sorted_by_id()`
  - Method `.test_find_returns_the_card()`
  - Method `.test_find_missing_card_raises_the_triad()`
  - Method `.test_state_persists_across_instances()`
  - Method `.test_due_cards_return_only_today_and_earlier()`
  - Method `.test_record_review_updates_card_and_log()`
  - Method `.test_record_review_missing_card_raises()`

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

### [`tests/test_scheduler.py`](tests/test_scheduler.py)
> *Tests of the SM-2 scheduling functions, pinned to exact dates and values.*

**Size**: `104` lines (`4562` bytes)

**Classes:**
- `class GradeParsingTests`
  - Method `.test_grade_from_text_accepts_digits()`
  - Method `.test_grade_from_text_accepts_words_case_insensitively()`
  - Method `.test_grade_from_text_rejects_other_answers()`
- `class NextStateTests`
  - Method `.test_first_successful_review()`
  - Method `.test_second_successful_review_uses_six_days()`
  - Method `.test_third_review_multiplies_interval_by_updated_ease()`
  - Method `.test_failed_review_resets_the_streak()`
  - Method `.test_zero_grade_keeps_the_published_formula()`
  - Method `.test_ease_never_drops_below_the_floor()`
  - Method `.test_out_of_range_quality_is_refused()`
  - Method `.test_identity_fields_survive_and_input_is_untouched()`
- `class DueAndMaturityTests`
  - Method `.test_is_due_compares_iso_dates()`
  - Method `.test_maturity_splits_new_learning_and_mature()`

**Functions:**
- `def make_card(**overrides)`

---

### [`tests/test_stats.py`](tests/test_stats.py)
> *Tests of the pure deck statistics over cards, reviews and a fixed day.*

**Size**: `62` lines (`2335` bytes)

**Classes:**
- `class SummarizeTests`
  - Method `.test_counts_by_maturity_and_due()`
  - Method `.test_retention_from_the_review_log()`
  - Method `.test_retention_is_absent_without_reviews()`
  - Method `.test_forecast_covers_seven_days_from_today()`
  - Method `.test_empty_deck()`

**Functions:**
- `def make_card(card_id, **overrides)`

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

### [`tests/test_study.py`](tests/test_study.py)
> *Tests of the study session engine over scripted input and captured output.*

**Size**: `112` lines (`4615` bytes)

**Classes:**
- `class ScriptedInput` - *A read_line double that replays lines and reports EOF as None.*
  - Method `.__init__(lines)`
  - Method `.__call__()`
- `class CaptureOutput` - *A write_line double that collects every line the session prints.*
  - Method `.__init__()`
  - Method `.__call__(text)`
  - Method `.text()`
- `class SessionTests`
  - Method `.setUp()`
  - Method `.script(*lines)`
  - Method `.test_session_grades_and_schedules_every_card()`
  - Method `.test_quit_at_the_first_reveal_reviews_nothing()`
  - Method `.test_eof_quits_gracefully()`
  - Method `.test_quit_mid_session_keeps_finished_reviews()`
  - Method `.test_invalid_grade_reprompts_until_valid()`
  - Method `.test_limit_caps_the_session()`
  - Method `.test_summary_names_the_next_due_day()`
  - Method `.test_session_without_due_cards_says_so()`

---
