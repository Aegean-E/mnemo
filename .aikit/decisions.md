# Decisions

Why this project is built the way it is, oldest first. One entry per decision that changes a
contract, a dependency, a data format or the architecture; IDs are consecutive and never reused.

### ADR-001: One JSON deck file with cards, a review log and atomic, locked writes
- **Date**: 2026-10-21
- **Status**: Accepted
- **Context**: A spaced-repetition tool lives or dies with its state: the schedule is the
  program, and losing a deck loses weeks of memory work. There must be no database dependency
  and no cloud, and the whole state must stay inspectable by hand.
- **Decision**: Store everything in one JSON document
  (`{"version": 1, "cards": [...], "reviews": [...]}`). Each card carries its full SM-2 state
  (`ease`, `interval_days`, `repetitions`, `lapses`, `due`), with `ease` floored at 1.3 and
  every date a strict `YYYY-MM-DD` string. The `reviews` list is the append-only log of graded
  answers (`card_id`, `date`, `quality` 0-5) that later statistics are computed from. Each save
  copies the current file to `.bak`, writes a unique temporary file, fsyncs it, then replaces
  the deck; each read-modify-write holds `<deck>.lock` for at most 3 seconds, and a lock older
  than 30 seconds is broken. Malformed JSON is quarantined and recovered from `.bak`; an
  unknown `version` is refused in place. Card ids are one past the highest remaining id, so
  removing the newest card frees its id.
- **Consequences**: The deck is easy to inspect, back up and edit by hand, and a crash can lose
  at most the single write in flight. The whole deck is held in memory per command, which is
  fine at personal-study scale but would need a different store for shared or huge decks. The
  review log grows without bound, so a later decision will have to bound it if decks run for
  years.

