# Contributing

- `main`: production. Protected; merge only from `dev` via PR once CI is green. Every merge deploys.
- `dev`: integration branch.
- `feature/<name>`, `fix/<name>`: one branch per GitHub Issue, PR into `dev`.

Rules: one teammate reviews every PR; CI must pass; never commit keys, `.env`, resumes or user data;
commit messages like `feat: add notice-period filter`, `fix: handle JSearch timeout`.
Every task in docs/PLAN.md is a GitHub Issue with a label and a weekly milestone.
