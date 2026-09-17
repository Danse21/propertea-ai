# propertea-ai

Ingests a CSV dataset over HTTP, persists it to Postgres, trains a scikit-learn
regression model on it, and serves predictions. See [PLAN.md](PLAN.md) for scope
and [KNOWN_ISSUES.md](KNOWN_ISSUES.md) for open problems.

## Local setup

Requires [uv](https://docs.astral.sh/uv/) and Docker.

```bash
docker compose up -d          # Postgres 17 on :5432, database "propertea"
cp .env.example .env
uv sync
cd backend && uv run uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000/docs.

Tables are created on startup by `create_all` in the FastAPI lifespan - there is
no migration step.

### If port 5432 is already taken

A native Postgres (Homebrew, Postgres.app) will hold the port. Either stop it:

```bash
brew services stop postgresql@17    # match your installed version
```

or move the container and update `DATABASE_URL` in your `.env` to match:

```yaml
ports: ["5433:5432"]
```

### Notes

- `.env` is gitignored and per-machine. Never copy someone else's - the
  credentials refer to their database, not yours.
- Use Postgres 17 locally. CI and Neon both run 17; other versions are untested.

## Git flow

Branches off `dev`:

| Prefix | Use |
|---|---|
| `feat/` | new features |
| `fix/` | bug fixes |

Branches off `main`:

| Prefix | Use |
|---|---|
| `hotfix/` | urgent fixes to released code |

Name the rest after the change: `feat/dataset-upload`, `fix/cascade-delete`.
