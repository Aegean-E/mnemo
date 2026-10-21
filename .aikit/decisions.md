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

### ADR-002: The published SM-2 algorithm, date-injected and unmodified
- **Date**: 2026-10-21
- **Status**: Accepted
- **Context**: Scheduling is the heart of the tool, and every variant of SM-2 that "improves" it
  invents parameters nobody can verify. The tests must also pin exact dates without waiting for
  calendar time to pass.
- **Decision**: Implement the SM-2 algorithm exactly as published: grades 0-5, ease updated by
  `EF' = EF + (0.1 - q*(0.08 + q*0.02))` on every answer and floored at 1.3, intervals 1, 6,
  then `round(interval * EF')`, and any grade below 3 resets repetitions and sets a 1-day
  interval while counting a lapse. The words again=1, hard=3, good=4, easy=5 also grade an
  answer. Every function takes the current day as an explicit argument; no function reads the
  clock. Maturity labels: new (never answered), learning (interval under 21 days), mature.
- **Consequences**: The schedule is byte-for-byte reproducible from the deck file and unit tests
  pin exact due dates. Fidelity keeps the published formula's known quirk that a grade of 0
  raises the ease by 0.1; it is floored but otherwise left alone, and a test pins it so the
  behaviour is a decision, not a bug. Cards graded 4 every time grind their ease down to the
  1.3   floor, exactly as the published algorithm does.

### ADR-003: Study sessions are line-driven with injected input and output
- **Date**: 2026-10-21
- **Status**: Accepted
- **Context**: A study session is the one interactive surface of the tool, and it must behave
  identically for a person at a terminal, for a pipe, and under test. Interrupting a session
  must never lose the answers already graded, and the engine must not touch `sys.stdin` or
  `print` itself to stay testable without subprocesses.
- **Decision**: The session engine takes `read_line` and `write_line` callables and the current
  day as arguments. A line is either `q` (quit) or end-of-input (quit) or an answer; an invalid
  grade is re-asked with a hint, never fatal. Each graded answer is committed in one locked
  read-modify-write that stores the card's next SM-2 state and appends the review log entry.
  Sessions are bounded by `--limit` (default 20) and end with a summary of counts and the next
  due day. The CLI wires `input` (EOF becomes end-of-input) and `print`, so terminal and pipe
  run the same flow.
- **Consequences**: Sessions are unit-testable with scripted line lists and captured output, and
  a piped script (answer-per-line) drives a full session for dogfooding. A quit mid-session
  leaves finished reviews committed and the rest of the queue due today. Very long piped input
  cannot loop forever: end-of-input ends the session at the next read.

### ADR-004: Statistics are defined over the whole review log, purely
- **Date**: 2026-10-21
- **Status**: Accepted
- **Context**: A spaced-repetition tool invites invented metrics (daily streaks, "true
  retention", workload scores) whose definitions drift with mood. Every number `stats` prints
  must have one definition a test can pin, computed without side effects.
- **Decision**: `summarize(cards, reviews, today)` is a pure function returning a frozen
  `DeckStats`. Definitions: due today = cards whose due day is `today` or earlier; maturity is
  new (no repetitions), learning (interval under 21 days), mature (interval at least 21 days);
  retention = the share of logged reviews graded 3 or higher, absent when nothing is logged;
  forecast = for each of the next seven days including today, the count of cards due exactly
  that day.
- **Consequences**: The command's output is fully determined by the deck file and the day, so a
  test pins it exactly. Overdue cards count toward due today but toward no forecast day, so a
  neglected deck shows its backlog in one number. Retention over the whole log moves slowly;
  windowed retention is deliberately not invented here.


