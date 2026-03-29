# AGENTS.md — Harness Manifest

## Project Goal

The digest has one job: surface 5–7 stories per day that are genuinely worth
reading — surprising, intellectually stimulating, or consequential to someone
who thinks about technology and business for a living.

## Definition of Done

- [ ] All tests pass (`pytest tests/`)
- [ ] Coverage is at or above 90% (`pytest --cov=src --cov-report=term-missing tests/`)
- [ ] No linter errors (`ruff check .`)
- [ ] No type errors (`mypy src/`)
- [ ] spec.md checklist is fully checked off
- [ ] JUDGE_REPORT.md shows all tasks as PASS with no flagged violations

## Tech Stack

- Language: Python 3.11+
- Test runner: pytest
- Coverage: pytest-cov (fail_under = 90 enforced in pyproject.toml)
- Linter: ruff
- Type checker: mypy

## Agent Boundaries

### PLANNER (Codex)

- Reads: AGENTS.md only — no source files, no tests
- Writes: spec.md
- Must NOT write any implementation or test code
- Output: spec.md with atomic task checklist

### CODER (Codex)

- Reads: spec.md + only the files listed in the current task
- Writes: test file first, then implementation (TDD — see rules below)
- Must NOT touch files outside the task's listed scope
- Must NOT call a task done until coverage is ≥ 90%
- One task per session — no batching

### JUDGE (Claude Code)

- Reads: spec.md + git diff since harness-baseline + test/coverage output
- Writes: JUDGE_REPORT.md
- Must NOT write any implementation or test code
- Verdicts: PASS, FAIL, or DRIFT — plus flags for principle violations

## Coder Principles (apply to every line written)

### KISS — Keep It Simple

- Write the simplest code that makes the test pass
- No clever abstractions, no design patterns unless the test demands it
- If you feel proud of how elegant it is, that is a warning sign — simplify it

### YAGNI — You Aren't Gonna Need It

- Do not build anything not required by the current task
- No "we will need this later" parameters, config options, or extension points
- If the test does not require it, do not write it

### Maintainability

- Functions must be 20 lines or fewer
- Each function does exactly one thing
- Descriptive names — no single-letter variables outside list comprehensions
- If you feel the urge to create a helper or abstraction, ask: does the test require it?
  If no, do not create it

## Coder TDD Rules (Red → Green → Refactor)

1. RED: Write the failing test first. Run it. Show the raw failing output before proceeding.
2. GREEN: Write the minimum implementation to make the test pass. Run it. Show passing output.
3. REFACTOR: Clean up using KISS, YAGNI, and maintainability rules. Re-run. Still green.
4. COVERAGE: Run `pytest --cov=src --cov-report=term-missing tests/`. Must be ≥ 90%.
   If below 90%, write additional tests and repeat from step 2.
5. Do not proceed to the next task until all four steps are done and shown.

## Loop Rules

- One task per Codex prompt — no batching
- On failure, paste raw stdout/stderr — do not describe or summarise the error
- If a task loops more than 3 times, stop and revise spec.md before retrying
- DRIFT means files were touched outside task scope — return to Coder with a correction note
- Judge always runs cold at the start of a new day (fresh session, no prior context)
