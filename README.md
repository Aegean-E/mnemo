# mnemo

[![Built with AIKit](https://img.shields.io/badge/built%20with-AIKit-6f42c1)](https://github.com/Aegean-E/AIKit)

A dependency-free, local-first spaced-repetition flashcard CLI. Add what you want to remember,
study it on the days the SM-2 algorithm says it is due, and watch the schedule stretch as you
recall and compress it when you forget. Everything stays in one readable JSON file on your
machine.

## ⚡ 30-Second Cold-Start Quick Reference

- **Runtime Prerequisites**: Python 3.10 or newer (standard library only; no third-party packages)
- **Canonical Regression Shield Gate**:
  ```bash
  python -m unittest discover
  ```
- **Try it now** (under 10 seconds, from this folder):
  ```bash
  python -m mnemo add "What is SM-2?" --back "a spaced-repetition scheduling algorithm"
  python -m mnemo add "Ease factor floor?" --back "1.3"
  python -m mnemo list
  python -m mnemo study
  ```
  In the session, press Enter to reveal each answer, then grade it with `4` (or `good`).

### 🛠️ AIKit Commands (run from the AIKit folder)

| Role | Command |
|---|---|
| Status, task and gates | `python aikit.py status mnemo` |
| Phase 4: every gate | `python aikit.py check mnemo` |
| Repair memory and map, then check | `python aikit.py fix mnemo` |
| Resume an interrupted task | `python aikit.py resume mnemo` |

## 💡 How It Works

- **One deck file.** `mnemo.json` (or `--db <path>`) holds `{"version": 1, "cards": [...],
  "reviews": [...]}`: every card with its full SM-2 state, and a log of graded answers.
- **Cards are due the day they are added.** A new card starts at ease 2.5 with no interval, so
  `study` can pick it up immediately.
- **Scheduling is the published SM-2, unchanged.** Each answer is graded 0-5 (or
  again/hard/good/easy); the ease factor moves by the published formula, floored at 1.3, the
  interval grows 1, 6, then interval x ease, and a grade below 3 resets the streak to a 1-day
  interval. Every date is injected, so the schedule is deterministic and replayable.
- **Stable ids.** `list` shows each id, and later commands address cards by it. A new id is one
  past the highest remaining id, so removing the newest card frees that id for the next one.
- **Crash-safe writes.** Each save keeps a `.bak`, writes a temporary file, fsyncs it, then
  replaces the deck atomically. A transient Windows sharing violation is retried; any other
  replace failure is reported at once. A failed backup or directory fsync prints a warning. A
  malformed file is quarantined and the last backup is restored into place, so the next command
  still sees the deck.
- **One writer at a time.** Read-modify-write operations hold an advisory `.lock` with a 3-second
  wait; a lock older than 30 seconds is broken.
- **Sessions are line-driven.** `study` walks the due queue: question, Enter to reveal, answer,
  grade. An invalid grade is re-asked, `q` or the end of input quits without losing finished
  reviews, and each answer is committed atomically with its log entry. The same flow runs from a
  terminal and from a pipe, so sessions can be scripted.
- **Stats read the log, not guesses.** `stats` reports counts by maturity (new, learning,
  mature), how many cards are due today, retention as the share of logged grades at or above 3,
  and how many cards fall due on each of the next seven days.
- **Decks partition the file, not the machine.** `--deck` narrows `list`, `study` and `stats` to
  one label; `edit` can move a card between decks. The review log is append-only, so removing a
  card keeps its history in the retention numbers.
- **UTF-8 everywhere.** The deck file is always UTF-8, and the CLI reconfigures its output
  streams to UTF-8 with replacement, so non-Latin scripts print instead of crashing on legacy
  consoles.
- **Clear failures.** Every user error prints `Error:`, `Why:` and `Fix:`, and exits 1.

### Commands

```text
python -m mnemo [--db PATH] add FRONT --back TEXT [--deck NAME]
python -m mnemo [--db PATH] list [--due] [--deck NAME]
python -m mnemo [--db PATH] study [--limit N] [--deck NAME]
python -m mnemo [--db PATH] stats [--deck NAME]
python -m mnemo [--db PATH] edit ID [--front TEXT] [--back TEXT] [--deck NAME]
python -m mnemo [--db PATH] remove ID
```

## 📦 What's Inside

```text
mnemo/
├── .aikit/                   <- this project's memory: record, ledger, decisions, map
├── .gitignore                <- transient AIKit state and local decks excluded
├── LICENSE
├── README.md
├── COMMERCIAL.md
├── pyproject.toml            <- package metadata and the `mnemo` console script
├── mnemo/
│   ├── __init__.py
│   ├── __main__.py           <- `python -m mnemo`
│   ├── cli.py                <- argument parsing and command output
│   ├── deck.py               <- add, find and list operations
│   ├── errors.py             <- the Error/Why/Fix triad
│   ├── models.py             <- Card and Review value objects and parsing rules
│   ├── scheduler.py          <- the SM-2 functions: grade, next state, due, maturity
│   ├── stats.py              <- pure deck counts, retention and 7-day forecast
│   ├── storage.py            <- atomic JSON store, backup, lock and recovery
│   └── study.py              <- the guided review session engine
└── tests/
    ├── __init__.py
    ├── test_cli.py
    ├── test_deck.py
    ├── test_models.py
    ├── test_scheduler.py
    ├── test_stats.py
    ├── test_storage.py
    └── test_study.py
```

## 📚 Design Notes

The on-disk schema, the crash-safety envelope and the id policy are recorded in
`.aikit/decisions.md` (ADR-001); the scheduling contract in ADR-002; the session input/output
contract in ADR-003; the statistics definitions in ADR-004; card management in ADR-005;
corrupt-deck recovery in ADR-006.
