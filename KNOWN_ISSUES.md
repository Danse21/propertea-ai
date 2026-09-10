# Known issues

> Problems found in propertea-ai that are understood but not yet fixed. Each entry states the
> problem, its impact, and the recommended solution. Referenced from `PLAN.md`.

## KI-1 — SQLite test dialect does not enforce foreign keys

**Problem.** Tests are planned against in-memory SQLite (see *Key design calls* in `PLAN.md`) while prod runs
Neon Postgres. SQLite ships `PRAGMA foreign_keys=OFF`, so the `ondelete="CASCADE"` on
`dataset_rows.dataset_id` is inert there. Combined with `passive_deletes=True` on the relationship,
deleting a `Dataset` whose `rows` collection was never loaded leaves the child rows behind —
verified locally, 3 of 3 rows survived. If the collection *was* loaded in the same session, the
Python-side cascade deletes them and the bug is invisible.

So the planned test *"dataset delete cascades to rows"* passes or fails on incidental session state,
not on whether cascade works. Prod is unaffected — Postgres enforces the constraint.

**Impact.** A green suite says nothing about the behaviour it claims to cover. The same blind spot
applies to every other Postgres-only guarantee the code leans on: FK enforcement, constraint
violations surfacing as 4xx rather than silent success, and any dialect difference in `JSON`
handling. The test suite is measuring a database we do not ship.

**Recommended solution — run CI against real Postgres.** Upgrade the `PLAN.md` checklist item
"CI: GitHub Actions running `pytest --cov`" to use a Postgres service container, and point the test
session at it instead of SQLite:

```yaml
# .github/workflows/ci.yml
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:17
        env:
          POSTGRES_PASSWORD: postgres
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready --health-interval 10s
          --health-timeout 5s --health-retries 5
    env:
      DATABASE_URL: postgresql://postgres:postgres@localhost:5432/postgres
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync --dev
      - run: uv run pytest --cov
```

`conftest.py` then drops the SQLite engine, builds the schema once per session with
`create_all`/`drop_all`, and isolates tests by rolling back a transaction per test. Same dialect as
Neon, no Neon credentials in CI, no network dependency beyond the runner.

Cost: CI item grows from 1h to ~1.5h, suite gets slower than in-memory SQLite. Worth it — it
retires the whole dialect-mismatch class, not just this one symptom.

**Until CI lands.** Do not trust the cascade test. Either skip it or run the suite locally against a
Docker Postgres.
