# propertea-ai

House-price prediction as a small full-stack app. Upload a CSV (or fetch one by
URL), store it in Postgres, explore it, train a scikit-learn regression model on
it and ask the model for a price.

- **Backend** - FastAPI + SQLAlchemy, in [backend/app/](backend/app/)
- **Frontend** - Streamlit, in [frontend/](frontend/). Talks to the backend over HTTP only.
- **Database** - Postgres 17 (Docker locally, Neon when deployed)

Design notes and the course report: [TECHNICAL_REPORT.md](TECHNICAL_REPORT.md).
Original plan: [PLAN.md](PLAN.md). Open problems: [KNOWN_ISSUES.md](KNOWN_ISSUES.md).

## Requirements

- [uv](https://docs.astral.sh/uv/) - installs Python 3.13 and all dependencies
- Docker - for the local Postgres

## Run it locally

```bash
docker compose up -d          # Postgres 17 on :5432, database "propertea"
cp .env.example .env
uv sync                       # runtime + dev deps (Streamlit is in the dev group)
```

Then start the backend and the frontend in two terminals. Both must be running.

**Terminal 1** - backend:

```bash
cd backend && uv run uvicorn app.main:app --reload
```

API docs at http://127.0.0.1:8000/docs.

**Terminal 2** - frontend (from the repo root):

```bash
uv run streamlit run frontend/app.py
```

App at http://localhost:8501.

Tables are created on backend startup by `create_all` in the FastAPI lifespan,
followed by a few idempotent `ALTER TABLE` statements (`MIGRATIONS` in
[backend/app/main.py](backend/app/main.py)). There is no separate migration step.

### First run

1. Create an account on the sign-in screen (username 3+ chars, password 8+ chars).
2. **Datasets -> Upload dataset**. Upload
   [exploratory-data-analysis/data/train.csv](exploratory-data-analysis/data/train.csv)
   (Kaggle Ames House Prices) with target column `SalePrice`.
3. **Explore** shows the target distribution, missingness and correlations.
4. **Train** - pick an algorithm and train. Each run is saved; train several to compare.
5. **Predict** - describe a house and get an estimated price.

Explore, Train and Predict need an Ames-shaped dataset (all Ames feature columns
plus `SalePrice`). Any other CSV opens in **Prepare**, where you can trim, rename,
reorder, cast, impute and filter columns, then save the result as a new dataset.

### Environment variables

| Variable       | Used by  | Default                                             |
| -------------- | -------- | --------------------------------------------------- |
| `DATABASE_URL` | backend  | required; `.env.example` points at the Docker DB    |
| `BACKEND_URL`  | frontend | `http://localhost:8000`                             |

`.env` is gitignored and per-machine. Never copy someone else's - the
credentials refer to their database, not yours.

### If port 5432 is already taken

A native Postgres (Homebrew, Postgres.app) will hold the port. Either stop it:

```bash
brew services stop postgresql@17    # match your installed version
```

or move the container and update `DATABASE_URL` in your `.env` to match:

```yaml
ports: ["5433:5432"]
```

Use Postgres 17 locally. CI and Neon both run 17; other versions are untested.

## Tests

```bash
uv run pytest            # in-memory SQLite, no Docker needed
uv run pytest --cov      # same, with coverage
```

CI ([.github/workflows/ci.yml](.github/workflows/ci.yml)) runs the same suite
against a Postgres 17 service container on every push and PR to `main`. To do
that locally, point `DATABASE_URL` at a **separate** database - the fixtures
drop every table after each test:

```bash
docker compose exec db createdb -U postgres propertea_test
DATABASE_URL=postgresql://postgres:dev@localhost:5432/propertea_test uv run pytest
```

## API

All routes except `/health`, `/algorithms` and `/auth/*` need the
`X-Session-Id` header with the token returned by register/login.

| Method | Path                         | Does                                   |
| ------ | ---------------------------- | -------------------------------------- |
| GET    | `/health`                    | liveness check                         |
| POST   | `/auth/register`             | create account, returns token          |
| POST   | `/auth/login`                | returns a fresh token                  |
| POST   | `/auth/logout`               | invalidates the token                  |
| POST   | `/datasets/upload`           | multipart CSV upload (max 10 MB)       |
| POST   | `/datasets/from-url`         | backend downloads a CSV by URL         |
| GET    | `/datasets`                  | your datasets                          |
| GET    | `/datasets/{id}`             | metadata + paginated rows              |
| GET    | `/algorithms`                | trainable algorithm names              |
| POST   | `/datasets/{id}/train`       | train, store model + metrics           |
| GET    | `/datasets/{id}/models`      | models trained on a dataset            |
| POST   | `/models/{id}/predict`       | price for one house                    |

## Project layout

```
backend/app/
  main.py            FastAPI app, startup schema setup
  db.py models.py    engine/session, ORM tables
  auth.py            bcrypt hashing, token lookup
  routers/           auth, datasets, models (train/predict)
  services/          preprocessing.py (Ames), modeling.py (pipeline + training)
frontend/
  app.py             entry point, sidebar navigation
  api_client.py      every HTTP call to the backend
  views/             one module per page
  prep_ops.py        pure pandas operations behind the Prepare page
  eda_service.py     plotting and EDA helpers
tests/               pytest suite (API, services, frontend helpers)
exploratory-data-analysis/
                     EDA notebooks (Ames, King County, Realtor) and raw CSVs
```

## Deployment

- **Frontend** - Streamlit Community Cloud, entry point `frontend/app.py`.
  It installs [frontend/requirements.txt](frontend/requirements.txt), so a new
  frontend import must be added there as well as to `pyproject.toml`. Set
  `BACKEND_URL` in the app's secrets.
- **Backend** - any host that runs
  `uvicorn app.main:app --host 0.0.0.0 --port $PORT` from `backend/`, with
  `DATABASE_URL` set to the Neon connection string.

## Git flow

Branch off `main` and open a PR back into `main`. CI must pass before merging.

| Prefix    | Use          |
| --------- | ------------ |
| `feat/`   | new features |
| `fix/`    | bug fixes    |
| `chore/`  | cleanup, config, docs |

Name the rest after the change: `feat/dataset-upload`, `fix/cascade-delete`.
