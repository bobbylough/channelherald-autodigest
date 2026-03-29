# PLANNER_PROMPT.md

> Paste the block below into Codex to run the Planner agent.
> Do this ONCE at the start of the session, before any code is written.
> The Planner reads AGENTS.md only — do not give it source files.

---

## Prompt to paste into Codex

```
You are the PLANNER agent. Read AGENTS.md in this repository.

Your ONLY output is a completed spec.md file.

Rules:
- Do NOT write any implementation code
- Do NOT write any test code
- Do NOT modify any existing source files

Your job:
1. Read AGENTS.md — understand the project goal, tech stack, and constraints
2. Break the goal into atomic tasks, each:
   - Independently testable
   - Completable in under 45 minutes
   - Small enough that KISS and YAGNI are easy to honour
3. For each task specify:
   - Exact file paths the Coder may touch (no others)
   - The test file path
   - A one-sentence acceptance criterion
   - A TDD note: what the failing test should assert BEFORE any implementation
   - A YAGNI boundary: explicitly state what is out of scope for this task

Output format: Fill in spec.md exactly as templated. Do not add new sections.

When done output exactly: PLANNER COMPLETE — spec.md is ready for review.
```

---

## After Codex responds

1. Read spec.md yourself — do not skip this
2. Trim any task that is not truly atomic (split it further)
3. Check every task has a test file path, TDD note, and YAGNI boundary
4. Resolve any Open Questions before handing to Coder
5. Commit as the harness anchor:

```bash
git add spec.md AGENTS.md
git commit -m "harness: planner complete — spec.md ready"
git tag harness-baseline
```
