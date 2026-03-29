# CODER_PROMPT.md

> Paste ONE of the task blocks below into Codex per task.
> Never give Codex more than one task at a time.
> Always run tests and coverage yourself after Codex says it is done.

---

## Prompt to paste into Codex (fill in TASK details before pasting)

```
You are the CODER agent. Your scope is [TASK-NNN] ONLY.

Before writing anything, read:
- spec.md — find the entry for [TASK-NNN]
- AGENTS.md — Coder Principles and TDD Rules sections

Files you MAY edit:
- [paste exact file paths from spec.md for this task]

YAGNI boundary for this task:
- [paste the YAGNI boundary line from spec.md]

Guiding principles — apply to every line you write:
- KISS: Write the simplest code that makes the test pass. No abstractions beyond what
  the test requires. If you feel proud of how clever it is, simplify it.
- YAGNI: Do not build anything outside the YAGNI boundary above. No extra parameters,
  no config options, no helper functions the test does not require.
- Maintainability: Functions ≤ 20 lines. One responsibility per function.
  Descriptive names. No single-letter variables outside list comprehensions.

TDD — follow this exact order and show output at each step:

STEP 1 — RED:
Write the test in [test file path] based on the TDD note in spec.md.
Run: pytest [test file path] -v
Show the raw failing output. Do not proceed until you have shown a failure.

STEP 2 — GREEN:
Write the minimum implementation in [source file path] to make the test pass.
Run: pytest [test file path] -v
Show the raw passing output.

STEP 3 — REFACTOR:
Apply KISS, YAGNI, and maintainability rules.
Check: is every function ≤ 20 lines? Does each do exactly one thing?
Is there any code that exists beyond what the test requires? Remove it.
Run: pytest [test file path] -v
Show the raw output confirming still green.

STEP 4 — COVERAGE:
Run: pytest --cov=src --cov-report=term-missing tests/
Show the full coverage output.
If any file touched in this task is below 90%, write additional tests and repeat
from STEP 2. Do not call the task done until coverage is ≥ 90%.

STEP 5 — LINT:
Run: ruff check .
Show output. Fix any errors before calling done.

When all steps pass, output exactly:
TASK-[NNN] COMPLETE
Coverage: [X]%
Tests: [N] passing
Principles check: KISS ✓ | YAGNI ✓ | Maintainability ✓
```

---

## After Codex responds — run this yourself

```bash
pytest --cov=src --cov-report=term-missing tests/
ruff check .
mypy src/

# If all pass — stage only task-scoped files
git add -p
git commit -m "coder: TASK-NNN — short description"
```

Then mark the task done in spec.md:
```
- [x] TASK-NNN: ...
```

---

## If tests or coverage fail — paste this back to Codex

```
TASK-[NNN] is not complete. Raw output below.
Fix only this issue. Do not touch files outside the original task scope.
Do not add abstractions or helpers beyond what the fix requires.

[paste full raw output here]
```

---

## Loop limit

If you are on your 3rd loop for the same task, STOP.
1. Note the failure in JUDGE_REPORT.md
2. Return to Planner — the task spec needs more detail
3. Add a sub-task (e.g. TASK-002a) to spec.md before retrying

---

## Quick reference — commands

```bash
# Run tests
pytest tests/ -v

# Run with coverage
pytest --cov=src --cov-report=term-missing tests/

# Lint
ruff check .

# Type check
mypy src/
```

## pyproject.toml coverage threshold (must be set)

```toml
[tool.coverage.report]
fail_under = 90
show_missing = true
```
