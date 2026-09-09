# PLAN

> Working plan for the propertea-ai coursework project. Tick the checklist as you go.
> Full reasoning behind each decision is in the sections below the checklist.

## Progress

**MVP**
- [~] 1. Scaffold, deps, settings, `/health` (1.5h) — `requirements.txt` (frontend + backend),
      `.gitignore`, `.python-version` done. No venv, no `main.py` yet.
- [~] 2. SQLAlchemy models + session + `create_all` (2h) — `backend/app/db.py` written;
      `create_all` call still lives in the not-yet-written `main.py`.
- [ ] 3. `POST /datasets/from-url` + list/get (3h)
- [ ] 4. Training pipeline, CV, artifact persistence, `POST /train` (4h)
- [ ] 5. `POST /predict` (2h)
- [ ] 6. Streamlit: ingest / datasets / train / predict pages (5h)
- [ ] 7. Tests + conftest (4h)
- [ ] 8. Neon + Render + Streamlit Cloud wiring (4h) — **freeze point, 17 Sept**
- [ ] 9. README, buffer (1.5h)
- [ ] CI: GitHub Actions running `pytest --cov` (1h)

**Nice-to-have** (only after task 8 ships a public URL)
- [ ] 10. Upload CSV via drag-and-drop (1.5h)
- [ ] 11. Delete dataset (1h)
- [ ] 12. Edit dataset (4h)
- [ ] 13. Auth: users table, bcrypt, JWT, login/register UI (5h)
- [ ] 14. Swap `X-Session-Id` for real `user_id` (1.5h)

Legend: `[ ]` not started · `[~]` in progress · `[x]` done

**Next action:** write `backend/app/ml.py`, then `schemas.py`, then `main.py`.

---


## Context

Coursework project (MAI25HA/AI1/KK1), deadline **25 Sept 17:00**. Repo is greenfield: two commits,
an empty `notebook.ipynb`, and the Kaggle Ames "House Prices" CSVs under
`exploratory-data-analysis/data/` (1460 train rows × 80 columns, `SalePrice` target).

Goal: a deployed fullstack app that ingests a dataset over HTTP, persists it, trains a sklearn
regression model on it, and serves predictions — with tests and a public URL.

Decisions already made with the user:
- Data enters via **fetch of a CSV URL** by the backend (satisfies "download via web API"; no Kaggle credentials).
- **Neon Postgres** (auto-resumes from idle; Supabase free projects pause after ~7 days and would be
  asleep on grading day).
- **Render** (FastAPI) + **Streamlit Community Cloud** (frontend) + Neon. Three free tiers, no card.
- Trained models stored as **joblib blobs in Postgres** — Render's disk is ephemeral.
- **Auth is a stretch goal**, but `owner_id` exists in the schema from day 1 so nothing is rewritten.

---

## Key design calls

**Process before or after the DB? → After. Store raw, transform at train time.**
Raw rows stay reproducible, re-doing feature engineering costs no re-download, and the stretch
"edit dataset" feature operates on raw values. All preprocessing lives *inside* the sklearn
`Pipeline`, so it is serialized with the model — no train/serve skew, and `POST /predict` needs no
duplicated transform code.

**Portable column types.** Use `sqlalchemy.JSON`, not PG-specific `JSONB`. Tests then run against
in-memory SQLite while prod runs Postgres, with one models file and no dialect branching.

**No Alembic.** `Base.metadata.create_all()` on startup. Two-week project, one developer, no
production data. *Upgrade path: add Alembic the first time you need to change a live schema.*

**One `dataset_rows` table with a JSON column**, not an 80-column Ames-specific table. Handles any
uploaded CSV, makes row edits trivial, and `pd.DataFrame([r.data for r in rows])` reconstructs the
frame in one line.

---

## Data model

```
users        id, email, password_hash, created_at            # stretch; table created day 1
datasets     id, name, source_url, target_column, n_rows,
             owner_id (nullable FK), created_at, updated_at
dataset_rows id, dataset_id (FK cascade), idx, data JSON
models       id, dataset_id (FK), algo, metrics JSON,
             artifact LargeBinary, created_at
```

Pre-auth, `owner_id` holds a UUID the Streamlit client generates into `st.session_state` and sends
as an `X-Session-Id` header. Adding auth later swaps that value for a real user id — same column,
same queries. That is the whole "separate sessions per user" nice-to-have, delivered by the MVP schema.

## Repo layout

```
backend/app/    main.py db.py ml.py schemas.py   # models live in db.py; no router package for 7 endpoints
frontend/       app.py pages/
tests/          conftest.py test_ingest.py test_ml.py test_api.py
requirements.txt          # frontend deps — Streamlit Cloud auto-detects repo root
backend/requirements.txt  # backend deps — Render build command points here
tests/requirements.txt    # pytest + pytest-cov (CI only)
.python-version           # 3.13 — Render reads this; build the local venv with it too
```

## Endpoints (MVP)

| Method | Path | Notes |
|---|---|---|
| GET | `/health` | Render health check |
| POST | `/datasets/from-url` | `{url, name, target_column}` → httpx GET, `pd.read_csv`, bulk insert |
| GET | `/datasets` | scoped by `X-Session-Id` |
| GET | `/datasets/{id}` | metadata + paginated row preview |
| POST | `/datasets/{id}/train` | `{algo}` → fit pipeline, CV, store artifact + metrics |
| GET | `/models` | filter by `dataset_id` |
| POST | `/models/{id}/predict` | `{rows: [...]}` → predictions |

## ML

