# Working on Tradeforge

## Git workflow

- Never commit directly to `main`. Before starting any new piece of work, create a new feature branch off an up-to-date `main` (`git checkout main && git pull --ff-only && git checkout -b <type>/<name>`).
- If reworking a branch that hasn't been merged yet, push fixes to that same branch. Only start a new branch for a rework if explicitly told to, or if the existing branch's PR would otherwise be silently overwritten with an incompatible design.
- Before pushing, sanity-check the diff (`git diff origin/main HEAD --stat` or `--summary`) for unintended file drops.
- When a feature/PR-sized piece of work is complete and pushed, write the PR title + description directly in chat — do not assume the PR should be opened automatically. Match the established style (see PR #8 on GitHub as the reference example):
  - `## Summary` — one paragraph on what changed and why
  - `## What's included` — bold subsection headers, bullet points underneath
  - `## Test plan` — what was actually verified (lint/build/migrations/manual testing), plainly stated, not padded
  - `## Known limitations` — anything genuinely not done (no automated tests, not browser-verified, etc.)
  - No "Generated with Claude Code" footer or similar attribution line.
- Only actually run `gh pr create` if the GitHub CLI is authenticated and available — otherwise give the compare-branch URL plus the description text for the user to paste in.

## Verification before calling something done

- Backend: run `ruff check .`, the import smoke check (`python -c "from app.main import app"`), and apply all Alembic migrations from scratch against a genuinely fresh throwaway Postgres container (not the already-migrated dev DB).
- Frontend: run `tsc --noEmit`, lint, and `next build` inside an isolated container (never inside the live `next dev` container — it corrupts the shared `.next` directory).
