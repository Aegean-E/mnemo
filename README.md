# mnemo

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
  ```

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
- **Stable ids.** `list` shows each id, and later commands address cards by it. A new id is one
  past the highest remaining id, so removing the newest card frees that id for the next one.
- **Crash-safe writes.** Each save keeps a `.bak`, writes a temporary file, fsyncs it, then
  replaces the deck atomically. A transient Windows sharing violation is retried; any other
  replace failure is reported at once. A failed backup or directory fsync prints a warning. A
  malformed file is quarantined and the backup is restored.
- **One writer at a time.** Read-modify-write operations hold an advisory `.lock` with a 3-second
  wait; a lock older than 30 seconds is broken.
- **Clear failures.** Every user error prints `Error:`, `Why:` and `Fix:`, and exits 1.

### Commands

```text
python -m mnemo [--db PATH] add FRONT --back TEXT [--deck NAME]
python -m mnemo [--db PATH] list
```

## 📦 What's Inside

```text
mnemo/
├── .aikit/                   <- this project's memory: record, ledger, decisions, map
├── .gitignore                <- transient AIKit state and local decks excluded
├── LICENSE
├── README.md
├── pyproject.toml            <- package metadata and the `mnemo` console script
├── mnemo/
│   ├── __init__.py
│   ├── __main__.py           <- `python -m mnemo`
│   ├── cli.py                <- argument parsing and command output
│   ├── deck.py               <- add, find and list operations
│   ├── errors.py             <- the Error/Why/Fix triad
│   ├── models.py             <- Card and Review value objects and parsing rules
│   └── storage.py            <- atomic JSON store, backup, lock and recovery
└── tests/
    ├── __init__.py
    ├── test_cli.py
    ├── test_deck.py
    ├── test_models.py
    └── test_storage.py
```

## 📚 Design Notes

The on-disk schema, the crash-safety envelope and the id policy are recorded in
`.aikit/decisions.md` (ADR-001).