- Target `log1p(SalePrice)`; report RMSE on the log scale (the Kaggle metric), inverse-transform for
  display.
- `ColumnTransformer`: numeric → `SimpleImputer(median)`; categorical →
  `SimpleImputer(most_frequent)` + `OneHotEncoder(handle_unknown="ignore")`.
  `handle_unknown="ignore"` is not optional — a category unseen in training will arrive at predict time.
- Estimator: `HistGradientBoostingRegressor` (default), `Ridge` as a second choice so the UI can
  compare two models and the `algo` column earns its existence.
- 5-fold CV, store mean/std RMSE + R² in `metrics`.
- **Do not add xgboost/lightgbm** — Render free is 512MB RAM and sklearn+pandas+numpy already
  costs ~250MB at import.

## Tests

`pytest` + `TestClient`, SQLite in-memory via `app.dependency_overrides[get_db]`. Cover the paths
that can actually lose you marks, not every line:

- ingest happy path (monkeypatched httpx, 20-row CSV fixture) → rows land in DB with right count
- ingest failures: unreachable URL, non-CSV body, missing target column → 4xx not 500
- pipeline: trains on the fixture, RMSE finite, joblib round-trips and predicts identically
- predict with an unseen category → does not raise
- predict with a missing feature column → 422
- dataset delete cascades to rows
- session scoping: session A cannot see session B's datasets

GitHub Actions running `pytest --cov` on push. Cheap, and gives a coverage number to report.

## Deploy

- **Neon** — create project, take the direct connection string (not the pooled one),
  `postgresql+psycopg://...?sslmode=require`.
- **Render** — web service, build `pip install -r backend/requirements.txt`,
  start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, env `DATABASE_URL`.
- **Streamlit Cloud** — point at `frontend/app.py`, secret `API_URL`.
- README must state that the first request after ~15 min idle takes ~50s (Render free spins down),
  so a grader hitting a cold URL doesn't record it as broken.

---

## Estimates

### MVP — 27h

| # | Task | h |
|---|---|---|
| 1 | Scaffold, deps, settings, `/health` | 1.5 |
| 2 | SQLAlchemy models + session + `create_all` | 2 |
| 3 | `POST /datasets/from-url` + list/get | 3 |
| 4 | Training pipeline, CV, artifact persistence, `POST /train` | 4 |
| 5 | `POST /predict` | 2 |
| 6 | Streamlit: ingest / datasets / train / predict pages | 5 |
| 7 | Tests + conftest | 4 |
| 8 | Neon + Render + Streamlit Cloud wiring | 4 |
| 9 | README, buffer | 1.5 |

### Nice-to-have — 13h

| # | Task | h |
|---|---|---|
| 10 | Upload CSV via drag-and-drop (`st.file_uploader` + `POST /datasets/upload`) | 1.5 |
| 11 | Delete dataset (endpoint + UI confirm) | 1 |
| 12 | Edit dataset (`st.data_editor` + bulk row `PATCH`) | 4 |
| 13 | Auth: users table, bcrypt, JWT, login/register UI | 5 |
| 14 | Swap `X-Session-Id` for real `user_id`; scope every query | 1.5 |

Edit-dataset has a trap worth 10 minutes of design: editing rows makes existing models stale.
Don't build invalidation machinery — compare `datasets.updated_at` against `models.created_at` in the
UI and show "model is older than the data" warning. One comparison, no new columns.

**CI: +1h. Total ≈ 41h.**

## Schedule (today = Tue 9 Sept)

| Dates | Work |
|---|---|
| Sep 10–12 | Tasks 1–5: backend end-to-end, ingest→train→predict working via `/docs` |
| Sep 13–15 | Tasks 6–7: Streamlit UI + test suite + CI |
| Sep 16–17 | Task 8: **deploy MVP. Hard freeze point — a working public URL exists by the 17th.** |
| Sep 18–21 | Tasks 10–14: nice-to-haves, in that order (cheapest and lowest-risk first) |
| Sep 22–23 | Tests for the new features, polish, README |
| Sep 24 | Buffer, final redeploy, verify cold-start path |
| Sep 25 | Submit |

Eight days of slack against a 41h estimate. The schedule's value is the **17 Sept freeze**: after
that date you always have something deployed to submit, and every stretch goal is genuinely optional.
If you slip, cut from the bottom of the nice-to-have table — auth (13–14) is 6.5h and the most likely
thing to eat a day on token/CORS/session debugging.

## Risks

| Risk | Mitigation |
|---|---|
| Render free 512MB OOM during training | Ames is 1460 rows — fine. Keep to sklearn; no gradient-boosting libraries |
| Render cold start looks like an outage | Document it; optionally ping `/health` from the Streamlit app on load |
| Neon idle suspend | Auto-resumes in <1s, no action needed (this is why not Supabase) |
| Kaggle CSVs need a fetchable URL | Serve them from GitHub raw in this repo — already committed |
| Streamlit Cloud can't reach the DB | It shouldn't; frontend talks only to FastAPI. Never put `DATABASE_URL` in Streamlit secrets |

## Verification

1. `pytest --cov` green locally.
2. `uvicorn app.main:app --reload` + `streamlit run frontend/app.py` against local SQLite: ingest the
   GitHub raw URL of `train.csv`, train, predict a row, check the price is plausible (~$100k–300k).
3. Repeat all of step 2 against the deployed URLs, from a browser that has never hit them, after
   letting Render idle — this is exactly what the grader will do.
4. Confirm a second browser session (different `X-Session-Id`) sees an empty dataset list.
